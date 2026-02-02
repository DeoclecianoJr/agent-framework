"""
Tests for document parsing and chunking.

Story 7.6: Document Parsing & Chunking
"""

import pytest
from io import BytesIO

from ai_framework.core.parsers import (
    DocumentParser,
    ParsedDocument,
    ParserError,
    UnsupportedFormatError,
    TextParser,
    TextChunker,
    TextChunk,
    ParserFactory,
    get_parser_factory,
)


class TestParsedDocument:
    """Tests for ParsedDocument dataclass."""
    
    def test_parsed_document_basic(self):
        """Test basic ParsedDocument creation."""
        doc = ParsedDocument(
            text="Hello world",
            metadata={"filename": "test.txt"},
        )
        
        assert doc.text == "Hello world"
        assert doc.metadata == {"filename": "test.txt"}
        assert doc.word_count == 2
        assert doc.char_count == 11
    
    def test_parsed_document_auto_word_count(self):
        """Test automatic word count calculation."""
        doc = ParsedDocument(
            text="This is a test document with multiple words.",
            metadata={},
        )
        
        assert doc.word_count == 8
    
    def test_parsed_document_auto_char_count(self):
        """Test automatic character count."""
        doc = ParsedDocument(
            text="12345",
            metadata={},
        )
        
        assert doc.char_count == 5
    
    def test_parsed_document_with_page_count(self):
        """Test ParsedDocument with page count."""
        doc = ParsedDocument(
            text="Content",
            metadata={},
            page_count=10,
        )
        
        assert doc.page_count == 10


class TestTextParser:
    """Tests for plain text parser."""
    
    def test_text_parser_can_parse_txt(self):
        """Test TextParser recognizes .txt files."""
        parser = TextParser()
        
        assert parser.can_parse("text/plain", ".txt") is True
        assert parser.can_parse("text/plain", ".md") is True
        assert parser.can_parse("application/pdf", ".pdf") is False
    
    def test_text_parser_parse_simple(self):
        """Test parsing simple text file."""
        parser = TextParser()
        content = b"Hello world\nThis is a test."
        
        doc = parser.parse(content, "test.txt")
        
        assert doc.text == "Hello world\nThis is a test."
        assert doc.metadata["filename"] == "test.txt"
        assert doc.metadata["encoding"] == "utf-8"
        assert doc.word_count == 6
    
    def test_text_parser_normalize_line_endings(self):
        """Test line ending normalization."""
        parser = TextParser()
        
        # Windows line endings
        content = b"Line 1\r\nLine 2\r\nLine 3"
        doc = parser.parse(content)
        
        assert "\r\n" not in doc.text
        assert "Line 1\nLine 2\nLine 3" == doc.text
    
    def test_text_parser_fallback_encoding(self):
        """Test fallback encoding handling."""
        parser = TextParser()
        
        # Latin-1 encoded text
        content = "Café résumé".encode("latin-1")
        
        doc = parser.parse(content, "test.txt")
        
        assert "Café résumé" in doc.text
        assert doc.metadata["encoding"] in ["utf-8", "latin-1"]
    
    def test_text_parser_invalid_encoding(self):
        """Test error on completely invalid encoding."""
        parser = TextParser(fallback_encodings=[])
        
        # Invalid UTF-8 sequence
        content = b"\xff\xfe\xfd"
        
        with pytest.raises(ParserError):
            parser.parse(content, "test.txt")
    
    def test_text_parser_markdown(self):
        """Test parsing markdown file."""
        parser = TextParser()
        content = b"# Heading\n\nParagraph with **bold** text."
        
        assert parser.can_parse("text/markdown", ".md") is True
        
        doc = parser.parse(content, "test.md")
        assert "# Heading" in doc.text
        assert "**bold**" in doc.text


class TestTextChunker:
    """Tests for text chunking."""
    
    def test_text_chunker_single_chunk(self):
        """Test text that fits in single chunk."""
        chunker = TextChunker(chunk_size=512, chunk_overlap=50)
        text = "Short text that fits in one chunk."
        
        chunks = chunker.chunk_text(text)
        
        assert len(chunks) == 1
        assert chunks[0].text == text
        assert chunks[0].chunk_index == 0
    
    def test_text_chunker_multiple_chunks(self):
        """Test text that requires multiple chunks."""
        chunker = TextChunker(chunk_size=50, chunk_overlap=10)
        
        # Generate long text
        text = " ".join([f"Word{i}" for i in range(200)])
        
        chunks = chunker.chunk_text(text)
        
        assert len(chunks) > 1
        assert all(chunk.token_count <= 50 for chunk in chunks)
        
        # Check chunk indices
        for i, chunk in enumerate(chunks):
            assert chunk.chunk_index == i
    
    def test_text_chunker_overlap(self):
        """Test chunk overlap."""
        chunker = TextChunker(chunk_size=20, chunk_overlap=5)
        
        text = " ".join([f"Word{i}" for i in range(50)])
        chunks = chunker.chunk_text(text)
        
        # With overlap, should have more chunks
        assert len(chunks) > 2
    
    def test_text_chunker_empty_text(self):
        """Test chunking empty text."""
        chunker = TextChunker()
        
        chunks = chunker.chunk_text("")
        assert len(chunks) == 0
        
        chunks = chunker.chunk_text("   ")
        assert len(chunks) == 0
    
    def test_text_chunker_count_tokens(self):
        """Test token counting."""
        chunker = TextChunker()
        
        text = "Hello world, this is a test."
        token_count = chunker.count_tokens(text)
        
        assert token_count > 0
        assert isinstance(token_count, int)
    
    def test_text_chunker_metadata(self):
        """Test chunk metadata preservation."""
        chunker = TextChunker(chunk_size=50)
        text = " ".join([f"Word{i}" for i in range(100)])
        metadata = {"source": "test.txt", "page": 1}
        
        chunks = chunker.chunk_text(text, metadata=metadata)
        
        for chunk in chunks:
            assert chunk.metadata == metadata


class TestParserFactory:
    """Tests for parser factory."""
    
    def test_parser_factory_initialization(self):
        """Test parser factory initializes with default parsers."""
        factory = ParserFactory()
        
        # Should have at least text parser
        assert len(factory.parsers) > 0
    
    def test_parser_factory_get_text_parser(self):
        """Test getting text parser."""
        factory = ParserFactory()
        
        parser = factory.get_parser("text/plain", ".txt")
        
        assert isinstance(parser, TextParser)
    
    def test_parser_factory_unsupported_format(self):
        """Test error for unsupported format."""
        factory = ParserFactory()
        
        with pytest.raises(UnsupportedFormatError):
            factory.get_parser("application/unknown", ".xyz")
    
    def test_parser_factory_can_parse(self):
        """Test checking if format is supported."""
        factory = ParserFactory()
        
        assert factory.can_parse("text/plain", ".txt") is True
        assert factory.can_parse("application/unknown", ".xyz") is False
    
    def test_parser_factory_parse_text(self):
        """Test parsing through factory."""
        factory = ParserFactory()
        content = b"Hello world"
        
        doc = factory.parse(content, "text/plain", "test.txt")
        
        assert doc.text == "Hello world"
        assert doc.metadata["filename"] == "test.txt"
    
    def test_get_parser_factory_singleton(self):
        """Test global parser factory is singleton."""
        factory1 = get_parser_factory()
        factory2 = get_parser_factory()
        
        assert factory1 is factory2


class TestPDFParserIntegration:
    """Integration tests for PDF parser (requires PyPDF2)."""
    
    def test_pdf_parser_imports(self):
        """Test PDF parser can be imported."""
        try:
            from ai_framework.core.parsers import PDFParser
            assert PDFParser is not None
        except ImportError:
            pytest.skip("PyPDF2 not installed")
    
    def test_pdf_parser_can_parse(self):
        """Test PDF parser recognizes PDF files."""
        try:
            from ai_framework.core.parsers import PDFParser
            parser = PDFParser(use_pdfplumber=False)
            
            assert parser.can_parse("application/pdf", ".pdf") is True
            assert parser.can_parse("text/plain", ".txt") is False
        except ImportError:
            pytest.skip("PyPDF2 not installed")


class TestDOCXParserIntegration:
    """Integration tests for DOCX parser (requires python-docx)."""
    
    def test_docx_parser_imports(self):
        """Test DOCX parser can be imported."""
        try:
            from ai_framework.core.parsers import DOCXParser
            assert DOCXParser is not None
        except ImportError:
            pytest.skip("python-docx not installed")
    
    def test_docx_parser_can_parse(self):
        """Test DOCX parser recognizes DOCX files."""
        try:
            from ai_framework.core.parsers import DOCXParser
            parser = DOCXParser()
            
            assert parser.can_parse(
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                ".docx"
            ) is True
            assert parser.can_parse("text/plain", ".txt") is False
        except ImportError:
            pytest.skip("python-docx not installed")
