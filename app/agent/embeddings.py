import logging
import hashlib
import math
import re

from ..config import get_settings

log = logging.getLogger(__name__)


class LocalTokenEmbeddingFunction:
    """Small dependency-free embedding fallback for demos and offline deployments."""

    def __call__(self, input):
        return [self.embed_one(text) for text in input]

    def name(self):
        return "policybot-local-token-v1"

    def embed_documents(self, input):
        return self(input)

    def embed_query(self, input):
        if isinstance(input, list):
            return [self.embed_one(text) for text in input]
        return self.embed_one(input)

    def is_legacy(self):
        return True

    @staticmethod
    def embed_one(text: str) -> list[float]:
        vector = [0.0] * 384
        tokens = re.findall(r"[a-z0-9]+", str(text).lower())
        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:2], "big") % 384
            sign = 1.0 if digest[2] % 2 == 0 else -1.0
            vector[index] += sign
        norm = math.sqrt(sum(value * value for value in vector))
        if norm:
            vector = [value / norm for value in vector]
        return vector


def build_embedding_function():
    """Pick the Chroma embedding function.

    Returns an OpenAI embedding function when configured, otherwise a
    dependency-free local token embedding that does not require a model download.
    """
    settings = get_settings()
    backend = settings.embedding_backend.lower().strip()
    want_openai = backend == "openai" or (backend == "auto" and bool(settings.openai_api_key.strip()))

    if want_openai:
        if not settings.openai_api_key.strip():
            log.warning("EMBEDDING_BACKEND=openai but OPENAI_API_KEY is empty - using local embeddings")
        else:
            try:
                from chromadb.utils import embedding_functions

                return embedding_functions.OpenAIEmbeddingFunction(
                    api_key=settings.openai_api_key,
                    model_name=settings.openai_embedding_model,
                )
            except Exception as exc:  # noqa: BLE001
                log.warning("OpenAI embedding function unavailable (%s) - using local embeddings", exc)
    return LocalTokenEmbeddingFunction()


def describe_embedding_backend() -> str:
    settings = get_settings()
    backend = settings.embedding_backend.lower().strip()
    if backend == "openai" or (backend == "auto" and bool(settings.openai_api_key.strip())):
        return f"openai:{settings.openai_embedding_model}"
    return "local:policybot-token-v1"
