from rag.retriever import PHPRetriever


class PHPContextBuilder:

    def __init__(self, top_k=3):
        self.retriever = PHPRetriever(top_k=top_k)

    def build_context(self, query):

        results = self.retriever.retrieve(query)

        if not results:
            return "No relevant PHP documentation was found."

        context_parts = []

        for i, result in enumerate(results, start=1):

            source = result.get("source", "Unknown")
            text = result.get("text", "")

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