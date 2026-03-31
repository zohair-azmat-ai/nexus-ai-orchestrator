"""
Text Chunker — splits documents into overlapping chunks for embedding.

Returns typed ChunkItem objects with deterministic IDs derived from
document_id + chunk_index so re-ingestion is idempotent.
"""

import uuid
from dataclasses import dataclass

from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ChunkItem:
    chunk_id: str    # deterministic UUID5 from (document_id, chunk_index)
    chunk_index: int
    text: str


def _chunk_id(document_id: str, chunk_index: int) -> str:
    """Generate a deterministic UUID5 from document_id + chunk_index."""
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{document_id}:{chunk_index}"))


class TextChunker:
    @property
    def chunk_size(self) -> int:
        return settings.rag_chunk_size

    @property
    def overlap(self) -> int:
        return settings.rag_chunk_overlap

    def chunk(self, text: str, document_id: str) -> list[ChunkItem]:
        """
        Split text into overlapping chunks with deterministic IDs.

        Args:
            text: The raw text to split.
            document_id: Used to generate deterministic chunk IDs.

        Returns:
            Ordered list of ChunkItem objects.
        """
        if not text.strip():
            return []

        items: list[ChunkItem] = []
        start = 0
        chunk_index = 0

        while start < len(text):
            end = start + self.chunk_size
            fragment = text[start:end].strip()
            if fragment:
                items.append(ChunkItem(
                    chunk_id=_chunk_id(document_id, chunk_index),
                    chunk_index=chunk_index,
                    text=fragment,
                ))
                chunk_index += 1
            start += self.chunk_size - self.overlap

        logger.debug(
            "chunker.done",
            extra={"document_id": document_id, "input_len": len(text), "chunks": len(items)},
        )
        return items


chunker = TextChunker()
