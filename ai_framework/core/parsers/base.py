"""
Document Parser Base Classes.

Provides abstract interface for parsing documents of different types.

Story 7.6: Document Parsing & Chunking
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional, BinaryIO
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class ParsedDocument:
    """
    Result of parsing a document.
    
    Attributes:
        text: Extracted text content
        metadata: Document metadata (title, author, page count, etc.)
        page_count: Number of pages (if applicable)
        word_count: Estimated word count
        char_count: Character count
        language: Detected language (optional)
    """
    text: str
    metadata: dict
    page_count: Optional[int] = None
    word_count: Optional[int] = None
    char_count: Optional[int] = None
    language: Optional[str] = None
    
    def __post_init__(self):
        """Calculate derived fields."""
        if self.char_count is None:
            self.char_count = len(self.text)
        
        if self.word_count is None:
            # Simple word count estimation
            self.word_count = len(self.text.split())


class DocumentParser(ABC):
    """
    Abstract base class for document parsers.
    
    Each parser implementation handles a specific document type
    (PDF, DOCX, TXT, etc.) and extracts text content.
    """
    
    @abstractmethod
    def can_parse(self, mime_type: str, file_extension: str) -> bool:
        """
        Check if this parser can handle the given file type.
        
        Args:
            mime_type: MIME type of the file
            file_extension: File extension (e.g., '.pdf')
            
        Returns:
            bool: True if parser can handle this file type
        """
        pass
    
    @abstractmethod
    def parse(self, file_content: bytes, filename: str = "") -> ParsedDocument:
        """
        Parse document content.
        
        Args:
            file_content: Raw file bytes
            filename: Original filename (for metadata)
            
        Returns:
            ParsedDocument: Parsed document with text and metadata
            
        Raises:
            ParserError: If parsing fails
        """
        pass
    
    def parse_file(self, file_path: str) -> ParsedDocument:
        """
        Parse document from file path.
        
        Args:
            file_path: Path to file
            
        Returns:
            ParsedDocument: Parsed document
        """
        with open(file_path, 'rb') as f:
            return self.parse(f.read(), filename=file_path)


class ParserError(Exception):
    """Exception raised when document parsing fails."""
    pass


class UnsupportedFormatError(ParserError):
    """Exception raised when file format is not supported."""
    pass
