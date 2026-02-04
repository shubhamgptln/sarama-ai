"""
domain/model/document.py

Python domain models for documents and chunks.
Mirrors Go structures in domain/model/
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class WebhookSource(str, Enum):
    """Source of the webhook event"""
    CONFLUENCE = "confluence"
    # Future: GITHUB = "github"


class WebhookEventType(str, Enum):
    """Type of webhook event"""
    CREATED = "created"
    UPDATED = "updated"
    DELETED = "deleted"


@dataclass
class DocumentChunk:
    """Represents a chunk of a document with parent-child relationships"""
    id: str
    document_id: str
    parent_chunk_id: Optional[str] = None
    child_chunk_ids: List[str] = field(default_factory=list)
    title: str = ""
    content: str = ""
    header: Optional[str] = None
    level: int = 0
    event_type: str = "created"
    source: str = "confluence"
    document_title: str = ""
    timestamp: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "id": self.id,
            "document_id": self.document_id,
            "parent_chunk_id": self.parent_chunk_id,
            "child_chunk_ids": self.child_chunk_ids,
            "title": self.title,
            "content": self.content,
            "header": self.header,
            "level": self.level,
            "event_type": self.event_type,
            "source": self.source,
            "document_title": self.document_title,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }


@dataclass
class Document:
    """Represents a generic document to be chunked"""
    id: str
    title: str
    content: str
    source: str
    space_key: Optional[str] = None
    version: int = 1
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
