import re
import unicodedata

_PUNCT = ".?!,;:"
_WHITESPACE = re.compile(r"\s+")


def normalize_answer(value: str) -> str:
    """Canonical form for short-answer matching.

    The seeder and the grading path MUST share this function so a stored
    `normalized_value` always matches a user answer normalized the same way.
    """
    text = unicodedata.normalize("NFC", value)
    text = _WHITESPACE.sub(" ", text.strip()).lower()
    return text.strip(_PUNCT).strip()
