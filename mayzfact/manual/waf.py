"""WAF proof-of-work Douyin: soal hash yang biasanya diselesaiin JS di browser tanpa interaksi manusia (D-018)."""

from __future__ import annotations

import base64
import hashlib
import json
import re

_CS = re.compile(r'cs\s*=\s*"([^"]+)"')


def solve_waf(html: str, max_iter: int = 1_000_000) -> str | None:
    match = _CS.search(html)
    if not match:
        return None
    try:
        challenge = json.loads(base64.b64decode(match.group(1)).decode("utf-8"))
        prefix = base64.b64decode(challenge["v"]["a"])
        expected = base64.b64decode(challenge["v"]["c"]).hex()
    except (ValueError, KeyError, TypeError):
        return None
    for i in range(max_iter + 1):
        if hashlib.sha256(prefix + str(i).encode()).hexdigest() == expected:
            challenge["d"] = base64.b64encode(str(i).encode()).decode()
            return base64.b64encode(json.dumps(challenge, separators=(",", ":")).encode()).decode()
    return None
