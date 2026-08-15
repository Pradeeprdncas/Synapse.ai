"""Measured basic vs structure-aware retrieval evaluation over the bundled demo PRD."""
import json
import math
from pathlib import Path

from app.services.document_chunks import basic_chunks, hashed_embedding, structure_aware_chunks

QUERIES = [
    ("password reset registered email", "reset their password"),
    ("task status blocked done", "update task status"),
    ("unauthenticated API 401", "HTTP 401"),
    ("notify task assignee", "notify an assignee"),
]

def cosine(left, right): return sum(a * b for a, b in zip(left, right))
def evaluate(chunks):
    hit, irrelevant = 0, 0
    vectors = [hashed_embedding(chunk) for chunk in chunks]
    for query, expected in QUERIES:
        ranked = sorted(range(len(chunks)), key=lambda i: cosine(hashed_embedding(query), vectors[i]), reverse=True)[:1]
        matched = [expected.lower() in chunks[i].lower() for i in ranked]
        hit += int(any(matched)); irrelevant += sum(not value for value in matched)
    return {"queries": len(QUERIES), "topK": 1, "topKHits": hit, "topKHitRate": hit / len(QUERIES), "irrelevantTopKResults": irrelevant}

def main():
    text = (Path(__file__).parents[2] / "demo" / "atlas-agent-sample-prd.md").read_text()
    basic = basic_chunks(text, 90); structured = [chunk.text for chunk in structure_aware_chunks(text)]
    print(json.dumps({"basic": {"chunks": len(basic), **evaluate(basic)}, "structureAware": {"chunks": len(structured), **evaluate(structured)}}, indent=2))

if __name__ == "__main__": main()
