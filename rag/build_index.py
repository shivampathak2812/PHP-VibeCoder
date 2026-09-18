import json
from pathlib import Path

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer


# =========================
# Paths
# =========================

BASE_DIR = Path(__file__).resolve().parent.parent

CHUNKS_FILE = BASE_DIR / "knowledge_base" / "chunks" / "php_chunks.jsonl"

OUTPUT_DIR = BASE_DIR / "knowledge_base" / "processed"

INDEX_FILE = OUTPUT_DIR / "php_faiss.index"
METADATA_FILE = OUTPUT_DIR / "php_metadata.json"


# =========================
# Configuration
# =========================

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

BATCH_SIZE = 32


def load_chunks():
    """Load chunks from JSONL file."""

    records = []

    with open(CHUNKS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()

            if not line:
                continue

            records.append(json.loads(line))

    return records


def build_index(records):
    """Create embeddings and build FAISS index."""

    print(f"Loading embedding model: {MODEL_NAME}")

    model = SentenceTransformer(MODEL_NAME)

    texts = [record["text"] for record in records]

    print(f"Creating embeddings for {len(texts)} chunks...")

    embeddings = model.encode(
        texts,
        batch_size=BATCH_SIZE,
        show_progress_bar=True,
        normalize_embeddings=True,
        convert_to_numpy=True,
    )

    embeddings = embeddings.astype("float32")

    dimension = embeddings.shape[1]

    print(f"Embedding dimension: {dimension}")

    # Inner Product + normalized vectors = cosine similarity
    index = faiss.IndexFlatIP(dimension)

    index.add(embeddings)

    return index


def save_metadata(records):
    """Save metadata corresponding to FAISS vector positions."""

    metadata = []

    for record in records:
        metadata.append(
            {
                "id": record.get("id"),
                "text": record.get("text"),
                "source": record.get("source"),
                "type": record.get("type"),
                "chunk_index": record.get("chunk_index"),
            }
        )

    with open(METADATA_FILE, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)


def main():

    print("=" * 60)
    print("PHP VibeCoder - FAISS Index Builder")
    print("=" * 60)

    if not CHUNKS_FILE.exists():
        raise FileNotFoundError(
            f"Chunks file not found:\n{CHUNKS_FILE}"
        )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("\n1. Loading chunks...")
    records = load_chunks()

    print(f"Chunks loaded: {len(records)}")

    if not records:
        raise ValueError("No chunks found.")

    print("\n2. Building FAISS index...")
    index = build_index(records)

    print("\n3. Saving FAISS index...")
    faiss.write_index(index, str(INDEX_FILE))

    print("\n4. Saving metadata...")
    save_metadata(records)

    print("\n" + "=" * 60)
    print("INDEX BUILD COMPLETE")
    print("=" * 60)

    print(f"Vectors : {index.ntotal}")
    print(f"Dimension: {index.d}")
    print(f"FAISS   : {INDEX_FILE}")
    print(f"Metadata: {METADATA_FILE}")


if __name__ == "__main__":
    main()