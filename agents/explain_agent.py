from agents.gemini_model_manager import GeminiModelManager, TASK_LIGHT
from rag.context_builder import PHPContextBuilder
from agents.reply_language import language_instruction


class PHPExplainAgent:
    """
    Answers "explain ..." questions.

    Gives a clear explanation with only short, focused code snippets.
    It never generates a project and never writes files.
    """

    MAX_OUTPUT_TOKENS = 3000

    # Earlier chat messages sent with a follow-up question.
    MAX_HISTORY_MESSAGES = 6
    MAX_HISTORY_CHARS_PER_MESSAGE = 2000

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

    def format_history(self, history):
        """Recent chat messages as plain text for the prompt."""

        if not history:
            return ""

        lines = []

        for message in history[-self.MAX_HISTORY_MESSAGES:]:

            role = "User" if message.get("role") == "user" else "Assistant"

            content = (message.get("content") or "").strip()

            if len(content) > self.MAX_HISTORY_CHARS_PER_MESSAGE:
                content = (
                    content[:self.MAX_HISTORY_CHARS_PER_MESSAGE] + " ..."
                )

            lines.append(f"{role}: {content}")

        return "\n\n".join(lines)

    def _search_query(self, question, history):
        """
        Text used to look up PHP docs. A follow-up such as "what are
        its disadvantages" says nothing about the topic, so the user's
        earlier questions are added to it.
        """

        if not history:
            return question

        earlier = [
            (m.get("content") or "").strip()
            for m in history
            if m.get("role") == "user"
        ]

        return " ".join(earlier[-2:] + [question])[:500]

    def build_prompt(self, question, history=None):
        """
        history: earlier messages [{"role", "content"}, ...] when this
        is a follow-up question in the same chat.
        """

        rag_context = self.get_rag_context(
            self._search_query(question, history)
        )

        conversation = self.format_history(history)

        shared_rules = f"""
- {language_instruction(question)}
- Use code only to illustrate: SHORT snippets, each under 25 lines.
- Do NOT create a full project, folder structure, FILE: sections,
  CSS, or complete pages.
- Use PDO with prepared statements for database examples.
- Do not put passwords or secrets directly in examples; mention
  environment variables or a config file instead."""

        # ----------------------------------------------------------
        # FOLLOW-UP: answer only the new question
        # ----------------------------------------------------------

        if conversation:
            return f"""
You are a PHP teacher in an ongoing chat.

EARLIER CONVERSATION:
{conversation}

NEW QUESTION (it may refer to the conversation above with words like
"it", "this", "that example"):
{question}

PHP DOCUMENTATION (use as reference):
{rag_context}

RULES:
- Answer ONLY the new question. If it asks for disadvantages, give
  only the disadvantages; if it asks for an example, give only the
  example; and so on.
- Do NOT repeat or re-explain what was already said earlier. No
  "What it is" / "How it works" sections unless the new question
  asks for them.
- Match the length to the question: a narrow question gets a short,
  focused answer.
- No closing line suggesting a project.{shared_rules}
"""

        # ----------------------------------------------------------
        # FIRST QUESTION
        # ----------------------------------------------------------

        return f"""
You are a PHP teacher. The user asked a question and wants an
EXPLANATION, not a project.

USER QUESTION:
{question}

PHP DOCUMENTATION (use as reference):
{rag_context}

RULES:
- Answer exactly what was asked. If the question is narrow (only the
  disadvantages, only a difference, only one function), answer just
  that, briefly, and skip the structure below.
- For a broad "what is / explain X" question, use this structure:
  1. What it is (2-4 sentences)
  2. How it works (short numbered steps)
  3. Small code example
  4. Common mistakes (2-3 bullets){shared_rules}

For a broad question, end with one line: if the user wants a full
working project, they can ask for it, for example
"create a PHP project that ...".
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
            max_output_tokens=self.MAX_OUTPUT_TOKENS,
            task=TASK_LIGHT
        )

    def explain(self, question):

        prompt = self.build_prompt(question)

        result = self.model_manager.generate(
            prompt,
            max_output_tokens=self.MAX_OUTPUT_TOKENS,
            task=TASK_LIGHT
        )

        if not result.get("success"):
            raise RuntimeError(
                f"Gemini explanation failed: {result.get('error')}"
            )

        return {
            "answer": result["response"],
            "model": result["model"],
        }