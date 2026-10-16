import logging

from ..config import get_settings

log = logging.getLogger(__name__)


def build_embedding_function():
    """Pick the Chroma embedding function.

    Returns an OpenAI embedding function when configured, otherwise None which
    makes Chroma use its default local ONNX model (all-MiniLM-L6-v2, ~80 MB,
    downloaded on first ingest).
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
    return None


def describe_embedding_backend() -> str:
    settings = get_settings()
    backend = settings.embedding_backend.lower().strip()
    if backend == "openai" or (backend == "auto" and bool(settings.openai_api_key.strip())):
        return f"openai:{settings.openai_embedding_model}"
    return "local:all-MiniLM-L6-v2"
