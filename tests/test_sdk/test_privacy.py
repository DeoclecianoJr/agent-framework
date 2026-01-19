import pytest
from ai_framework.core.privacy import PIIProcessor

def test_mask_email():
    processor = PIIProcessor()
    text = "My email is test@example.com"
    masked = processor.mask(text)
    assert masked == "My email is [REDACTED]"
    assert "test@example.com" not in masked

def test_mask_phone():
    processor = PIIProcessor()
    text = "Call me at 123-456-7890"
    masked = processor.mask(text)
    assert masked == "Call me at [REDACTED]"

def test_mask_multiple():
    processor = PIIProcessor()
    text = "Email test@example.com and phone 123-456-7890"
    masked = processor.mask(text)
    assert masked == "Email [REDACTED] and phone [REDACTED]"

def test_detect_pii():
    processor = PIIProcessor()
    text = "Email test@example.com"
    detections = processor.detect(text)
    assert len(detections) == 1
    assert detections[0]["type"] == "email"
    assert detections[0]["value"] == "test@example.com"
