"""CLI: (re)build the policy vector store.

Usage:
    python -m scripts.ingest_policies
    python -m scripts.ingest_policies --no-reset
"""

import argparse
import logging

from app.knowledge import ingest_policies


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    parser = argparse.ArgumentParser(description="Ingest policy markdown files into ChromaDB.")
    parser.add_argument("--no-reset", action="store_true", help="keep the existing collection instead of rebuilding it")
    args = parser.parse_args()

    summary = ingest_policies(reset=not args.no_reset)
    print(
        f"Ingested {summary['documents']} documents into {summary['chunks']} chunks "
        f"(collection: {summary['collection']})."
    )


if __name__ == "__main__":
    main()
