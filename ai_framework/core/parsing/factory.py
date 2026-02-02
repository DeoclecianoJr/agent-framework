"""
Parser factory for selecting the right parser based on MIME type.
"""

import logging
from typing import Dict, Type, Optional

from .base import DocumentParser, ParsingError
from .parsers import PDFParser, DOCXParser, TextParser, GoogleDocsParser

logger = logging.getLogger(__name__)


class ParserFactory:
    """
    Factory for creating document parsers based on MIME type.
    
    Features:
    - Automatic parser selection
    - Parser registration system
    - Fallback to text parser
    
    Usage:
        parser = ParserFactory.get_parser('application/pdf')
        text = parser.parse(file_stream)
    """
    
    # Registry of parsers
    _parsers: Dict[str, Type[DocumentParser]] = {}
    
    # Initialized parser instances (singleton pattern)
    _instances: Dict[str, DocumentParser] = {}
    
    @classmethod
    def register_parser(cls, parser_class: Type[DocumentParser]):
        """
        Register a parser class.
        
        Args:
            parser_class: Parser class to register
        """
        try:
            # Create instance to check MIME types
            instance = parser_class()
            
            # Store parser class for each supported MIME type
            # We'll check dynamically, so store the instance
            cls._instances[parser_class.__name__] = instance
            
            logger.info(f"Registered parser: {parser_class.__name__}")
            
        except Exception as e:
            logger.warning(f"Failed to register parser {parser_class.__name__}: {e}")
    
    @classmethod
    def get_parser(cls, mime_type: str) -> Optional[DocumentParser]:
        """
        Get parser for MIME type.
        
        Args:
            mime_type: Document MIME type
            
        Returns:
            DocumentParser: Parser instance or None
        """
        # Check each registered parser
        for instance in cls._instances.values():
            if instance.supports_mime_type(mime_type):
                return instance
        
        logger.warning(f"No parser found for MIME type: {mime_type}")
        return None
    
    @classmethod
    def get_supported_mime_types(cls) -> list[str]:
        """
        Get list of all supported MIME types.
        
        Returns:
            list[str]: Supported MIME types
        """
        supported = []
        
        # Common MIME types to check
        test_types = [
            'application/pdf',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'text/plain',
            'application/vnd.google-apps.document'
        ]
        
        for mime_type in test_types:
            if cls.get_parser(mime_type):
                supported.append(mime_type)
        
        return supported
    
    @classmethod
    def can_parse(cls, mime_type: str) -> bool:
        """
        Check if MIME type can be parsed.
        
        Args:
            mime_type: MIME type to check
            
        Returns:
            bool: True if supported
        """
        return cls.get_parser(mime_type) is not None


# Register built-in parsers
try:
    ParserFactory.register_parser(PDFParser)
except Exception as e:
    logger.warning(f"PDFParser not available: {e}")

try:
    ParserFactory.register_parser(DOCXParser)
except Exception as e:
    logger.warning(f"DOCXParser not available: {e}")

try:
    ParserFactory.register_parser(TextParser)
except Exception as e:
    logger.warning(f"TextParser not available: {e}")

try:
    ParserFactory.register_parser(GoogleDocsParser)
except Exception as e:
    logger.warning(f"GoogleDocsParser not available: {e}")
