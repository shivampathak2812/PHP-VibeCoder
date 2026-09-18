from rag.context_builder import PHPContextBuilder
from agents.gemini_model_manager import GeminiModelManager


class RAGAgent:

    def __init__(self, top_k=3):

        self.context_builder = PHPContextBuilder(top_k=top_k)
        self.model_manager = GeminiModelManager()

    def answer(self, query):

        # Step 1: Retrieve relevant PHP documentation
        context = self.context_builder.build_context(query)

        # Step 2: Build RAG prompt
        prompt = f"""
You are a PHP programming assistant.

Use the PHP documentation provided below as your primary
technical knowledge source.

PHP DOCUMENTATION:
{context}

USER QUESTION:
{query}

Instructions:
- Answer the user's question clearly.
- Prefer information supported by the provided PHP documentation.
- If the documentation does not contain enough information,
  clearly say so instead of inventing PHP-specific details.
- When useful, provide a PHP code example.
"""

        # Step 3: Send context + question to Gemini
        print("\nGenerating RAG answer...")
        print("Model priority: Gemini 3.6 Flash -> Gemini 3.5 Flash")

        result = self.model_manager.generate(prompt)

        if not result.get("success"):
            raise RuntimeError(
                f"Gemini RAG generation failed: "
                f"{result.get('error')}"
            )

        response = result["response"]

        print(f"RAG MODEL USED: {result['model']}")

        return response


if __name__ == "__main__":

    print("=" * 70)
    print("PHP VibeCoder - RAG Agent Test")
    print("=" * 70)

    agent = RAGAgent(top_k=3)

    query = "How do PHP interfaces work?"

    print(f"\nUser: {query}")

    print("\nGenerating RAG answer...\n")

    answer = agent.answer(query)

    print("=" * 70)
    print("GEMINI RAG RESPONSE")
    print("=" * 70)
    print(answer)