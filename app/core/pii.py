"""
PII Detection and Masking module.

Handles detection and anonymization of sensitive data (CPF, Email, Phone, Credit Card).
Conformance with LGPD requirements.
"""
import re
from typing import List, Dict, Any

# Regex patterns
CPF_PATTERN = r'(?:\d{3}\.?\d{3}\.?\d{3}-?\d{2})'
EMAIL_PATTERN = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
PHONE_BR_PATTERN = r'(?:\(?\d{2}\)?\s?)?(?:9\d{4}|\d{4})[ -]?\d{4}'
# Basic Luhn check is expensive in regex, using simple pattern for potential Credit Cards
# Matches 4 groups of 4 digits or 16 digits
CC_PATTERN = r'(?:\d{4}[ -]?){3}\d{4}'


class PIIAnonymizer:
    """Detects and masks PII in text content."""
    
    def __init__(self):
        self.patterns = {
            "cpf": re.compile(CPF_PATTERN),
            "email": re.compile(EMAIL_PATTERN),
            "phone": re.compile(PHONE_BR_PATTERN),
            # "credit_card": re.compile(CC_PATTERN) # Disabled by default to avoid false positives on IDs
        }
        
    def mask_text(self, text: str) -> str:
        """
        Replace identifying information with [PII:TYPE].
        
        Args:
            text: Input text
            
        Returns:
            Text with PII replaced by placeholders
        """
        if not text:
            return text
            
        anonymized = text
        
        # Mask Emails
        anonymized = self.patterns["email"].sub("[PII:EMAIL]", anonymized)
        
        # Mask CPFs
        # We need a stricter check for CPF to avoid masking simple numbers? 
        # For now, regex match is sufficient for MVP
        anonymized = self.patterns["cpf"].sub("[PII:CPF]", anonymized)
        
        # Mask Phones (apply last to avoid partial matches on other numbers)
        # Note: Phone regex is broad, might match dates/times. 
        # Using a more specific strategy or context would be better for prod.
        anonymized = self.patterns["phone"].sub("[PII:PHONE]", anonymized)
        
        return anonymized

    def contains_pii(self, text: str) -> bool:
        """Check if identifying information is present."""
        return any(p.search(text) for p in self.patterns.values())

# Singleton instance
pii_anonymizer = PIIAnonymizer()
