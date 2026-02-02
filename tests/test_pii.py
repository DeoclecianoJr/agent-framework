import pytest
from app.core.pii import PIIAnonymizer, pii_anonymizer

class TestPIIAnonymizer:
    def test_mask_email(self):
        text = "Contact me at user@example.com for details."
        masked = pii_anonymizer.mask_text(text)
        assert "[PII:EMAIL]" in masked
        assert "user@example.com" not in masked
        assert masked == "Contact me at [PII:EMAIL] for details."

    def test_mask_cpf(self):
        # Test formatted and unformatted
        text = "My CPF is 123.456.789-00."
        masked = pii_anonymizer.mask_text(text)
        assert "[PII:CPF]" in masked
        assert "123.456.789-00" not in masked
        
        # Simple digits might overlap with phone or other numbers, 
        # regex expects dots/dash or just 11 digits?
        # Our regex was `(?:\d{3}\.?\d{3}\.?\d{3}-?\d{2})`
        # It handles 12345678900
        text2 = "Raw 12345678900 here"
        masked2 = pii_anonymizer.mask_text(text2)
        assert "[PII:CPF]" in masked2

    def test_mask_phone(self):
        text = "Call 11 91234-5678 now"
        masked = pii_anonymizer.mask_text(text)
        assert "[PII:PHONE]" in masked
        assert "91234-5678" not in masked
        
    def test_mask_multiple(self):
        text = "Email: test@test.com, CPF: 111.222.333-44"
        masked = pii_anonymizer.mask_text(text)
        assert "[PII:EMAIL]" in masked
        assert "[PII:CPF]" in masked
        
    def test_no_pii(self):
        text = "Just a simple text message."
        assert pii_anonymizer.mask_text(text) == text
        
    def test_contains_pii(self):
        assert pii_anonymizer.contains_pii("user@example.com")
        assert not pii_anonymizer.contains_pii("Hello World")
