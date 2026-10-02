"""Separate explicit reasoning markup; never decode arbitrary escapes."""
import re

REASONING = re.compile(r"<(think|thought|analysis)\b[^>]*>.*?</\1\s*>", re.I | re.S)
UNFINISHED = re.compile(r"<(?:think|thought|analysis)\b[^>]*>.*$", re.I | re.S)
LEADING_FENCE = re.compile(r"^\s*```(?:xml|text|plaintext)?[ \t]*\r?\n")
OUTER_FENCE = re.compile(r"\s*```(?:xml|text|plaintext|json)?[ \t]*\r?\n(.*?)\r?\n```\s*", re.S)


def final_text(text: str) -> str:
    cleaned, count = REASONING.subn('', text)
    cleaned, unfinished = UNFINISHED.subn('', cleaned)
    if count or unfinished:
        # Some services repeat opening xml fences before every thought block.
        removed = False
        while LEADING_FENCE.match(cleaned):
            cleaned = LEADING_FENCE.sub('', cleaned, count=1)
            removed = True
        if removed:
            cleaned = re.sub(r'\r?\n```\s*$', '', cleaned)
        cleaned = cleaned.strip()
    match = OUTER_FENCE.fullmatch(cleaned)
    return match.group(1).strip() if match else cleaned
