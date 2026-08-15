from sqlalchemy.orm import Session

from app.models.atlas_agent import DocumentChunk
from app.models.document import Document
from app.services.document_chunks import structure_aware_chunks
from app.services.documents.extractor import extract_text
from app.services.rag.keyword_rag import create_chunks, save_chunks
from app.services.vector_store import index_chunks


def ingest_document(db: Session, document: Document, text: str | None = None) -> int:
    """Run local and provider documents through the same Atlas ingestion path."""
    content = text if text is not None else extract_text(document.file_path)
    save_chunks(document.project_id, create_chunks(content))
    structured = structure_aware_chunks(content)
    db.query(DocumentChunk).filter_by(document_id=document.id).delete()
    for chunk in structured:
        db.add(DocumentChunk(
            project_id=document.project_id,
            document_id=document.id,
            chunk_id=chunk.chunk_id,
            section=chunk.heading_path,
            source_filename=document.original_name,
            chunk_index=chunk.chunk_index,
            chunking_method=chunk.chunking_method,
            text=chunk.text,
        ))
    db.flush()
    index_chunks(document.project_id, document.id, document.original_name, structured)
    return len(structured)
