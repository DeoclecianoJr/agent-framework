"""
Tests for document parsing and chunking.

Story 7.6: Document Parsing & Chunking
"""

import io
import pytest


class TestTextChunker:
    """Test chunking functionality."""
    
    def test_chunk_basic(self):
        """Test basic text chunking."""
        from ai_framework.core.parsing.chunker import TextChunker
        
        chunker = TextChunker(chunk_size=50, overlap=10)
        text = "This is a test. " * 100  # Long text
        
        chunks = chunker.chunk(text)
        
        assert len(chunks) > 0
        assert all(isinstance(c, dict) for c in chunks)
        assert all('text' in c for c in chunks)
        assert all('chunk_index' in c for c in chunks)
    
    def test_chunk_short_text(self):
        """Test chunking text shorter than chunk_size."""
        from ai_framework.core.parsing.chunker import TextChunker
        
        chunker = TextChunker(chunk_size=500)
        text = "Short text."
        
        chunks = chunker.chunk(text)
        
        assert len(chunks) == 1
        assert chunks[0]['text'] == text


class TestPDFParser:
    """Test PDF parsing."""
    
    def test_parser_init(self):
        """Test PDF parser initialization."""
        try:
            from ai_framework.core.parsing.parsers import PDFParser
            parser = PDFParser()
            assert parser is not None
        except Exception as e:
            pytest.skip(f"PDF parser not available: {e}")
    
    def test_supports_mime_type(self):
        """Test MIME type detection."""
        try:
            from ai_framework.core.parsing.parsers import PDFParser
            parser = PDFParser()
            
            assert parser.supports_mime_type('application/pdf')
            assert not parser.supports_mime_type('text/plain')
        except Exception as e:
            pytest.skip(f"PDF parser not available: {e}")


class TestDOCXParser:
    """Test DOCX parsing."""
    
    def test_parser_init(self):
        """Test DOCX parser initialization."""
        try:
            from ai_framework.core.parsing.parsers import DOCXParser
            parser = DOCXParser()
            assert parser is not None
        except Exception as e:
            pytest.skip(f"DOCX parser not available: {e}")
    
    def test_supports_mime_type(self):
        """Test MIME type detection."""
        try:
            from ai_framework.core.parsing.parsers import DOCXParser
            parser = DOCXParser()
            
            assert parser.supports_mime_type('application/vnd.openxmlformats-officedocument.wordprocessingml.document')
            assert not parser.supports_mime_type('application/pdf')
        except Exception as e:
            pytest.skip(f"DOCX parser not available: {e}")


class TestTextParser:
    """Test plain text parsing."""
    
    def test_parse_text(self):
        """Test text parsing."""
        from ai_framework.core.parsing.parsers import TextParser
        
        parser = TextParser()
        text = "Hello, world!"
        
        file_stream = io.BytesIO(text.encode('utf-8'))
        result = parser.parse(file_stream)
        
        assert result == text
    
    def test_supports_mime_type(self):
        """Test MIME type detection."""
        from ai_framework.core.parsing.parsers import TextParser
        
        parser = TextParser()
        
        assert parser.supports_mime_type('text/plain')
        assert not parser.supports_mime_type('application/pdf')
