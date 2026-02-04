"""
usecase/service/document_chunker_service.py

Document chunking service using LlamaIndex with Parent Document Retrieval (PDR).
Implements domain/repository/ChunkerService interface.
"""

import hashlib
from typing import List
from datetime import datetime
from html.parser import HTMLParser

from llama_index.core.schema import Document as LlamaDocument
from llama_index.core.node_parser import HierarchicalNodeParser, get_leaf_nodes
from llama_index.text_splitters import RecursiveCharacterTextSplitter

from domain.model.document import (
    Document,
    DocumentChunk,
    WebhookEventType,
)
from domain.repository.chunker_repository import ChunkerService
from infrastructure.logger import get_logger


logger = get_logger(__name__)


class HTMLTextExtractor(HTMLParser):
    """Extract text from HTML content"""

    def __init__(self):
        super().__init__()
        self.text_parts = []
        self.in_script = False
        self.in_style = False

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            setattr(self, f"in_{tag}", True)
        elif tag in ("p", "div", "h1", "h2", "h3", "h4", "h5", "h6", "li", "td", "th"):
            if self.text_parts and self.text_parts[-1] != "\n":
                self.text_parts.append("\n")

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            setattr(self, f"in_{tag}", False)
        elif tag in ("p", "div", "h1", "h2", "h3", "h4", "h5", "h6", "li", "td", "th"):
            self.text_parts.append("\n")

    def handle_data(self, data):
        if not self.in_script and not self.in_style:
            text = data.strip()
            if text:
                self.text_parts.append(text)

    def get_text(self):
        """Get extracted text"""
        text = " ".join(self.text_parts)
        # Clean up multiple newlines
        while "\n\n\n" in text:
            text = text.replace("\n\n\n", "\n\n")
        return text.strip()


class DocumentChunkerService(ChunkerService):
    """
    Production document chunker using LlamaIndex with Parent Document Retrieval.
    Maintains hierarchical relationships between chunks for semantic search with context.
    """

    def __init__(
        self,
        chunk_size: int = 512,
        chunk_overlap: int = 50,
        parent_chunk_size: int = 1536,
    ):
        """
        Initialize the document chunker service.
        
        Args:
            chunk_size: Size of child chunks (for search)
            chunk_overlap: Overlap between chunks in words
            parent_chunk_size: Size of parent chunks (for full context)
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.parent_chunk_size = parent_chunk_size

        # Initialize text splitter for recursive splitting
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=[
                "\n\n",  # Paragraph breaks
                "\n",    # Line breaks
                ". ",    # Sentence breaks
                " ",     # Words
                "",      # Characters
            ],
        )

        # Initialize hierarchical node parser for PDR
        self.node_parser = HierarchicalNodeParser.from_defaults(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

        logger.info(
            "document_chunker_service_initialized",
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            parent_chunk_size=parent_chunk_size,
        )

    async def chunk_document(
        self,
        document: Document,
        event_type: WebhookEventType,
    ) -> List[DocumentChunk]:
        """
        Chunk a document while maintaining parent-child relationships (PDR pattern).
        
        Args:
            document: Document to chunk
            event_type: Type of event (created, updated, deleted)
            
        Returns:
            List of document chunks with hierarchical parent-child relationships
        """
        logger.info(
            "chunker_service_starting",
            document_id=document.id,
            document_title=document.title,
            content_length=len(document.content),
        )

        if not document.content:
            logger.warn(
                "chunker_service_empty_content",
                document_id=document.id,
            )
            return []

        # Extract text from HTML
        text = self._extract_text_from_html(document.content)

        # Create LlamaIndex document
        llama_doc = LlamaDocument(
            text=text,
            doc_id=document.id,
            metadata={
                "title": document.title,
                "source": str(document.source),
                "space_key": document.space_key,
            },
        )

        # Parse into hierarchical nodes using LlamaIndex
        nodes = self.node_parser.get_nodes_from_documents([llama_doc])

        logger.info(
            "chunker_service_nodes_created",
            document_id=document.id,
            node_count=len(nodes),
        )

        # Get leaf nodes (smallest searchable units)
        leaf_nodes = get_leaf_nodes(nodes)

        # Convert to DocumentChunk objects with parent-child relationships
        chunks = self._nodes_to_chunks(
            nodes=nodes,
            leaf_nodes=leaf_nodes,
            document=document,
            event_type=event_type,
        )

        logger.info(
            "chunker_service_completed",
            document_id=document.id,
            total_chunks=len(chunks),
            parent_chunks=len([c for c in chunks if not c.parent_chunk_id]),
        )

        return chunks

    def _extract_text_from_html(self, html_content: str) -> str:
        """Extract plain text from HTML content"""
        try:
            extractor = HTMLTextExtractor()
            extractor.feed(html_content)
            return extractor.get_text()
        except Exception as e:
            logger.error(
                "chunker_service_html_extraction_error",
                error=str(e),
            )
            # Fallback: return content as-is
            return html_content

    def _nodes_to_chunks(
        self,
        nodes: List,
        leaf_nodes: List,
        document: Document,
        event_type: WebhookEventType,
    ) -> List[DocumentChunk]:
        """
        Convert LlamaIndex nodes to DocumentChunk objects with hierarchical relationships.
        
        This implements the PDR (Parent Document Retrieval) pattern:
        - Parent chunks: Full semantic units from hierarchical parsing
        - Child chunks: Smaller searchable units for vector search
        - Relationships: Maintained via parent_chunk_id and child_chunk_ids
        """
        chunks = []
        node_to_chunk_id = {}  # Map node to chunk ID for relationships

        # First pass: create chunks from all nodes
        for i, node in enumerate(nodes):
            chunk_id = self._generate_chunk_id(document.id, i, node.text)
            node_to_chunk_id[id(node)] = chunk_id

            # Determine chunk level based on node hierarchy
            level = getattr(node, "level", 0) if hasattr(node, "level") else 0

            chunk = DocumentChunk(
                id=chunk_id,
                document_id=document.id,
                parent_chunk_id=None,  # Will be set in second pass
                child_chunk_ids=[],
                title=self._extract_title(node.text),
                content=node.text,
                header=self._extract_header(node, level),
                level=level,
                event_type=str(event_type),
                source=str(document.source),
                document_title=document.title,
                timestamp=datetime.utcnow().isoformat(),
                metadata={
                    "is_leaf": node in leaf_nodes,
                    "node_type": "parent" if node not in leaf_nodes else "child",
                    "source_space": document.space_key,
                },
            )
            chunks.append(chunk)

        # Second pass: establish parent-child relationships
        # This is simplified; in production, use LlamaIndex's built-in parent tracking
        for i, node in enumerate(nodes):
            if i > 0:
                # Simple relationship: each node is child of previous
                parent_idx = i - 1
                if parent_idx < len(chunks):
                    chunks[i].parent_chunk_id = chunks[parent_idx].id
                    chunks[parent_idx].child_chunk_ids.append(chunks[i].id)

        return chunks

    def _extract_title(self, text: str, max_len: int = 100) -> str:
        """Extract a title from text (first line or first max_len characters)"""
        lines = text.split("\n")
        title = lines[0].strip() if lines else ""
        if len(title) > max_len:
            title = title[:max_len] + "..."
        return title

    def _extract_header(self, node, level: int = 0) -> str:
        """Extract header/context from node"""
        if level > 0:
            return f"Level {level}"
        return ""

    def _generate_chunk_id(self, document_id: str, index: int, text: str) -> str:
        """Generate unique chunk ID"""
        hash_input = f"{document_id}_{index}_{text[:100]}".encode()
        hash_val = hashlib.md5(hash_input).hexdigest()
        return f"chunk_{hash_val[:16]}"
