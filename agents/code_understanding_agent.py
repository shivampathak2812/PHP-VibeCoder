from pathlib import Path

from agents.gemini_model_manager import GeminiModelManager
from agents.project_analyzer import PHPProjectAnalyzer
from rag.context_builder import PHPContextBuilder


class PHPCodeUnderstandingAgent:
    """
    Understands an existing PHP project using:
    - Project Analyzer
    - PHP RAG
    - Gemini Model Manager

    Gemini model priority:
    - Gemini 3.6 Flash
    - Gemini 3.5 Flash (fallback)

    Supports questions about:
    - Project architecture
    - File responsibilities
    - Classes and methods
    - Code flow
    - Database interaction
    - Routing
    - PHP concepts used in the project
    """

    def __init__(self, top_k=5):
        self.model_manager = GeminiModelManager()
        self.top_k = top_k

    def analyze_project(self, project_path):
        """Analyze the existing PHP project."""
        analyzer = PHPProjectAnalyzer(project_path)
        return analyzer.analyze()

    def build_project_context(self, project_path):
        """Build structured project context."""
        analyzer = PHPProjectAnalyzer(project_path)
        return analyzer.build_context()

    def get_rag_context(self, question):
        """Retrieve relevant PHP documentation."""
        context_builder = PHPContextBuilder(
            top_k=self.top_k
        )

        try:
            return context_builder.build_context(question)
        except Exception as e:
            return f"[PHP RAG unavailable: {e}]"

    def ask(self, project_path, question):
        """
        Understand the project and answer the user's question.
        """

        print("\nAnalyzing PHP project...")

        project_context = self.build_project_context(
            project_path
        )

        print("Retrieving PHP knowledge...")

        rag_context = self.get_rag_context(
            question
        )

        prompt = f"""
You are an expert PHP code understanding agent.

Your job is to understand an EXISTING PHP project and answer
the user's question accurately.

IMPORTANT RULES:

1. Base your answer primarily on the provided project code.
2. Use the PHP documentation context when it helps explain
   PHP-specific concepts.
3. Do not invent files, classes, methods, routes, or behavior.
4. If something cannot be determined from the provided project,
   clearly say so.
5. Explain the actual code flow.
6. Mention relevant file paths when possible.
7. Keep technical explanations clear and structured.
8. Do not modify or generate code unless the user explicitly asks.

USER QUESTION:
{question}

============================================================
EXISTING PHP PROJECT
============================================================

{project_context}

============================================================
PHP KNOWLEDGE / RAG CONTEXT
============================================================

{rag_context}

============================================================

Provide the answer in this structure when applicable:

1. Direct Answer
2. Project Flow
3. Relevant Files
4. Classes / Methods Involved
5. PHP Concepts Used
6. Important Notes

Only include sections that are relevant to the question.
"""

        print("Sending project context to Gemini...")
        print(
            "Model priority: Gemini 3.6 Flash -> Gemini 3.5 Flash"
        )

        result = self.model_manager.generate(
            prompt
        )

        if not result.get("success"):
            raise RuntimeError(
                f"Gemini code understanding failed: "
                f"{result.get('error')}"
            )

        response = result["response"]

        print(
            f"UNDERSTANDING MODEL USED: "
            f"{result['model']}"
        )

        return response

    def explain_project(self, project_path):
        """Generate a high-level explanation of the complete project."""

        question = """
Explain this PHP project completely.

Cover:
- Overall purpose
- Architecture
- Request flow
- Routing
- Controllers
- Models
- Repositories
- Database connection
- Exceptions
- Important classes
- Important methods
- How the components interact
"""

        return self.ask(
            project_path,
            question
        )


def main():

    project_path = str(
        Path(__file__).resolve().parent.parent
        / "generated_projects" / "product-api"
    )

    agent = PHPCodeUnderstandingAgent(
        top_k=5
    )

    question = """
Explain how the Product API works from the incoming HTTP request
until the database operation is completed.
"""

    print("\n")
    print("=" * 70)
    print("PHP CODE UNDERSTANDING AGENT")
    print("=" * 70)

    answer = agent.ask(
        project_path,
        question
    )

    print("\n")
    print("=" * 70)
    print("AGENT RESPONSE")
    print("=" * 70)

    print(answer)


if __name__ == "__main__":
    main()