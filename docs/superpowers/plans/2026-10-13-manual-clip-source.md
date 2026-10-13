# Manual Clip Source Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Mode `CLIP_SOURCE=manual` (default): pipeline nyiapin brief per shot, Akmal ngisi link atau file lewat halaman lokal, terus pipeline download + pilih bagian terbaik pakai SigLIP dan lanjut ke timeline.

**Architecture:**
- Ada 2 step baru setelah suara: `plan` (daftar shot + frame hook + keyword) dan `fetch` (link/file → media → potongan terbaik → `clips.json`).
- Server brief (`http.server` stdlib) baca/tulis `links.json` dan nerima upload.
- Resolver Douyin/RedNote hasil port dari scrapr, dipakai kalau `yt-dlp` gagal.
- Mode `auto` (Fase 2) tetap jalan.
- `fetch` berhenti pakai `AwaitingInput` (exit code 3) kalau ada shot yang kosong atau gagal.

**Tech Stack:** Python 3.14 (uv), httpx, `http.server`, yt-dlp, SigLIP (open_clip), ffmpeg. Semuanya udah ada di project.

**Spec:** [`docs/superpowers/specs/2026-10-13-manual-clip-source-design.md`](../specs/2026-10-13-manual-clip-source-design.md). Keputusannya ada di D-018 dan D-019.

## Global Constraints

**Test**

- Test otomatis nggak boleh pakai network beneran, browser, atau model SigLIP asli. Server brief dites di `127.0.0.1` port acak.

**Aturan dari fase sebelumnya**

- Step `plan` dan `fetch` masuk `AFTER_VOICE`. `--from plan`/`--from fetch` nggak boleh manggil ElevenLabs.
- Mode `auto` nggak boleh berubah perilakunya, dan test lamanya tetap lolos.

**Server brief**

- Bind cuma ke `127.0.0.1`.
- Upload maksimal 500 MB.
- Ekstensi yang diterima: video `.mp4 .mov .webm .m4v`, gambar `.jpg .jpeg .png .webp`.
- File cuma boleh disajikan dari dalam folder run.

**Angka & batas**

- Fetch: frame tiap 0.5 detik dari 60 detik pertama. Batas peringatan skor rendah: teks 0.10, gambar 0.60.
- Batas anti-bot (D-018): WAF proof-of-work boleh, solve captcha manusia otomatis nggak, proxy/rotasi IP nggak.

**Aturan kerja**

- Pesan ke user pakai bahasa Indonesia santai. Prompt ke Gemini pakai English.
- Kerjain di branch `manual-source`. Commit pakai skill `caveman-commit`, 1 baris, tanpa atribusi AI.
- Abis edit video, jangan render final. Review dulu di Studio.

## Review Focus

1. **Link Douyin/RedNote ada teks share-nya**, misalnya "复制打开抖音… https://v.douyin.com/xxx/ …". Link harus diambil dari teks itu, bukan ditolak. Test: Task 2 (`parse_entry`).
2. **Path upload jahat** (`../../.env`) atau nomor shot di luar plan. Server harus nolak. Test: Task 9.
3. **Link yang sama dipakai di 2 shot.** Download cukup sekali (cache), tapi tiap shot tetap dapat potongan sendiri. Test: Task 5 (cache) dan Task 8.
4. **`#n` lebih besar dari jumlah foto di post.** Shot itu error dengan pesan jelas, bukan crash. Test: Task 8.
5. **Mode `auto` di `.env` lama.** `--from hook` tetap jalan di auto, tapi ditolak dengan pesan jelas di manual. Test: Task 10.

---

## File Structure

```text
mayzfact/
  config.py            (modify) clip_source, brief_port
  store.py             (modify) shots_plan_json, plan_dir, links_json, links_status_json, manual_dir
  errors.py            (modify) AwaitingInput
  models.py            (modify) Translation, Translations
  hook_queries.py      (modify) translate_queries
  prompts/translate_queries.md
  steps/hook.py        (modify) prepare_source_segments (dipisah dari run_hook)
  steps/clips.py       (modify) normalize_local (dipisah dari _hook_entry)
  steps/plan.py        run_plan
  steps/fetch.py       run_fetch
  manual/__init__.py
  manual/links.py      parse_entry, link_kind, load_links, save_links, normalize_links, missing_shots, VIDEO_EXTS, IMAGE_EXTS
  manual/types.py      Media
  manual/waf.py        solve_waf
  manual/douyin.py     resolve_douyin (+ item_id, router_data, find_item, item_media)
  manual/rednote.py    resolve_rednote (+ rednote_state, find_note, note_media)
  manual/og.py         og_media
  manual/obtain.py     cache_key, media_kind, Obtainer
  brief/__init__.py
  brief/page.py        render_page
  brief/server.py      make_server, MAX_UPLOAD
  pipeline.py          (modify) MANUAL_STEPS, ALL_STEPS, plan_steps(steps=), Deps.plan/fetch
  cli.py               (modify) brief command, AwaitingInput → exit 3
tests/ test_manual_links.py test_waf.py test_douyin.py test_rednote_og.py test_obtain.py
       test_plan.py test_fetch.py test_brief_server.py (+ modify test_config, test_store, test_pipeline, test_cli)
```

---

### Task 1: Config, path run, `AwaitingInput`

**Files:**
- Modify: `mayzfact/config.py`, `mayzfact/store.py`, `mayzfact/errors.py`, `.env.example`
- Test: `tests/test_config.py`, `tests/test_store.py`

**Interfaces:**
- Produces:
  - `Settings.clip_source: str = "manual"` (cuma `manual`/`auto`) dan `Settings.brief_port: int = 3100`
  - Property baru di `RunPaths`: `shots_plan_json`, `plan_dir`, `links_json`, `links_status_json`, `manual_dir`
  - `AwaitingInput(PipelineError)`

- [ ] **Step 1: Bikin branch**

```bash
git switch -c manual-source
```

- [ ] **Step 2: Tulis test yang gagal**

Tambahin ke `tests/test_config.py`:

```python
def test_clip_source_and_brief_port():
    settings = settings_from_env({})
    assert (settings.clip_source, settings.brief_port) == ("manual", 3100)
    settings = settings_from_env({"CLIP_SOURCE": "AUTO", "BRIEF_PORT": "3200"})
    assert (settings.clip_source, settings.brief_port) == ("auto", 3200)
    with pytest.raises(PipelineError, match="CLIP_SOURCE"):
        settings_from_env({"CLIP_SOURCE": "kadang"})
```

Tambahin ke `tests/test_store.py`:

```python
def test_run_paths_manual_files(tmp_path):
    from mayzfact.errors import AwaitingInput, PipelineError

    paths = RunPaths(tmp_path)
    assert paths.shots_plan_json == tmp_path / "shots_plan.json"
    assert paths.plan_dir == tmp_path / "plan"
    assert paths.links_json == tmp_path / "links.json"
    assert paths.links_status_json == tmp_path / "links_status.json"
    assert paths.manual_dir == tmp_path / "manual"
    assert issubclass(AwaitingInput, PipelineError)
```

- [ ] **Step 3: Jalanin test, pastiin gagal**

Run: `uv run pytest tests/test_config.py tests/test_store.py -q`
Expected: FAIL dengan `AttributeError ... clip_source` dan `shots_plan_json`.

- [ ] **Step 4: Implementasi**

`mayzfact/config.py`:

- Tambahin field di akhir `Settings`:

```python
    clip_source: str = "manual"  # "manual" | "auto"
    brief_port: int = 3100
```

- Di bawah `_flag`:

```python
def _clip_source(raw: str) -> str:
    value = raw.lower()
    if value not in {"manual", "auto"}:
        raise ValueError(raw)
    return value
```

- Tambahin di akhir `ENV_FIELDS`:

```python
    "CLIP_SOURCE": ("clip_source", _clip_source),
    "BRIEF_PORT": ("brief_port", int),
```

`mayzfact/store.py`: tambahin property ini di `RunPaths`, setelah `hook_json`:

```python
    @property
    def shots_plan_json(self) -> Path:
        return self.root / "shots_plan.json"

    @property
    def plan_dir(self) -> Path:
        return self.root / "plan"

    @property
    def links_json(self) -> Path:
        return self.root / "links.json"

    @property
    def links_status_json(self) -> Path:
        return self.root / "links_status.json"

    @property
    def manual_dir(self) -> Path:
        return self.root / "manual"
```

Tambahin di akhir `mayzfact/errors.py`:

```python
class AwaitingInput(PipelineError):
    """Pipeline berhenti nunggu input manusia (misalnya link klip), bukan error."""
```

Tambahin di akhir `.env.example`:

```dotenv
CLIP_SOURCE=manual
BRIEF_PORT=3100
```

- [ ] **Step 5: Jalanin test, pastiin lolos**

Run: `uv run pytest tests/test_config.py tests/test_store.py -q`
Expected: semua PASS.

- [ ] **Step 6: Commit**

```bash
git add mayzfact/config.py mayzfact/store.py mayzfact/errors.py .env.example tests/test_config.py tests/test_store.py
git commit -m "feat: add clip source setting and manual run paths"
```

---

### Task 2: Model link (`manual/links.py`, `manual/types.py`)

**Files:**
- Create: `mayzfact/manual/__init__.py` (kosong), `mayzfact/manual/types.py`, `mayzfact/manual/links.py`
- Test: `tests/test_manual_links.py`

**Interfaces:**
- Consumes: `read_json`, `write_json_atomic` (store)
- Produces:
  - `Media(kind: str, url: str)` (frozen dataclass, `kind` = `"video"`/`"photo"`)
  - Konstanta `VIDEO_EXTS`, `IMAGE_EXTS`
  - Fungsi:
    - `parse_entry(text) -> tuple[str, int | None]`: ngambil URL pertama dari teks + `#n`
    - `link_kind(url) -> str`: `"douyin"|"rednote"|"tiktok"|"pinterest"|"direct"|"other"`
    - `load_links(path) -> dict` dan `save_links(path, data) -> None`
    - `normalize_links(raw: dict, shot_count: int) -> dict` (bisa raise `ValueError`)
    - `missing_shots(plan: dict, links: dict) -> list[int]` (nomor shot mulai dari 1)

- [ ] **Step 1: Tulis test yang gagal**

`tests/test_manual_links.py`:

```python
import pytest

from mayzfact.manual.links import link_kind, load_links, missing_shots, normalize_links, parse_entry, save_links


def test_parse_entry_extracts_url_from_share_text_and_pick():
    assert parse_entry("https://www.xiaohongshu.com/explore/abc #3") == ("https://www.xiaohongshu.com/explore/abc", 3)
    assert parse_entry("  https://v.douyin.com/iRNBho6u/  ") == ("https://v.douyin.com/iRNBho6u/", None)
    share = "8.97 复制打开抖音，看看【鲎】躲过五次大灭绝 https://v.douyin.com/iRNBho6u/ x@W.zt 09/12"
    assert parse_entry(share) == ("https://v.douyin.com/iRNBho6u/", None)
    assert parse_entry("https://www.tiktok.com/@a/video/1#ref") == ("https://www.tiktok.com/@a/video/1#ref", None)
    assert parse_entry("bukan link") == ("bukan link", None)


@pytest.mark.parametrize(("url", "kind"), [
    ("https://www.douyin.com/video/7694448955383418155", "douyin"),
    ("https://v.douyin.com/iRNBho6u/", "douyin"),
    ("https://www.xiaohongshu.com/explore/66a1b2c3d4e5f6a7b8c9d0e1", "rednote"),
    ("http://xhslink.com/a/xyz", "rednote"),
    ("https://www.tiktok.com/@a/video/1", "tiktok"),
    ("https://id.pinterest.com/pin/123/", "pinterest"),
    ("https://pin.it/abc", "pinterest"),
    ("https://cdn.example.com/a/b.JPG?x=1", "direct"),
    ("https://example.com/clip.mp4", "direct"),
    ("https://example.com/page", "other"),
])
def test_link_kind(url, kind):
    assert link_kind(url) == kind


def test_normalize_links_validates_and_keeps_pick():
    raw = {"shots": {
        "1": {"url": "https://v.douyin.com/x/ #2"},
        "2": {"file": "manual/shot_02.mp4"},
        "3": {"url": "  "},
        "4": {"url": "https://example.com/a.jpg", "pick": 1},
    }}
    assert normalize_links(raw, 4) == {"shots": {
        "1": {"url": "https://v.douyin.com/x/", "pick": 2},
        "2": {"file": "manual/shot_02.mp4"},
        "4": {"url": "https://example.com/a.jpg", "pick": 1},
    }}
    with pytest.raises(ValueError, match="shot 9"):
        normalize_links({"shots": {"9": {"url": "https://a.b/c"}}}, 4)
    with pytest.raises(ValueError, match="http"):
        normalize_links({"shots": {"1": {"url": "ftp://a/b"}}}, 4)
    with pytest.raises(ValueError, match="manual/"):
        normalize_links({"shots": {"1": {"file": "../../.env"}}}, 4)


def test_load_save_and_missing(tmp_path):
    path = tmp_path / "links.json"
    assert load_links(path) == {"shots": {}}
    save_links(path, {"shots": {"2": {"url": "https://a.b/c"}}})
    plan = {"shots": [{"index": 0}, {"index": 1}, {"index": 2}]}
    assert missing_shots(plan, load_links(path)) == [1, 3]
```

- [ ] **Step 2: Jalanin test, pastiin gagal**

Run: `uv run pytest tests/test_manual_links.py -q`
Expected: FAIL dengan `ModuleNotFoundError: No module named 'mayzfact.manual'`.

- [ ] **Step 3: Implementasi**

`mayzfact/manual/__init__.py`: file kosong.

`mayzfact/manual/types.py`:

```python
"""Tipe hasil resolver link manual."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Media:
    kind: str  # "video" | "photo"
    url: str
```

`mayzfact/manual/links.py`:

```python
"""links.json: link/file per shot yang diisi Akmal lewat halaman brief (spec metode manual bagian 4)."""

from __future__ import annotations

import re
from pathlib import Path, PurePosixPath
from urllib.parse import urlparse

from mayzfact.store import read_json, write_json_atomic

VIDEO_EXTS = {".mp4", ".mov", ".webm", ".m4v"}
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}
_URL = re.compile(r"https?://[^\s，。！？、]+", re.IGNORECASE)
_PICK = re.compile(r"\s+#(\d+)\s*$")


def parse_entry(text: str) -> tuple[str, int | None]:
    """'<teks share> https://… #3' → ('https://…', 3). Teks share Douyin/RedNote dibuang."""
    text = text.strip()
    pick = None
    match = _PICK.search(text)
    if match:
        pick = int(match.group(1))
        text = text[: match.start()].strip()
    url = _URL.search(text)
    return (url.group(0) if url else text), pick


def link_kind(url: str) -> str:
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    if "douyin.com" in host or "iesdouyin.com" in host:
        return "douyin"
    if any(h in host for h in ("xiaohongshu.com", "xhslink.com", "xhslink.cn", "rednote.com")):
        return "rednote"
    if "tiktok.com" in host:
        return "tiktok"
    if "pinterest." in host or host == "pin.it":
        return "pinterest"
    if PurePosixPath(parsed.path).suffix.lower() in VIDEO_EXTS | IMAGE_EXTS:
        return "direct"
    return "other"


def load_links(path: Path) -> dict:
    return read_json(path) if path.exists() else {"shots": {}}


def save_links(path: Path, data: dict) -> None:
    write_json_atomic(path, data)


def normalize_links(raw: dict, shot_count: int) -> dict:
    shots: dict[str, dict] = {}
    for key, entry in (raw.get("shots") or {}).items():
        number = int(key)
        if not 1 <= number <= shot_count:
            raise ValueError(f"shot {number} nggak ada di plan (1-{shot_count})")
        if not isinstance(entry, dict):
            continue
        out: dict = {}
        url_text = str(entry.get("url") or "").strip()
        file = str(entry.get("file") or "").strip()
        if url_text:
            url, pick = parse_entry(url_text)
            if not url.lower().startswith(("http://", "https://")):
                raise ValueError(f"shot {number}: link harus diawali http(s)://")
            out["url"] = url
            pick = entry.get("pick") or pick
        elif file:
            if not file.startswith("manual/") or ".." in file:
                raise ValueError(f"shot {number}: file harus di folder manual/")
            out["file"] = file
            pick = entry.get("pick")
        else:
            continue
        if pick:
            out["pick"] = int(pick)
        shots[str(number)] = out
    return {"shots": shots}


def missing_shots(plan: dict, links: dict) -> list[int]:
    filled = links.get("shots", {})
    return [shot["index"] + 1 for shot in plan["shots"] if not filled.get(str(shot["index"] + 1))]
```

- [ ] **Step 4: Jalanin test, pastiin lolos**

Run: `uv run pytest tests/test_manual_links.py -q`
Expected: semua PASS.

- [ ] **Step 5: Commit**

```bash
git add mayzfact/manual tests/test_manual_links.py
git commit -m "feat: add manual links model"
```

---

### Task 3: WAF solver + resolver Douyin

**Files:**
- Create: `mayzfact/manual/waf.py`, `mayzfact/manual/douyin.py`
- Test: `tests/test_waf.py`, `tests/test_douyin.py`

**Interfaces:**
- Consumes: `Media` (Task 2), `PipelineError`
- Produces:
  - `solve_waf(html: str, max_iter: int = 1_000_000) -> str | None`
  - `item_id(text) -> str | None`
  - `router_data(html) -> dict | None`
  - `find_item(data) -> dict | None`
  - `item_media(item) -> list[Media]`
  - `resolve_douyin(url, *, transport=None) -> list[Media]` (bisa raise `PipelineError("fetch", …)`)

- [ ] **Step 1: Tulis test yang gagal**

`tests/test_waf.py`:

```python
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
```

`tests/test_douyin.py`:

```python
import json
from urllib.parse import quote

import httpx

from mayzfact.manual.douyin import find_item, item_id, item_media, resolve_douyin, router_data
from mayzfact.manual.types import Media
from tests.test_waf import challenge_html

VIDEO_ITEM = {"aweme_id": "7694448955383418155", "desc": "鲎",
              "video": {"play_addr": {"url_list": ["http://v26.douyinvod.com/playwm/?video_id=v0200fg&ratio=720p"]}}}
IMAGE_ITEM = {"aweme_id": "7111", "images": [{"url_list": ["http://p3.douyinpic.com/a.jpeg"]},
                                            {"url_list": ["https://p3.douyinpic.com/b.jpeg"]}]}


def router_html(item):
    data = {"loaderData": {"video_(id)/page": {"videoInfoRes": {"item_list": [item]}}}}
    return f"<script>window._ROUTER_DATA = {json.dumps(data)};</script>"


def test_item_id_and_router_data():
    assert item_id("https://www.douyin.com/video/7694448955383418155?x=1") == "7694448955383418155"
    assert item_id("https://www.douyin.com/note/7111222233334444555") == "7111222233334444555"
    assert item_id("https://v.douyin.com/abc/") is None
    assert find_item(router_data(router_html(VIDEO_ITEM)))["aweme_id"] == "7694448955383418155"
    encoded = f'<script id="RENDER_DATA" type="application/json">{quote(json.dumps({"aweme": {"detail": IMAGE_ITEM}}))}</script>'
    assert find_item(router_data(encoded))["aweme_id"] == "7111"
    assert router_data("<html></html>") is None


def test_item_media_prefers_no_watermark_and_lists_photos():
    assert item_media(VIDEO_ITEM) == [
        Media("video", "https://aweme.snssdk.com/aweme/v1/play/?video_id=v0200fg"),
        Media("video", "https://v26.douyinvod.com/play/?video_id=v0200fg&ratio=720p"),
    ]
    assert item_media(IMAGE_ITEM) == [Media("photo", "https://p3.douyinpic.com/a.jpeg"), Media("photo", "https://p3.douyinpic.com/b.jpeg")]


def test_resolve_follows_short_link_and_solves_waf():
    seen = []

    def handler(request):
        seen.append((request.method, request.url.host, request.headers.get("cookie", "")))
        if request.url.host == "ttwid.bytedance.com":
            return httpx.Response(200, headers={"set-cookie": "ttwid=tt123; Path=/"})
        if request.url.host == "v.douyin.com":
            return httpx.Response(302, headers={"location": "https://www.iesdouyin.com/share/video/7694448955383418155/"})
        if "_wafchallengeid" not in request.headers.get("cookie", ""):
            return httpx.Response(200, text=challenge_html(b"pre", 7) + "<div>_wafchallengeid</div>")
        return httpx.Response(200, text=router_html(VIDEO_ITEM))

    media = resolve_douyin("https://v.douyin.com/iRNBho6u/", transport=httpx.MockTransport(handler))
    assert media[0].url.endswith("video_id=v0200fg")
    assert any("ttwid=tt123" in cookie for _, host, cookie in seen if host == "www.iesdouyin.com")


def test_resolve_falls_back_to_iteminfo_api():
    def handler(request):
        if request.url.host == "ttwid.bytedance.com":
            return httpx.Response(200)
        if "iteminfo" in request.url.path:
            return httpx.Response(200, json={"item_list": [IMAGE_ITEM]})
        return httpx.Response(200, text="<html>kosong</html>")

    media = resolve_douyin("https://www.douyin.com/note/7111222233334444555", transport=httpx.MockTransport(handler))
    assert [m.kind for m in media] == ["photo", "photo"]
```

- [ ] **Step 2: Jalanin test, pastiin gagal**

Run: `uv run pytest tests/test_waf.py tests/test_douyin.py -q`
Expected: FAIL dengan `ModuleNotFoundError: No module named 'mayzfact.manual.waf'`.

- [ ] **Step 3: Implementasi**

`mayzfact/manual/waf.py`:

```python
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
```

`mayzfact/manual/douyin.py`:

```python
"""Resolver link Douyin → URL media. Port dari scrapr (MIT): ttwid + data SSR + WAF proof-of-work + API iteminfo."""

from __future__ import annotations

import json
import re
from typing import Any
from urllib.parse import unquote

import httpx

from mayzfact.errors import PipelineError
from mayzfact.manual.types import Media
from mayzfact.manual.waf import solve_waf

MOBILE_UA = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1"
)
_IDS = (
    re.compile(r"(?:video|note|share/(?:video|slides))[/?](\d{15,22})", re.IGNORECASE),
    re.compile(r"(?:modal_id|group_id|aweme_id)=(\d{15,22})", re.IGNORECASE),
)
_MARKERS = ("window._ROUTER_DATA =", "window._SSR_DATA =", "window._RENDER_DATA =", "window.__INIT_PROPS__ =")
_RENDER_DATA = re.compile(r'<script[^>]*id="RENDER_DATA"[^>]*>(.*?)</script>', re.S)


def item_id(text: str) -> str | None:
    for pattern in _IDS:
        match = pattern.search(text or "")
        if match:
            return match.group(1)
    return None


def router_data(html: str) -> dict | None:
    decoder = json.JSONDecoder()
    for marker in _MARKERS:
        start = html.find(marker)
        if start == -1:
            continue
        rest = html[start + len(marker):].lstrip()
        if rest.startswith("%7B"):
            rest = unquote(rest)
        try:
            data, _ = decoder.raw_decode(rest)
            return data
        except ValueError:
            continue
    for block in _RENDER_DATA.findall(html):
        try:
            return json.loads(unquote(block.strip()))
        except ValueError:
            continue
    return None


def find_item(data: Any) -> dict | None:
    if not isinstance(data, dict):
        return None
    for value in (data.get("loaderData") or {}).values():
        items = ((value or {}).get("videoInfoRes") or {}).get("item_list") or []
        if items:
            return items[0]
    detail = (data.get("aweme") or {}).get("detail")
    if detail:
        return detail
    if data.get("item_list"):
        return data["item_list"][0]
    return data.get("aweme_detail")


def _https(url: str) -> str:
    return re.sub(r"^http:", "https:", url)


def item_media(item: dict) -> list[Media]:
    images = item.get("images") or []
    if images:
        out = []
        for image in images:
            urls = (image or {}).get("url_list") or (image or {}).get("download_url_list") or []
            if urls:
                out.append(Media("photo", _https(urls[0])))
        return out
    video = item.get("video") or {}
    urls = ((video.get("play_addr") or {}).get("url_list") or []) + ((video.get("download_addr") or {}).get("url_list") or [])
    if not urls:
        return []
    url = _https(urls[0]).replace("playwm", "play")
    match = re.search(r"video_id=([^&]+)", url)
    out = [Media("video", f"https://aweme.snssdk.com/aweme/v1/play/?video_id={match.group(1)}")] if match else []
    return out + [Media("video", url)]


def resolve_douyin(url: str, *, transport: httpx.BaseTransport | None = None) -> list[Media]:
    headers = {"User-Agent": MOBILE_UA, "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8", "Referer": "https://www.douyin.com/"}
    with httpx.Client(headers=headers, timeout=15.0, transport=transport) as client:
        try:
            client.post(
                "https://ttwid.bytedance.com/ttwid/union/register/",
                json={"region": "cn", "aid": 1768, "needFparam": "0", "service": "www.ixigua.com",
                      "migrate_info": {"ticket": "", "src": "ucp"}, "cbUrlProtocol": "https", "union": True},
            )
        except httpx.HTTPError:
            pass
        target = url
        if "v.douyin.com" in url:
            response = client.get(url)
            target = response.headers.get("location") or url
        iid = item_id(target)
        target = re.sub(r"share/slides/", "share/video/", target)
        response = client.get(target, follow_redirects=True)
        html = response.text
        if "_wafchallengeid" in html:
            token = solve_waf(html)
            if token:
                client.cookies.set("_wafchallengeid", token)
                html = client.get(target, follow_redirects=True).text
        item = find_item(router_data(html))
        iid = iid or item_id(str(response.url)) or item_id(html)
        if not item and iid:
            api = client.get(f"https://www.iesdouyin.com/web/api/v2/aweme/iteminfo/?item_ids={iid}")
            try:
                item = find_item(api.json())
            except ValueError:
                item = None
    if not item:
        raise PipelineError("fetch", "Data Douyin nggak ketemu di halaman. Coba link lain atau upload file-nya.")
    media = item_media(item)
    if not media:
        raise PipelineError("fetch", "Post Douyin ini nggak punya video/foto yang bisa diambil.")
    return media
```

- [ ] **Step 4: Jalanin test, pastiin lolos**

Run: `uv run pytest tests/test_waf.py tests/test_douyin.py -q`
Expected: semua PASS.

- [ ] **Step 5: Commit**

```bash
git add mayzfact/manual/waf.py mayzfact/manual/douyin.py tests/test_waf.py tests/test_douyin.py
git commit -m "feat: add douyin link resolver with waf solver"
```

---

### Task 4: Resolver RedNote + fallback meta `og:`

**Files:**
- Create: `mayzfact/manual/rednote.py`, `mayzfact/manual/og.py`
- Test: `tests/test_rednote_og.py`

**Interfaces:**
- Produces:
  - `rednote_state(html) -> dict | None`
  - `find_note(state) -> dict | None`
  - `note_media(note) -> list[Media]`
  - `resolve_rednote(url, *, transport=None) -> list[Media]`
  - `og_media(url, *, transport=None) -> list[Media]`

- [ ] **Step 1: Tulis test yang gagal**

`tests/test_rednote_og.py`:

```python
import json

import httpx
import pytest

from mayzfact.errors import PipelineError
from mayzfact.manual.og import og_media
from mayzfact.manual.rednote import find_note, note_media, rednote_state, resolve_rednote
from mayzfact.manual.types import Media

VIDEO_NOTE = {"title": "鲎", "video": {"media": {"stream": {"h264": [{"masterUrl": "//sns-video.xhscdn.com/a.mp4"}]}}}}
PHOTO_NOTE = {"title": "鹦鹉螺", "imageList": [{"urlDefault": "//sns-img.xhscdn.com/1.jpg"}, {"urlOriginal": "https://sns-img.xhscdn.com/2.jpg"}]}


def state_html(note):
    state = {"note": {"noteDetailMap": {"abc": {"note": note}}}, "x": "__UNDEF__"}
    raw = json.dumps(state).replace('"__UNDEF__"', "undefined")
    return f"<script>window.__INITIAL_STATE__={raw}</script>"


def test_state_parsing_and_media():
    assert find_note(rednote_state(state_html(VIDEO_NOTE)))["title"] == "鲎"
    assert note_media(VIDEO_NOTE) == [Media("video", "https://sns-video.xhscdn.com/a.mp4")]
    assert note_media(PHOTO_NOTE) == [Media("photo", "https://sns-img.xhscdn.com/1.jpg"), Media("photo", "https://sns-img.xhscdn.com/2.jpg")]
    assert rednote_state("<html></html>") is None


def test_resolve_rednote_reads_note_page():
    transport = httpx.MockTransport(lambda r: httpx.Response(200, text=state_html(PHOTO_NOTE)))
    assert len(resolve_rednote("https://www.xiaohongshu.com/explore/66a1b2c3d4e5f6a7b8c9d0e1", transport=transport)) == 2


def test_resolve_rednote_reports_ip_block():
    def handler(request):
        if "website-login" in request.url.path:
            return httpx.Response(200, text="安全限制 IP at risk")
        return httpx.Response(302, headers={"location": "https://www.xiaohongshu.com/website-login/error?error_code=300012"})

    with pytest.raises(PipelineError, match="upload"):
        resolve_rednote("https://www.xiaohongshu.com/explore/66a1b2c3d4e5f6a7b8c9d0e1", transport=httpx.MockTransport(handler))


def test_og_media():
    html = ('<meta property="og:video" content="https://v.example/a.mp4">'
            '<meta property="og:image" content="//img.example/a.jpg">')
    transport = httpx.MockTransport(lambda r: httpx.Response(200, text=html))
    assert og_media("https://example.com/p", transport=transport) == [
        Media("video", "https://v.example/a.mp4"), Media("photo", "https://img.example/a.jpg")]
    empty = httpx.MockTransport(lambda r: httpx.Response(200, text="<html></html>"))
    assert og_media("https://example.com/p", transport=empty) == []
```

- [ ] **Step 2: Jalanin test, pastiin gagal**

Run: `uv run pytest tests/test_rednote_og.py -q`
Expected: FAIL dengan `ModuleNotFoundError`.

- [ ] **Step 3: Implementasi**

`mayzfact/manual/rednote.py`:

```python
"""Resolver link RedNote → URL media dari window.__INITIAL_STATE__ halaman note. Port dari scrapr (MIT)."""

from __future__ import annotations

import json
import re
from typing import Any

import httpx

from mayzfact.errors import PipelineError
from mayzfact.manual.types import Media

DESKTOP_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
_STATE = re.compile(r"window\.__INITIAL_STATE__\s*=\s*(\{.*?\})\s*;?\s*</script>", re.S)
_NOTE_ID = re.compile(r"/([a-f0-9]{24})", re.IGNORECASE)


def rednote_state(html: str) -> dict | None:
    match = _STATE.search(html)
    if not match:
        return None
    try:
        return json.loads(re.sub(r":\s*undefined", ":null", match.group(1)))
    except ValueError:
        return None


def _is_note(value: Any) -> bool:
    return isinstance(value, dict) and any(value.get(k) for k in ("title", "desc", "imageList", "video"))


def find_note(state: Any) -> dict | None:
    if not isinstance(state, dict):
        return None
    for entry in ((state.get("note") or {}).get("noteDetailMap") or {}).values():
        note = (entry or {}).get("note") or entry
        if _is_note(note):
            return note
    for candidate in ((state.get("noteData") or {}).get("data") or {}).get("noteData"), (state.get("note") or {}).get("firstNote"):
        if _is_note(candidate):
            return candidate
    return None


def _https(url: str) -> str:
    return f"https:{url}" if url.startswith("//") else url


def note_media(note: dict) -> list[Media]:
    stream = (((note.get("video") or {}).get("media") or {}).get("stream")) or {}
    for codec in ("h264", "h265", "h266", "av1"):
        for item in stream.get(codec) or []:
            url = item.get("masterUrl") or (item.get("backupUrls") or [None])[0]
            if url:
                return [Media("video", _https(url))]
    photos = []
    for image in note.get("imageList") or []:
        url = (image or {}).get("urlOriginal") or (image or {}).get("urlDefault") or (image or {}).get("url")
        if url:
            photos.append(Media("photo", _https(url)))
    return photos


def resolve_rednote(url: str, *, transport: httpx.BaseTransport | None = None) -> list[Media]:
    headers = {"User-Agent": DESKTOP_UA, "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"}
    with httpx.Client(headers=headers, timeout=15.0, transport=transport, follow_redirects=True) as client:
        response = client.get(url)
        if "website-login" in str(response.url):
            raise PipelineError("fetch", "RedNote nolak akses (IP diblok / minta login). Save file-nya dari app, terus upload di brief.")
        note = find_note(rednote_state(response.text))
        match = _NOTE_ID.search(str(response.url)) or _NOTE_ID.search(url)
        if not note and match:
            for alt in (f"https://www.xiaohongshu.com/discovery/item/{match.group(1)}", f"https://www.xiaohongshu.com/explore/{match.group(1)}"):
                note = find_note(rednote_state(client.get(alt).text))
                if note:
                    break
    if not note:
        raise PipelineError("fetch", "Data note RedNote nggak ketemu. Coba link lain atau upload file-nya.")
    media = note_media(note)
    if not media:
        raise PipelineError("fetch", "Note RedNote ini nggak punya video/foto yang bisa diambil.")
    return media
```

`mayzfact/manual/og.py`:

```python
"""Fallback umum: ambil og:video / og:image dari halaman."""

from __future__ import annotations

import re

import httpx

from mayzfact.manual.rednote import DESKTOP_UA
from mayzfact.manual.types import Media

_META = re.compile(r'<meta[^>]+(?:property|name)="og:(video(?::url)?|image)"[^>]+content="([^"]+)"', re.IGNORECASE)


def og_media(url: str, *, transport: httpx.BaseTransport | None = None) -> list[Media]:
    with httpx.Client(headers={"User-Agent": DESKTOP_UA}, timeout=15.0, transport=transport, follow_redirects=True) as client:
        html = client.get(url).text
    out: list[Media] = []
    for kind, content in _META.findall(html):
        media_url = f"https:{content}" if content.startswith("//") else content
        out.append(Media("video" if kind.lower().startswith("video") else "photo", media_url))
    return out
```

- [ ] **Step 4: Jalanin test, pastiin lolos**

Run: `uv run pytest tests/test_rednote_og.py -q`
Expected: semua PASS.

- [ ] **Step 5: Commit**

```bash
git add mayzfact/manual/rednote.py mayzfact/manual/og.py tests/test_rednote_og.py
git commit -m "feat: add rednote resolver and og fallback"
```

---

### Task 5: `Obtainer` (link/file → file lokal)

**Files:**
- Create: `mayzfact/manual/obtain.py`
- Test: `tests/test_obtain.py`

**Interfaces:**
- Consumes:
  - `link_kind`, `VIDEO_EXTS`, `IMAGE_EXTS` (Task 2)
  - `resolve_douyin` (Task 3), `resolve_rednote`, `og_media` (Task 4)
  - `run_ytdlp`, `download`, `can_open_image`, `probe` (yang udah ada)
- Produces:
  - `cache_key(url) -> str` (sha1 16 karakter)
  - `media_kind(path) -> "video" | "photo" | None`
  - `Obtainer(cache_dir, client, *, ytdlp=run_ytdlp, resolvers=None, log=print)` dengan method `.obtain(entry: dict, run_root: Path) -> list[Path]`

- [ ] **Step 1: Tulis test yang gagal**

`tests/test_obtain.py`:

```python
import shutil

import httpx
import pytest
from PIL import Image

from mayzfact.errors import PipelineError
from mayzfact.manual.obtain import Obtainer, cache_key, media_kind
from mayzfact.manual.types import Media


def client_serving(files):
    return httpx.Client(transport=httpx.MockTransport(
        lambda r: httpx.Response(200, content=files[r.url.path]) if r.url.path in files else httpx.Response(404)))


def test_media_kind(tmp_path, make_video):
    photo = tmp_path / "a.jpg"
    Image.new("RGB", (8, 8)).save(photo)
    junk = tmp_path / "b.bin"
    junk.write_bytes(b"<html>")
    assert media_kind(photo) == "photo"
    assert media_kind(make_video(320, 240, 1.0)) == "video"
    assert media_kind(junk) is None


def test_uploaded_file_is_used_and_must_stay_in_run(tmp_path):
    run = tmp_path / "run"
    (run / "manual").mkdir(parents=True)
    (run / "manual" / "shot_01.jpg").write_bytes(b"x")
    obtainer = Obtainer(tmp_path / "cache", client_serving({}))
    assert obtainer.obtain({"file": "manual/shot_01.jpg"}, run) == [run / "manual" / "shot_01.jpg"]
    with pytest.raises(PipelineError, match="nggak ketemu"):
        obtainer.obtain({"file": "manual/shot_09.jpg"}, run)


def test_direct_link_downloads_once(tmp_path):
    hits = []

    def handler(request):
        hits.append(request.url.path)
        return httpx.Response(200, content=b"jpg-bytes")

    obtainer = Obtainer(tmp_path / "cache", httpx.Client(transport=httpx.MockTransport(handler)))
    entry = {"url": "https://cdn.example.com/a.jpg"}
    first = obtainer.obtain(entry, tmp_path)
    second = obtainer.obtain(entry, tmp_path)
    assert first == second and first[0].name.startswith(cache_key(entry["url"]))
    assert hits == ["/a.jpg"]


def test_ytdlp_first_then_resolver_then_og(tmp_path, make_video):
    video = make_video(320, 240, 1.0)
    calls = []

    def failing_ytdlp(url, dest, **kwargs):
        calls.append("ytdlp")
        raise PipelineError("fetch", "yt-dlp gagal")

    def douyin_resolver(url):
        calls.append("douyin")
        return [Media("video", "https://cdn.example.com/v.mp4")]

    obtainer = Obtainer(tmp_path / "cache", client_serving({"/v.mp4": video.read_bytes()}),
                        ytdlp=failing_ytdlp, resolvers={"douyin": douyin_resolver, "og": lambda url: []})
    files = obtainer.obtain({"url": "https://www.douyin.com/video/7694448955383418155"}, tmp_path)
    assert calls == ["ytdlp", "douyin"]
    assert files[0].suffix == ".mp4"


def test_photo_post_downloads_all_photos(tmp_path):
    jpg = tmp_path / "src.jpg"
    Image.new("RGB", (8, 8)).save(jpg)
    resolvers = {"rednote": lambda url: [Media("photo", "https://img.example/1.jpg"), Media("photo", "https://img.example/2.webp")],
                 "og": lambda url: []}
    obtainer = Obtainer(tmp_path / "cache", client_serving({"/1.jpg": jpg.read_bytes(), "/2.webp": jpg.read_bytes()}),
                        ytdlp=lambda *a, **k: (_ for _ in ()).throw(PipelineError("fetch", "no video")), resolvers=resolvers)
    files = obtainer.obtain({"url": "https://www.xiaohongshu.com/explore/66a1b2c3d4e5f6a7b8c9d0e1"}, tmp_path)
    assert [f.suffix for f in files] == [".jpg", ".webp"]


def test_all_methods_failing_suggests_upload(tmp_path):
    obtainer = Obtainer(tmp_path / "cache", client_serving({}),
                        ytdlp=lambda *a, **k: (_ for _ in ()).throw(PipelineError("fetch", "ytdlp x")),
                        resolvers={"og": lambda url: []})
    with pytest.raises(PipelineError, match="upload"):
        obtainer.obtain({"url": "https://example.com/page"}, tmp_path)
```

- [ ] **Step 2: Jalanin test, pastiin gagal**

Run: `uv run pytest tests/test_obtain.py -q`
Expected: FAIL dengan `ModuleNotFoundError: No module named 'mayzfact.manual.obtain'`.

- [ ] **Step 3: Implementasi**

`mayzfact/manual/obtain.py`:

```python
"""Link/file dari brief → file media lokal (spec metode manual bagian 5)."""

from __future__ import annotations

import hashlib
from pathlib import Path, PurePosixPath
from typing import Any, Callable
from urllib.parse import urlparse

import httpx

from mayzfact.embed import can_open_image
from mayzfact.errors import PipelineError
from mayzfact.ffmpeg import probe
from mayzfact.manual.douyin import resolve_douyin
from mayzfact.manual.links import IMAGE_EXTS, VIDEO_EXTS, link_kind
from mayzfact.manual.og import og_media
from mayzfact.manual.rednote import resolve_rednote
from mayzfact.manual.types import Media
from mayzfact.net import download
from mayzfact.ytdlp import run_ytdlp

YTDLP_TIMEOUT_S = 300


def cache_key(url: str) -> str:
    return hashlib.sha1(url.encode("utf-8")).hexdigest()[:16]


def media_kind(path: Path) -> str | None:
    if can_open_image(path):
        return "photo"
    try:
        info = probe(path, "fetch")
    except PipelineError:
        return None
    return "video" if info.get("width") and (info.get("duration_s") or 0) > 0 else None


def _suffix(url: str, default: str) -> str:
    suffix = PurePosixPath(urlparse(url).path).suffix.lower()
    return suffix if suffix in VIDEO_EXTS | IMAGE_EXTS else default


class Obtainer:
    def __init__(
        self,
        cache_dir: Path,
        client: httpx.Client,
        *,
        ytdlp: Callable[..., Path] = run_ytdlp,
        resolvers: dict[str, Callable[[str], list[Media]]] | None = None,
        log: Callable[[str], None] = print,
    ) -> None:
        self._cache = cache_dir
        self._client = client
        self._ytdlp = ytdlp
        self._resolvers = resolvers or {"douyin": resolve_douyin, "rednote": resolve_rednote, "og": og_media}
        self._log = log

    def obtain(self, entry: dict, run_root: Path) -> list[Path]:
        if entry.get("file"):
            path = (run_root / entry["file"]).resolve()
            if run_root.resolve() not in path.parents or not path.exists():
                raise PipelineError("fetch", f"File upload {entry['file']} nggak ketemu. Upload ulang di brief.")
            return [path]
        url = entry["url"]
        key = cache_key(url)
        cached = sorted(self._cache.glob(f"{key}_*"))
        cached = [p for p in cached if not p.name.endswith((".part", ".tmp.mp4"))]
        if cached:
            return cached
        kind = link_kind(url)
        if kind == "direct":
            return [download(self._client, url, self._cache / f"{key}_0{_suffix(url, '.bin')}", step="fetch")]
        errors: list[str] = []
        try:
            return [self._ytdlp(url, self._cache / f"{key}_0.mp4", step="fetch", timeout_s=YTDLP_TIMEOUT_S)]
        except PipelineError as exc:
            errors.append(f"yt-dlp: {exc.message.splitlines()[0][:120]}")
        for name in [kind, "og"]:
            resolver: Any = self._resolvers.get(name)
            if resolver is None:
                continue
            try:
                media = resolver(url)
            except (PipelineError, httpx.HTTPError) as exc:
                errors.append(f"{name}: {getattr(exc, 'message', str(exc))[:120]}")
                continue
            if media:
                return self._download(media, key)
        raise PipelineError("fetch", f"Link {kind} nggak bisa di-download ({'; '.join(errors)}). Coba link lain atau upload file-nya.")

    def _download(self, media: list[Media], key: str) -> list[Path]:
        videos = [m for m in media if m.kind == "video"]
        if videos:
            last = None
            for item in videos:
                try:
                    return [download(self._client, item.url, self._cache / f"{key}_0.mp4", step="fetch")]
                except PipelineError as exc:
                    last = exc
            raise last  # type: ignore[misc]
        return [
            download(self._client, item.url, self._cache / f"{key}_{i}{_suffix(item.url, '.jpg')}", step="fetch")
            for i, item in enumerate(media)
        ]
```

- [ ] **Step 4: Jalanin test, pastiin lolos**

Run: `uv run pytest tests/test_obtain.py -q`
Expected: semua PASS.

- [ ] **Step 5: Commit**

```bash
git add mayzfact/manual/obtain.py tests/test_obtain.py
git commit -m "feat: obtain media files from manual links"
```

---

### Task 6: Refactor yang bisa dipakai bareng (`normalize_local`, `prepare_source_segments`)

**Files:**
- Modify: `mayzfact/steps/clips.py`, `mayzfact/steps/hook.py`
- Test: test lama (`tests/test_clips_hook.py`, `tests/test_hook.py`) + test baru di `tests/test_clips_hook.py`

**Interfaces:**
- Produces:
  - `clips.normalize_local(index, start_s, end_s, raw: Path, kind: str, offset_s: float, paths: RunPaths, fg_min_ratio: float) -> dict`. Balikin `{"kind","file","width","height"}`, dan raise `PipelineError` kalau video kependekan atau gagal diproses.
  - `hook.prepare_source_segments(paths, source, download_source, hook_seconds, out_dir: Path, retry_step: str = "hook") -> list[dict]`. Tiap item `{"index","start_s","end_s","frames": list[Path],"transcript": str}`.

- [ ] **Step 1: Tulis test yang gagal**

Tambahin ke `tests/test_clips_hook.py`:

```python
def test_normalize_local_clamps_offset_and_rejects_short_video(tmp_path, make_video):
    import pytest

    from mayzfact.errors import PipelineError
    from mayzfact.steps.clips import normalize_local

    paths = RunPaths(tmp_path / "run")
    out = normalize_local(2, 4.0, 6.0, make_video(1080, 1920, 5.0), "video", 4.9, paths, 0.5)
    assert out["file"] == "clips/shot_03.mp4" and out["kind"] == "video"
    assert abs(probe(paths.root / out["file"], "clips")["duration_s"] - 2.2) < 0.1
    with pytest.raises(PipelineError, match="cuma"):
        normalize_local(0, 0.0, 3.0, make_video(1080, 1920, 1.0), "video", 0.0, paths, 0.5)
```

Tambahin ke `tests/test_hook.py`:

```python
def test_prepare_source_segments_writes_frames_to_out_dir(tmp_path, cut_video, make_photo):
    from mayzfact.steps.hook import prepare_source_segments

    paths = RunPaths(tmp_path / "run")
    segs = prepare_source_segments(paths, SOURCE, lambda vid, dest: shutil.copyfile(cut_video, dest) or dest, 10.0, paths.root / "plan")
    assert len(segs) == 2
    assert all(len(s["frames"]) == 3 and s["frames"][0].parent.name == "plan" for s in segs)
    assert segs[0]["transcript"] == "five ancient creatures"
```

- [ ] **Step 2: Jalanin test, pastiin gagal**

Run: `uv run pytest tests/test_clips_hook.py tests/test_hook.py -q`
Expected: FAIL dengan `ImportError: cannot import name 'normalize_local'` dan `'prepare_source_segments'`.

- [ ] **Step 3: Implementasi**

Di `mayzfact/steps/clips.py`, tambahin fungsi ini di atas `_hook_entry`, terus ganti isi `_hook_entry` biar make fungsi itu:

```python
def normalize_local(
    index: int, start_s: float, end_s: float, raw: Path, kind: str, offset_s: float, paths: RunPaths, fg_min_ratio: float
) -> dict:
    """File lokal → clips/shot_XX. Video dipotong di sekitar offset_s, dibatasi biar nggak lewat ujung file."""
    duration_s = end_s - start_s
    try:
        if kind == "video":
            info = probe(raw, "clips")
            total = info["duration_s"] or 0.0
            if total < duration_s + 0.2:
                raise PipelineError("clips", f"video cuma {total:.1f} detik, shot butuh {duration_s:.1f}")
            start = min(max(0.0, offset_s - duration_s / 2), total - duration_s - 0.2)
            dest = paths.clips_dir / f"shot_{index + 1:02d}.mp4"
            normalize_video(raw, dest, start_s=start, duration_s=duration_s + 0.2,
                            scale=downscale_factor(info["width"], info["height"], fg_min_ratio))
            out = probe(dest, "clips")
            width, height = out["width"], out["height"]
        else:
            dest = paths.clips_dir / f"shot_{index + 1:02d}.jpg"
            width, height = normalize_photo(raw, dest, fg_min_ratio=fg_min_ratio)
    except (OSError, ValueError, KeyError) as exc:
        raise PipelineError("clips", f"{raw.name} gagal diproses: {exc}") from exc
    return {"kind": kind, "file": f"clips/{dest.name}", "width": width, "height": height}


def _hook_entry(slot: ShotSlot, segment: dict, paths: RunPaths, fg_min_ratio: float, log: Callable[[str], None]) -> dict | None:
    winner = segment["winner"]
    try:
        out = normalize_local(slot.index, slot.start_s, slot.end_s, paths.root / winner["file"], winner["kind"],
                              winner["offset_s"], paths, fg_min_ratio)
    except PipelineError as exc:
        log(f"[clips] hook segmen {segment['index'] + 1} gagal dipakai, pakai klip biasa: {exc.message}")
        return None
    return {
        "index": slot.index, "beat": slot.beat, "start_s": slot.start_s, "end_s": slot.end_s, **out,
        "provider": winner["provider"], "provider_id": winner["provider_id"],
        "page_url": winner["page_url"], "author": winner["author"],
        "query": f"hook:{segment['index']}", "hook_segment": segment["index"], "match": winner["label"],
    }
```

Di `mayzfact/steps/hook.py`, tambahin fungsi ini di atas `run_hook`:

```python
def prepare_source_segments(
    paths: RunPaths, source: dict, download_source: Callable[[str, Path], Path], hook_seconds: float,
    out_dir: Path, retry_step: str = "hook",
) -> list[dict]:
    """Download source (kalau belum ada), deteksi segmen di hook_seconds awal, ambil 3 frame per segmen ke out_dir."""
    src = paths.source_mp4
    out_dir.mkdir(parents=True, exist_ok=True)
    try:
        if not src.exists():
            download_source(source["video_id"], src)
        end_s = min(hook_seconds, probe(src, "hook")["duration_s"] or 0.0)
        segs = segments(merge_cuts(detect_cuts(src, end_s)), end_s)
    except PipelineError as exc:
        raise PipelineError(
            retry_step, f"{exc.message}\nUlang step ini pakai: mayzfact run {source['video_id']} --from {retry_step}"
        ) from exc
    out = []
    for i, (start, end) in enumerate(segs):
        frames = [
            extract_frame(src, start + (end - start) * pos, out_dir / f"seg_{i + 1:02d}_{k}.jpg")
            for k, pos in enumerate(FRAME_POSITIONS)
        ]
        out.append({"index": i, "start_s": start, "end_s": end, "frames": frames,
                    "transcript": transcript_near(source["transcript"], start, end)})
    return out
```

Bagian awal `run_hook`, mulai dari `src = paths.source_mp4` sampai sebelum `deps.log(f"[hook] {len(segs)} segmen…`, diganti jadi:

```python
    segs_info = prepare_source_segments(paths, source, deps.download_source, hook_seconds, paths.hook_dir)
    end_s = segs_info[-1]["end_s"] if segs_info else 0.0
    infos = [{k: s[k] for k in ("index", "start_s", "end_s", "transcript")} for s in segs_info]
    seg_frames = [s["frames"] for s in segs_info]
    segs = [(s["start_s"], s["end_s"]) for s in segs_info]
```

- [ ] **Step 4: Jalanin test, pastiin lolos**

Run: `uv run pytest tests/test_clips_hook.py tests/test_hook.py tests/test_clips_step.py -q`
Expected: semua PASS.

- [ ] **Step 5: Commit**

```bash
git add mayzfact/steps/clips.py mayzfact/steps/hook.py tests/test_clips_hook.py tests/test_hook.py
git commit -m "refactor: share local clip normalization and source segment prep"
```

---

### Task 7: Terjemahan keyword + step `plan`

**Files:**
- Modify: `mayzfact/models.py`, `mayzfact/hook_queries.py`
- Create: `mayzfact/prompts/translate_queries.md`, `mayzfact/steps/plan.py`
- Test: `tests/test_hook_queries.py`, `tests/test_plan.py`

**Interfaces:**
- Consumes:
  - `prepare_source_segments` (Task 6)
  - `split_shots`, `beat_subjects` (clips), `beat_timings`, `beat_texts`
  - `hook_slot_map` (matching)
- Produces:
  - Model `Translation(en: str, zh: str)` dan `Translations(items: list[Translation])`
  - `translate_queries(writer, queries: list[str], log=print) -> dict[str, str]`
  - `run_plan(paths, script, tts, source, *, max_shot_s, hook_seconds, download_source, describe, translate, log=print) -> dict`. Format output sesuai spec bagian 3.

- [ ] **Step 1: Tulis test yang gagal**

Tambahin ke `tests/test_hook_queries.py`:

```python
def test_translate_queries_maps_en_to_zh_and_falls_back():
    from mayzfact.hook_queries import translate_queries
    from mayzfact.models import Translation, Translations

    writer = FakeWriter(Translations(items=[Translation(en="horseshoe crab", zh=" 鲎 "), Translation(en="unknown", zh="x")]))
    assert translate_queries(writer, ["horseshoe crab", "fossil"], log=lambda m: None) == {"horseshoe crab": "鲎"}
    assert writer.calls[0][3] == "plan"
    assert translate_queries(FakeWriter(error=PipelineError("plan", "503")), ["a"], log=lambda m: None) == {}
    assert translate_queries(None, ["a"]) == {}
```

`tests/test_plan.py`:

```python
import shutil

from mayzfact.steps.plan import run_plan
from mayzfact.store import RunPaths, read_json
from tests.factories import fake_alignment

SCRIPT = {
    "beats": [
        {"text": "Look at this.", "media": "video", "queries": ["crab"], "subject": ""},
        {"text": "Number five, horseshoe crab.", "media": "photo", "queries": ["fossil", "crab"]},
    ],
    "fallback_query": "animals",
}
TTS = {"duration_s": 3.0, "alignment": fake_alignment("Look at this. Number five, horseshoe crab.", 2.4)}
SOURCE = {"video_id": "abc", "duration_s": 2.0, "transcript": [{"text": "five ancient creatures", "start": 0.0, "duration": 2.0}]}


def plan_with(tmp_path, cut_video, hook_seconds):
    paths = RunPaths(tmp_path / "run")
    data = run_plan(
        paths, SCRIPT, TTS, SOURCE, max_shot_s=2.5, hook_seconds=hook_seconds,
        download_source=lambda vid, dest: shutil.copyfile(cut_video, dest) or dest,
        describe=lambda infos, frames: {0: {"en": ["horseshoe crab beach"], "zh": ["鲎 海滩"]}},
        translate=lambda queries: {"fossil": "化石", "crab": "螃蟹"},
        log=lambda m: None,
    )
    return paths, data


def test_plan_marks_hook_shots_with_reference_frames(tmp_path, cut_video):
    paths, data = plan_with(tmp_path, cut_video, hook_seconds=1.5)
    assert read_json(paths.shots_plan_json) == data
    first, second = data["shots"]
    assert first["hook_segment"] == 0
    assert first["keywords"] == {"en": ["horseshoe crab beach"], "zh": ["鲎 海滩"]}
    assert len(first["ref_frames"]) == 3 and (paths.root / first["ref_frames"][0]).exists()
    assert second["hook_segment"] is None and second["ref_frames"] == []
    assert second["keywords"] == {"en": ["fossil", "crab"], "zh": ["化石", "螃蟹"]}
    assert second["subject"] == "horseshoe crab"
    assert (second["start_s"], second["end_s"], second["text"]) == (1.4, 3.0, "Number five, horseshoe crab.")
    assert data["segments"][0]["frames"][0] == "plan/seg_01_0.jpg"


def test_plan_without_hook_area(tmp_path, cut_video):
    _, data = plan_with(tmp_path, cut_video, hook_seconds=0.0)
    assert all(shot["hook_segment"] is None for shot in data["shots"])
```

- [ ] **Step 2: Jalanin test, pastiin gagal**

Run: `uv run pytest tests/test_hook_queries.py tests/test_plan.py -q`
Expected: FAIL dengan `ImportError: cannot import name 'translate_queries'` dan `No module named 'mayzfact.steps.plan'`.

- [ ] **Step 3: Implementasi**

Tambahin ke `mayzfact/models.py`:

```python
class Translation(BaseModel):
    en: str
    zh: str


class Translations(BaseModel):
    items: list[Translation]
```

`mayzfact/prompts/translate_queries.md`:

```markdown
You translate English stock-footage search queries into short Simplified Chinese queries, the way a Douyin or Xiaohongshu user would type them when looking for that clip.

You get a JSON list of English queries. Return one item per query with "en" copied exactly as given and "zh" as the Chinese query (2 to 8 characters or words, no punctuation, no hashtags).
```

Tambahin ke `mayzfact/hook_queries.py` (import `json` di blok atas):

```python
TRANSLATE_PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "translate_queries.md"


def translate_queries(writer: HookQueryWriter | None, queries: list[str], log: Callable[[str], None] = print) -> dict[str, str]:
    if writer is None or not queries:
        return {}
    from mayzfact.models import Translations

    try:
        result = writer.generate(
            TRANSLATE_PROMPT_PATH.read_text(encoding="utf-8"), json.dumps(queries, ensure_ascii=False), Translations, step="plan"
        )
    except PipelineError as exc:
        log(f"[plan] Gemini gagal nerjemahin keyword, kolom 中文 dikosongin: {exc.message[:120]}")
        return {}
    wanted = set(queries)
    return {item.en: item.zh.strip() for item in result.items if item.en in wanted and item.zh.strip()}
```

`mayzfact/steps/plan.py`:

```python
"""Step plan (mode manual): daftar shot + frame referensi hook + keyword buat brief (spec metode manual bagian 3)."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from mayzfact.matching import hook_slot_map
from mayzfact.steps.clips import beat_subjects, split_shots
from mayzfact.steps.hook import prepare_source_segments
from mayzfact.store import RunPaths, write_json_atomic
from mayzfact.text import beat_texts
from mayzfact.timing import beat_timings


def run_plan(
    paths: RunPaths,
    script: dict,
    tts: dict,
    source: dict,
    *,
    max_shot_s: float,
    hook_seconds: float,
    download_source: Callable[[str, Path], Path],
    describe: Callable[[list[dict], list[Path]], dict[int, dict]],
    translate: Callable[[list[str]], dict[str, str]],
    log: Callable[[str], None] = print,
) -> dict:
    beats = script["beats"]
    slots = split_shots(beat_timings(beat_texts(beats), tts["alignment"], tts["duration_s"]), beats, max_shot_s)
    subjects = beat_subjects(beats)
    segs = prepare_source_segments(paths, source, download_source, hook_seconds, paths.plan_dir, retry_step="plan") if hook_seconds > 0 else []
    mapping = hook_slot_map(slots, len(segs), hook_seconds)
    infos = [{k: s[k] for k in ("index", "start_s", "end_s", "transcript")} for s in segs]
    hook_keywords = describe(infos, [s["frames"][1] for s in segs]) if mapping else {}
    zh = translate(sorted({q for beat in beats for q in beat["queries"]}))

    def rel(path: Path) -> str:
        return path.relative_to(paths.root).as_posix()

    shots = []
    for slot in slots:
        beat = beats[slot.beat]
        segment = mapping.get(slot.index)
        if segment is not None:
            keywords = hook_keywords.get(segment, {"en": [], "zh": []})
            ref_frames = [rel(f) for f in segs[segment]["frames"]]
        else:
            keywords = {"en": list(beat["queries"]), "zh": [zh[q] for q in beat["queries"] if zh.get(q)]}
            ref_frames = []
        shots.append({
            "index": slot.index, "beat": slot.beat, "start_s": slot.start_s, "end_s": slot.end_s, "media": slot.media,
            "text": beat["text"], "subject": subjects[slot.beat], "hook_segment": segment,
            "ref_frames": ref_frames, "keywords": keywords,
        })
    data = {
        "hook_seconds": hook_seconds,
        "segments": [{"index": s["index"], "start_s": s["start_s"], "end_s": s["end_s"], "frames": [rel(f) for f in s["frames"]]} for s in segs],
        "shots": shots,
    }
    write_json_atomic(paths.shots_plan_json, data)
    log(f"[plan] {len(shots)} shot ({len(mapping)} hook). Isi link: mayzfact brief {paths.root.name}")
    return data
```

- [ ] **Step 4: Jalanin test, pastiin lolos**

Run: `uv run pytest tests/test_hook_queries.py tests/test_plan.py -q`
Expected: semua PASS.

- [ ] **Step 5: Commit**

```bash
git add mayzfact/models.py mayzfact/hook_queries.py mayzfact/prompts/translate_queries.md mayzfact/steps/plan.py tests/test_hook_queries.py tests/test_plan.py
git commit -m "feat: add plan step with shot list and keywords"
```

---

### Task 8: Step `fetch`

**Files:**
- Create: `mayzfact/steps/fetch.py`
- Test: `tests/test_fetch.py`

**Interfaces:**
- Consumes:
  - `load_links`, `missing_shots`, `link_kind` (Task 2)
  - `cache_key`, `media_kind` (Task 5)
  - `normalize_local` (Task 6)
  - `sample_frames`, `mean_unit`, `AwaitingInput`
- Produces:
  - `run_fetch(paths, plan, *, obtain: Callable[[dict, Path], list[Path]], encoder, fg_min_ratio, log=print) -> dict`
  - Konstanta `LOW_TEXT_SCORE`, `LOW_IMAGE_SCORE`, `SAMPLE_EVERY_S`, `SAMPLE_MAX_S`

- [ ] **Step 1: Tulis test yang gagal**

`tests/test_fetch.py`:

```python
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from mayzfact.embed import unit
from mayzfact.errors import AwaitingInput
from mayzfact.manual.links import save_links
from mayzfact.steps.fetch import run_fetch
from mayzfact.store import RunPaths, read_json

E = np.eye(3, dtype=np.float32)


class FakeEncoder:
    """Gambar: vektor dari nama file. Frame video f_0003 = E0, lainnya E2. Teks 'crab' = E1."""

    def images(self, paths):
        out = []
        for p in map(Path, paths):
            if p.name.startswith("seg_") or p.stem in {"good", "f_0003"}:
                out.append(E[0])
            elif p.stem == "crab":
                out.append(E[1])
            else:
                out.append(E[2])
        return unit(np.stack(out))

    def texts(self, texts):
        return unit(np.stack([E[1] if "crab" in t else E[2] for t in texts]))


def make_plan(paths):
    (paths.root / "plan").mkdir(parents=True)
    for k in range(3):
        Image.new("RGB", (8, 8)).save(paths.root / "plan" / f"seg_01_{k}.jpg")
    return {"shots": [
        {"index": 0, "beat": 0, "start_s": 0.0, "end_s": 1.5, "media": "video", "text": "Look.", "subject": None,
         "hook_segment": 0, "ref_frames": [f"plan/seg_01_{k}.jpg" for k in range(3)], "keywords": {"en": [], "zh": []}},
        {"index": 1, "beat": 1, "start_s": 1.5, "end_s": 3.0, "media": "photo", "text": "Number five, horseshoe crab.",
         "subject": "horseshoe crab", "hook_segment": None, "ref_frames": [], "keywords": {"en": ["crab"], "zh": []}},
    ]}


def photos(tmp_path, *names):
    out = []
    for name in names:
        path = tmp_path / "media" / f"{name}.jpg"
        path.parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (1200, 800), "white").save(path)
        out.append(path)
    return out


def test_missing_links_stop_with_awaiting_input(tmp_path):
    paths = RunPaths(tmp_path / "run")
    plan = make_plan(paths)
    save_links(paths.links_json, {"shots": {"1": {"url": "https://a.b/v.mp4"}}})
    with pytest.raises(AwaitingInput, match="2"):
        run_fetch(paths, plan, obtain=lambda e, r: [], encoder=FakeEncoder(), fg_min_ratio=0.5, log=lambda m: None)
    status = read_json(paths.links_status_json)["shots"]
    assert status["2"]["state"] == "missing"
    assert not paths.clips_json.exists()


def test_fetch_picks_best_video_offset_and_best_photo(tmp_path, cut_video):
    paths = RunPaths(tmp_path / "run")
    plan = make_plan(paths)
    save_links(paths.links_json, {"shots": {"1": {"url": "https://www.douyin.com/video/1"}, "2": {"url": "https://x.com/post"}}})
    files = {"https://www.douyin.com/video/1": [cut_video], "https://x.com/post": photos(tmp_path, "other", "crab")}
    data = run_fetch(paths, plan, obtain=lambda e, r: files[e["url"]], encoder=FakeEncoder(), fg_min_ratio=0.5, log=lambda m: None)
    first, second = data["shots"]
    assert (first["kind"], first["provider"], first["hook_segment"], first["match"]) == ("video", "douyin", 0, 1.0)
    assert (second["kind"], second["provider"], second["query"]) == ("photo", "other", "manual")
    assert second["match"] == 1.0
    assert read_json(paths.clips_json) == data
    assert read_json(paths.links_status_json)["shots"]["2"]["state"] == "ok"


def test_pick_number_and_errors_are_reported(tmp_path):
    paths = RunPaths(tmp_path / "run")
    plan = make_plan(paths)
    save_links(paths.links_json, {"shots": {"1": {"url": "https://a.b/p", "pick": 5}, "2": {"url": "https://a.b/q", "pick": 1}}})
    two = photos(tmp_path, "other", "crab")
    with pytest.raises(AwaitingInput, match="1"):
        run_fetch(paths, plan, obtain=lambda e, r: two, encoder=FakeEncoder(), fg_min_ratio=0.5, log=lambda m: None)
    status = read_json(paths.links_status_json)["shots"]
    assert status["1"]["state"] == "error" and "#5" in status["1"]["message"]
    assert status["2"]["state"] == "ok" and "skor rendah" in status["2"]["message"]


def test_same_link_in_two_shots_gets_two_clips(tmp_path):
    paths = RunPaths(tmp_path / "run")
    plan = make_plan(paths)
    save_links(paths.links_json, {"shots": {"1": {"url": "https://a.b/p"}, "2": {"url": "https://a.b/p"}}})
    shared = photos(tmp_path, "good", "crab")
    data = run_fetch(paths, plan, obtain=lambda e, r: shared, encoder=FakeEncoder(), fg_min_ratio=0.5, log=lambda m: None)
    assert [s["file"] for s in data["shots"]] == ["clips/shot_01.jpg", "clips/shot_02.jpg"]
```

- [ ] **Step 2: Jalanin test, pastiin gagal**

Run: `uv run pytest tests/test_fetch.py -q`
Expected: FAIL dengan `ModuleNotFoundError: No module named 'mayzfact.steps.fetch'`.

- [ ] **Step 3: Implementasi**

`mayzfact/steps/fetch.py`:

```python
"""Step fetch (mode manual): link/file dari brief → potongan terbaik → clips.json (spec metode manual bagian 5)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

import numpy as np

from mayzfact.embed import Encoder, mean_unit
from mayzfact.errors import AwaitingInput, PipelineError
from mayzfact.ffmpeg import sample_frames
from mayzfact.manual.links import link_kind, load_links, missing_shots
from mayzfact.manual.obtain import cache_key, media_kind
from mayzfact.steps.clips import normalize_local
from mayzfact.store import RunPaths, write_json_atomic

LOW_TEXT_SCORE = 0.10
LOW_IMAGE_SCORE = 0.60
SAMPLE_EVERY_S = 0.5
SAMPLE_MAX_S = 60.0


def _target(shot: dict, paths: RunPaths, encoder: Encoder) -> tuple[np.ndarray, float]:
    if shot["ref_frames"]:
        return mean_unit(encoder.images([paths.root / f for f in shot["ref_frames"]])), LOW_IMAGE_SCORE
    text = shot.get("subject") or (shot["keywords"]["en"] or [shot["text"]])[0]
    return encoder.texts([text])[0], LOW_TEXT_SCORE


def _choose(shot: dict, entry: dict, files: list[Path], paths: RunPaths, encoder: Encoder) -> tuple[Path, str, float, float]:
    target, _ = _target(shot, paths, encoder)
    kinds = [(f, media_kind(f)) for f in files]
    videos = [f for f, k in kinds if k == "video"]
    photos = [f for f, k in kinds if k == "photo"]
    pick = entry.get("pick")
    if pick and photos:
        if pick > len(photos):
            raise PipelineError("fetch", f"Post ini cuma punya {len(photos)} foto, tapi diminta #{pick}.")
        chosen = photos[pick - 1]
        return chosen, "photo", float(encoder.images([chosen])[0] @ target), 0.0
    if videos:
        frames = sample_frames(videos[0], paths.plan_dir / "fetch" / f"shot_{shot['index'] + 1:02d}",
                               every_s=SAMPLE_EVERY_S, max_s=SAMPLE_MAX_S)
        if not frames:
            raise PipelineError("fetch", "Video-nya nggak punya frame yang bisa dibaca.")
        sims = encoder.images([p for _, p in frames]) @ target
        best = int(np.argmax(sims))
        return videos[0], "video", float(sims[best]), frames[best][0]
    if photos:
        sims = encoder.images(photos) @ target
        best = int(np.argmax(sims))
        return photos[best], "photo", float(sims[best]), 0.0
    raise PipelineError("fetch", "File-nya bukan video/gambar yang bisa dibaca.")


def run_fetch(
    paths: RunPaths,
    plan: dict,
    *,
    obtain: Callable[[dict, Path], list[Path]],
    encoder: Encoder | Any,
    fg_min_ratio: float,
    log: Callable[[str], None] = print,
) -> dict:
    links = load_links(paths.links_json)
    missing = set(missing_shots(plan, links))
    paths.clips_dir.mkdir(parents=True, exist_ok=True)
    for old in paths.clips_dir.glob("shot_*"):
        old.unlink()
    status: dict[str, dict] = {}
    problems: list[int] = []
    clips = []
    for shot in plan["shots"]:
        number = shot["index"] + 1
        if number in missing:
            status[str(number)] = {"state": "missing", "message": "belum diisi"}
            problems.append(number)
            continue
        entry = links["shots"][str(number)]
        try:
            raw, kind, score, offset = _choose(shot, entry, obtain(entry, paths.root), paths, encoder)
            out = normalize_local(shot["index"], shot["start_s"], shot["end_s"], raw, kind, offset, paths, fg_min_ratio)
        except PipelineError as exc:
            status[str(number)] = {"state": "error", "message": exc.message[:300]}
            problems.append(number)
            log(f"[fetch] shot {number}: {exc.message.splitlines()[0][:120]}")
            continue
        _, low = _target(shot, paths, encoder)
        url = entry.get("url")
        clips.append({
            "index": shot["index"], "beat": shot["beat"], "start_s": shot["start_s"], "end_s": shot["end_s"], **out,
            "provider": link_kind(url) if url else "upload", "provider_id": cache_key(url) if url else Path(entry["file"]).name,
            "page_url": url or entry["file"], "author": "", "query": "manual",
            "match": round(score, 4), "hook_segment": shot["hook_segment"],
        })
        status[str(number)] = {
            "state": "ok", "score": round(score, 4),
            "message": f"skor rendah ({score:.2f}), mungkin kurang cocok" if score < low else "",
        }
        log(f"[fetch] shot {number}: {kind} skor {score:.3f}")
    write_json_atomic(paths.links_status_json, {"shots": status})
    if problems:
        raise AwaitingInput(
            "fetch",
            f"{len(problems)} shot perlu diisi/diganti: {', '.join(map(str, sorted(problems)))}. "
            f"Buka: mayzfact brief {paths.root.name}",
        )
    data = {"shots": clips}
    write_json_atomic(paths.clips_json, data)
    return data
```

- [ ] **Step 4: Jalanin test, pastiin lolos**

Run: `uv run pytest tests/test_fetch.py -q`
Expected: semua PASS.

- [ ] **Step 5: Commit**

```bash
git add mayzfact/steps/fetch.py tests/test_fetch.py
git commit -m "feat: add fetch step for manual links"
```

---

### Task 9: Halaman brief + server lokal

**Files:**
- Create: `mayzfact/brief/__init__.py` (kosong), `mayzfact/brief/page.py`, `mayzfact/brief/server.py`
- Test: `tests/test_brief_server.py`

**Interfaces:**
- Consumes:
  - `load_links`, `save_links`, `normalize_links`, `missing_shots`, `VIDEO_EXTS`, `IMAGE_EXTS` (Task 2)
  - `RunPaths` (Task 1)
- Produces:
  - `render_page(run_id: str, plan: dict, links: dict, status: dict) -> str`
  - `make_server(paths: RunPaths, port: int, *, max_upload: int = MAX_UPLOAD) -> ThreadingHTTPServer`. Kalau `port=0`, port dipilih acak. Kalau port bentrok, coba sampai +10.

- [ ] **Step 1: Tulis test yang gagal**

`tests/test_brief_server.py`:

```python
import threading

import httpx
import pytest

from mayzfact.brief.server import make_server
from mayzfact.store import RunPaths, read_json, write_json_atomic

PLAN = {"shots": [
    {"index": 0, "beat": 0, "start_s": 0.0, "end_s": 2.0, "media": "video", "text": "Look <b>at</b> this.", "subject": None,
     "hook_segment": 0, "ref_frames": ["plan/seg_01_0.jpg"], "keywords": {"en": ["crab beach"], "zh": ["鲎"]}},
    {"index": 1, "beat": 1, "start_s": 2.0, "end_s": 4.0, "media": "photo", "text": "Fossil.", "subject": "fossil",
     "hook_segment": None, "ref_frames": [], "keywords": {"en": ["fossil"], "zh": []}},
]}


@pytest.fixture
def server(tmp_path):
    paths = RunPaths(tmp_path / "abc")
    (paths.root / "plan").mkdir(parents=True)
    (paths.root / "plan" / "seg_01_0.jpg").write_bytes(b"jpg")
    (tmp_path / "secret.txt").write_text("rahasia")
    write_json_atomic(paths.shots_plan_json, PLAN)
    srv = make_server(paths, 0, max_upload=1000)
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    yield paths, f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()
    srv.server_close()


def test_page_lists_shots_and_escapes_text(server):
    _, base = server
    html = httpx.get(base + "/").text
    assert "Look &lt;b&gt;at&lt;/b&gt; this." in html
    assert "鲎" in html and "HOOK" in html and "/files/plan/seg_01_0.jpg" in html
    assert "0/2" in html


def test_save_links_validates(server):
    paths, base = server
    ok = httpx.post(base + "/api/links", json={"shots": {"1": {"url": "复制 https://v.douyin.com/x/ 打开"}}})
    assert ok.status_code == 200 and ok.json()["missing"] == [2]
    assert read_json(paths.links_json) == {"shots": {"1": {"url": "https://v.douyin.com/x/"}}}
    bad = httpx.post(base + "/api/links", json={"shots": {"7": {"url": "https://a.b/c"}}})
    assert bad.status_code == 400 and "shot 7" in bad.json()["error"]


def test_upload_saves_file_and_links_it(server):
    paths, base = server
    ok = httpx.post(base + "/api/upload?shot=2", content=b"video-bytes", headers={"X-Filename": "klip.MP4"})
    assert ok.status_code == 200 and ok.json()["file"] == "manual/shot_02.mp4"
    assert (paths.root / "manual" / "shot_02.mp4").read_bytes() == b"video-bytes"
    assert read_json(paths.links_json)["shots"]["2"] == {"file": "manual/shot_02.mp4"}
    assert httpx.post(base + "/api/upload?shot=2", content=b"x", headers={"X-Filename": "a.exe"}).status_code == 400
    assert httpx.post(base + "/api/upload?shot=9", content=b"x", headers={"X-Filename": "a.jpg"}).status_code == 400
    assert httpx.post(base + "/api/upload?shot=1", content=b"x" * 2000, headers={"X-Filename": "a.jpg"}).status_code == 413


def test_files_are_confined_to_run_dir(server):
    _, base = server
    assert httpx.get(base + "/files/plan/seg_01_0.jpg").content == b"jpg"
    assert httpx.get(base + "/files/../secret.txt").status_code == 404
    assert httpx.get(base + "/files/%2E%2E/secret.txt").status_code == 404
    assert httpx.get(base + "/api/state").json()["plan"]["shots"][0]["index"] == 0
```

- [ ] **Step 2: Jalanin test, pastiin gagal**

Run: `uv run pytest tests/test_brief_server.py -q`
Expected: FAIL dengan `ModuleNotFoundError: No module named 'mayzfact.brief'`.

- [ ] **Step 3: Implementasi**

`mayzfact/brief/__init__.py`: file kosong.

`mayzfact/brief/page.py`:

```python
"""HTML halaman brief: kartu per shot, keyword yang bisa di-copy, input link/upload, status fetch."""

from __future__ import annotations

import json
from html import escape

_CSS = """
body{font-family:system-ui,sans-serif;margin:0;background:#f4f4f5;color:#18181b}
header{position:sticky;top:0;background:#18181b;color:#fff;padding:12px 16px;display:flex;gap:16px;align-items:center;z-index:2}
header button{padding:8px 16px;font-size:15px;cursor:pointer}
main{max-width:980px;margin:0 auto;padding:16px;display:grid;gap:12px}
.card{background:#fff;border-radius:10px;padding:14px;display:grid;gap:8px;box-shadow:0 1px 3px #0002}
.tag{font-size:12px;font-weight:700;padding:2px 8px;border-radius:99px;background:#e4e4e7}
.tag.hook{background:#fde68a}
.refs{display:flex;gap:6px}.refs img{height:160px;border-radius:6px}
.kw{display:flex;flex-wrap:wrap;gap:6px}.kw button{border:1px solid #d4d4d8;background:#fafafa;border-radius:6px;padding:3px 8px;cursor:pointer}
input[type=text]{width:100%;padding:8px;font-size:14px;box-sizing:border-box}
.state{font-size:13px}.state.ok{color:#15803d}.state.error,.state.missing{color:#b91c1c}.state.warn{color:#b45309}
"""

_JS = """
const plan = PLAN;
async function save(){
  const shots = {};
  document.querySelectorAll('[data-shot]').forEach(card => {
    const n = card.dataset.shot, url = card.querySelector('.url').value.trim(), file = card.querySelector('.file').value;
    if (url) shots[n] = {url}; else if (file) shots[n] = {file};
  });
  const res = await fetch('/api/links', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({shots})});
  const data = await res.json();
  document.getElementById('msg').textContent = res.ok ? `Tersimpan. Kosong: ${data.missing.join(', ') || '-'}` : data.error;
  if (res.ok) setTimeout(() => location.reload(), 600);
}
async function upload(n, input){
  const file = input.files[0]; if (!file) return;
  const res = await fetch(`/api/upload?shot=${n}`, {method:'POST', headers:{'X-Filename': encodeURIComponent(file.name)}, body:file});
  const data = await res.json();
  document.getElementById('msg').textContent = res.ok ? `Shot ${n}: ${data.file} ke-upload` : data.error;
  if (res.ok) setTimeout(() => location.reload(), 600);
}
function copyText(t){ navigator.clipboard.writeText(t); document.getElementById('msg').textContent = `Ke-copy: ${t}`; }
"""


def _card(shot: dict, entry: dict, state: dict) -> str:
    number = shot["index"] + 1
    is_hook = shot["hook_segment"] is not None
    refs = "".join(f'<img src="/files/{escape(f)}" loading="lazy">' for f in shot["ref_frames"])
    keywords = "".join(
        f'<button type="button" onclick=\'copyText({escape(json.dumps(k), quote=True)})\'>{escape(k)}</button>'
        for lang in ("en", "zh") for k in shot["keywords"].get(lang, [])
    )
    url_value = escape(entry.get("url", "") + (f" #{entry['pick']}" if entry.get("pick") else ""), quote=True)
    file_value = escape(entry.get("file", ""), quote=True)
    css = state.get("state", "missing" if not entry else "")
    if css == "ok" and state.get("message"):
        css = "warn"
    label = {"ok": "OK", "warn": "OK", "error": "GAGAL", "missing": "KOSONG"}.get(css, "TERSIMPAN")
    message = escape(state.get("message", "") or ("file: " + entry["file"] if entry.get("file") else ""))
    return f"""
<section class="card" data-shot="{number}">
  <div><b>Shot {number}</b> · {shot['start_s']:.1f}–{shot['end_s']:.1f}s ·
    <span class="tag {'hook' if is_hook else ''}">{'HOOK' if is_hook else 'ISI'}</span>
    · {escape(shot['media'])} · subjek: <b>{escape(shot.get('subject') or '-')}</b></div>
  <div>{escape(shot['text'])}</div>
  {f'<div class="refs">{refs}</div>' if refs else ''}
  <div class="kw">{keywords or '<i>tanpa keyword</i>'}</div>
  <input class="url" type="text" placeholder="Link Douyin/RedNote/TikTok/Pinterest/URL langsung (opsional: #3 buat foto ke-3)" value="{url_value}">
  <input class="file" type="hidden" value="{file_value}">
  <div>Atau upload: <input type="file" accept="video/*,image/*" onchange="upload({number}, this)"></div>
  <div class="state {css}">{label} {message}</div>
</section>"""


def render_page(run_id: str, plan: dict, links: dict, status: dict) -> str:
    entries = links.get("shots", {})
    states = status.get("shots", {})
    filled = sum(1 for shot in plan["shots"] if entries.get(str(shot["index"] + 1)))
    cards = "".join(
        _card(shot, entries.get(str(shot["index"] + 1), {}), states.get(str(shot["index"] + 1), {})) for shot in plan["shots"]
    )
    return f"""<!doctype html>
<html lang="id"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Brief {escape(run_id)}</title><style>{_CSS}</style></head>
<body><header><b>Brief {escape(run_id)}</b><span>{filled}/{len(plan['shots'])} terisi</span>
<button onclick="save()">Simpan</button><span id="msg"></span></header>
<main>{cards}</main>
<script>const PLAN = {json.dumps({'count': len(plan['shots'])})};{_JS}</script></body></html>"""
```

`mayzfact/brief/server.py`:

```python
"""Server lokal halaman brief: 127.0.0.1 doang, baca/tulis links.json, terima upload (spec metode manual bagian 4)."""

from __future__ import annotations

import json
import mimetypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path, PurePosixPath
from urllib.parse import parse_qs, unquote, urlparse

from mayzfact.brief.page import render_page
from mayzfact.manual.links import IMAGE_EXTS, VIDEO_EXTS, load_links, missing_shots, normalize_links, save_links
from mayzfact.store import RunPaths, read_json

MAX_UPLOAD = 500 * 1024 * 1024
PORT_TRIES = 10


def make_server(paths: RunPaths, port: int, *, max_upload: int = MAX_UPLOAD) -> ThreadingHTTPServer:
    root = paths.root.resolve()

    def plan() -> dict:
        return read_json(paths.shots_plan_json)

    def status() -> dict:
        return read_json(paths.links_status_json) if paths.links_status_json.exists() else {"shots": {}}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args) -> None:  # jangan spam terminal
            pass

        def _send(self, code: int, body: bytes, content_type: str) -> None:
            self.send_response(code)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _json(self, code: int, data: dict) -> None:
            self._send(code, json.dumps(data, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

        def do_GET(self) -> None:
            url = urlparse(self.path)
            if url.path == "/":
                html = render_page(paths.root.name, plan(), load_links(paths.links_json), status())
                return self._send(200, html.encode("utf-8"), "text/html; charset=utf-8")
            if url.path == "/api/state":
                return self._json(200, {"plan": plan(), "links": load_links(paths.links_json), "status": status()})
            if url.path.startswith("/files/"):
                target = (root / unquote(url.path[len("/files/"):])).resolve()
                if root in target.parents and target.is_file():
                    kind = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
                    return self._send(200, target.read_bytes(), kind)
            self._json(404, {"error": "nggak ada"})

        def do_POST(self) -> None:
            url = urlparse(self.path)
            length = int(self.headers.get("Content-Length") or 0)
            if url.path == "/api/links":
                try:
                    data = normalize_links(json.loads(self.rfile.read(length) or b"{}"), len(plan()["shots"]))
                except (ValueError, TypeError) as exc:
                    return self._json(400, {"error": str(exc)})
                save_links(paths.links_json, data)
                return self._json(200, {"ok": True, "missing": missing_shots(plan(), data)})
            if url.path == "/api/upload":
                try:
                    number = int(parse_qs(url.query).get("shot", ["0"])[0])
                except ValueError:
                    number = 0
                suffix = PurePosixPath(unquote(self.headers.get("X-Filename", ""))).suffix.lower()
                if not 1 <= number <= len(plan()["shots"]):
                    return self._json(400, {"error": f"shot {number} nggak ada di plan"})
                if suffix not in VIDEO_EXTS | IMAGE_EXTS:
                    return self._json(400, {"error": f"ekstensi {suffix or '?'} nggak didukung"})
                if length > max_upload:
                    return self._json(413, {"error": f"file kegedean (maks {max_upload // (1024 * 1024)} MB)"})
                paths.manual_dir.mkdir(parents=True, exist_ok=True)
                for old in paths.manual_dir.glob(f"shot_{number:02d}.*"):
                    old.unlink()
                dest = paths.manual_dir / f"shot_{number:02d}{suffix}"
                dest.write_bytes(self.rfile.read(length))
                rel = f"manual/{dest.name}"
                links = load_links(paths.links_json)
                links.setdefault("shots", {})[str(number)] = {"file": rel}
                save_links(paths.links_json, links)
                return self._json(200, {"file": rel})
            self._json(404, {"error": "nggak ada"})

    last: OSError | None = None
    for candidate in [0] if port == 0 else range(port, port + PORT_TRIES):
        try:
            return ThreadingHTTPServer(("127.0.0.1", candidate), Handler)
        except OSError as exc:
            last = exc
    raise OSError(f"Port {port}-{port + PORT_TRIES - 1} kepakai semua: {last}")
```

- [ ] **Step 4: Jalanin test, pastiin lolos**

Run: `uv run pytest tests/test_brief_server.py -q`
Expected: semua PASS.

- [ ] **Step 5: Commit**

```bash
git add mayzfact/brief tests/test_brief_server.py
git commit -m "feat: add local brief page and server"
```

---

### Task 10: Pipeline mode manual + CLI

**Files:**
- Modify: `mayzfact/pipeline.py`, `mayzfact/cli.py`, `README.md`
- Test: `tests/test_pipeline.py`, `tests/test_cli.py`

**Interfaces:**
- Consumes: `run_plan` (Task 7), `run_fetch` (Task 8), `Obtainer` (Task 5), `make_server` (Task 9), `translate_queries`/`describe_segments`, `AwaitingInput`
- Produces:
  - Konstanta `MANUAL_STEPS` dan `ALL_STEPS`
  - `plan_steps(done, voice_exists, from_step, new_voice, steps=STEPS)`
  - `Deps.plan` dan `Deps.fetch`, dengan tipe `Callable[[RunPaths, Callable[[str], None]], dict] | None = None`
  - CLI `mayzfact brief <video> [--port N]`. `AwaitingInput` jadi exit code 3.

- [ ] **Step 1: Tulis test yang gagal**

Di `tests/test_pipeline.py`, `SETTINGS` diganti jadi `Settings(**KEYS, max_shot_seconds=10.0, clip_source="auto")` biar test mode `auto` yang lama tetap sama. Terus tambahin:

```python
MANUAL = Settings(**KEYS, max_shot_seconds=10.0, clip_source="manual")


def test_manual_mode_runs_plan_then_waits_for_links(world):
    from mayzfact.errors import AwaitingInput

    calls = []

    def fake_plan(paths, log):
        calls.append("plan")
        write_json_atomic(paths.shots_plan_json, {"shots": []})
        return {"shots": []}

    def fake_fetch(paths, log):
        calls.append("fetch")
        raise AwaitingInput("fetch", "2 shot perlu diisi")

    world.deps.plan, world.deps.fetch = fake_plan, fake_fetch
    with pytest.raises(AwaitingInput):
        run(world, settings=MANUAL, no_render=True)
    assert calls == ["plan", "fetch"]
    assert world.tts.calls == 1


def test_manual_mode_rejects_auto_steps_and_auto_rejects_manual(world):
    run(world)
    with pytest.raises(PipelineError, match="hook"):
        run(world, settings=MANUAL, from_step="hook")
    with pytest.raises(PipelineError, match="fetch"):
        run(world, from_step="fetch")


def test_manual_fetch_success_continues_to_timeline(world):
    def fake_plan(paths, log):
        write_json_atomic(paths.shots_plan_json, {"shots": []})
        return {}

    def fake_fetch(paths, log):
        clips = {"shots": [{"index": 0, "beat": 0, "start_s": 0.0, "end_s": 30.0, "kind": "photo",
                            "file": "clips/shot_01.jpg", "width": 1080, "height": 1920}]}
        write_json_atomic(paths.clips_json, clips)
        return clips

    world.deps.plan, world.deps.fetch = fake_plan, fake_fetch
    paths = run(world, settings=MANUAL, no_render=True)
    assert paths.timeline_json.exists() and world.renders == 0
```

Tambahin ke `tests/test_cli.py`:

```python
def test_awaiting_input_exits_with_code_3(monkeypatch, capsys):
    from mayzfact.errors import AwaitingInput

    def wait(*args, **kwargs):
        raise AwaitingInput("fetch", "3 shot perlu diisi. Buka: mayzfact brief abc")

    monkeypatch.setattr(cli, "load_settings", lambda: Settings())
    monkeypatch.setattr(cli, "run_pipeline", wait)
    assert cli.main(["run", "i2xag_1OJfM", "--from", "fetch"]) == 3
    assert "mayzfact brief abc" in capsys.readouterr().out


def test_brief_needs_plan_first(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(cli, "load_settings", lambda: Settings())
    monkeypatch.setattr(cli, "RUNS_DIR", tmp_path)
    assert cli.main(["brief", "i2xag_1OJfM"]) == 1
    assert "--no-render" in capsys.readouterr().err
```

- [ ] **Step 2: Jalanin test, pastiin gagal**

Run: `uv run pytest tests/test_pipeline.py tests/test_cli.py -q`
Expected: test baru FAIL (misalnya `AttributeError: 'Deps' object has no attribute 'plan'`, `SystemExit: 2` buat `brief`).

- [ ] **Step 3: Implementasi**

Di `mayzfact/pipeline.py`:

1. Konstanta:

```python
STEPS = ["source", "script", "tts", "hook", "clips", "timeline", "render"]
MANUAL_STEPS = ["source", "script", "tts", "plan", "fetch", "timeline", "render"]
ALL_STEPS = list(dict.fromkeys(STEPS + MANUAL_STEPS))
VOICE_LOCKED = ("source", "script", "tts")
AFTER_VOICE = ("hook", "clips", "plan", "fetch", "timeline", "render")
```

2. Di `step_outputs`, tambahin `"plan": [paths.shots_plan_json],` dan `"fetch": [paths.clips_json],`.

3. `plan_steps` dapat parameter `steps: list[str] = STEPS`. Semua `STEPS` di dalam fungsi diganti `steps`, dan di awal blok `if from_step:` tambahin:

```python
        if from_step not in steps:
            raise PipelineError("cli", f"Step {from_step} nggak dipakai di mode CLIP_SOURCE ini. Pilihan: {', '.join(steps)}.")
```

4. Di `Deps`, tambahin di akhir:

```python
    plan: Callable[[RunPaths, Callable[[str], None]], dict] | None = None
    fetch: Callable[[RunPaths, Callable[[str], None]], dict] | None = None
```

5. Di `real_deps`, sebelum `return Deps(...)`:

```python
    def plan(paths: RunPaths, log: Callable[[str], None]) -> dict:
        from mayzfact.hook_queries import describe_segments, translate_queries
        from mayzfact.steps.plan import run_plan
        from mayzfact.ytdlp import run_ytdlp, youtube_url

        writer = GeminiScriptWriter(settings.gemini_api_keys, settings.gemini_model) if settings.gemini_api_keys else None
        return run_plan(
            paths, read_json(paths.script_json), read_json(paths.tts_json), read_json(paths.source_json),
            max_shot_s=settings.max_shot_seconds, hook_seconds=settings.hook_seconds,
            download_source=lambda video_id, dest: run_ytdlp(youtube_url(video_id), dest),
            describe=lambda infos, frames: describe_segments(writer, infos, frames, log),
            translate=lambda queries: translate_queries(writer, queries, log),
            log=log,
        )

    def fetch(paths: RunPaths, log: Callable[[str], None]) -> dict:
        from mayzfact.manual.obtain import Obtainer
        from mayzfact.manual.rednote import DESKTOP_UA
        from mayzfact.steps.fetch import run_fetch

        client = httpx.Client(headers={"User-Agent": DESKTOP_UA}, timeout=httpx.Timeout(120.0, connect=15.0), follow_redirects=True)
        closers.append(client.close)
        obtainer = Obtainer(CACHE_DIR / "manual", client, log=log)
        return run_fetch(
            paths, read_json(paths.shots_plan_json), obtain=obtainer.obtain, encoder=encoder(),
            fg_min_ratio=settings.fg_min_height_ratio, log=log,
        )
```

   Terus tambahin `plan=plan, fetch=fetch,` ke `Deps(...)`.

6. Di `run_pipeline`, ganti 2 baris pertama setelah `paths = …` jadi:

```python
    mode_steps = MANUAL_STEPS if settings.clip_source == "manual" else STEPS
    done = {step: step_done(step, paths) for step in mode_steps}
    steps = plan_steps(done, paths.voice_mp3.exists(), from_step, new_voice, mode_steps)
```

   Kondisi `if any(step in steps for step in ("hook", "clips", "timeline"))` diganti `("hook", "clips", "plan", "fetch", "timeline")`.

7. Di `_run_step`, sebelum cabang `"timeline"`:

```python
    elif step in ("plan", "fetch"):
        runner = deps.plan if step == "plan" else deps.fetch
        if runner is None:
            raise PipelineError(step, f"Step {step} butuh mode manual yang lengkap (deps.{step} kosong).")
        runner(paths, log)
```

Di `mayzfact/cli.py`:

- Import `ALL_STEPS` (gantiin `STEPS`), `RUNS_DIR`, dan `AwaitingInput`:

```python
from mayzfact.config import RUNS_DIR, Settings, load_settings, missing_env
from mayzfact.errors import AwaitingInput, PipelineError
from mayzfact.pipeline import ALL_STEPS, run_pipeline
```

- `choices=STEPS` diganti `choices=ALL_STEPS`.
- Tambahin subcommand di `build_parser`, sebelum `return parser`:

```python
    brief = sub.add_parser("brief", help="Buka halaman brief buat ngisi link klip (mode manual)")
    brief.add_argument("video", help="Video ID atau URL YouTube")
    brief.add_argument("--port", type=int, default=None, help="Port lokal (default BRIEF_PORT)")
```

- Di `main`, setelah blok `login`:

```python
        if args.command == "brief":
            return _brief(args, settings)
```

- Tambahin `except AwaitingInput` **sebelum** `except PipelineError`:

```python
    except AwaitingInput as exc:
        print(f"Nunggu input: {exc.message}")
        return 3
```

- Tambahin fungsi:

```python
def _brief(args: argparse.Namespace, settings: Settings) -> int:
    from mayzfact.brief.server import make_server
    from mayzfact.steps.source import parse_video_id
    from mayzfact.store import RunPaths

    paths = RunPaths(RUNS_DIR / parse_video_id(args.video))
    if not paths.shots_plan_json.exists():
        raise PipelineError("brief", f"Plan belum ada. Jalanin dulu: mayzfact run {paths.root.name} --no-render")
    server = make_server(paths, args.port or settings.brief_port)
    print(f"Brief {paths.root.name}: http://127.0.0.1:{server.server_address[1]}  (Ctrl+C buat stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0
```

`README.md`: tambahin section ini sebelum `## Hook (Fase 2)`:

````markdown
## Mode manual (default)

Klip dicari sendiri, terus pipeline yang download + milih bagian terbaik.

```bash
uv run mayzfact run <id> --no-render        # sampai plan, terus berhenti (exit 3): nunggu link
uv run mayzfact brief <id>                  # buka http://127.0.0.1:3100, isi link/upload per shot, Simpan
uv run mayzfact run <id> --from fetch --no-render   # download + potong; shot gagal muncul lagi di brief
```

Link boleh teks share Douyin/RedNote apa adanya. Tambahin ` #3` buat maksa foto ke-3 dari post foto ganda. Mode lama: `CLIP_SOURCE=auto`.
````

- [ ] **Step 4: Jalanin test, pastiin lolos**

Run: `uv run pytest -q`
Expected: full suite PASS.

- [ ] **Step 5: Commit**

```bash
git add mayzfact/pipeline.py mayzfact/cli.py README.md tests/test_pipeline.py tests/test_cli.py
git commit -m "feat: wire manual clip mode and brief command"
```

---

### Task 11: E2E `i2xag_1OJfM` bareng Akmal

**Files:**
- Modify: `docs/HANDOFF.md` (+ resolver/test kalau payload asli beda)

- [ ] **Step 1: Plan**

Run: `uv run mayzfact run i2xag_1OJfM --from plan --no-render; echo "exit=$?"`
Expected:
- `exit=3`, pesan "Nunggu input … mayzfact brief i2xag_1OJfM"
- `shots_plan.json` isinya ±16 shot
- `voice.mp3` nggak berubah (cek mtime sebelum vs sesudah)

- [ ] **Step 2: Brief**

Jalanin `uv run mayzfact brief i2xag_1OJfM` di background. Cek `curl http://127.0.0.1:3100/` balikin 200. Minta Akmal ngisi semua shot, termasuk minimal 1 link Douyin, 1 RedNote (link atau upload), dan 1 post foto ganda.

- [ ] **Step 3: Fetch**

Run: `uv run mayzfact run i2xag_1OJfM --from fetch --no-render; echo "exit=$?"`
Expected: `exit=0`. Kalau `exit=3`, baca `links_status.json`:
- Masalahnya di link: minta Akmal ganti link di brief.
- Masalahnya di resolver (bentuk halaman asli beda dari fixture): perbaiki pakai test regression dari HTML asli yang udah dipangkas, terus catat ruling.

Ulangi sampai `exit=0`.

- [ ] **Step 4: Studio**

Restart Studio pakai `timeline.json` baru (matiin dulu proses lama di port 3000), terus minta Akmal review. Render cuma setelah Akmal bilang oke.

- [ ] **Step 5: Handoff + check terakhir**

Run: `uv run pytest -q`, `uv run pytest -m render -q`, dan `(cd remotion && npx tsc --noEmit)`

Tambahin section "Metode manual" di `docs/HANDOFF.md`, isinya hasil asli:
- jumlah shot
- link per platform: berhasil/gagal, dan resolver mana yang kepake
- review Akmal

```bash
git add docs/HANDOFF.md
git commit -m "docs: record manual clip source e2e"
```
