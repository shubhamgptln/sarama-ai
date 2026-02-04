"""
adapter/handler/chunker.py

REST handler for document chunking requests.
Called by Go server via HTTP.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

from domain.model.document import (
    Document,
    DocumentChunk,
    WebhookEventType,
    WebhookSource,
    ChunkingRequest,
    ChunkingResponse,
)
from usecase.service.document_chunker_service import DocumentChunkerService
from infrastructure.logger import get_logger

logger = get_logger(__name__)

# Initialize chunker service
chunker_service = DocumentChunkerService(
    chunk_size=512,
    chunk_overlap=50,
    parent_chunk_size=1536,
)

router = APIRouter()


# Pydantic models for REST API
class DocumentInput(BaseModel):
    """Document input model for API"""
    id: str
    title: str
    content: str
    source: str = "confluence"
    space_key: Optional[str] = None
    version: int = 1
    metadata: Dict[str, Any] = {}


class DocumentChunkOutput(BaseModel):
    """Document chunk output model for API"""
    id: str
    document_id: str
    parent_chunk_id: Optional[str] = None
    child_chunk_ids: List[str] = []
    title: str
    content: str
    header: Optional[str] = None
    level: int
    event_type: str
    source: str
    document_title: str
    timestamp: str
    metadata: Dict[str, Any] = {}


class ChunkingRequestInput(BaseModel):
    """Chunking request model for API"""
    document: DocumentInput
    event_type: str


class ChunkingResponseOutput(BaseModel):
    """Chunking response model for API"""
    chunks: List[DocumentChunkOutput]
    document_id: str
    chunk_count: int
    parent_chunk_count: int
    timestamp: str


@router.post("/chunk", response_model=ChunkingResponseOutput)
async def chunk_document(request: ChunkingRequestInput) -> ChunkingResponseOutput:
    """
    Chunk a document using LlamaIndex PDR (Parent Document Retrieval).
    
    Called by Go server (golang chunker client).
    Returns chunks with parent-child relationships for hierarchical indexing.
    
    Args:
        request: ChunkingRequestInput with document and event_type
        
    Returns:
        ChunkingResponseOutput with chunks and metadata
    """
    logger.info(
        "chunk_endpoint_received",
        document_id=request.document.id,
        document_title=request.document.title,
        event_type=request.event_type,
    )

    try:
        # Convert API input to domain models
        source = WebhookSource(request.document.source)
        event_type = WebhookEventType(request.event_type)

        document = Document(
            id=request.document.id,
            title=request.document.title,
            content=request.document.content,
            source=source,
            space_key=request.document.space_key,
            version=request.document.version,
            metadata=request.document.metadata,
        )

        # Chunk the document
        chunks = await chunker_service.chunk_document(document, event_type)

        logger.info(
            "chunk_endpoint_completed",
            document_id=request.document.id,
            chunk_count=len(chunks),
            parent_chunk_count=len([c for c in chunks if not c.parent_chunk_id]),
        )

        # Convert to API output format
        chunk_outputs = [
            DocumentChunkOutput(
                id=chunk.id,
                document_id=chunk.document_id,
                parent_chunk_id=chunk.parent_chunk_id,
                child_chunk_ids=chunk.child_chunk_ids,
                title=chunk.title,
                content=chunk.content,
                header=chunk.header,
                level=chunk.level,
                event_type=chunk.event_type,
                source=chunk.source,
                document_title=chunk.document_title,
                timestamp=chunk.timestamp,
                metadata=chunk.metadata,
            )
            for chunk in chunks
        ]

        return ChunkingResponseOutput(
            chunks=chunk_outputs,
            document_id=request.document.id,
            chunk_count=len(chunks),
            parent_chunk_count=len([c for c in chunks if not c.parent_chunk_id]),
            timestamp=chunks[0].timestamp if chunks else "",
        )

    except ValueError as e:
        logger.error(
            "chunk_endpoint_invalid_input",
            error=str(e),
            document_id=request.document.id,
        )
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(
            "chunk_endpoint_error",
            error=str(e),
            document_id=request.document.id,
        )
        raise HTTPException(status_code=500, detail="Chunking failed")
