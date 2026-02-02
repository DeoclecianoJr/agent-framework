"""
Text chunking utilities.

Splits text into chunks for embedding and retrieval.

Story 7.6: Document Parsing & Chunking
"""

import logging
from typing import List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class TextChunk:
    """
    A chunk of text from a document.
    
    Attributes:
        text: The chunk text content
        chunk_index: Index of this chunk in the document (0-based)
        start_char: Starting character position in original document
        end_char: Ending character position in original document
        token_count: Estimated token count
        metadata: Additional chunk metadata
    """
    text: str
    chunk_index: int
    start_char: int
    end_char: int
    token_count: int
    metadata: dict


class TextChunker:
    """
    Splits text into chunks for embedding.
    
    Uses token-based chunking with configurable size and overlap.
    Supports multiple tokenization strategies.
    """
    
    def __init__(
        self,
        chunk_size: int = 512,
        chunk_overlap: int = 50,
        encoding_name: str = "cl100k_base",
    ):
        """
        Initialize text chunker.
        
        Args:
            chunk_size: Maximum tokens per chunk (default: 512)
            chunk_overlap: Number of tokens to overlap between chunks (default: 50)
            encoding_name: Tiktoken encoding name (default: cl100k_base for GPT-4)
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.encoding_name = encoding_name
        
        # Load tiktoken encoder
        try:
            import tiktoken
            self.encoder = tiktoken.get_encoding(encoding_name)
        except ImportError:
            raise ImportError(
                "tiktoken is required for text chunking. "
                "Install with: pip install tiktoken"
            )
    
    def chunk_text(self, text: str, metadata: Optional[dict] = None) -> List[TextChunk]:
        """
        Split text into chunks.
        
        Args:
            text: Text to chunk
            metadata: Optional metadata to attach to each chunk
            
        Returns:
            List of TextChunk objects
        """
        if not text.strip():
            return []
        
        metadata = metadata or {}
        
        # Tokenize entire text
        tokens = self.encoder.encode(text)
        
        if len(tokens) <= self.chunk_size:
            # Text fits in single chunk
            return [
                TextChunk(
                    text=text,
                    chunk_index=0,
                    start_char=0,
                    end_char=len(text),
                    token_count=len(tokens),
                    metadata=metadata,
                )
            ]
        
        # Split into overlapping chunks
        chunks = []
        chunk_index = 0
        start_token_idx = 0
        
        while start_token_idx < len(tokens):
            # Calculate end token index
            end_token_idx = min(start_token_idx + self.chunk_size, len(tokens))
            
            # Extract chunk tokens
            chunk_tokens = tokens[start_token_idx:end_token_idx]
            
            # Decode to text
            chunk_text = self.encoder.decode(chunk_tokens)
            
            # Estimate character positions (approximation)
            # This is not perfect but good enough for most cases
            chars_per_token = len(text) / len(tokens)
            start_char = int(start_token_idx * chars_per_token)
            end_char = int(end_token_idx * chars_per_token)
            
            chunks.append(
                TextChunk(
                    text=chunk_text,
                    chunk_index=chunk_index,
                    start_char=start_char,
                    end_char=end_char,
                    token_count=len(chunk_tokens),
                    metadata=metadata,
                )
            )
            
            chunk_index += 1
            
            # Move to next chunk with overlap
            start_token_idx += self.chunk_size - self.chunk_overlap
        
        logger.info(f"Split text into {len(chunks)} chunks (size={self.chunk_size}, overlap={self.chunk_overlap})")
        
        return chunks
    
    def count_tokens(self, text: str) -> int:
        """
        Count tokens in text.
        
        Args:
            text: Text to count
            
        Returns:
            int: Token count
        """
        return len(self.encoder.encode(text))
