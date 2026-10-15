"""
Decides what the user actually wants:

    EXPLAIN -> answer with an explanation (short code snippets only)
    BUILD   -> generate a complete PHP project

Rules run first (free, instant, works for English + Hinglish).
Gemini is asked only when the rules cannot decide.
"""

import re


EXPLAIN = "EXPLAIN"
BUILD = "BUILD"


# Words that mean "teach me / tell me", not "make me a project".
EXPLAIN_PATTERNS = [
    r"\bexplain\b",
    r"\bexplanation\b",
    r"\bsamjh(a|ao|ana|ado|a do)\b",
    r"\bsamajh\b",
    r"\bbata(o|na|do)\b",
    r"\bwhat is\b",
    r"\bwhat are\b",
    r"\bwhat does\b",
    r"\bwhy\b",
    r"\bhow does\b",
    r"\bhow do(es)?\b.*\bwork\b",
    r"\bhow to connect\b",
    r"\bdifference between\b",
    r"\bkya hai\b",
    r"\bkya hota\b",
    r"\bkaise (kaam|work|connect|hota)\b",
    r"\bkyu(n)?\b",
    r"\bmeaning of\b",
    r"\bconcept\b",
    r"\bwalk me through\b",
    r"\bteach me\b",
]

# Words that clearly ask for a whole project / app.
BUILD_PATTERNS = [
    r"\b(build|create|generate|make|develop|banao|bana do|bana de)\b"
    r".*\b(project|app|application|website|site|system|api|portal|"
    r"dashboard|cms|crud|login|module|shop|store|cart|e-?commerce|"
    r"blog|forum|todo|to-do|tracker|crm|erp|booking|platform|tool|"
    r"calculator|form|page|panel|game|chat|gallery|quiz|survey|"
    r"inventory|library|backend|webapp|web app)s?\b",
    r"\b(complete|full|poora|pura)\b.*\b(project|app|website)\b",
    # "give me code for a REST API", "I need a PHP CRUD", "mujhe ek
    # blog chahiye"
    r"\b(give me|i need|i want|need a|mujhe)\b.*\b(project|app|website|"
    r"system|api|crud|portal|dashboard|shop|store|blog|cms|module)\b",
    r"\bgenerate\b.*\bproject\b",
    r"\bproject (banao|bana do|bana de|generate)\b",
]


# A sentence that starts like a question is a question, even if it
# contains "create" or "make" ("how to create login in php").
QUESTION_START = r"^(how|what|why|when|which|where|can you explain|kya|kaise|kyu|kyun|kab|kaun)\b"

# ...unless the user clearly asks for a whole project.
EXPLICIT_PROJECT = r"\b(project|complete|full|poora|pura|generate)\b"


def _matches(patterns, text):
    return any(re.search(p, text) for p in patterns)


def rule_based_intent(text):
    """Return EXPLAIN, BUILD, or None when the rules cannot decide."""

    t = " ".join((text or "").lower().split())

    if not t:
        return None

    if re.search(QUESTION_START, t) and not re.search(EXPLICIT_PROJECT, t):
        return EXPLAIN

    if re.search(r"\bkaise\b", t) and not re.search(EXPLICIT_PROJECT, t):
        return EXPLAIN

    wants_explain = _matches(EXPLAIN_PATTERNS, t)
    wants_build = _matches(BUILD_PATTERNS, t)

    # "explain ... with php code" is still an explanation.
    if wants_explain and not wants_build:
        return EXPLAIN

    if wants_build and not wants_explain:
        return BUILD

    # Both or neither matched: let the model decide.
    return None


def classify_intent(text, model_manager=None):
    """
    Returns EXPLAIN or BUILD.

    Without a model manager, an unclear request defaults to EXPLAIN,
    because explaining is cheap and harmless, while wrongly building a
    whole project wastes a generation and floods the screen with code.
    """

    intent = rule_based_intent(text)

    if intent:
        return intent

    if model_manager is None:
        return EXPLAIN

    prompt = f"""
Classify the user's request for a PHP assistant.

Answer with exactly one word:

EXPLAIN - the user wants to understand or learn something
          (a concept, how something works, why, a short example).
BUILD   - the user wants a complete working project or application
          created for them.

If unsure, answer EXPLAIN.

USER REQUEST:
{text}
"""

    result = model_manager.generate(
        prompt,
        max_output_tokens=8,
        # TASK_CLASSIFY: smallest Groq / NVIDIA model first, Gemini last.
        task="classify"
    )

    if result.get("success"):

        answer = (result.get("response") or "").strip().upper()

        if answer.startswith(BUILD):
            return BUILD

    return EXPLAIN