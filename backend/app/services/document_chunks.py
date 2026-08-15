import hashlib
import math
import re
from dataclasses import dataclass


@dataclass(frozen=True)
class StructuredChunk:
    text: str
    heading_path: str | None
    chunk_index: int
    chunk_id: str
    chunking_method: str = "structure-aware-v1"


def _sentences(text: str) -> list[str]:
    return [part.strip() for part in re.split(r"(?<=[.!?])\s+", text.strip()) if part.strip()]


def structure_aware_chunks(text: str, max_chars: int = 3600, overlap_ratio: float = .12) -> list[StructuredChunk]:
    """Heading/list/paragraph aware chunks, roughly 500–900 tokens for ordinary prose."""
    heading_stack: list[tuple[int, str]] = []
    blocks: list[tuple[str | None, str]] = []
    pending: list[str] = []

    def flush():
        if pending:
            blocks.append((" > ".join(value for _, value in heading_stack) or None, "\n".join(pending).strip()))
            pending.clear()

    for raw in text.splitlines():
        line = raw.rstrip()
        heading = re.match(r"^\s*(#{1,6})\s+(.+?)\s*$", line)
        plain_heading = re.match(r"^\s*([^.!?]{2,80}):\s*$", line)
        if heading or plain_heading:
            flush()
            level = len(heading.group(1)) if heading else 2
            title = (heading.group(2) if heading else plain_heading.group(1)).strip()
            heading_stack[:] = [(depth, value) for depth, value in heading_stack if depth < level]
            heading_stack.append((level, title))
        elif not line.strip():
            flush()
        else:
            pending.append(line.strip())
    flush()

    results: list[StructuredChunk] = []
    for path, block in blocks:
        prefix = f"{path}\n" if path else ""
        if len(prefix) + len(block) <= max_chars:
            pieces = [block]
        else:
            pieces, current = [], ""
            for sentence in _sentences(block):
                if current and len(prefix) + len(current) + len(sentence) + 1 > max_chars:
                    pieces.append(current); overlap = current[-int(max_chars * overlap_ratio):]
                    current = overlap.lstrip() + " " + sentence
                else:
                    current = (current + " " + sentence).strip()
            if current: pieces.append(current)
        for piece in pieces:
            rendered = prefix + piece
            digest = hashlib.sha256(rendered.encode()).hexdigest()[:20]
            results.append(StructuredChunk(rendered, path, len(results), digest))
    return results


def basic_chunks(text: str, words_per_chunk: int = 600) -> list[str]:
    words = text.split()
    return [" ".join(words[i:i + words_per_chunk]) for i in range(0, len(words), words_per_chunk)]


def hashed_embedding(text: str, dimensions: int = 256) -> list[float]:
    vector = [0.0] * dimensions
    for token in re.findall(r"[a-z0-9_]+", text.lower()):
        digest = int(hashlib.sha256(token.encode()).hexdigest()[:16], 16)
        vector[digest % dimensions] += 1.0 if digest & 1 else -1.0
    norm = math.sqrt(sum(value * value for value in vector)) or 1.0
    return [value / norm for value in vector]
