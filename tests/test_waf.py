import base64
import hashlib
import json

from mayzfact.manual.waf import solve_waf


def challenge_html(prefix: bytes, answer: int) -> str:
    digest = hashlib.sha256(prefix + str(answer).encode()).digest()
    payload = {"v": {"a": base64.b64encode(prefix).decode(), "c": base64.b64encode(digest).decode()}}
    return f'<script>var cs = "{base64.b64encode(json.dumps(payload).encode()).decode()}";</script>'


def test_solve_waf_finds_proof_of_work_answer():
    token = solve_waf(challenge_html(b"abc", 42))
    data = json.loads(base64.b64decode(token))
    assert base64.b64decode(data["d"]) == b"42"


def test_solve_waf_returns_none_without_challenge_or_answer():
    assert solve_waf("<html>biasa</html>") is None
    assert solve_waf(challenge_html(b"abc", 500), max_iter=100) is None
