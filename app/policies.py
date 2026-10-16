import re
from functools import lru_cache
from pathlib import Path

import yaml

from .config import get_settings

FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
REQUIRED_FIELDS = ("id", "title", "category", "version", "effective_date", "owner")


def parse_policy_file(path: Path) -> dict:
    raw = path.read_text(encoding="utf-8")
    match = FRONTMATTER_RE.match(raw)
    if not match:
        raise ValueError(f"Policy file missing YAML frontmatter: {path}")
    meta = yaml.safe_load(match.group(1)) or {}
    meta["roles"] = [str(r) for r in (meta.get("roles") or [])]
    meta["content"] = raw[match.end():].strip()
    meta["path"] = str(path)
    for key in REQUIRED_FIELDS:
        meta.setdefault(key, "")
        meta[key] = str(meta[key])
    return meta


@lru_cache(maxsize=1)
def load_policy_index() -> tuple[dict, ...]:
    """All policy documents with parsed frontmatter + content."""
    settings = get_settings()
    docs = [parse_policy_file(p) for p in sorted(settings.policies_path.glob("*.md"))]
    return tuple(docs)


def get_policy(doc_id: str) -> dict | None:
    for doc in load_policy_index():
        if doc["id"] == doc_id:
            return doc
    return None


def can_access(doc: dict, role: str) -> bool:
    return role in doc["roles"]


def accessible_documents(role: str) -> list[dict]:
    return [d for d in load_policy_index() if can_access(d, role)]
