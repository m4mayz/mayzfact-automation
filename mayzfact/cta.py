"""Aturan pemicu CTA like/subscribe/comment: dipakai timeline (animasi) dan check-script (naskah), biar nggak beda."""

from __future__ import annotations

import re

SUBSCRIBE = {"subscribe", "subscribed", "subscribing"}  # bukan "subscribers"/"subscription"
LIKE_BEFORE = {"hit", "smash", "tap", "press", "drop", "leave", "give", "a"}  # "hit like", "drop a like"
LIKE_AFTER = {"and", "&", "or", "comment", "share", "button"} | SUBSCRIBE  # "like and subscribe"
LIKE_AFTER_2 = {("the", "video"), ("this", "video")}  # "like the video"
COMMENT = {"comment", "comments", "commenting"}
_EDGE_PUNCT = re.compile(r"^[^\w']+|[^\w']+$")


def clean(word: str) -> str:
    return _EDGE_PUNCT.sub("", word).lower()


def is_like_cta(tokens: list[str], j: int) -> bool:
    """"like" yang ngajak (hit like, like and subscribe), bukan yang artinya "mirip" (creatures like this)."""
    before = clean(tokens[j - 1]) if j else ""
    after = tokens[j + 1].strip() if j + 1 < len(tokens) else ""
    after_2 = (clean(after), clean(tokens[j + 2])) if j + 2 < len(tokens) else ("", "")
    return clean(tokens[j]) == "like" and (
        tokens[j].rstrip().endswith(",") or before in LIKE_BEFORE or (clean(after) or after) in LIKE_AFTER
        or after_2 in LIKE_AFTER_2)


def cta_kinds(text: str) -> set[str]:
    """CTA apa aja yang kepicu dari teks: subset dari {"like", "subscribe", "comment"}."""
    tokens = text.split()
    found: set[str] = set()
    for j, token in enumerate(tokens):
        word = clean(token)
        if word in SUBSCRIBE:
            found.add("subscribe")
        elif word in COMMENT:
            found.add("comment")
        elif is_like_cta(tokens, j):
            found.add("like")
    return found
