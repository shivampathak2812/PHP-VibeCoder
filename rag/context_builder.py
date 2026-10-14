from functools import lru_cache

from rag.retriever import PHPRetriever


# Each documentation chunk is trimmed to this many characters
# so the prompt sent to Gemini stays small.
MAX_CHUNK_CHARS = 1500


@lru_cache(maxsize=None)
def get_retriever(top_k):
    """
    Load the embedding model and FAISS index once per process
    instead of on every request.
    """
    return PHPRetriever(top_k=top_k)


class PHPContextBuilder:

    def __init__(self, top_k=3, max_chunk_chars=MAX_CHUNK_CHARS):
        self.retriever = get_retriever(top_k)
        self.max_chunk_chars = max_chunk_chars

    def build_context(self, query):

        results = self.retriever.retrieve(query)

        if not results:
            return "No relevant PHP documentation was found."

        context_parts = []

        for i, result in enumerate(results, start=1):

            source = result.get("source", "Unknown")
            text = result.get("text", "") or ""

            if len(text) > self.max_chunk_chars:
                text = text[:self.max_chunk_chars] + " ..."

            context_parts.append(
                f"""
--- PHP Documentation {i} ---
Source: {source}

{text}
"""
            )

        return "\n".join(context_parts)


if __name__ == "__main__":

    builder = PHPContextBuilder(top_k=3)

    query = "How do PHP interfaces work?"

    context = builder.build_context(query)

    print("=" * 70)
    print("RETRIEVED PHP CONTEXT")
    print("=" * 70)
    print(context)
