import json
from pathlib import Path

import faiss
import numpy as np
from fastembed import TextEmbedding


BASE_DIR = Path(__file__).resolve().parent.parent

INDEX_FILE = (
    BASE_DIR
    / "knowledge_base"
    / "processed"
    / "php_faiss.index"
)

METADATA_FILE = (
    BASE_DIR
    / "knowledge_base"
    / "processed"
    / "php_metadata.json"
)

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


class PHPRetriever:

    def __init__(self, top_k=5):
        self.top_k = top_k

        print("Loading embedding model...")
        self.model = TextEmbedding(model_name=MODEL_NAME)

        print("Loading FAISS index...")
        self.index = faiss.read_index(str(INDEX_FILE))

        print("Loading metadata...")
        with open(METADATA_FILE, "r", encoding="utf-8") as f:
            self.metadata = json.load(f)

        print(f"Retriever ready: {self.index.ntotal} vectors")

    def retrieve(self, query):

        query_embedding = np.array(
            list(self.model.embed([query])),
            dtype="float32",
        )

        norms = np.linalg.norm(
            query_embedding, axis=1, keepdims=True
        )
        norms[norms == 0] = 1.0
        query_embedding = (query_embedding / norms).astype("float32")

        scores, indices = self.index.search(
            query_embedding,
            self.top_k,
        )

        results = []

        for score, index_id in zip(scores[0], indices[0]):

            if index_id < 0:
                continue

            record = self.metadata[index_id]

            results.append(
                {
                    "score": float(score),
                    "id": record.get("id"),
                    "source": record.get("source"),
                    "chunk_index": record.get("chunk_index"),
                    "text": record.get("text"),
                }
            )

        return results