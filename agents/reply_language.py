"""
Decides which language an answer must be written in, in code, so the
model does not have to guess (models often answer a Hinglish question
in Devanagari Hindi).

Rules, in order:
1. The user asks for a language ("hindi mein batao", "in English")
   -> that language.
2. The question is written in Devanagari -> Hindi.
3. The question is Roman-script Hindi / Hinglish -> Hinglish.
4. Otherwise (plain English) -> DEFAULT_REPLY_LANGUAGE, which is
   English unless DEFAULT_REPLY_LANGUAGE=hinglish is set in .env or
   Streamlit secrets.
"""

import os
import re


ENGLISH = "english"
HINDI = "hindi"
HINGLISH = "hinglish"


# Explicit requests. Checked first, so "explain in hindi" -> Hindi.
ASK_HINDI = re.compile(
    r"(\bin hindi\b|\bhindi (me|mein|mai|main|mei)\b|\bhindi language\b"
    r"|\bshuddh hindi\b|हिंदी|हिन्दी)",
    re.IGNORECASE,
)
ASK_HINGLISH = re.compile(r"\bhinglish\b", re.IGNORECASE)
ASK_ENGLISH = re.compile(
    r"(\bin english\b|\benglish (me|mein|mai|main|mei)\b|\bonly english\b)",
    re.IGNORECASE,
)

DEVANAGARI = re.compile(r"[ऀ-ॿ]")

# Roman-script Hindi words. Words that are also common English words
# ("me", "do", "to", "so", "the", "par") are left out on purpose.
STRONG_HINGLISH = {
    "hai", "hain", "kya", "kaise", "kaisa", "kaisi", "kyu", "kyun",
    "kyon", "kyunki", "chahiye", "batao", "bataiye", "bata", "samjhao",
    "samjha", "samjhaiye", "samajh", "karo", "kariye", "karna", "karte",
    "karta", "karti", "nahi", "nahin", "mujhe", "humein", "isme",
    "isko", "iska", "iski", "uska", "uski", "usme", "yeh", "woh",
    "matlab", "liye", "wala", "wali", "wale", "hota", "hoti", "hote",
    "hona", "banao", "banana", "banta", "bhai", "accha", "acha",
    "theek", "thik", "mein", "aur", "agar", "lekin", "toh", "abhi",
    "kab", "kahan", "kaun", "kitna", "kitne", "dikhao", "sakte",
    "sakta", "sakti", "raha", "rahi", "rahe", "gaya", "gayi",
    "dijiye", "dena", "dedo", "hoga", "hogi", "kaam", "pehle", "baad",
}

WEAK_HINGLISH = {"ka", "ki", "ke", "ko", "ho", "se", "ye", "wo", "ek", "mai"}


def _setting(name):

    value = os.getenv(name)

    if not value:
        try:
            import streamlit as st
            value = st.secrets.get(name)
        except Exception:
            value = None

    return str(value).strip().lower() if value else None


def detect_reply_language(text):
    """Return ENGLISH, HINDI or HINGLISH for the user's message."""

    text = text or ""

    if ASK_HINDI.search(text):
        return HINDI

    if ASK_HINGLISH.search(text):
        return HINGLISH

    if ASK_ENGLISH.search(text):
        return ENGLISH

    if DEVANAGARI.search(text):
        return HINDI

    words = re.findall(r"[a-z]+", text.lower())

    score = sum(
        2 if w in STRONG_HINGLISH else 1 if w in WEAK_HINGLISH else 0
        for w in words
    )

    # "login page ka code do": a Hindi request verb at the end.
    if words and words[-1] in ("do", "de", "dena", "dijiye", "dedo"):
        score += 1

    if score >= 2:
        return HINGLISH

    default = _setting("DEFAULT_REPLY_LANGUAGE")

    if default in (HINGLISH, HINDI):
        return default

    return ENGLISH


INSTRUCTIONS = {
    ENGLISH: (
        "LANGUAGE: Reply in English."
    ),
    HINDI: (
        "LANGUAGE: Reply in Hindi written in Devanagari script. Keep "
        "technical terms, function names and code in English."
    ),
    HINGLISH: (
        "LANGUAGE: Reply in Hinglish - Hindi written in ROMAN (English) "
        "letters, mixed naturally with English technical words, the way "
        "Indian developers chat. Example: \"Login system mein pehle user "
        "ka password hash karke database mein save karte hain, phir "
        "password_verify() se check hota hai.\" NEVER use Devanagari "
        "script (no हिंदी letters) anywhere in the answer."
    ),
}


def language_instruction(text):
    """One prompt line telling the model which language to use."""

    return INSTRUCTIONS[detect_reply_language(text)]