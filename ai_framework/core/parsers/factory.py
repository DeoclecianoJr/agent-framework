"""
Parser factory for automatic parser selection.

Routes documents to appropriate parser based on MIME type and extension.

Story 7.6: Document Parsing & Chunking
"""

import logging
from typing import List, Optional

from .base import DocumentParser, ParsedDocument, UnsupportedFormatError
from .text import TextParser
from .pdf import PDFParser
from .docx import DOCXParser

logger = logging.getLogger(__name__)


class ParserFactory:
    """
    Factory for creating and selecting document parsers.
    
    Automatically routes documents to the appropriate parser
    based on MIME type and file extension.
    """
    
    def __init__(self):
        """Initialize parser factory with default parsers."""
        self.parsers: List[DocumentParser] = []
        self._register_default_parsers()
    
    def _register_default_parsers(self):
        """Register built-in parsers."""
        try:
            self.register_parser(PDFParser(use_pdfplumber=True))
        except ImportError as e:
            logger.warning(f"PDF parser not available: {e}")
        
        try:
            self.register_parser(DOCXParser())
        except ImportError as e:
            logger.warning(f"DOCX parser not available: {e}")
        
        # Text parser always available (no dependencies)
        self.register_parser(TextParser())
    
    def register_parser(self, parser: DocumentParser):
        """
        Register a custom parser.
        
        Args:
            parser: Parser instance to register
        """
        self.parsers.append(parser)
        logger.info(f"Registered parser: {parser.__class__.__name__}")
    
    def get_parser(self, mime_type: str, file_extension: str) -> DocumentParser:
        """
        Get appropriate parser for file type.
        
        Args:
            mime_type: MIME type of the file
            file_extension: File extension (e.g., '.pdf')
            
        Returns:
            DocumentParser: Appropriate parser instance
            
        Raises:
            UnsupportedFormatError: If no parser can handle the file type
        """
        for parser in self.parsers:
            if parser.can_parse(mime_type, file_extension):
                return parser
        
        raise UnsupportedFormatError(
            f"No parser available for MIME type '{mime_type}' "
            f"and extension '{file_extension}'"
        )
    
    def parse(
        self,
        file_content: bytes,
        mime_type: str,
        filename: str = "",
    ) -> ParsedDocument:
        """
        Parse document using appropriate parser.
        
        Args:
            file_content: Raw file bytes
            mime_type: MIME type of the file
            filename: Original filename (for extension detection)
            
        Returns:
            ParsedDocument: Parsed document
            
        Raises:
            UnsupportedFormatError: If file format is not supported
            ParserError: If parsing fails
        """
        # Extract file extension from filename
        file_extension = ""
        if filename and "." in filename:
            file_extension = "." + filename.rsplit(".", 1)[-1].lower()
        
        # Get appropriate parser
        parser = self.get_parser(mime_type, file_extension)
        
        logger.info(
            f"Parsing {filename or 'document'} with {parser.__class__.__name__}"
        )
        
        # Parse document
        return parser.parse(file_content, filename)
    
    def can_parse(self, mime_type: str, file_extension: str) -> bool:
        """
        Check if any parser can handle the file type.
        
        Args:
            mime_type: MIME type of the file
            file_extension: File extension (e.g., '.pdf')
            
        Returns:
            bool: True if a parser is available
        """
        try:
            self.get_parser(mime_type, file_extension)
            return True
        except UnsupportedFormatError:
            return False


# Global parser factory instance
_default_factory: Optional[ParserFactory] = None


def get_parser_factory() -> ParserFactory:
    """
    Get global parser factory instance.
    
    Returns:
        ParserFactory: Singleton parser factory
    """
    global _default_factory
    if _default_factory is None:
        _default_factory = ParserFactory()
    return _default_factory
