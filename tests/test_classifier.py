import pytest

from app.services import classifier

pytestmark = pytest.mark.skipif(
    not classifier.settings.model_path.exists()
    or not classifier.settings.tokenizer_path.exists(),
    reason="Trained model artifacts not present",
)


def test_predict_returns_trusted_label_and_confidence():
    trusted, confidence = classifier.predict(
        "Ransomware group demands million from healthcare provider"
    )
    assert trusted in ("Real", "Fake")
    assert 0.5 <= confidence <= 1.0


def test_predict_is_deterministic():
    headline = "New malware campaign targets banking customers via phishing emails"
    assert classifier.predict(headline) == classifier.predict(headline)
