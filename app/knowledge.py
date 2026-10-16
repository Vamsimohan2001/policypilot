"""Policy ingestion: split markdown into chunks and upsert into ChromaDB with
role metadata used by the RBAC where-filter."""

import hashlib
import logging
import re

from .agent.embeddings import build_embedding_function
from .agent.retriever import get_client, reset_collection
from .config import get_settings
from .policies import load_policy_index

log = logging.getLogger(__name__)

MAX_CHARS = 900
OVERLAP = 120


def chunk_text(text: str, max_chars: int = MAX_CHARS, overlap: int = OVERLAP) -> list[str]:
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        if not current:
            current = paragraph
        elif len(current) + len(paragraph) + 2 <= max_chars:
            current += "\n\n" + paragraph
        else:
            chunks.append(current)
            tail = current[-overlap:] if len(current) > overlap else ""
            current = (tail + "\n\n" + paragraph).strip() if tail else paragraph
    if current:
        chunks.append(current)

    final: list[str] = []
    for chunk in chunks:
        while len(chunk) > max_chars * 2:
            final.append(chunk[:max_chars])
            chunk = chunk[max_chars - overlap:]
        final.append(chunk)
    return final


def split_policy(doc: dict) -> list[dict]:
    """Break a policy document into (section, chunk) pieces."""
    sections = re.split(r"\n(?=##\s)", doc["content"])
    pieces: list[dict] = []
    for section in sections:
        heading = re.match(r"##\s+(.+)", section)
        if heading:
            title = heading.group(1).strip()
            body = section[heading.end():].strip()
        else:
            title = "Overview"
            body = re.sub(r"^#\s+.*\n?", "", section).strip()
        if not body:
            continue
        for chunk in chunk_text(body):
            pieces.append({"section": title, "text": f"{doc['title']} - {title}\n\n{chunk}"})
    return pieces


def ingest_policies(reset: bool = True) -> dict:
    settings = get_settings()
    docs = load_policy_index()
    client = get_client()
    if reset:
        reset_collection()

    collection = client.get_or_create_collection(
        name=settings.collection_name,
        embedding_function=build_embedding_function(),
        metadata={"hnsw:space": "cosine"},
    )

    ids: list[str] = []
    texts: list[str] = []
    metadatas: list[dict] = []
    for doc in docs:
        for piece in split_policy(doc):
            digest = hashlib.md5(piece["text"].encode("utf-8")).hexdigest()[:10]
            ids.append(f"{doc['id']}::{digest}")
            texts.append(piece["text"])
            metadatas.append(
                {
                    "doc_id": doc["id"],
                    "title": doc["title"],
                    "category": doc["category"],
                    "version": doc["version"],
                    "effective_date": doc["effective_date"],
                    "owner": doc["owner"],
                    "section": piece["section"],
                    "roles_csv": ",".join(doc["roles"]),
                    "role_employee": "employee" in doc["roles"],
                    "role_hr": "hr" in doc["roles"],
                    "role_admin": "admin" in doc["roles"],
                }
            )

    batch_size = 64
    for start in range(0, len(ids), batch_size):
        collection.upsert(
            ids=ids[start:start + batch_size],
            documents=texts[start:start + batch_size],
            metadatas=metadatas[start:start + batch_size],
        )

    summary = {"documents": len(docs), "chunks": len(ids), "collection": settings.collection_name}
    log.info("ingested %d documents into %d chunks", summary["documents"], summary["chunks"])
    return summary
