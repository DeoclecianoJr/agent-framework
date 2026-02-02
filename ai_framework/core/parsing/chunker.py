"""
Text chunking for RAG.

Splits documents into fixed-size chunks with optional overlap.
"""

import logging
from typing import List, Optional

logger = logging.getLogger(__name__)


class TextChunker:
    """
    Splits text into chunks for embeddings and RAG.
    
    Features:
    - Token-based chunking (using tiktoken)
    - Overlap between chunks
    - Preserves sentence boundaries
    
    Usage:
        chunker = TextChunker(chunk_size=512, overlap=50)
        chunks = chunker.chunk(long_text)
    """
    
    def __init__(
        self,
        chunk_size: int = 512,
        overlap: int = 50,
        encoding_name: str = "cl100k_base"
    ):
        """
        Initialize chunker.
        
        Args:
            chunk_size: Maximum tokens per chunk
            overlap: Token overlap between chunks
            encoding_name: Tiktoken encoding (cl100k_base for GPT-4/3.5)
        """
        self.chunk_size = chunk_size
        self.overlap = overlap
        
        try:
            import tiktoken
            self.encoding = tiktoken.get_encoding(encoding_name)
        except ImportError:
            logger.warning("tiktoken not installed, using character-based chunking")
            self.encoding = None
    
    def chunk(self, text: str, metadata: Optional[dict] = None) -> List[dict]:
        """
        Split text into chunks.
        
        Args:
            text: Text to chunk
            metadata: Optional metadata to attach to each chunk
            
        Returns:
            List[dict]: List of chunks with text and metadata
        """
        if not text or not text.strip():
            return []
        
        if self.encoding:
            return self._chunk_by_tokens(text, metadata)
        else:
            return self._chunk_by_chars(text, metadata)
    
    def _chunk_by_tokens(self, text: str, metadata: Optional[dict]) -> List[dict]:
        """Chunk text by token count."""
        # Encode text to tokens
        tokens = self.encoding.encode(text)
        
        chunks = []
        start_idx = 0
        
        while start_idx < len(tokens):
            # Get chunk tokens
            end_idx = start_idx + self.chunk_size
            chunk_tokens = tokens[start_idx:end_idx]
            
            # Decode back to text
            chunk_text = self.encoding.decode(chunk_tokens)
            
            # Create chunk
            chunk = {
                'text': chunk_text,
                'chunk_index': len(chunks),
                'token_count': len(chunk_tokens),
                'char_count': len(chunk_text)
            }
            
            if metadata:
                chunk['metadata'] = metadata
            
            chunks.append(chunk)
            
            # Move to next chunk with overlap
            start_idx = end_idx - self.overlap
            
            # Avoid infinite loop
            if start_idx >= len(tokens):
                break
        
        logger.info(f"Created {len(chunks)} chunks from {len(tokens)} tokens")
        return chunks
    
    def _chunk_by_chars(self, text: str, metadata: Optional[dict]) -> List[dict]:
        """Fallback: Chunk by character count (approx 4 chars = 1 token)."""
        char_chunk_size = self.chunk_size * 4
        char_overlap = self.overlap * 4
        
        chunks = []
        start_idx = 0
        
        while start_idx < len(text):
            end_idx = start_idx + char_chunk_size
            chunk_text = text[start_idx:end_idx]
            
            chunk = {
                'text': chunk_text,
                'chunk_index': len(chunks),
                'token_count': len(chunk_text) // 4,  # Approximate
                'char_count': len(chunk_text)
            }
            
            if metadata:
                chunk['metadata'] = metadata
            
            chunks.append(chunk)
            
            start_idx = end_idx - char_overlap
            
            if start_idx >= len(text):
                break
        
        logger.info(f"Created {len(chunks)} chunks (char-based) from {len(text)} chars")
        return chunks
    
    def get_chunk_count(self, text: str) -> int:
        """
        Get number of chunks for a given text.
        
        Args:
            text: Text to analyze
            
        Returns:
            int: Number of chunks
        """
        return len(self.chunk(text))
