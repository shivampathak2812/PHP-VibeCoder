"""
Adaptive thinking: decide how much the model should "think" before
writing a project, from the requirement text alone (no AI call).

  simple  -> thinking "low"     login, CRUD, todo, contact form, blog
  medium  -> thinking "medium"  several modules, admin panel, uploads
  complex -> thinking "high"    payments, roles/permissions, booking
                                conflicts, inventory, CRM/ERP, ...

More thinking gives better logic on hard projects but costs time and
tokens, so easy projects stay fast.

GEMINI_THINKING_LEVEL in .env / Streamlit secrets:
  adaptive (default, or not set)  -> this module decides
  low | medium | high | minimal   -> that level for every request
  off                             -> Google's default
"""

import os
import re


LOW = "low"
MEDIUM = "medium"
HIGH = "high"

# Features that each add a part (page, table, module) to a project.
FEATURE_WORDS = [
    r"login", r"log ?in", r"register", r"sign ?up", r"logout",
    r"forgot password|reset password", r"profile", r"admin",
    r"dashboard", r"crud", r"search", r"filter", r"pagination",
    r"upload", r"image", r"comments?", r"categor(y|ies)", r"tags?",
    r"cart", r"checkout", r"orders?", r"products?", r"email",
    r"notifications?", r"reports?", r"export|csv|pdf", r"api",
    r"booking|reservation", r"calendar", r"chat", r"messages?",
    r"reviews?|ratings?", r"invoices?", r"attendance", r"payroll",
    r"students?", r"courses?", r"grades?", r"employees?", r"tasks?",
    r"projects?", r"users?", r"settings", r"analytics", r"charts?",
]

# Things whose LOGIC is easy to get wrong: worth more thinking.
HARD_WORDS = [
    r"payments?|razorpay|stripe|paypal", r"roles?|permissions?|rbac|acl",
    r"multi[- ]?(user|vendor|tenant|role|step)", r"double[- ]?booking",
    r"prevent|conflict|overlap|availability|concurren",
    r"transactions?|ledger|wallet|balance", r"inventory|stock",
    r"crm\b|erp\b", r"subscriptions?|billing|recurring",
    r"approval|workflow", r"jwt|oauth|token[- ]?based|2fa|otp",
    r"real[- ]?time|websocket|live updates?", r"schedul",
    r"discount|coupon|tax|gst", r"refund", r"audit (log|trail)",
    r"queue|cron", r"rate limit", r"recommendation",
    r"(time|date) ?slots?|slot booking",
]


def _count(patterns, text):
    return sum(1 for p in patterns if re.search(rf"\b(?:{p})", text))


def estimate(requirement):
    """
    Returns (level, details). details explains the decision, for logs.
    """

    text = " ".join((requirement or "").lower().split())

    words = len(text.split())
    features = _count(FEATURE_WORDS, text)
    hard = _count(HARD_WORDS, text)

    # Each hard topic counts as much as two ordinary features.
    score = features + 2 * hard

    if words > 120:
        score += 2
    elif words > 60:
        score += 1

    if hard >= 2 or score >= 9 or (hard >= 1 and features >= 5):
        level = HIGH
    elif hard >= 1 or score >= 5:
        level = MEDIUM
    else:
        level = LOW

    details = (
        f"words={words} features={features} hard={hard} "
        f"score={score} -> {level}"
    )

    return level, details


def thinking_for(requirement):
    """Just the level ("low", "medium" or "high")."""
    return estimate(requirement)[0]


def effective_level(requested=None):
    """
    The level really used: a fixed GEMINI_THINKING_LEVEL in .env /
    Streamlit secrets wins, otherwise the requested (adaptive) level.
    """

    fixed = os.getenv("GEMINI_THINKING_LEVEL")

    if not fixed:
        try:
            import streamlit as st
            fixed = st.secrets.get("GEMINI_THINKING_LEVEL")
        except Exception:
            fixed = None

    fixed = (str(fixed).strip().lower() if fixed else "adaptive")

    if fixed != "adaptive":
        return fixed

    return (requested or LOW).lower()