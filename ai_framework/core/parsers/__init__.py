"""
Document parsing and chunking module.

Story 7.6: Document Parsing & Chunking
"""

from .base import DocumentParser, ParsedDocument, ParserError, UnsupportedFormatError
from .text import TextParser
from .pdf import PDFParser
from .docx import DOCXParser
from .chunker import TextChunker, TextChunk
from .factory import ParserFactory, get_parser_factory

__all__ = [
    # Base classes
    "DocumentParser",
    "ParsedDocument",
    "ParserError",
    "UnsupportedFormatError",
    
    # Parsers
    "TextParser",
    "PDFParser",
    "DOCXParser",
    
    # Chunking
    "TextChunker",
    "TextChunk",
    
    # Factory
    "ParserFactory",
    "get_parser_factory",
]
