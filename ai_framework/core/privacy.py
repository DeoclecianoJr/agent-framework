"""PII detection and masking utilities."""
import re
from typing import List, Dict, Any

# Simple regex-based PII detection
PII_PATTERNS = {
    "email": r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+',
    "phone": r'\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b',
    "credit_card": r'\b(?:\d[ -]*?){13,16}\b',
    "cpf": r'\b\d{3}\.\d{3}\.\d{3}-\d{2}\b', # Brazilian Tax ID for example
}

class PIIProcessor:
    """Detects and masks PII in text content."""

    def __init__(self, patterns: Dict[str, str] = None, mask_token: str = "[REDACTED]"):
        self.patterns = patterns or PII_PATTERNS
        self.mask_token = mask_token

    def mask(self, text: str) -> str:
        """Mask detected PII with mask token."""
        result = text
        for name, pattern in self.patterns.items():
            result = re.sub(pattern, self.mask_token, result)
        return result

    def detect(self, text: str) -> List[Dict[str, Any]]:
        """Return list of detected PII including type and position."""
        detections = []
        for name, pattern in self.patterns.items():
            for match in re.finditer(pattern, text):
                detections.append({
                    "type": name,
                    "start": match.start(),
                    "end": match.end(),
                    "value": match.group()
                })
        return detections
