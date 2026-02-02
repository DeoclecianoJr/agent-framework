"""
PDF document parser.

Handles .pdf files using PyPDF2 and pdfplumber.

Story 7.6: Document Parsing & Chunking
"""

import logging
from typing import Optional

from .base import DocumentParser, ParsedDocument, ParserError

logger = logging.getLogger(__name__)


class PDFParser(DocumentParser):
    """
    Parser for PDF documents.
    
    Uses:
    - PyPDF2: Basic metadata and text extraction
    - pdfplumber: Advanced text extraction with layout preservation
    """
    
    SUPPORTED_MIME_TYPES = {
        "application/pdf",
    }
    
    SUPPORTED_EXTENSIONS = {
        ".pdf",
    }
    
    def __init__(self, use_pdfplumber: bool = True):
        """
        Initialize PDF parser.
        
        Args:
            use_pdfplumber: Use pdfplumber for better text extraction (default: True)
        """
        self.use_pdfplumber = use_pdfplumber
        self._check_dependencies()
    
    def _check_dependencies(self):
        """Check if required libraries are installed."""
        try:
            import PyPDF2
            self.pypdf2 = PyPDF2
        except ImportError:
            raise ImportError(
                "PyPDF2 is required for PDF parsing. "
                "Install with: pip install PyPDF2"
            )
        
        if self.use_pdfplumber:
            try:
                import pdfplumber
                self.pdfplumber = pdfplumber
            except ImportError:
                logger.warning(
                    "pdfplumber not installed. Falling back to PyPDF2. "
                    "Install with: pip install pdfplumber"
                )
                self.use_pdfplumber = False
    
    def can_parse(self, mime_type: str, file_extension: str) -> bool:
        """Check if this parser can handle the file type."""
        return (
            mime_type in self.SUPPORTED_MIME_TYPES or
            file_extension.lower() in self.SUPPORTED_EXTENSIONS
        )
    
    def parse(self, file_content: bytes, filename: str = "") -> ParsedDocument:
        """
        Parse PDF content.
        
        Args:
            file_content: Raw PDF bytes
            filename: Original filename
            
        Returns:
            ParsedDocument: Parsed PDF document
            
        Raises:
            ParserError: If PDF parsing fails
        """
        try:
            if self.use_pdfplumber:
                return self._parse_with_pdfplumber(file_content, filename)
            else:
                return self._parse_with_pypdf2(file_content, filename)
        except Exception as e:
            raise ParserError(f"Failed to parse PDF {filename}: {str(e)}")
    
    def _parse_with_pypdf2(self, file_content: bytes, filename: str) -> ParsedDocument:
        """Parse PDF using PyPDF2."""
        import io
        
        pdf_file = io.BytesIO(file_content)
        reader = self.pypdf2.PdfReader(pdf_file)
        
        # Extract metadata
        metadata = {
            "filename": filename,
            "mime_type": "application/pdf",
            "page_count": len(reader.pages),
        }
        
        # Add PDF metadata if available
        if reader.metadata:
            if reader.metadata.title:
                metadata["title"] = reader.metadata.title
            if reader.metadata.author:
                metadata["author"] = reader.metadata.author
            if reader.metadata.subject:
                metadata["subject"] = reader.metadata.subject
            if reader.metadata.creator:
                metadata["creator"] = reader.metadata.creator
        
        # Extract text from all pages
        text_parts = []
        for page_num, page in enumerate(reader.pages, start=1):
            try:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
            except Exception as e:
                logger.warning(f"Failed to extract text from page {page_num}: {e}")
        
        text = "\n\n".join(text_parts)
        
        return ParsedDocument(
            text=text,
            metadata=metadata,
            page_count=len(reader.pages),
        )
    
    def _parse_with_pdfplumber(self, file_content: bytes, filename: str) -> ParsedDocument:
        """Parse PDF using pdfplumber (better text extraction)."""
        import io
        
        pdf_file = io.BytesIO(file_content)
        
        with self.pdfplumber.open(pdf_file) as pdf:
            # Extract metadata
            metadata = {
                "filename": filename,
                "mime_type": "application/pdf",
                "page_count": len(pdf.pages),
            }
            
            # Add PDF metadata if available
            if pdf.metadata:
                for key in ["Title", "Author", "Subject", "Creator"]:
                    if key in pdf.metadata and pdf.metadata[key]:
                        metadata[key.lower()] = pdf.metadata[key]
            
            # Extract text from all pages
            text_parts = []
            for page_num, page in enumerate(pdf.pages, start=1):
                try:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
                except Exception as e:
                    logger.warning(f"Failed to extract text from page {page_num}: {e}")
            
            text = "\n\n".join(text_parts)
            
            return ParsedDocument(
                text=text,
                metadata=metadata,
                page_count=len(pdf.pages),
            )
