import json
from pathlib import Path

import faiss
import numpy as np
from fastembed import TextEmbedding


# =========================
# Paths
# =========================

BASE_DIR = Path(__file__).resolve().parent.parent

INDEX_FILE = BASE_DIR / "knowledge_base" / "processed" / "php_faiss.index"
METADATA_FILE = BASE_DIR / "knowledge_base" / "processed" / "php_metadata.json"


# =========================
# Configuration
# =========================

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

TOP_K = 5


def load_metadata():
    with open(METADATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def search(query):
    print(f"\nQuery: {query}")
    print("-" * 70)

    # Load model
    model = TextEmbedding(model_name=MODEL_NAME)

    # Load FAISS index
    index = faiss.read_index(str(INDEX_FILE))

    # Load metadata
    metadata = load_metadata()

    # Convert query into embedding
    query_embedding = np.array(
        list(model.embed([query])),
        dtype="float32",
    )

    norms = np.linalg.norm(query_embedding, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    query_embedding = (query_embedding / norms).astype("float32")

    # Search
    scores, indices = index.search(query_embedding, TOP_K)

    for rank, (score, index_id) in enumerate(
        zip(scores[0], indices[0]), start=1
    ):
        record = metadata[index_id]

        print(f"\nResult #{rank}")
        print(f"Score  : {score:.4f}")
        print(f"Source : {record.get('source')}")
        print(f"Chunk  : {record.get('chunk_index')}")

        text = record.get("text", "")

        print(f"Text   : {text[:1000]}")


def main():

    print("=" * 70)
    print("PHP VibeCoder - RAG Retrieval Test")
    print("=" * 70)

    if not INDEX_FILE.exists():
        raise FileNotFoundError(
            f"FAISS index not found:\n{INDEX_FILE}"
        )

    if not METADATA_FILE.exists():
        raise FileNotFoundError(
            f"Metadata not found:\n{METADATA_FILE}"
        )

    # Test queries
    queries = [
        "How do PHP interfaces work?",
        "How does PHP exception handling work?",
        "How do I connect PHP to MySQL?",
    ]

    for query in queries:
        search(query)

        print("\n" + "=" * 70)


if __name__ == "__main__":
    main()