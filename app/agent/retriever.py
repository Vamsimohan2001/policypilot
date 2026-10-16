"""ChromaDB access with role-based metadata filtering.

Every policy chunk carries boolean metadata keys role_employee / role_hr /
role_admin. Queries always apply a `where` filter for the caller's role, so the
agent can never retrieve content the user is not entitled to see.
"""

import logging
from functools import lru_cache

import chromadb

from ..config import get_settings
from .embeddings import build_embedding_function

log = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_client():
    settings = get_settings()
    settings.chroma_path.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(settings.chroma_path))


@lru_cache(maxsize=1)
def get_collection():
    settings = get_settings()
    return get_client().get_or_create_collection(
        name=settings.collection_name,
        embedding_function=build_embedding_function(),
        metadata={"hnsw:space": "cosine"},
    )


def collection_count() -> int:
    try:
        return get_collection().count()
    except Exception:  # noqa: BLE001
        return 0


def role_where(role: str) -> dict:
    return {f"role_{role}": True}


def search_policies(question: str, role: str, k: int = 5) -> list[dict]:
    """Top-k policy chunks visible to `role` for the given question."""
    collection = get_collection()
    if collection.count() == 0:
        return []
    result = collection.query(
        query_texts=[question],
        n_results=k,
        where=role_where(role),
        include=["documents", "metadatas", "distances"],
    )
    out: list[dict] = []
    ids = (result.get("ids") or [[]])[0]
    documents = (result.get("documents") or [[]])[0]
    metadatas = (result.get("metadatas") or [[]])[0]
    distances = (result.get("distances") or [[]])[0]
    for i, chunk_id in enumerate(ids):
        meta = metadatas[i] or {}
        out.append(
            {
                "chunk_id": chunk_id,
                "text": documents[i] or "",
                "doc_id": meta.get("doc_id", ""),
                "title": meta.get("title", ""),
                "section": meta.get("section", ""),
                "roles": [r for r in (meta.get("roles_csv") or "").split(",") if r],
                "distance": float(distances[i]) if distances else None,
            }
        )
    return out


def reset_collection() -> None:
    settings = get_settings()
    try:
        get_client().delete_collection(name=settings.collection_name)
    except Exception:  # noqa: BLE001 - collection may not exist yet
        pass
    get_collection.cache_clear()
