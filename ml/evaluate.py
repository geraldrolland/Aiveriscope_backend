"""Evaluate the trained model on the held-out test set and print metrics."""
import pickle
from pathlib import Path

import pandas as pd
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix

from backend.ml.preprocess import clean_text

REPO_ROOT = Path(__file__).resolve().parents[1]
MODELS_DIR = REPO_ROOT / "models"
DATA_DIR = Path(__file__).resolve().parent / "data"
TEST_FILE = DATA_DIR / "test.csv"
MAX_LEN = 50


def main() -> None:
    from keras.models import load_model
    from keras.preprocessing.sequence import pad_sequences

    if not TEST_FILE.exists():
        raise SystemExit("Test set missing. Run: python ml/train.py")

    model = load_model(str(MODELS_DIR / "CS_model.keras"))
    with open(MODELS_DIR / "tokenizer.pkl", "rb") as f:
        tokenizer = pickle.load(f)

    test = pd.read_csv(TEST_FILE)
    cleaned = test["headline"].map(clean_text)
    seq = tokenizer.texts_to_sequences(cleaned)
    padded = pad_sequences(seq, maxlen=MAX_LEN, padding="post", truncating="post")

    probs = model.predict(padded, verbose=0).ravel()
    predictions = (probs > 0.5).astype(int)

    print(f"Accuracy: {accuracy_score(test['is_fake'], predictions):.4f}")
    print(classification_report(test["is_fake"], predictions, target_names=["Real", "Fake"]))
    print("Confusion matrix (rows=actual, cols=predicted):")
    print(confusion_matrix(test["is_fake"], predictions))


if __name__ == "__main__":
    main()
