"""
Document Parsing Package.

Provides document parsing and text extraction capabilities for RAG.

Story 7.6: Document Parsing & Chunking
"""

from .base import DocumentParser, ParsingError
from .parsers import PDFParser, DOCXParser, TextParser
from .chunker import TextChunker
from .factory import ParserFactory

__all__ = [
    'DocumentParser',
    'ParsingError',
    'PDFParser',
    'DOCXParser',
    'TextParser',
    'TextChunker',
    'ParserFactory'
]
