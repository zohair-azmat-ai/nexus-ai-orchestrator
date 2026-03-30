"""
Text Chunker — splits documents into overlapping chunks for embedding.

Phase 1: simple fixed-size character chunker.
Phase 2: semantic chunking, recursive text splitter, or token-aware splitting.
"""

from app.core.logger import get_logger

logger = get_logger(__name__)

DEFAULT_CHUNK_SIZE = 512
DEFAULT_OVERLAP = 64


class TextChunker:
    def __init__(self, chunk_size: int = DEFAULT_CHUNK_SIZE, overlap: int = DEFAULT_OVERLAP):
        self.chunk_size = chunk_size
        self.overlap = overlap

    async def chunk(self, text: str) -> list[str]:
        """Split text into overlapping chunks."""
        if not text.strip():
            return []

        chunks: list[str] = []
        start = 0

        while start < len(text):
            end = start + self.chunk_size
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            start += self.chunk_size - self.overlap

        logger.debug("chunker.done", extra={"input_len": len(text), "chunks": len(chunks)})
        return chunks


chunker = TextChunker()
