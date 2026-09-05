"""Lazy-loaded Keras model and tokenizer for headline classification."""
import pickle

from ..config import settings
from .preprocess import clean_text

_model = None
_tokenizer = None


def load():
    """Load the model and tokenizer on first use; reuse afterwards."""
    global _model, _tokenizer
    if _model is None:
        from keras.models import load_model

        _model = load_model(str(settings.model_path))
        with open(settings.tokenizer_path, "rb") as f:
            _tokenizer = pickle.load(f)
    return _model, _tokenizer


def predict(text: str) -> tuple[str, float]:
    """Classify a single headline.

    Returns a (trusted, confidence) tuple where trusted is "Real" or "Fake"
    and confidence is the probability of the predicted class (0.5-1.0).
    """
    model, tokenizer = load()

    from keras.preprocessing.sequence import pad_sequences

    cleaned = clean_text(text)
    seq = tokenizer.texts_to_sequences([cleaned])
    padded = pad_sequences(
        seq, maxlen=settings.max_len, padding="post", truncating="post"
    )
    score = float(model.predict(padded, verbose=0)[0][0])
    trusted = "Fake" if score > 0.5 else "Real"
    confidence = round(max(score, 1.0 - score), 4)
    return trusted, confidence
