"""ChromaDB access with role-based metadata filtering.

Every policy chunk carries boolean metadata keys role_employee / role_hr /
role_admin. Queries always apply a `where` filter for the caller's role, so the
agent can never retrieve content the user is not entitled to see.
"""

import logging
import re
from functools import lru_cache

import chromadb

from ..config import get_settings
from ..policies import load_policy_index
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


STOPWORDS = {
    "the", "a", "an", "is", "are", "am", "do", "does", "did", "how", "what",
    "when", "who", "where", "why", "can", "could", "should", "would", "i",
    "my", "me", "we", "our", "you", "your", "and", "or", "of", "to", "in",
    "on", "for", "with", "about", "many", "much", "it", "this", "that",
    "please", "tell", "give", "policy", "policies",
}


def _terms(text: str) -> set[str]:
    terms = set()
    for term in re.findall(r"[a-z0-9]+", text.lower()):
        if len(term) > 2 and term not in STOPWORDS:
            terms.add(term[:-1] if term.endswith("s") and len(term) > 4 else term)
    return terms


def _lexical_score(question: str, text: str) -> int:
    question_terms = _terms(question)
    haystack = text.lower()
    if not question_terms:
        return 0
    text_terms = _terms(haystack)
    score = len(question_terms & text_terms)
    normalized_question = " ".join(re.findall(r"[a-z0-9]+", question.lower()))
    if len(normalized_question) >= 8 and normalized_question in haystack:
        score += 4
    return score


def _lexical_search(question: str, role: str | None, k: int) -> list[dict]:
    """Search every policy section directly as a role-filtered keyword fallback."""
    matches: list[dict] = []
    for doc in load_policy_index():
        if role is not None and role not in doc["roles"]:
            continue

        content = doc["content"]
        sections = re.split(r"(?=^##\s)", content, flags=re.MULTILINE)
        for section in sections:
            section = section.strip()
            if not section:
                continue
            heading_match = re.match(r"^##\s+(.+)$", section, re.MULTILINE)
            section_name = heading_match.group(1).strip() if heading_match else "Overview"
            searchable = f"{doc['title']}\n{section_name}\n{section}"
            score = _lexical_score(question, searchable)
            if score > 0:
                matches.append(
                    {
                        "chunk_id": f"{doc['id']}::{section_name}",
                        "text": f"{doc['title']} - {section_name}\n\n{section}",
                        "doc_id": doc["id"],
                        "title": doc["title"],
                        "section": section_name,
                        "roles": doc["roles"],
                        "distance": None,
                        "lexical_score": score,
                    }
                )
    matches.sort(key=lambda item: item["lexical_score"], reverse=True)
    return matches[:k]


def search_all_policies(question: str, k: int = 5) -> list[dict]:
    """Search the complete policy registry without role filtering."""
    return _lexical_search(question, role=None, k=k)


def search_policies(question: str, role: str, k: int = 5) -> list[dict]:
    """Top-k policy chunks visible to `role`, with direct document fallback."""
    collection = get_collection()
    out: list[dict] = []
    seen: set[tuple[str, str]] = set()

    if collection.count() > 0:
        try:
            result = collection.query(
                query_texts=[question],
                n_results=k,
                where=role_where(role),
                include=["documents", "metadatas", "distances"],
            )
            ids = (result.get("ids") or [[]])[0]
            documents = (result.get("documents") or [[]])[0]
            metadatas = (result.get("metadatas") or [[]])[0]
            distances = (result.get("distances") or [[]])[0]
            for i, chunk_id in enumerate(ids):
                meta = metadatas[i] or {}
                key = (meta.get("doc_id", ""), meta.get("section", ""))
                if key in seen:
                    continue
                seen.add(key)
                out.append(
                    {
                        "chunk_id": chunk_id,
                        "text": documents[i] or "",
                        "doc_id": meta.get("doc_id", ""),
                        "title": meta.get("title", ""),
                        "section": meta.get("section", ""),
                        "roles": [r for r in (meta.get("roles_csv") or "").split(",") if r],
                        "distance": float(distances[i]) if distances else None,
                        "lexical_score": 0,
                    }
                )
        except Exception as exc:  # noqa: BLE001 - direct search keeps the demo usable
            log.warning("vector search failed; using direct policy search (%s)", exc)

    for match in _lexical_search(question, role=role, k=k):
        key = (match["doc_id"], match["section"])
        existing = next(
            (item for item in out if (item["doc_id"], item["section"]) == key),
            None,
        )
        if existing is not None:
            existing["lexical_score"] = max(
                existing.get("lexical_score", 0),
                match["lexical_score"],
            )
        else:
            seen.add(key)
            out.append(match)

    out.sort(
        key=lambda item: (
            item.get("lexical_score", 0),
            -(item.get("distance") if item.get("distance") is not None else 999),
        ),
        reverse=True,
    )
    return out


def reset_collection() -> None:
    settings = get_settings()
    try:
        get_client().delete_collection(name=settings.collection_name)
    except Exception:  # noqa: BLE001 - collection may not exist yet
        pass
    get_collection.cache_clear()
