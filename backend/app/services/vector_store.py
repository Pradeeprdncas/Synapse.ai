import os
import uuid
from datetime import datetime

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, FieldCondition, Filter, FilterSelector, MatchValue, PointStruct, VectorParams

from app.services.document_chunks import StructuredChunk, hashed_embedding

COLLECTION = "atlas_document_chunks"
VECTOR_SIZE = 256
_client = None


def client():
    global _client
    if _client is None:
        path = os.getenv("ATLAS_QDRANT_PATH", "storage/atlas_qdrant")
        _client = QdrantClient(path=path)
        names = {item.name for item in _client.get_collections().collections}
        if COLLECTION not in names:
            _client.create_collection(COLLECTION, vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE))
    return _client


def index_chunks(project_id: int, document_id: int, source_filename: str, chunks: list[StructuredChunk]):
    points = [PointStruct(id=str(uuid.uuid5(uuid.NAMESPACE_URL, f"{project_id}:{document_id}:{chunk.chunk_id}")), vector=hashed_embedding(chunk.text), payload={
        "project_id": project_id, "document_id": document_id, "requirement_id": None,
        "chunk_id": chunk.chunk_id, "section": chunk.heading_path, "source_filename": source_filename,
        "chunk_index": chunk.chunk_index, "chunking_method": chunk.chunking_method,
        "created_at": datetime.utcnow().isoformat(), "text": chunk.text,
    }) for chunk in chunks]
    if points: client().upsert(COLLECTION, points=points)


def search(project_id: int, query: str, top_k: int = 5):
    response = client().query_points(collection_name=COLLECTION, query=hashed_embedding(query),
        query_filter=Filter(must=[FieldCondition(key="project_id", match=MatchValue(value=project_id))]),
        limit=max(1, min(top_k, 20)), with_payload=True)
    return [{"score": round(point.score, 4), **(point.payload or {})} for point in response.points]


def delete_document_chunks(project_id: int, document_id: int):
    client().delete(
        collection_name=COLLECTION,
        points_selector=FilterSelector(filter=Filter(must=[
            FieldCondition(key="project_id", match=MatchValue(value=project_id)),
            FieldCondition(key="document_id", match=MatchValue(value=document_id)),
        ])),
    )
