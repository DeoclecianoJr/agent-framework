"""
Plain text document parser.

Handles .txt and other plain text formats.

Story 7.6: Document Parsing & Chunking
"""

import logging
from typing import Optional

from .base import DocumentParser, ParsedDocument, ParserError

logger = logging.getLogger(__name__)


class TextParser(DocumentParser):
    """
    Parser for plain text files.
    
    Handles:
    - .txt files
    - text/plain MIME type
    - Simple encoding detection and normalization
    """
    
    SUPPORTED_MIME_TYPES = {
        "text/plain",
        "text/markdown",
        "text/csv",
        "application/json",
        "application/xml",
        "text/xml",
    }
    
    SUPPORTED_EXTENSIONS = {
        ".txt",
        ".md",
        ".markdown",
        ".csv",
        ".json",
        ".xml",
        ".log",
        ".yaml",
        ".yml",
    }
    
    def __init__(self, encoding: str = "utf-8", fallback_encodings: Optional[list] = None):
        """
        Initialize text parser.
        
        Args:
            encoding: Primary encoding to try (default: utf-8)
            fallback_encodings: List of fallback encodings to try
        """
        self.encoding = encoding
        self.fallback_encodings = fallback_encodings or ["latin-1", "cp1252", "iso-8859-1"]
    
    def can_parse(self, mime_type: str, file_extension: str) -> bool:
        """Check if this parser can handle the file type."""
        return (
            mime_type in self.SUPPORTED_MIME_TYPES or
            file_extension.lower() in self.SUPPORTED_EXTENSIONS
        )
    
    def parse(self, file_content: bytes, filename: str = "") -> ParsedDocument:
        """
        Parse plain text content.
        
        Args:
            file_content: Raw file bytes
            filename: Original filename
            
        Returns:
            ParsedDocument: Parsed text document
            
        Raises:
            ParserError: If all encoding attempts fail
        """
        # Try primary encoding
        text = self._try_decode(file_content, self.encoding)
        encoding_used = self.encoding
        
        if text is None:
            # Try fallback encodings
            for enc in self.fallback_encodings:
                text = self._try_decode(file_content, enc)
                if text is not None:
                    encoding_used = enc
                    logger.warning(f"Used fallback encoding {enc} for {filename}")
                    break
        
        if text is None:
            raise ParserError(
                f"Failed to decode text file {filename} with encodings: "
                f"{self.encoding}, {', '.join(self.fallback_encodings)}"
            )
        
        # Normalize line endings
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        
        # Build metadata
        metadata = {
            "filename": filename,
            "encoding": encoding_used,
            "mime_type": "text/plain",
        }
        
        return ParsedDocument(
            text=text,
            metadata=metadata,
        )
    
    def _try_decode(self, content: bytes, encoding: str) -> Optional[str]:
        """
        Try to decode bytes with given encoding.
        
        Args:
            content: Raw bytes
            encoding: Encoding to try
            
        Returns:
            Decoded string or None if failed
        """
        try:
            return content.decode(encoding)
        except (UnicodeDecodeError, LookupError):
            return None
