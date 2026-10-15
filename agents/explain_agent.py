from agents.gemini_model_manager import GeminiModelManager
from rag.context_builder import PHPContextBuilder


class PHPExplainAgent:
    """
    Answers "explain ..." questions.

    Gives a clear explanation with only short, focused code snippets.
    It never generates a project and never writes files.
    """

    MAX_OUTPUT_TOKENS = 3000

    def __init__(self, top_k=3, api_key=None):
        self.model_manager = GeminiModelManager(api_key=api_key)
        self.top_k = top_k

    def get_rag_context(self, question):

        try:
            return PHPContextBuilder(
                top_k=self.top_k
            ).build_context(question)

        except Exception as e:
            return f"[PHP RAG unavailable: {e}]"

    def build_prompt(self, question):

        rag_context = self.get_rag_context(question)

        return f"""
You are a PHP teacher. The user asked a question and wants an
EXPLANATION, not a project.

USER QUESTION:
{question}

PHP DOCUMENTATION (use as reference):
{rag_context}

RULES:
- Reply in the same language style the user used
  (English, Hindi, or Hinglish).
- Start with the explanation in plain words.
- Use code only to illustrate: one or two SHORT snippets,
  each under 25 lines.
- Do NOT create a full project, folder structure, FILE: sections,
  CSS, or complete pages.
- Use PDO with prepared statements for database examples.
- Do not put passwords or secrets directly in examples; mention
  environment variables or a config file instead.

STRUCTURE:
1. What it is (2-4 sentences)
2. How it works (short numbered steps)
3. Small code example
4. Common mistakes (2-3 bullets)

End with one line: if the user wants a full working project,
they can ask for it, for example "create a PHP project that ...".
"""

    def explain_stream(self, prompt):
        """
        Yields the explanation piece by piece.
        Pass the text returned by build_prompt().
        After the stream ends, self.model_manager.last_model holds
        the model that answered.
        """

        yield from self.model_manager.generate_stream(
            prompt,
            max_output_tokens=self.MAX_OUTPUT_TOKENS
        )

    def explain(self, question):

        prompt = self.build_prompt(question)

        result = self.model_manager.generate(
            prompt,
            max_output_tokens=self.MAX_OUTPUT_TOKENS
        )

        if not result.get("success"):
            raise RuntimeError(
                f"Gemini explanation failed: {result.get('error')}"
            )

        return {
            "answer": result["response"],
            "model": result["model"],
        }