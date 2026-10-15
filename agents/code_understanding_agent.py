from pathlib import Path

from agents.gemini_model_manager import GeminiModelManager, TASK_LIGHT
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

    MAX_OUTPUT_TOKENS = 4096

    # How many earlier chat messages are sent along with a question.
    MAX_HISTORY_MESSAGES = 6

    def __init__(self, top_k=3, api_key=None):
        self.model_manager = GeminiModelManager(api_key=api_key)
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

    def format_history(self, history):
        """Turn recent chat messages into plain text for the prompt."""

        if not history:
            return "No earlier messages."

        lines = []

        for message in history[-self.MAX_HISTORY_MESSAGES:]:

            role = "User" if message.get("role") == "user" else "Assistant"
            content = (message.get("content") or "").strip()

            # Long earlier answers are trimmed to keep the prompt small.
            if len(content) > 1500:
                content = content[:1500] + " ..."

            lines.append(f"{role}: {content}")

        return "\n\n".join(lines)

    def build_prompt(
        self,
        project_path,
        question,
        history=None,
        requirement=None
    ):
        """Analyze the project and build the full prompt."""

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
9. Use the earlier conversation to understand follow-up questions.
10. Answer ONLY what was asked. If the user asks to explain one
    topic (for example the database connection), explain just that
    topic and the files directly involved.
11. Do NOT paste whole files or the whole project. Quote only the
    few relevant lines (under 25 lines per snippet) with the file
    path. Give the full code of a file only if the user explicitly
    asks for it ("show full code", "give me the file").
12. Reply in the language style the user wrote in
    (English, Hindi, or Hinglish).

ORIGINAL PROJECT REQUIREMENT:
{requirement or "Not available."}

EARLIER CONVERSATION:
{self.format_history(history)}

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

        return prompt

    def ask_stream(self, prompt):
        """
        Yields the answer piece by piece.
        Pass the text returned by build_prompt().
        """

        yield from self.model_manager.generate_stream(
            prompt,
            max_output_tokens=self.MAX_OUTPUT_TOKENS,
            task=TASK_LIGHT
        )

    def ask(self, project_path, question, history=None, requirement=None):
        """
        Understand the project and answer the user's question.

        history: earlier chat messages [{"role", "content"}, ...]
        requirement: the original requirement the project was built from
        """

        prompt = self.build_prompt(
            project_path,
            question,
            history=history,
            requirement=requirement
        )

        print("Sending project context to Gemini...")

        result = self.model_manager.generate(
            prompt,
            max_output_tokens=self.MAX_OUTPUT_TOKENS,
            task=TASK_LIGHT
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