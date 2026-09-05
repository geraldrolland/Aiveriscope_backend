"""Train a headline-level fake-news classifier (Embedding + BiLSTM).

Usage:
    python download_data.py     # once, fetches the WELFake dataset
    python train.py --field title
"""
import argparse
import pickle
from pathlib import Path

import nltk
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

from backend.ml.preprocess import clean_text

REPO_ROOT = Path(__file__).resolve().parents[1]
MODELS_DIR = REPO_ROOT / "models"
DATA_DIR = Path(__file__).resolve().parent / "data"
DATA_FILE = DATA_DIR / "WELFake.parquet"
TEST_OUTPUT = DATA_DIR / "test.csv"

MAX_LEN = 50
MAX_WORDS = 20000


def load_frame() -> pd.DataFrame:
    if not DATA_FILE.exists():
        raise SystemExit("Dataset missing. Run: python ml/download_data.py")
    df = pd.read_parquet(DATA_FILE)
    if "label" not in df.columns:
        raise SystemExit("Dataset has no 'label' column; expected WELFake format")

    text_col = "title" if "title" in df.columns else "text"
    if "title" in df.columns and "text" in df.columns:
        text_col = "title"

    frame = pd.DataFrame(
        {"headline": df[text_col], "is_fake": df["label"].astype(int)}
    )
    frame = frame.dropna(subset=["headline"])

    # WELFake semantics: 0 = fake, 1 = real -> flip to is_fake (1 = fake)
    frame["is_fake"] = 1 - frame["is_fake"]
    frame["headline"] = frame["headline"].astype(str)
    return frame


def build_model(vocab_size: int, max_len: int):
    from keras.layers import Bidirectional, Dense, Embedding, Input, LSTM, SpatialDropout1D
    from keras.models import Model

    inputs = Input(shape=(max_len,))
    x = Embedding(input_dim=vocab_size, output_dim=100)(inputs)
    x = SpatialDropout1D(0.2)(x)
    x = Bidirectional(LSTM(64, dropout=0.2, recurrent_dropout=0.2))(x)
    outputs = Dense(1, activation="sigmoid")(x)
    model = Model(inputs, outputs)
    model.compile(optimizer="adam", loss="binary_crossentropy", metrics=["accuracy"])
    return model


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--epochs", type=int, default=10)
    parser.add_argument("--batch-size", type=int, default=256)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    for resource in ("punkt", "stopwords", "wordnet", "punkt_tab"):
        try:
            nltk.download(resource, quiet=True)
        except Exception:
            pass

    frame = load_frame()
    frame = frame.dropna()
    frame = frame[frame["headline"].str.strip().astype(bool)]
    frame["clean"] = frame["headline"].map(clean_text)
    frame = frame[frame["clean"].str.strip().astype(bool)].reset_index(drop=True)
    print(f"Loaded {len(frame)} samples; fake={int(frame['is_fake'].sum())} real={int((1 - frame['is_fake']).sum())}")

    train, rest = train_test_split(
        frame, test_size=0.2, stratify=frame["is_fake"], random_state=args.seed
    )
    val, test = train_test_split(
        rest, test_size=0.5, stratify=rest["is_fake"], random_state=args.seed
    )

    from tensorflow.keras.preprocessing.text import Tokenizer

    tokenizer = Tokenizer(num_words=MAX_WORDS, oov_token="<OOV>")
    tokenizer.fit_on_texts(train["clean"])
    vocab_size = min(len(tokenizer.word_index) + 1, MAX_WORDS + 1)
    print(f"Vocabulary size: {vocab_size}")

    from keras.preprocessing.sequence import pad_sequences

    def to_sequences(texts: pd.Series) -> np.ndarray:
        seq = tokenizer.texts_to_sequences(texts)
        return pad_sequences(seq, maxlen=MAX_LEN, padding="post", truncating="post")

    x_train, y_train = to_sequences(train["clean"]), train["is_fake"].to_numpy()
    x_val, y_val = to_sequences(val["clean"]), val["is_fake"].to_numpy()
    x_test, y_test = to_sequences(test["clean"]), test["is_fake"].to_numpy()

    model = build_model(vocab_size, MAX_LEN)
    model.summary()

    from keras.callbacks import EarlyStopping, ModelCheckpoint

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    model_path = MODELS_DIR / "CS_model.keras"
    callbacks = [
        EarlyStopping(monitor="val_accuracy", patience=3, restore_best_weights=True, mode="max"),
        ModelCheckpoint(str(model_path), monitor="val_accuracy", save_best_only=True, mode="max"),
    ]

    model.fit(
        x_train,
        y_train,
        validation_data=(x_val, y_val),
        epochs=args.epochs,
        batch_size=args.batch_size,
        callbacks=callbacks,
        verbose=1,
    )

    with open(MODELS_DIR / "tokenizer.pkl", "wb") as f:
        pickle.dump(tokenizer, f)

    test.to_csv(TEST_OUTPUT, index=False)
    print(f"\nSaved model to {model_path}")
    print(f"Saved tokenizer to {MODELS_DIR / 'tokenizer.pkl'}")
    print(f"Saved test set to {TEST_OUTPUT}")

    test_loss, test_acc = model.evaluate(x_test, y_test, verbose=0)
    print(f"Test accuracy: {test_acc:.4f}")


if __name__ == "__main__":
    main()
