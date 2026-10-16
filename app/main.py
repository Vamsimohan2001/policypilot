import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import __version__
from .agent.embeddings import describe_embedding_backend
from .agent.llm import llm_active
from .agent.retriever import collection_count
from .config import get_settings
from .db import init_db
from .knowledge import ingest_policies
from .policies import load_policy_index
from .routers import admin, auth, chat, documents
from .schemas import HealthOut
from .seed import seed_database

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("policybot")

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    if settings.seed_on_startup:
        seed_database()
    if settings.auto_ingest_on_startup:
        try:
            if collection_count() == 0:
                log.info("vector store is empty - ingesting policies (first run may download the embedding model, ~80 MB)...")
                ingest_policies(reset=False)
        except Exception:  # noqa: BLE001
            log.exception("policy ingestion failed at startup - run 'python -m scripts.ingest_policies' manually")
    log.info(
        "Policy Bot ready | llm=%s | embeddings=%s | documents=%d | chunks=%d",
        "on" if llm_active() else "offline-extractive",
        describe_embedding_backend(),
        len(load_policy_index()),
        collection_count(),
    )
    yield


app = FastAPI(title="Policy Bot API", version=__version__, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8501", "http://127.0.0.1:8501",
        "http://localhost:8000", "http://127.0.0.1:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(documents.router)
app.include_router(admin.router)


@app.get("/health", response_model=HealthOut, tags=["system"])
def health() -> HealthOut:
    return HealthOut(
        status="ok",
        app=settings.app_name,
        version=__version__,
        llm_mode="llm" if llm_active() else "offline",
        embedding_backend=describe_embedding_backend(),
        documents=len(load_policy_index()),
        chunks=collection_count(),
    )


@app.get("/", tags=["system"])
def root() -> dict:
    return {"app": settings.app_name, "docs": "/docs", "health": "/health"}
