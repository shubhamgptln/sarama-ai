"""
domain/repository/chunker_repository.py

Repository interfaces for document chunking service.
Mirrors Go interfaces: domain/repository/interfaces.go
"""

from abc import ABC, abstractmethod
from typing import List, Union

from domain.model.document import Document, DocumentChunk, WebhookEventType


class ChunkerService(ABC):
    """Service interface for chunking documents using LlamaIndex"""

    @abstractmethod
    async def chunk_document(
        self,
        document: Document,
        event_type: Union[WebhookEventType, str],
    ) -> List[DocumentChunk]:
        """
        Chunk a document while maintaining parent-child relationships.
        
        Args:
            document: Document to chunk
            event_type: Type of event (created, updated, deleted)
            
        Returns:
            List of document chunks with hierarchical relationships
        """
        pass

    @abstractmethod
    def split_chunk_by_size(self, chunk: DocumentChunk) -> List[DocumentChunk]:
        """
        Split a chunk if it exceeds size limits.
        
        Args:
            chunk: Document chunk to potentially split
            
        Returns:
            List of chunks after splitting
        """
        pass

