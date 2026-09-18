import json
from pathlib import Path

import faiss
from sentence_transformers import SentenceTransformer


# =========================
# Paths
# =========================

BASE_DIR = Path(r"D:\PHP-VibeCoder")

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
    model = SentenceTransformer(MODEL_NAME)

    # Load FAISS index
    index = faiss.read_index(str(INDEX_FILE))

    # Load metadata
    metadata = load_metadata()

    # Convert query into embedding
    query_embedding = model.encode(
        [query],
        normalize_embeddings=True,
        convert_to_numpy=True,
    )

    query_embedding = query_embedding.astype("float32")

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