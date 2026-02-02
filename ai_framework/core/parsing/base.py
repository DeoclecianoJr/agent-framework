"""
Base classes for document parsing.

Defines abstract interface for document parsers.
"""

from abc import ABC, abstractmethod
from typing import BinaryIO, Optional
import logging

logger = logging.getLogger(__name__)


class ParsingError(Exception):
    """Exception raised when document parsing fails."""
    pass


class DocumentParser(ABC):
    """
    Abstract base class for document parsers.
    
    Parsers extract text content from various document formats
    (PDF, DOCX, TXT, etc.) for indexing and RAG.
    
    Usage:
        parser = PDFParser()
        text = parser.parse(file_stream)
    """
    
    @abstractmethod
    def parse(self, file_stream: BinaryIO) -> str:
        """
        Extract text from document.
        
        Args:
            file_stream: Binary file stream
            
        Returns:
            str: Extracted text content
            
        Raises:
            ParsingError: If parsing fails
        """
        pass
    
    @abstractmethod
    def supports_mime_type(self, mime_type: str) -> bool:
        """
        Check if parser supports given MIME type.
        
        Args:
            mime_type: MIME type string
            
        Returns:
            bool: True if supported
        """
        pass
    
    def clean_text(self, text: str) -> str:
        """
        Clean extracted text (remove extra whitespace, etc.).
        
        Args:
            text: Raw extracted text
            
        Returns:
            str: Cleaned text
        """
        # Remove multiple spaces
        text = ' '.join(text.split())
        
        # Remove multiple newlines (keep max 2)
        while '\n\n\n' in text:
            text = text.replace('\n\n\n', '\n\n')
        
        return text.strip()
