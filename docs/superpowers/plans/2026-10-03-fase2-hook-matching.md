# Fase 2 Hook Matching Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Nambah step `hook` (klip `HOOK_SECONDS` awal dicari di TikTok/Douyin/RedNote/Pinterest + stock, lalu dipilih pakai SigLIP) dan rerank SigLIP buat shot lain, di atas pipeline Fase 1.

**Architecture:**

- Modul murni (tanpa network/model) buat:
  - segmen (`scenes.py`)
  - ranking (`matching.py`)
  - parser JSON platform (`platforms/parsers.py`)
  - deteksi blok + cookie (`platforms/base.py`)
- Modul berat yang di-load lazy:
  - SigLIP (`embed.py`)
  - Playwright (`platforms/browser.py`)
  - yt-dlp (`ytdlp.py`)
- `steps/hook.py` ngerangkai semuanya lewat `HookDeps` yang bisa diganti fake. `steps/clips.py` baca `hook.json` dan pakai `Scorer` opsional.
- Pipeline dapat step `hook` di grup setelah suara, jadi aturan kunci suara Fase 1 nggak berubah.

**Tech Stack:**

- Python 3.14 via uv: numpy, torch (CPU, PyPI Windows), open-clip-torch (`ViT-B-16-SigLIP`/`webli`), playwright (`channel="chrome"`), yt-dlp
- Plus semua stack Fase 1

**Spec:** [`docs/superpowers/specs/2026-10-03-fase2-hook-matching-design.md`](../specs/2026-10-03-fase2-hook-matching-design.md). Keputusannya ada di `docs/DECISIONS.md` D-011 sampai D-014. Baca juga spec Fase 1, karena aturan kunci suara (3.4) tetap berlaku.

## Global Constraints

### Test

- Test otomatis nggak boleh buka browser, nggak boleh akses network beneran, dan nggak boleh load SigLIP asli.
- SigLIP asli cuma di test marker `clip`. Remotion asli tetap di marker `render`.

### Data sensitif

- API key, cookie, dan isi `browser-profiles/` nggak boleh di-print, di-log, atau di-commit.
- `browser-profiles/`, `runs/`, dan `cache/` tetap gitignored.

### Aturan dari Fase 1 yang tetap jalan

- Step `hook` masuk `AFTER_VOICE`. `--from hook` nggak boleh manggil ElevenLabs.
- Klip nggak boleh dobel dalam 1 video. Ini berlaku juga buat pemenang hook vs klip stock.

### Default config & konstanta

- Config: `HOOK_SECONDS=10`, `HOOK_EXACT_THRESHOLD=0.85`, `HOOK_PLATFORMS=tiktok,douyin,rednote,pinterest`, `BROWSER_HEADLESS=false`.
- Segmen: scene threshold 0.25, gabung cut < 0.4 detik, buang segmen < 0.5 detik, 3 frame per segmen di 25%/50%/75% dengan lebar 448px.
- Seleksi: maksimal 8 kandidat per sumber per segmen, verifikasi 3 teratas, frame tiap 0.5 detik dari 30 detik pertama, simpan 5 kandidat teratas di `hook.json`.
- Platform: jeda acak 2–5 detik antar search, maksimal 12 search per platform per run, nunggu JSON maksimal 20 detik.

### Aturan kerja

- Pesan ke user pakai bahasa Indonesia santai. Prompt ke Gemini pakai English.
- Kerjain di branch `fase2-hook`. Commit pakai skill `caveman-commit`, 1 baris, tanpa `Co-Authored-By`.

## Review Focus

1. **Bentuk JSON platform berubah atau item-nya rusak.** Parser harus balikin kandidat yang valid aja dan nggak crash. Test: Task 8.
2. **Captcha atau redirect ke halaman login di tengah run.** Platform itu di-skip buat sisa run, dicatat di `skipped_platforms`, dan run tetap jalan. Test: Task 9 dan Task 11.
3. **Klip yang sama menang di 2 segmen.** Nggak boleh kejadian. Pemenang segmen sebelumnya dikeluarin dari kandidat. Test: Task 11.
4. **Video pemenang hook lebih pendek dari shot, atau offset-nya mepet ujung.** Start dibatasi, dan kalau videonya kependekan, shot balik ke klip biasa. Test: Task 12.
5. **Thumbnail 403, isinya HTML, atau format gambarnya nggak didukung.** Kandidat itu di-skip, atau dapat skor -1 di rerank. Test: Task 11 dan Task 12.

---

## File Structure

```text
pyproject.toml / .gitignore / .env.example / README.md      (modify)
mayzfact/
  config.py            (modify) setting hook + BROWSER_PROFILES_DIR + _flag
  store.py             (modify) RunPaths.source_mp4 / hook_dir / hook_json
  providers/types.py   (modify) Candidate.thumbnail_url
  providers/pexels.py / pixabay.py (modify) isi thumbnail_url
  providers/gemini.py  (modify) generate(system, contents, schema, step)
  models.py            (modify) SegmentQueries, HookQueries
  ffmpeg.py            (modify) extract_frame, sample_frames
  scenes.py            detect_cuts, merge_cuts, segments
  embed.py             Encoder, SiglipEncoder, unit, mean_unit, can_open_image
  matching.py          top_k, match_label, hook_slot_map, rerank_key
  hook_queries.py      transcript_near, fallback_queries, build_contents, describe_segments
  prompts/hook_queries.md
  ytdlp.py             ytdlp_command, run_ytdlp, youtube_url
  platforms/__init__.py
  platforms/base.py    PlatformBlocked, PlatformInfo, PLATFORMS, platform_info, url_blocked, looks_blocked,
                       is_logged_in, cookies_to_netscape, Throttle
  platforms/parsers.py parse_tiktok/douyin/rednote/pinterest, PARSERS, SEARCH_PAGES, search_url
  platforms/browser.py BrowserPlatform, read_profile_cookies, open_login_browser
  thumbs.py            thumb_path, fetch_thumbnail
  scoring.py           ThumbScorer
  steps/hook.py        Searcher, HookDeps, StockSearcher, run_hook, real_hook_deps
  steps/clips.py       (modify) Scorer, rerank, hook shots
  pipeline.py          (modify) step hook, Deps.hook / Deps.scorer
  cli.py               (modify) command login
tests/ (baru) test_scenes, test_embed, test_matching, test_hook_queries, test_platform_base,
       test_platform_parsers, test_ytdlp, test_browser_platform, test_hook, test_clips_hook, test_scoring
```

---

### Task 1: Dependency, config, dan path hook

**Files:**

- Modify: `pyproject.toml`, `.gitignore`, `.env.example`, `mayzfact/config.py`, `mayzfact/store.py`
- Test: `tests/test_config.py`, `tests/test_store.py`

**Interfaces:**

- Consumes: `Settings`, `ENV_FIELDS`, `settings_from_env`, `RunPaths` (Fase 1)
- Produces:
  - Field baru di `Settings`: `hook_seconds: float = 10.0`, `hook_exact_threshold: float = 0.85`, `hook_platforms: tuple[str, ...] = ("tiktok","douyin","rednote","pinterest")`, `browser_headless: bool = False`
  - Konstanta `BROWSER_PROFILES_DIR`
  - Property baru di `RunPaths`: `source_mp4`, `hook_dir`, `hook_json`

- [ ] **Step 1: Bikin branch + update dependency**

```bash
git switch -c fase2-hook
```

`pyproject.toml`: tambahin ke `dependencies` (urutan alfabet), terus ganti `addopts` dan `markers`:

```toml
dependencies = [
  "google-genai>=1.33",
  "httpx>=0.28",
  "numpy>=2.0",
  "open-clip-torch>=3.0",
  "pillow>=11",
  "playwright>=1.55",
  "pydantic>=2.9",
  "python-dotenv>=1.0",
  "torch>=2.9",
  "youtube-transcript-api>=1.2",
  "yt-dlp>=2026.8.19",
]
```

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-m 'not render and not clip'"
markers = [
  "render: jalanin Remotion beneran (lambat, butuh Node 22)",
  "clip: load model SigLIP asli (lambat, download ±800 MB sekali)",
]
```

`.gitignore`: tambahin baris `browser-profiles/`.

`.env.example`: tambahin di paling bawah:

```dotenv
HOOK_SECONDS=10
HOOK_EXACT_THRESHOLD=0.85
HOOK_PLATFORMS=tiktok,douyin,rednote,pinterest
BROWSER_HEADLESS=false
```

Run: `uv sync`
Expected: torch, open-clip-torch, playwright, numpy, dan yt-dlp ke-install tanpa error.

Run: `uv run python -c "import torch, open_clip, playwright, numpy, yt_dlp; print(torch.__version__, torch.cuda.is_available())"`
Expected: versi torch dan `False`. Di Windows, torch dari PyPI itu build CPU.

- [ ] **Step 2: Tulis test yang gagal**

Tambahin ke `tests/test_config.py`:

```python
def test_hook_settings_defaults_and_parsing():
    settings = settings_from_env({})
    assert (settings.hook_seconds, settings.hook_exact_threshold, settings.browser_headless) == (10.0, 0.85, False)
    assert settings.hook_platforms == ("tiktok", "douyin", "rednote", "pinterest")
    settings = settings_from_env({"HOOK_SECONDS": "8", "HOOK_PLATFORMS": "tiktok,pinterest", "BROWSER_HEADLESS": "TRUE"})
    assert (settings.hook_seconds, settings.hook_platforms, settings.browser_headless) == (8.0, ("tiktok", "pinterest"), True)
    assert settings_from_env({"BROWSER_HEADLESS": "off"}).browser_headless is False


def test_invalid_flag_names_the_variable():
    with pytest.raises(PipelineError, match="BROWSER_HEADLESS"):
        settings_from_env({"BROWSER_HEADLESS": "kadang"})
```

Tambahin ke `tests/test_store.py`:

```python
def test_run_paths_hook_files(tmp_path):
    paths = RunPaths(tmp_path)
    assert paths.source_mp4 == tmp_path / "source.mp4"
    assert paths.hook_dir == tmp_path / "hook"
    assert paths.hook_json == tmp_path / "hook.json"
```

- [ ] **Step 3: Jalanin test, pastiin gagal**

Run: `uv run pytest tests/test_config.py tests/test_store.py -q`
Expected: FAIL dengan `AttributeError: 'Settings' object has no attribute 'hook_seconds'` dan `'RunPaths' object has no attribute 'source_mp4'`.

- [ ] **Step 4: Implementasi**

`mayzfact/config.py`:

- Tambahin `BROWSER_PROFILES_DIR = PROJECT_ROOT / "browser-profiles"` di bawah `CACHE_DIR`.
- Tambahin field di akhir `Settings`:

```python
    hook_seconds: float = 10.0
    hook_exact_threshold: float = 0.85
    hook_platforms: tuple[str, ...] = ("tiktok", "douyin", "rednote", "pinterest")
    browser_headless: bool = False
```

- Di bawah `_key_list`:

```python
_TRUE = {"1", "true", "yes", "on"}
_FALSE = {"0", "false", "no", "off"}


def _flag(raw: str) -> bool:
    value = raw.lower()
    if value in _TRUE:
        return True
    if value in _FALSE:
        return False
    raise ValueError(raw)
```

- Tambahin di akhir `ENV_FIELDS`:

```python
    "HOOK_SECONDS": ("hook_seconds", float),
    "HOOK_EXACT_THRESHOLD": ("hook_exact_threshold", float),
    "HOOK_PLATFORMS": ("hook_platforms", _key_list),
    "BROWSER_HEADLESS": ("browser_headless", _flag),
```

- Pesan error di `settings_from_env` diganti jadi `f"{env_name} nilainya nggak valid: {raw!r}"`.

`mayzfact/store.py`: tambahin di `RunPaths`, setelah `final_mp4`:

```python
    @property
    def source_mp4(self) -> Path:
        return self.root / "source.mp4"

    @property
    def hook_dir(self) -> Path:
        return self.root / "hook"

    @property
    def hook_json(self) -> Path:
        return self.root / "hook.json"
```

- [ ] **Step 5: Jalanin test, pastiin lolos**

Run: `uv run pytest tests/test_config.py tests/test_store.py -q`
Expected: semua PASS (13 test).

Run: `uv run pytest -q`
Expected: semua test lama tetap PASS.

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml uv.lock .gitignore .env.example mayzfact/config.py mayzfact/store.py tests/test_config.py tests/test_store.py
git commit -m "build: add hook deps, settings and run paths"
```

---

### Task 2: `thumbnail_url` di kandidat stock

**Files:**

- Modify: `mayzfact/providers/types.py`, `mayzfact/providers/pexels.py`, `mayzfact/providers/pixabay.py`, `tests/factories.py`
- Test: `tests/test_stock_providers.py`

**Interfaces:**

- Consumes: `Candidate`, `parse_video`, `parse_photo` (Fase 1)
- Produces:
  - `Candidate.thumbnail_url: str = ""` (field terakhir)
  - `cand(..., thumbnail_url: str | None = None)` di factories. Default-nya `https://cdn.test/{provider}_{id}_thumb.jpg`.

- [ ] **Step 1: Tulis test yang gagal**

Tambahin ke `tests/test_stock_providers.py`:

```python
def test_parsers_fill_thumbnail_url():
    assert pexels_mod.parse_video({**PEXELS_VIDEO, "image": "https://images.pexels.com/v/101.jpg"}, 0).thumbnail_url == "https://images.pexels.com/v/101.jpg"
    assert pexels_mod.parse_video(PEXELS_VIDEO, 0).thumbnail_url == ""
    photo = {**PEXELS_PHOTO, "src": {**PEXELS_PHOTO["src"], "medium": "https://images.pexels.com/202-medium.jpg"}}
    assert pexels_mod.parse_photo(photo, 0).thumbnail_url == "https://images.pexels.com/202-medium.jpg"
    assert pexels_mod.parse_photo(PEXELS_PHOTO, 0).thumbnail_url == PEXELS_PHOTO["src"]["original"]
    videos = {**PIXABAY_VIDEO["videos"], "small": {**PIXABAY_VIDEO["videos"]["small"], "thumbnail": "https://cdn.pixabay.com/303-small.jpg"}}
    assert pixabay_mod.parse_video({**PIXABAY_VIDEO, "videos": videos}, 0).thumbnail_url == "https://cdn.pixabay.com/303-small.jpg"
    assert pixabay_mod.parse_photo({**PIXABAY_PHOTO, "webformatURL": "https://pixabay.com/get/404_640.jpg"}, 0).thumbnail_url == "https://pixabay.com/get/404_640.jpg"
    assert pixabay_mod.parse_photo(PIXABAY_PHOTO, 0).thumbnail_url == PIXABAY_PHOTO["largeImageURL"]


def test_cand_factory_has_thumbnail():
    assert cand("pexels", "9").thumbnail_url == "https://cdn.test/pexels_9_thumb.jpg"
```

- [ ] **Step 2: Jalanin test, pastiin gagal**

Run: `uv run pytest tests/test_stock_providers.py -q`
Expected: FAIL dengan `AttributeError: 'Candidate' object has no attribute 'thumbnail_url'`.

- [ ] **Step 3: Implementasi**

`mayzfact/providers/types.py`: tambahin field terakhir di `Candidate`:

```python
    thumbnail_url: str = ""  # gambar kecil buat scoring SigLIP
```

`mayzfact/providers/pexels.py`:

- Di `Candidate(...)` milik `parse_video`, tambahin `thumbnail_url=item.get("image") or "",`.
- Di `parse_photo`, tambahin `thumbnail_url=(item.get("src") or {}).get("medium") or src,`.

`mayzfact/providers/pixabay.py`:

- Di `parse_video`, tambahin:

```python
        thumbnail_url=next((r["thumbnail"] for r in (hit.get("videos") or {}).values() if r.get("thumbnail")), ""),
```

- Di `parse_photo`, tambahin `thumbnail_url=hit.get("webformatURL") or url,`.

`tests/factories.py`: fungsi `cand` dapat parameter terakhir `thumbnail_url: str | None = None`, dan di `Candidate(...)` tambahin:

```python
        thumbnail_url=thumbnail_url if thumbnail_url is not None else f"https://cdn.test/{provider}_{id}_thumb.jpg",
```

- [ ] **Step 4: Jalanin test, pastiin lolos**

Run: `uv run pytest tests/test_stock_providers.py -q`
Expected: 11 test PASS.

- [ ] **Step 5: Commit**

```bash
git add mayzfact/providers/types.py mayzfact/providers/pexels.py mayzfact/providers/pixabay.py tests/factories.py tests/test_stock_providers.py
git commit -m "feat: carry thumbnail url on stock candidates"
```

---

### Task 3: Scene detection + ambil frame

**Files:**

- Create: `mayzfact/scenes.py`
- Modify: `mayzfact/ffmpeg.py`, `tests/conftest.py`
- Test: `tests/test_scenes.py`

**Interfaces:**

- Consumes: `PipelineError`, `ffmpeg._run(cmd, step)` (Fase 1)
- Produces:
  - Konstanta di `scenes.py`: `SCENE_THRESHOLD=0.25`, `MIN_CUT_GAP_S=0.4`, `MIN_SEGMENT_S=0.5`
  - `detect_cuts(path: Path, max_s: float) -> list[float]`
  - `merge_cuts(times: list[float], min_gap: float = MIN_CUT_GAP_S) -> list[float]`
  - `segments(cuts: list[float], end_s: float, min_len: float = MIN_SEGMENT_S) -> list[tuple[float, float]]`
  - `ffmpeg.extract_frame(src: Path, t: float, dest: Path, width: int = 448) -> Path`
  - `ffmpeg.sample_frames(src: Path, dest_dir: Path, *, every_s: float, max_s: float, width: int = 448) -> list[tuple[float, Path]]`
  - Fixture `cut_video` (2 detik: 1 detik merah, 1 detik biru)

- [ ] **Step 1: Tulis fixture + test yang gagal**

Tambahin ke `tests/conftest.py`:

```python
@pytest.fixture(scope="session")
def cut_video(media_dir) -> Path:
    """Video 2 detik: 1 detik merah lalu 1 detik biru, jadi ada 1 cut di detik 1.0."""
    path = media_dir / "cut_red_blue.mp4"
    if not path.exists():
        _ffmpeg(
            "-f", "lavfi", "-i", "color=red:s=320x240:d=1:r=30",
            "-f", "lavfi", "-i", "color=blue:s=320x240:d=1:r=30",
            "-filter_complex", "[0][1]concat=n=2:v=1:a=0", "-pix_fmt", "yuv420p", str(path),
        )
    return path
```

`tests/test_scenes.py`:

```python
from PIL import Image

from mayzfact.ffmpeg import extract_frame, sample_frames
from mayzfact.scenes import detect_cuts, merge_cuts, segments

# Cut asli dari 10 detik awal i2xag_1OJfM (filter scene 0.25)
I2X_CUTS = [0.0667, 1.15, 1.1833, 1.2333, 1.2667, 1.3167, 1.6833, 1.7333, 1.9, 1.9833,
            2.4333, 2.4833, 3.6667, 6.0667, 6.0833, 6.1, 6.1167, 8.45, 8.5]


def test_merge_cuts_keeps_last_cut_of_each_burst():
    assert merge_cuts(I2X_CUTS) == [0.067, 1.983, 2.483, 3.667, 6.117, 8.5]
    assert merge_cuts([]) == []


def test_segments_drop_short_pieces():
    assert segments([0.067, 1.983, 2.483, 3.667, 6.117, 8.5], 10.0) == [
        (0.067, 1.983), (1.983, 2.483), (2.483, 3.667), (3.667, 6.117), (6.117, 8.5), (8.5, 10.0),
    ]
    assert segments([], 3.0) == [(0.0, 3.0)]
    assert segments([0.2], 0.6) == []
    assert segments([4.0, 12.0], 10.0) == [(0.0, 4.0), (4.0, 10.0)]


def test_detect_cuts_finds_color_change(cut_video):
    cuts = detect_cuts(cut_video, 10.0)
    assert len(cuts) == 1
    assert abs(cuts[0] - 1.0) < 0.05


def _rgb(path):
    with Image.open(path) as img:
        return img.convert("RGB").getpixel((10, 10))


def test_extract_and_sample_frames(cut_video, tmp_path):
    red = _rgb(extract_frame(cut_video, 0.5, tmp_path / "a.jpg"))
    assert red[0] > 200 and red[2] < 60
    frames = sample_frames(cut_video, tmp_path / "s", every_s=0.5, max_s=2.0)
    assert [t for t, _ in frames][:4] == [0.0, 0.5, 1.0, 1.5]
    blue = _rgb(frames[3][1])
    assert blue[2] > 200 and blue[0] < 60
    again = sample_frames(cut_video, tmp_path / "s", every_s=1.0, max_s=2.0)
    assert len(again) == len(list((tmp_path / "s").glob("f_*.jpg")))
```

- [ ] **Step 2: Jalanin test, pastiin gagal**

Run: `uv run pytest tests/test_scenes.py -q`
Expected: FAIL dengan `ModuleNotFoundError: No module named 'mayzfact.scenes'`.

- [ ] **Step 3: Implementasi**

`mayzfact/scenes.py`:

```python
"""Deteksi cut di awal video source, terus pecah jadi segmen (spec Fase 2 4.1)."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

from mayzfact.errors import PipelineError

SCENE_THRESHOLD = 0.25
MIN_CUT_GAP_S = 0.4
MIN_SEGMENT_S = 0.5
_PTS = re.compile(r"pts_time:([0-9.]+)")


def detect_cuts(path: Path, max_s: float) -> list[float]:
    result = subprocess.run(
        [
            "ffmpeg", "-hide_banner", "-nostats", "-t", f"{max_s:.3f}", "-i", str(path), "-an",
            "-vf", f"scale=320:-2,select='gt(scene,{SCENE_THRESHOLD})',showinfo", "-f", "null", "-",
        ],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if result.returncode != 0:
        raise PipelineError("hook", f"Scene detect gagal:\n{result.stderr[-1500:]}")
    return [float(t) for t in _PTS.findall(result.stderr)]


def merge_cuts(times: list[float], min_gap: float = MIN_CUT_GAP_S) -> list[float]:
    """Cut yang rapat (transisi whip-blur) jadi 1. Wakilnya cut terakhir, pas shot baru udah kelihatan penuh."""
    groups: list[list[float]] = []
    for t in sorted(times):
        if groups and t - groups[-1][-1] < min_gap:
            groups[-1].append(t)
        else:
            groups.append([t])
    return [round(group[-1], 3) for group in groups]


def segments(cuts: list[float], end_s: float, min_len: float = MIN_SEGMENT_S) -> list[tuple[float, float]]:
    bounds = [0.0] + [c for c in cuts if 0 < c < end_s] + [end_s]
    return [
        (round(a, 3), round(b, 3)) for a, b in zip(bounds, bounds[1:]) if b - a >= min_len - 1e-9
    ]
```

Tambahin ke `mayzfact/ffmpeg.py`:

```python
def extract_frame(src: Path, t: float, dest: Path, width: int = 448) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    _run(
        ["ffmpeg", "-y", "-v", "error", "-ss", f"{t:.3f}", "-i", str(src), "-frames:v", "1",
         "-vf", f"scale={width}:-2", "-q:v", "3", str(dest)],
        "hook",
    )
    return dest


def sample_frames(src: Path, dest_dir: Path, *, every_s: float, max_s: float, width: int = 448) -> list[tuple[float, Path]]:
    """Frame tiap every_s detik dari max_s detik pertama. Balikin [(detik, path)]."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    for old in dest_dir.glob("f_*.jpg"):
        old.unlink()
    _run(
        ["ffmpeg", "-y", "-v", "error", "-t", f"{max_s:.3f}", "-i", str(src),
         "-vf", f"fps=1/{every_s},scale={width}:-2", "-q:v", "4", str(dest_dir / "f_%04d.jpg")],
        "hook",
    )
    return [(round(i * every_s, 3), path) for i, path in enumerate(sorted(dest_dir.glob("f_*.jpg")))]
```

- [ ] **Step 4: Jalanin test, pastiin lolos**

Run: `uv run pytest tests/test_scenes.py -q`
Expected: 4 test PASS.

- [ ] **Step 5: Commit**

```bash
git add mayzfact/scenes.py mayzfact/ffmpeg.py tests/conftest.py tests/test_scenes.py
git commit -m "feat: detect source cuts and sample frames"
```

---

### Task 4: Encoder SigLIP

**Files:**

- Create: `mayzfact/embed.py`
- Test: `tests/test_embed.py`

**Interfaces:**

- Consumes: `PipelineError`
- Produces:
  - Konstanta `MODEL_NAME = "ViT-B-16-SigLIP"`, `PRETRAINED = "webli"`
  - Protocol `Encoder` dengan `images(paths: list[Path]) -> np.ndarray` (baris ternormalisasi) dan `texts(texts: list[str]) -> np.ndarray`
  - Helper: `unit(vectors) -> np.ndarray`, `mean_unit(vectors) -> np.ndarray`, `can_open_image(path) -> bool`
  - `SiglipEncoder(batch_size=32)`

- [ ] **Step 1: Tulis test yang gagal**

`tests/test_embed.py`:

```python
import numpy as np
import pytest
from PIL import Image, ImageDraw

from mayzfact.embed import SiglipEncoder, can_open_image, mean_unit, unit


def test_unit_and_mean_unit():
    vectors = unit(np.array([[3.0, 4.0], [0.0, 0.0]]))
    assert np.allclose(vectors[0], [0.6, 0.8])
    assert np.allclose(vectors[1], [0.0, 0.0])
    assert np.allclose(mean_unit(np.array([[1.0, 0.0], [0.0, 1.0]])), [0.7071, 0.7071], atol=1e-4)


def test_can_open_image(tmp_path):
    good = tmp_path / "a.jpg"
    Image.new("RGB", (8, 8)).save(good)
    html = tmp_path / "b.jpg"
    html.write_bytes(b"<html>403 Forbidden</html>")
    assert can_open_image(good)
    assert not can_open_image(html)
    assert not can_open_image(tmp_path / "missing.jpg")


@pytest.mark.clip
def test_siglip_prefers_similar_image_and_matching_text(tmp_path):
    def circle(name, dx):
        img = Image.new("RGB", (224, 224), "white")
        ImageDraw.Draw(img).ellipse((40 + dx, 40, 180 + dx, 180), fill="red")
        img.save(tmp_path / name)
        return tmp_path / name

    def stripes(name):
        img = Image.new("RGB", (224, 224), "white")
        draw = ImageDraw.Draw(img)
        for x in range(0, 224, 28):
            draw.rectangle((x, 0, x + 14, 224), fill="blue")
        img.save(tmp_path / name)
        return tmp_path / name

    encoder = SiglipEncoder()
    a, a2, b = encoder.images([circle("a.jpg", 0), circle("a2.jpg", 12), stripes("b.jpg")])
    assert a @ a2 > a @ b
    texts = encoder.texts(["a red circle", "blue vertical stripes"])
    assert a @ texts[0] > a @ texts[1]
    assert b @ texts[1] > b @ texts[0]
```

- [ ] **Step 2: Jalanin test, pastiin gagal**

Run: `uv run pytest tests/test_embed.py -q`
Expected: FAIL dengan `ModuleNotFoundError: No module named 'mayzfact.embed'`.

- [ ] **Step 3: Implementasi**

`mayzfact/embed.py`:

```python
"""Embedding gambar & teks pakai SigLIP (open_clip) di CPU. Model baru di-load waktu pertama dipakai."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol

import numpy as np
from PIL import Image, ImageOps

from mayzfact.errors import PipelineError

MODEL_NAME = "ViT-B-16-SigLIP"
PRETRAINED = "webli"


class Encoder(Protocol):
    def images(self, paths: list[Path]) -> np.ndarray: ...

    def texts(self, texts: list[str]) -> np.ndarray: ...


def unit(vectors: Any) -> np.ndarray:
    vectors = np.asarray(vectors, dtype=np.float32)
    norms = np.linalg.norm(vectors, axis=-1, keepdims=True)
    return vectors / np.maximum(norms, 1e-12)


def mean_unit(vectors: Any) -> np.ndarray:
    return unit(np.asarray(vectors, dtype=np.float32).mean(axis=0))


def can_open_image(path: Path) -> bool:
    try:
        with Image.open(path) as img:
            img.load()
        return True
    except Exception:
        return False


def _open_rgb(path: Path) -> Image.Image:
    with Image.open(path) as img:
        return ImageOps.exif_transpose(img).convert("RGB")


class SiglipEncoder:
    def __init__(self, batch_size: int = 32) -> None:
        self._batch_size = batch_size
        self._model: Any = None

    def _load(self) -> None:
        if self._model is not None:
            return
        try:
            import open_clip
            import torch

            model, _, preprocess = open_clip.create_model_and_transforms(MODEL_NAME, pretrained=PRETRAINED)
        except Exception as exc:
            raise PipelineError(
                "hook",
                f"Model {MODEL_NAME} ({PRETRAINED}) gagal di-load: {exc}. Download pertama butuh internet (±800 MB).",
            ) from exc
        model.eval()
        self._torch = torch
        self._preprocess = preprocess
        self._tokenizer = open_clip.get_tokenizer(MODEL_NAME)
        self._model = model

    def images(self, paths: list[Path]) -> np.ndarray:
        self._load()
        chunks = []
        for start in range(0, len(paths), self._batch_size):
            batch = self._torch.stack([self._preprocess(_open_rgb(p)) for p in paths[start : start + self._batch_size]])
            with self._torch.no_grad():
                chunks.append(self._model.encode_image(batch).float().numpy())
        if not chunks:
            return np.zeros((0, 0), dtype=np.float32)
        return unit(np.concatenate(chunks))

    def texts(self, texts: list[str]) -> np.ndarray:
        self._load()
        with self._torch.no_grad():
            features = self._model.encode_text(self._tokenizer(list(texts))).float().numpy()
        return unit(features)
```

- [ ] **Step 4: Jalanin test cepat, pastiin lolos**

Run: `uv run pytest tests/test_embed.py -q`
Expected: 2 PASS, 1 deselected.

- [ ] **Step 5: Cek nama model + jalanin test model asli**

Run: `uv run python -c "import open_clip; print(open_clip.list_pretrained_tags_by_model('ViT-B-16-SigLIP'))"`
Expected: daftar yang isinya `'webli'`. Kalau nggak ada, cari nama terdekat pakai `open_clip.list_pretrained()` (misalnya `ViT-B-16-SigLIP2`), ganti `MODEL_NAME`/`PRETRAINED`, terus catat ruling-nya.

Run: `uv run pytest -m clip tests/test_embed.py -q`
Expected: 1 PASS. Run pertama download model.

- [ ] **Step 6: Commit**

```bash
git add mayzfact/embed.py tests/test_embed.py
git commit -m "feat: add siglip image and text encoder"
```

---

### Task 5: Aturan ranking & mapping

**Files:**

- Create: `mayzfact/matching.py`
- Test: `tests/test_matching.py`

**Interfaces:**

- Consumes: —
- Produces:
  - `top_k(scores: Sequence[float], k: int) -> list[int]`
  - `match_label(score: float, threshold: float) -> str` (`"exact"` / `"similar"`)
  - `hook_slot_map(slots, winners: int, hook_seconds: float) -> dict[int, int]`. Isi `slots` itu objek yang punya `.index` dan `.start_s`, urut berdasarkan waktu.
  - `rerank_key(score: float, tier_value: int, provider_rank: int) -> tuple`

- [ ] **Step 1: Tulis test yang gagal**

`tests/test_matching.py`:

```python
from types import SimpleNamespace

from mayzfact.matching import hook_slot_map, match_label, rerank_key, top_k


def test_top_k_is_stable():
    assert top_k([0.2, 0.9, 0.9, 0.1], 3) == [1, 2, 0]
    assert top_k([], 3) == []


def test_match_label():
    assert match_label(0.85, 0.85) == "exact"
    assert match_label(0.849, 0.85) == "similar"


def test_hook_slot_map():
    slots = [SimpleNamespace(index=i, start_s=s) for i, s in enumerate([0.0, 2.1, 4.0, 9.9, 10.0, 12.0])]
    assert hook_slot_map(slots, 6, 10.0) == {0: 0, 1: 1, 2: 2, 3: 3}
    assert hook_slot_map(slots, 2, 10.0) == {0: 0, 1: 1}
    assert hook_slot_map(slots, 0, 10.0) == {}


def test_rerank_key_prefers_score_but_puts_tier3_last():
    items = {"blurry_best": (0.30, 3, 0), "good": (0.25, 1, 1), "better": (0.28, 2, 0)}
    assert sorted(items, key=lambda name: rerank_key(*items[name])) == ["better", "good", "blurry_best"]
```

- [ ] **Step 2: Jalanin test, pastiin gagal**

Run: `uv run pytest tests/test_matching.py -q`
Expected: FAIL dengan `ModuleNotFoundError: No module named 'mayzfact.matching'`.

- [ ] **Step 3: Implementasi**

`mayzfact/matching.py`:

```python
"""Aturan ranking & mapping yang dipakai hook dan clips (tanpa model, tanpa network)."""

from __future__ import annotations

from typing import Any, Iterable, Sequence


def top_k(scores: Sequence[float], k: int) -> list[int]:
    return sorted(range(len(scores)), key=lambda i: (-scores[i], i))[:k]


def match_label(score: float, threshold: float) -> str:
    return "exact" if score >= threshold else "similar"


def hook_slot_map(slots: Iterable[Any], winners: int, hook_seconds: float) -> dict[int, int]:
    """Shot yang mulai sebelum hook_seconds dapat pemenang hook sesuai urutan: {slot.index: urutan pemenang}."""
    mapping: dict[int, int] = {}
    for slot in slots:
        if slot.start_s >= hook_seconds or len(mapping) >= winners:
            break
        mapping[slot.index] = len(mapping)
    return mapping


def rerank_key(score: float, tier_value: int, provider_rank: int) -> tuple:
    """Tier 3 (bakal di-upscale) di belakang. Sisanya skor tertinggi duluan, terus tier, terus provider."""
    return (tier_value == 3, -score, tier_value, provider_rank)
```

- [ ] **Step 4: Jalanin test, pastiin lolos**

Run: `uv run pytest tests/test_matching.py -q`
Expected: 4 PASS.

- [ ] **Step 5: Commit**

```bash
git add mayzfact/matching.py tests/test_matching.py
git commit -m "feat: add hook ranking and slot mapping rules"
```

---

### Task 6: Query hook dari Gemini vision

**Files:**

- Modify: `mayzfact/providers/gemini.py`, `mayzfact/models.py`
- Create: `mayzfact/hook_queries.py`, `mayzfact/prompts/hook_queries.md`
- Test: `tests/test_gemini.py`, `tests/test_hook_queries.py`

**Interfaces:**

- Consumes:
  - `GeminiScriptWriter` dengan `_key_rejected`, `_gemini_retryable`, `SERVER_BACKOFF_S` (Fase 1)
  - `words` (Fase 1)
- Produces:
  - `GeminiScriptWriter.generate(system: str, contents: Any, schema: type[M], step: str = "script") -> M`. Method `write(system, user)` tetap ada dan manggil `generate`.
  - Model: `SegmentQueries(index: int, en: list[str], zh: list[str])` dan `HookQueries(segments: list[SegmentQueries])`
  - Di `hook_queries.py`:
    - `transcript_near(transcript, start_s, end_s) -> str`
    - `fallback_queries(infos) -> dict[int, dict]`
    - `build_contents(infos, frames) -> list`
    - `describe_segments(writer, infos, frames, log=print) -> dict[int, {"en": list[str], "zh": list[str]}]`
  - Tiap item `infos` = `{"index", "start_s", "end_s", "transcript"}`.

- [ ] **Step 1: Tulis test yang gagal**

Tambahin ke `tests/test_gemini.py` (import `HookQueries` dari `mayzfact.models` di blok import atas):

```python
def test_generate_validates_against_given_schema():
    client = FakeClient(['{"segments": [{"index": 0, "en": ["crab"], "zh": []}]}'])
    writer = GeminiScriptWriter(["key"], "gemini-test", client_factory=lambda key: client)
    out = writer.generate("sys", ["part"], HookQueries, step="hook")
    assert out.segments[0].en == ["crab"]
    assert client.models.calls[0]["config"].response_schema is HookQueries
    assert client.models.calls[0]["contents"] == ["part"]


def test_generate_errors_use_given_step():
    writer = GeminiScriptWriter(["key"], "gemini-test", client_factory=lambda key: FakeClient(['{"segments": 1}']))
    with pytest.raises(PipelineError, match=r"\[hook\]"):
        writer.generate("sys", "u", HookQueries, step="hook")
```

`tests/test_hook_queries.py`:

```python
from PIL import Image
from google.genai import types

from mayzfact.errors import PipelineError
from mayzfact.hook_queries import describe_segments, transcript_near
from mayzfact.models import HookQueries, SegmentQueries

TRANSCRIPT = [
    {"text": "These are the top five", "start": 0.0, "duration": 2.0},
    {"text": "horseshoe crab look", "start": 2.0, "duration": 2.0},
    {"text": "later", "start": 9.0, "duration": 1.0},
]


def infos():
    return [
        {"index": 0, "start_s": 0.0, "end_s": 2.0, "transcript": "These are the top five ancient creatures still alive today wow"},
        {"index": 1, "start_s": 2.0, "end_s": 4.0, "transcript": ""},
    ]


def frames(tmp_path):
    out = []
    for i in range(2):
        path = tmp_path / f"seg_{i + 1:02d}_1.jpg"
        Image.new("RGB", (16, 16), "red").save(path)
        out.append(path)
    return out


class FakeWriter:
    def __init__(self, result=None, error=None):
        self.result, self.error, self.calls = result, error, []

    def generate(self, system, contents, schema, step="script"):
        self.calls.append((system, contents, schema, step))
        if self.error:
            raise self.error
        return self.result


def test_transcript_near():
    assert transcript_near(TRANSCRIPT, 1.5, 3.0) == "These are the top five horseshoe crab look"
    assert transcript_near(TRANSCRIPT, 4.5, 8.0) == ""


def test_describe_uses_gemini_and_sends_one_image_per_segment(tmp_path):
    result = HookQueries(segments=[
        SegmentQueries(index=0, en=[" crab beach ", "crab hand", "extra"], zh=["鲎"]),
        SegmentQueries(index=1, en=[], zh=["鹦鹉螺", "x", "y"]),
        SegmentQueries(index=7, en=["ignored"], zh=[]),
    ])
    writer = FakeWriter(result)
    out = describe_segments(writer, infos(), frames(tmp_path), log=lambda m: None)
    assert out == {0: {"en": ["crab beach", "crab hand"], "zh": ["鲎"]}, 1: {"en": [], "zh": ["鹦鹉螺", "x"]}}
    system, contents, schema, step = writer.calls[0]
    assert schema is HookQueries and step == "hook"
    assert "ignore those overlays" in system
    assert sum(isinstance(part, types.Part) for part in contents) == 2


def test_describe_falls_back_to_transcript_on_error(tmp_path):
    logs = []
    out = describe_segments(FakeWriter(error=PipelineError("hook", "503")), infos(), frames(tmp_path), log=logs.append)
    assert out[0] == {"en": ["these are the top five ancient creatures still"], "zh": []}
    assert out[1] == {"en": [], "zh": []}
    assert "pakai transcript" in logs[0]


def test_describe_without_writer_uses_fallback(tmp_path):
    assert describe_segments(None, infos(), frames(tmp_path))[0]["zh"] == []
```

- [ ] **Step 2: Jalanin test, pastiin gagal**

Run: `uv run pytest tests/test_gemini.py tests/test_hook_queries.py -q`
Expected: FAIL dengan `ImportError: cannot import name 'HookQueries'`.

- [ ] **Step 3: Implementasi**

Tambahin ke `mayzfact/models.py`:

```python
class SegmentQueries(BaseModel):
    index: int
    en: list[str]
    zh: list[str]


class HookQueries(BaseModel):
    segments: list[SegmentQueries]
```

Di `mayzfact/providers/gemini.py`:

- Import jadi `from typing import Any, Callable, Sequence, TypeVar` dan `from pydantic import BaseModel, ValidationError`.
- Tambahin `M = TypeVar("M", bound=BaseModel)` di bawah konstanta.
- Method `write` diganti jadi dua method ini:

```python
    def generate(self, system: str, contents: Any, schema: type[M], step: str = "script") -> M:
        reasons: list[str] = []
        for number, key in enumerate(self._keys, start=1):
            client = self._client(key)

            def call():
                return client.models.generate_content(
                    model=self._model,
                    contents=contents,
                    config=types.GenerateContentConfig(
                        system_instruction=system,
                        response_mime_type="application/json",
                        response_schema=schema,
                    ),
                )

            try:
                response = retry_call(
                    call, is_retryable=_gemini_retryable, step=step, what="Gemini",
                    backoff_s=SERVER_BACKOFF_S, sleep=self._sleep,
                )
            except PipelineError as exc:
                if _key_rejected(exc.__cause__):
                    reasons.append(f"key #{number}: HTTP {exc.__cause__.code}")
                    continue
                raise
            try:
                return schema.model_validate_json(response.text or "")
            except ValidationError as exc:
                raise PipelineError(step, f"Output Gemini nggak sesuai schema: {exc}") from exc
        raise PipelineError(step, f"Semua {len(self._keys)} key Gemini ditolak ({'; '.join(reasons)}).")

    def write(self, system: str, user: str) -> Script:
        return self.generate(system, user, Script)
```

`mayzfact/prompts/hook_queries.md`:

```markdown
You help find the original stock or social-media clip that was used in a short video.

For every segment you get one frame and the narration spoken during it. The frame may contain captions, arrows, circles or emoji added by the editor: ignore those overlays and describe only the filmed scene.

For every segment return:
- "index": the segment index you were given.
- "en": 2 short English search queries (2 to 6 words) describing what is literally visible: the animal or object, its action, and the setting. Example: "boy holding horseshoe crab beach".
- "zh": 2 short Simplified Chinese search queries with the same meaning, the way a Douyin or Xiaohongshu user would type them. Example: "男孩 手拿 鲎".

Use the narration only to identify the subject's name. No hashtags, no emoji, no quotes.
```

`mayzfact/hook_queries.py`:

```python
"""Query search per segmen hook: dari Gemini vision, fallback dari transcript (spec Fase 2 4.3)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Protocol

from google.genai import types

from mayzfact.errors import PipelineError
from mayzfact.models import HookQueries
from mayzfact.text import words

PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "hook_queries.md"
FALLBACK_WORDS = 8
MAX_QUERIES = 2


class HookQueryWriter(Protocol):
    def generate(self, system: str, contents: Any, schema: type, step: str = "script") -> Any: ...


def transcript_near(transcript: list[dict], start_s: float, end_s: float) -> str:
    return " ".join(s["text"] for s in transcript if s["start"] < end_s and s["start"] + s["duration"] > start_s)


def fallback_queries(infos: list[dict]) -> dict[int, dict]:
    out: dict[int, dict] = {}
    for info in infos:
        snippet = " ".join(words(info["transcript"])[:FALLBACK_WORDS])
        out[info["index"]] = {"en": [snippet] if snippet else [], "zh": []}
    return out


def build_contents(infos: list[dict], frames: list[Path]) -> list:
    parts: list = ["Write search queries for every segment below."]
    for info, frame in zip(infos, frames, strict=True):
        parts.append(
            f"Segment {info['index']} ({info['start_s']:.1f}s-{info['end_s']:.1f}s). Narration: {info['transcript'] or '-'}"
        )
        parts.append(types.Part.from_bytes(data=frame.read_bytes(), mime_type="image/jpeg"))
    return parts


def _clean(queries: list[str]) -> list[str]:
    return [q.strip() for q in queries if q.strip()][:MAX_QUERIES]


def describe_segments(
    writer: HookQueryWriter | None,
    infos: list[dict],
    frames: list[Path],
    log: Callable[[str], None] = print,
) -> dict[int, dict]:
    fallback = fallback_queries(infos)
    if writer is None or not infos:
        return fallback
    try:
        result = writer.generate(PROMPT_PATH.read_text(encoding="utf-8"), build_contents(infos, frames), HookQueries, step="hook")
    except PipelineError as exc:
        log(f"[hook] Gemini gagal bikin query, pakai transcript: {exc.message[:120]}")
        return fallback
    out = dict(fallback)
    for segment in result.segments:
        if segment.index in out:
            out[segment.index] = {"en": _clean(segment.en) or fallback[segment.index]["en"], "zh": _clean(segment.zh)}
    return out
```

- [ ] **Step 4: Jalanin test, pastiin lolos**

Run: `uv run pytest tests/test_gemini.py tests/test_hook_queries.py tests/test_script_step.py -q`
Expected: semua PASS.

- [ ] **Step 5: Commit**

```bash
git add mayzfact/providers/gemini.py mayzfact/models.py mayzfact/hook_queries.py mayzfact/prompts/hook_queries.md tests/test_gemini.py tests/test_hook_queries.py
git commit -m "feat: generate hook search queries with gemini vision"
```

---

### Task 7: Info platform, deteksi blok, cookie, throttle

**Files:**

- Create: `mayzfact/platforms/__init__.py` (kosong), `mayzfact/platforms/base.py`
- Test: `tests/test_platform_base.py`

**Interfaces:**

- Consumes: `PipelineError`
- Produces:
  - `PlatformBlocked(platform: str, reason: str)` dengan atribut `.platform` dan `.reason`
  - `PlatformInfo` (dataclass: `name`, `language`, `home_url`, `cookie_domain`, `login_cookie`, `login_cookie_value`, `blocked_url_markers`, `blocked_html_markers`) dan `PLATFORMS: dict[str, PlatformInfo]`
  - Fungsi:
    - `platform_info(name) -> PlatformInfo`
    - `url_blocked(info, url) -> bool`
    - `looks_blocked(info, url, html) -> bool`
    - `is_logged_in(info, cookies: list[dict]) -> bool`
    - `cookies_to_netscape(cookies: list[dict]) -> str`
  - `Throttle(min_s=2.0, max_s=5.0, *, sleep, rand, clock)` dengan method `.wait()`

- [ ] **Step 1: Tulis test yang gagal**

`tests/test_platform_base.py`:

```python
import pytest

from mayzfact.errors import PipelineError
from mayzfact.platforms.base import (
    PLATFORMS, Throttle, cookies_to_netscape, is_logged_in, looks_blocked, platform_info, url_blocked,
)


def test_platform_info_rejects_unknown():
    assert platform_info("douyin").language == "zh"
    with pytest.raises(PipelineError, match="instagram"):
        platform_info("instagram")


def test_url_and_html_block_detection():
    tiktok = PLATFORMS["tiktok"]
    assert url_blocked(tiktok, "https://www.tiktok.com/login?redirect_url=x")
    assert not url_blocked(tiktok, "https://www.tiktok.com/search/video?q=crab")
    assert looks_blocked(tiktok, "https://www.tiktok.com/search/video?q=crab", '<div id="captcha-verify-container">')
    assert not looks_blocked(tiktok, "https://www.tiktok.com/search/video?q=crab", "<div>hasil</div>")


def test_is_logged_in():
    rednote, pinterest = PLATFORMS["rednote"], PLATFORMS["pinterest"]
    assert is_logged_in(rednote, [{"name": "web_session", "value": "abc", "domain": ".xiaohongshu.com"}])
    assert not is_logged_in(rednote, [{"name": "web_session", "value": "abc", "domain": ".example.com"}])
    assert not is_logged_in(rednote, [{"name": "web_session", "value": "", "domain": ".xiaohongshu.com"}])
    assert is_logged_in(pinterest, [{"name": "_auth", "value": "1", "domain": ".pinterest.com"}])
    assert not is_logged_in(pinterest, [{"name": "_auth", "value": "0", "domain": ".pinterest.com"}])


def test_cookies_to_netscape():
    text = cookies_to_netscape([
        {"name": "sessionid", "value": "s3cr3t", "domain": ".tiktok.com", "path": "/", "secure": True, "expires": 1893456000.5},
        {"name": "tt", "value": "x", "domain": "www.tiktok.com", "path": "/", "secure": False, "expires": -1},
    ])
    lines = text.splitlines()
    assert lines[0] == "# Netscape HTTP Cookie File"
    assert lines[1] == ".tiktok.com\tTRUE\t/\tTRUE\t1893456000\tsessionid\ts3cr3t"
    assert lines[2] == "www.tiktok.com\tFALSE\t/\tFALSE\t0\ttt\tx"


def test_throttle_waits_random_gap():
    now = [100.0]
    sleeps = []

    def sleep(seconds):
        sleeps.append(seconds)
        now[0] += seconds

    throttle = Throttle(2.0, 5.0, sleep=sleep, rand=lambda a, b: 3.0, clock=lambda: now[0])
    throttle.wait()
    now[0] += 1.0
    throttle.wait()
    now[0] += 10.0
    throttle.wait()
    assert sleeps == [2.0]
```

- [ ] **Step 2: Jalanin test, pastiin gagal**

Run: `uv run pytest tests/test_platform_base.py -q`
Expected: FAIL dengan `ModuleNotFoundError: No module named 'mayzfact.platforms'`.

- [ ] **Step 3: Implementasi**

`mayzfact/platforms/__init__.py`: file kosong.

`mayzfact/platforms/base.py`:

```python
"""Info platform login, deteksi ke-blok, konversi cookie, dan jeda antar search (spec Fase 2 bagian 5)."""

from __future__ import annotations

import random
import time
from dataclasses import dataclass
from typing import Callable

from mayzfact.errors import PipelineError


class PlatformBlocked(Exception):
    def __init__(self, platform: str, reason: str) -> None:
        super().__init__(f"{platform}: {reason}")
        self.platform = platform
        self.reason = reason


@dataclass(frozen=True)
class PlatformInfo:
    name: str
    language: str  # "en" | "zh": bahasa query yang dipakai
    home_url: str
    cookie_domain: str
    login_cookie: str
    login_cookie_value: str | None  # None = asal nggak kosong
    blocked_url_markers: tuple[str, ...]
    blocked_html_markers: tuple[str, ...]


PLATFORMS: dict[str, PlatformInfo] = {
    "tiktok": PlatformInfo(
        "tiktok", "en", "https://www.tiktok.com/", "tiktok.com", "sessionid", None,
        ("/login", "/signup"), ("captcha-verify-container", "captcha_container"),
    ),
    "douyin": PlatformInfo(
        "douyin", "zh", "https://www.douyin.com/", "douyin.com", "sessionid", None,
        ("/login", "verify.zijieapi.com"), ("captcha_container", "verify-bar-close"),
    ),
    "rednote": PlatformInfo(
        "rednote", "zh", "https://www.xiaohongshu.com/explore", "xiaohongshu.com", "web_session", None,
        ("/website-login", "/login"), ("red-captcha", "captcha-container"),
    ),
    "pinterest": PlatformInfo(
        "pinterest", "en", "https://www.pinterest.com/", "pinterest.com", "_auth", "1",
        ("/login", "/signup"), (),
    ),
}


def platform_info(name: str) -> PlatformInfo:
    if name not in PLATFORMS:
        raise PipelineError("config", f"Platform {name!r} nggak dikenal. Pilihan: {', '.join(PLATFORMS)}")
    return PLATFORMS[name]


def url_blocked(info: PlatformInfo, url: str) -> bool:
    return any(marker in url for marker in info.blocked_url_markers)


def looks_blocked(info: PlatformInfo, url: str, html: str) -> bool:
    return url_blocked(info, url) or any(marker in html for marker in info.blocked_html_markers)


def is_logged_in(info: PlatformInfo, cookies: list[dict]) -> bool:
    for cookie in cookies:
        if cookie.get("name") != info.login_cookie or info.cookie_domain not in cookie.get("domain", ""):
            continue
        value = cookie.get("value") or ""
        if value and (info.login_cookie_value is None or value == info.login_cookie_value):
            return True
    return False


def cookies_to_netscape(cookies: list[dict]) -> str:
    """Cookie Playwright → format Netscape yang dibaca yt-dlp (--cookies)."""
    lines = ["# Netscape HTTP Cookie File"]
    for cookie in cookies:
        domain = cookie.get("domain", "")
        expires = cookie.get("expires", -1) or -1
        lines.append("\t".join([
            domain,
            "TRUE" if domain.startswith(".") else "FALSE",
            cookie.get("path") or "/",
            "TRUE" if cookie.get("secure") else "FALSE",
            str(int(expires)) if expires > 0 else "0",
            cookie.get("name", ""),
            cookie.get("value", ""),
        ]))
    return "\n".join(lines) + "\n"


class Throttle:
    """Jeda acak antar search biar pola request nggak kelihatan kayak bot."""

    def __init__(
        self,
        min_s: float = 2.0,
        max_s: float = 5.0,
        *,
        sleep: Callable[[float], None] = time.sleep,
        rand: Callable[[float, float], float] = random.uniform,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._min, self._max = min_s, max_s
        self._sleep, self._rand, self._clock = sleep, rand, clock
        self._last: float | None = None

    def wait(self) -> None:
        if self._last is not None:
            gap = self._rand(self._min, self._max)
            elapsed = self._clock() - self._last
            if elapsed < gap:
                self._sleep(gap - elapsed)
        self._last = self._clock()
```

- [ ] **Step 4: Jalanin test, pastiin lolos**

Run: `uv run pytest tests/test_platform_base.py -q`
Expected: 5 PASS.

- [ ] **Step 5: Commit**

```bash
git add mayzfact/platforms/__init__.py mayzfact/platforms/base.py tests/test_platform_base.py
git commit -m "feat: add platform info, block detection, cookie export"
```

---

### Task 8: Parser JSON search 4 platform

**Files:**

- Create: `mayzfact/platforms/parsers.py`
- Test: `tests/test_platform_parsers.py`

**Interfaces:**

- Consumes: `Candidate`, `Rendition` (Fase 1 + Task 2)
- Produces:
  - `parse_tiktok`, `parse_douyin`, `parse_rednote`, `parse_pinterest`, semuanya `(payload: dict, start_rank: int = 0) -> list[Candidate]`
  - `PARSERS: dict[str, Callable]`
  - `SEARCH_PAGES: dict[str, tuple[str, tuple[str, ...]]]` = (template URL, pola URL response)
  - `search_url(platform, query) -> str`
  - Nilai `Candidate.provider` sama dengan nama platform.

- [ ] **Step 1: Tulis test yang gagal**

`tests/test_platform_parsers.py`:

```python
from mayzfact.platforms.parsers import parse_douyin, parse_pinterest, parse_rednote, parse_tiktok, search_url


def tiktok_item(vid, **video):
    base = {"cover": f"https://p16.tiktokcdn.com/{vid}.jpeg", "duration": 12, "width": 576, "height": 1024,
            "playAddr": f"https://v16.tiktokcdn.com/{vid}.mp4"}
    return {"id": vid, "author": {"uniqueId": "crabguy"}, "video": {**base, **video}}


def test_parse_tiktok_item_list_and_general_format():
    payload = {"item_list": [tiktok_item("1"), {"id": "2", "video": {}}, tiktok_item("3", playAddr="")]}
    cands = parse_tiktok(payload, start_rank=4)
    assert [c.id for c in cands] == ["1", "3"]
    first = cands[0]
    assert (first.provider, first.kind, first.duration_s, first.author, first.rank) == ("tiktok", "video", 12.0, "crabguy", 4)
    assert first.page_url == "https://www.tiktok.com/@crabguy/video/1"
    assert first.thumbnail_url == "https://p16.tiktokcdn.com/1.jpeg"
    assert (first.renditions[0].width, first.renditions[0].height) == (576, 1024)
    assert cands[1].renditions == ()
    general = {"data": [{"type": 1, "item": tiktok_item("9")}, {"type": 4, "user_list": []}]}
    assert [c.id for c in parse_tiktok(general)] == ["9"]
    assert parse_tiktok({}) == []


def test_parse_douyin_video_and_image_post():
    video = {"aweme_info": {"aweme_id": "11", "duration": 8500, "author": {"nickname": "鲎哥"},
                            "video": {"cover": {"url_list": ["https://p3.douyinpic.com/11.jpeg"]}, "width": 1080, "height": 1920,
                                      "play_addr": {"url_list": ["https://v3.douyinvod.com/11.mp4"]}}}}
    images = {"aweme_info": {"aweme_id": "12", "author": {"nickname": "x"},
                             "video": {"cover": {"url_list": ["https://p3.douyinpic.com/12.jpeg"]}},
                             "images": [{"url_list": ["https://p3.douyinpic.com/12-1.jpeg"], "width": 1080, "height": 1440}]}}
    broken = {"aweme_info": {"aweme_id": "13", "video": {}}}
    cands = parse_douyin({"data": [video, images, broken, None]})
    assert [(c.id, c.kind) for c in cands] == [("11", "video"), ("12", "photo")]
    assert cands[0].duration_s == 8.5
    assert cands[0].page_url == "https://www.douyin.com/video/11"
    assert cands[1].renditions[0].url == "https://p3.douyinpic.com/12-1.jpeg"


def test_parse_rednote_notes():
    payload = {"data": {"items": [
        {"id": "a1", "model_type": "note", "xsec_token": "tok=",
         "note_card": {"type": "video", "user": {"nickname": "小红"},
                       "cover": {"url_default": "https://sns-webpic.xhscdn.com/a1.jpg", "width": 1080, "height": 1440}}},
        {"id": "b2", "model_type": "note", "xsec_token": "t2",
         "note_card": {"type": "normal", "user": {"nick_name": "绿"},
                       "cover": {"url_default": "https://sns-webpic.xhscdn.com/b2.jpg", "width": 1080, "height": 1350}}},
        {"id": "q", "model_type": "rec_query", "note_card": {}},
        {"id": "c3", "model_type": "note", "note_card": {"type": "video", "cover": {}}},
    ]}}
    cands = parse_rednote(payload)
    assert [(c.id, c.kind, c.author) for c in cands] == [("a1", "video", "小红"), ("b2", "photo", "绿")]
    assert cands[0].page_url == "https://www.xiaohongshu.com/explore/a1?xsec_token=tok%3D&xsec_source=pc_search"
    assert cands[0].renditions == ()
    assert cands[1].renditions[0].height == 1350


def test_parse_pinterest_video_and_photo():
    payload = {"resource_response": {"data": {"results": [
        {"id": "p1", "pinner": {"username": "ana"},
         "images": {"474x": {"url": "https://i.pinimg.com/474x/p1.jpg"}, "orig": {"url": "https://i.pinimg.com/originals/p1.jpg", "width": 800, "height": 1200}},
         "videos": {"video_list": {"V_HLSV4": {"url": "https://v.pinimg.com/p1.m3u8"},
                                   "V_720P": {"url": "https://v.pinimg.com/p1.mp4", "width": 720, "height": 1280, "duration": 6400}}}},
        {"id": "p2", "pinner": {"username": "budi"},
         "images": {"orig": {"url": "https://i.pinimg.com/originals/p2.jpg", "width": 1000, "height": 1000}}},
        {"id": "p3", "images": {}},
    ]}}}
    cands = parse_pinterest(payload)
    assert [(c.id, c.kind) for c in cands] == [("p1", "video"), ("p2", "photo")]
    assert cands[0].duration_s == 6.4
    assert cands[0].renditions[0].url == "https://v.pinimg.com/p1.mp4"
    assert cands[0].thumbnail_url == "https://i.pinimg.com/474x/p1.jpg"
    assert cands[1].thumbnail_url == "https://i.pinimg.com/originals/p2.jpg"
    assert cands[1].page_url == "https://www.pinterest.com/pin/p2/"


def test_search_url_quotes_query():
    assert search_url("tiktok", "horseshoe crab") == "https://www.tiktok.com/search/video?q=horseshoe%20crab"
    assert search_url("douyin", "鲎 视频") == "https://www.douyin.com/search/%E9%B2%8E%20%E8%A7%86%E9%A2%91?type=video"
```

- [ ] **Step 2: Jalanin test, pastiin gagal**

Run: `uv run pytest tests/test_platform_parsers.py -q`
Expected: FAIL dengan `ModuleNotFoundError: No module named 'mayzfact.platforms.parsers'`.

- [ ] **Step 3: Implementasi**

`mayzfact/platforms/parsers.py`:

```python
"""Parse JSON search internal platform jadi Candidate. Item yang field-nya kurang di-skip, nggak bikin crash."""

from __future__ import annotations

from typing import Any, Callable
from urllib.parse import quote

from mayzfact.providers.types import Candidate, Rendition


def _int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _first_url(obj: Any) -> str:
    urls = (obj or {}).get("url_list") or [] if isinstance(obj, dict) else []
    return urls[0] if urls else ""


def parse_tiktok(payload: dict, start_rank: int = 0) -> list[Candidate]:
    items = payload.get("item_list")
    if items is None:
        items = [entry.get("item") for entry in payload.get("data") or [] if isinstance(entry, dict)]
    out: list[Candidate] = []
    for item in items or []:
        if not isinstance(item, dict):
            continue
        video = item.get("video") or {}
        vid = str(item.get("id") or "")
        cover = video.get("originCover") or video.get("cover") or ""
        if not vid or not cover:
            continue
        author = (item.get("author") or {}).get("uniqueId", "")
        width, height = _int(video.get("width")), _int(video.get("height"))
        play = video.get("playAddr") or ""
        out.append(Candidate(
            provider="tiktok", id=vid, kind="video",
            duration_s=float(video.get("duration") or 0) or None,
            page_url=f"https://www.tiktok.com/@{author}/video/{vid}", author=author,
            renditions=(Rendition(play, width, height),) if play and width and height else (),
            rank=start_rank + len(out), thumbnail_url=cover,
        ))
    return out


def parse_douyin(payload: dict, start_rank: int = 0) -> list[Candidate]:
    out: list[Candidate] = []
    for entry in payload.get("data") or []:
        info = (entry or {}).get("aweme_info") if isinstance(entry, dict) else None
        if not info:
            continue
        aweme_id = str(info.get("aweme_id") or "")
        video = info.get("video") or {}
        cover = _first_url(video.get("cover")) or _first_url(video.get("origin_cover"))
        if not aweme_id or not cover:
            continue
        author = (info.get("author") or {}).get("nickname", "")
        images = info.get("images") or []
        if images:
            first = images[0] or {}
            url, width, height = _first_url(first), _int(first.get("width")), _int(first.get("height"))
            if not url or not width or not height:
                continue
            kind, duration, renditions = "photo", None, (Rendition(url, width, height),)
        else:
            millis = _int(info.get("duration")) or _int(video.get("duration"))
            play = _first_url(video.get("play_addr"))
            width, height = _int(video.get("width")), _int(video.get("height"))
            kind, duration = "video", (millis / 1000 if millis else None)
            renditions = (Rendition(play, width, height),) if play and width and height else ()
        out.append(Candidate(
            provider="douyin", id=aweme_id, kind=kind, duration_s=duration,
            page_url=f"https://www.douyin.com/video/{aweme_id}", author=author,
            renditions=renditions, rank=start_rank + len(out), thumbnail_url=cover,
        ))
    return out


def parse_rednote(payload: dict, start_rank: int = 0) -> list[Candidate]:
    out: list[Candidate] = []
    for item in (payload.get("data") or {}).get("items") or []:
        if not isinstance(item, dict) or item.get("model_type", "note") != "note":
            continue
        card = item.get("note_card") or {}
        cover = card.get("cover") or {}
        note_id = str(item.get("id") or "")
        url = cover.get("url_default") or cover.get("url") or ""
        if not note_id or not url:
            continue
        kind = "video" if card.get("type") == "video" else "photo"
        width, height = _int(cover.get("width")), _int(cover.get("height"))
        user = card.get("user") or {}
        token = quote(item.get("xsec_token", ""), safe="")
        out.append(Candidate(
            provider="rednote", id=note_id, kind=kind, duration_s=None,
            page_url=f"https://www.xiaohongshu.com/explore/{note_id}?xsec_token={token}&xsec_source=pc_search",
            author=user.get("nickname") or user.get("nick_name", ""),
            renditions=(Rendition(url, width, height),) if kind == "photo" and width and height else (),
            rank=start_rank + len(out), thumbnail_url=url,
        ))
    return out


def parse_pinterest(payload: dict, start_rank: int = 0) -> list[Candidate]:
    results = ((payload.get("resource_response") or {}).get("data") or {}).get("results") or []
    out: list[Candidate] = []
    for pin in results:
        if not isinstance(pin, dict):
            continue
        pin_id = str(pin.get("id") or "")
        images = pin.get("images") or {}
        orig = images.get("orig") or {}
        thumb = (images.get("474x") or {}).get("url") or orig.get("url", "")
        videos = ((pin.get("videos") or {}).get("video_list")) or {}
        mp4 = max(
            (v for v in videos.values() if isinstance(v, dict) and str(v.get("url", "")).endswith(".mp4")),
            key=lambda v: _int(v.get("width")), default=None,
        )
        if not pin_id or not thumb:
            continue
        if mp4 and _int(mp4.get("width")) and _int(mp4.get("height")):
            kind, duration = "video", (_int(mp4.get("duration")) / 1000 or None)
            renditions = (Rendition(mp4["url"], _int(mp4["width"]), _int(mp4["height"])),)
        elif orig.get("url") and _int(orig.get("width")) and _int(orig.get("height")):
            kind, duration = "photo", None
            renditions = (Rendition(orig["url"], _int(orig["width"]), _int(orig["height"])),)
        else:
            continue
        out.append(Candidate(
            provider="pinterest", id=pin_id, kind=kind, duration_s=duration,
            page_url=f"https://www.pinterest.com/pin/{pin_id}/", author=(pin.get("pinner") or {}).get("username", ""),
            renditions=renditions, rank=start_rank + len(out), thumbnail_url=thumb,
        ))
    return out


PARSERS: dict[str, Callable[[dict, int], list[Candidate]]] = {
    "tiktok": parse_tiktok,
    "douyin": parse_douyin,
    "rednote": parse_rednote,
    "pinterest": parse_pinterest,
}

# (template URL halaman search, pola URL response JSON yang ditangkep)
SEARCH_PAGES: dict[str, tuple[str, tuple[str, ...]]] = {
    "tiktok": ("https://www.tiktok.com/search/video?q={q}", ("/api/search/item/full", "/api/search/general/full")),
    "douyin": ("https://www.douyin.com/search/{q}?type=video", ("/aweme/v1/web/search/item", "/aweme/v1/web/general/search")),
    "rednote": (
        "https://www.xiaohongshu.com/search_result?keyword={q}&source=web_search_result_notes",
        ("/api/sns/web/v1/search/notes",),
    ),
    "pinterest": ("https://www.pinterest.com/search/pins/?q={q}", ("/resource/BaseSearchResource/get",)),
}


def search_url(platform: str, query: str) -> str:
    template, _ = SEARCH_PAGES[platform]
    return template.format(q=quote(query, safe=""))
```

- [ ] **Step 4: Jalanin test, pastiin lolos**

Run: `uv run pytest tests/test_platform_parsers.py -q`
Expected: 5 PASS.

- [ ] **Step 5: Commit**

```bash
git add mayzfact/platforms/parsers.py tests/test_platform_parsers.py
git commit -m "feat: parse tiktok, douyin, rednote, pinterest search json"
```

---

### Task 9: yt-dlp + `BrowserPlatform`

**Files:**

- Create: `mayzfact/ytdlp.py`, `mayzfact/platforms/browser.py`
- Test: `tests/test_ytdlp.py`, `tests/test_browser_platform.py`

**Interfaces:**

- Consumes:
  - `PlatformBlocked`, `Throttle`, `cookies_to_netscape`, `looks_blocked`, `url_blocked`, `platform_info` (Task 7)
  - `PARSERS`, `SEARCH_PAGES`, `search_url` (Task 8)
  - `download` dan `tmp_path_for` (Fase 1)
  - `BROWSER_PROFILES_DIR` (Task 1)
- Produces:
  - Di `ytdlp.py`: `ytdlp_command(url, dest, cookies=None) -> list[str]`, `run_ytdlp(url, dest, *, cookies=None, step="hook") -> Path`, `youtube_url(video_id) -> str`
  - `BrowserPlatform(name, *, client, root=BROWSER_PROFILES_DIR, headless=False, capture=None, throttle=None, max_searches=12, log=print)`:
    - atribut `.name`, `.language`, `.blocked_reason`
    - method `.search(query) -> list[Candidate]` (bisa raise `PlatformBlocked`), `.download(candidate, dest) -> Path`, `.close()`
  - `read_profile_cookies(name, root=BROWSER_PROFILES_DIR) -> list[dict]`
  - `open_login_browser(name, root=BROWSER_PROFILES_DIR, prompt=input) -> None`

- [ ] **Step 1: Tulis test yang gagal**

`tests/test_ytdlp.py`:

```python
from types import SimpleNamespace

import pytest

from mayzfact.errors import PipelineError
from mayzfact.ytdlp import run_ytdlp, youtube_url, ytdlp_command


def test_ytdlp_command_with_and_without_cookies(tmp_path):
    cmd = ytdlp_command("https://www.tiktok.com/@a/video/1", tmp_path / "x.mp4", tmp_path / "c.txt")
    assert cmd[1:3] == ["-m", "yt_dlp"]
    assert cmd[-1] == "https://www.tiktok.com/@a/video/1"
    assert cmd[cmd.index("--cookies") + 1] == str(tmp_path / "c.txt")
    assert cmd[cmd.index("-o") + 1] == str(tmp_path / "x.mp4")
    assert "--cookies" not in ytdlp_command("u", tmp_path / "y.mp4")
    assert youtube_url("i2xag_1OJfM") == "https://www.youtube.com/watch?v=i2xag_1OJfM"


def test_run_ytdlp_skips_existing_file(tmp_path, monkeypatch):
    dest = tmp_path / "s.mp4"
    dest.write_bytes(b"ada")
    monkeypatch.setattr("mayzfact.ytdlp.subprocess.run", lambda *a, **k: pytest.fail("nggak boleh download ulang"))
    assert run_ytdlp("u", dest) == dest


def test_run_ytdlp_failure_cleans_tmp(tmp_path, monkeypatch):
    def fake_run(cmd, **kwargs):
        (tmp_path / "z.tmp.mp4").write_bytes(b"setengah")
        return SimpleNamespace(returncode=1, stderr="ERROR: Unsupported URL", stdout="")

    monkeypatch.setattr("mayzfact.ytdlp.subprocess.run", fake_run)
    with pytest.raises(PipelineError, match="Unsupported URL"):
        run_ytdlp("u", tmp_path / "z.mp4")
    assert list(tmp_path.iterdir()) == []
```

`tests/test_browser_platform.py`:

```python
from pathlib import Path

import pytest

from mayzfact.errors import PipelineError
from mayzfact.platforms.base import PlatformBlocked, Throttle
from mayzfact.platforms.browser import BrowserPlatform


def tiktok_item(vid):
    return {"id": vid, "author": {"uniqueId": "u"}, "video": {"cover": f"https://c/{vid}.jpg", "duration": 9}}


def make_platform(capture, **kwargs):
    return BrowserPlatform(
        "tiktok", client=None, root=Path("unused"), capture=capture,
        throttle=Throttle(0, 0, sleep=lambda s: None), **kwargs,
    )


def test_search_parses_captured_payloads_with_running_rank():
    seen = []

    def capture(url, patterns):
        seen.append((url, patterns))
        return [{"item_list": [tiktok_item("1"), tiktok_item("2")]}, {"item_list": [tiktok_item("3")]}]

    platform = make_platform(capture)
    cands = platform.search("horseshoe crab")
    assert [c.id for c in cands] == ["1", "2", "3"]
    assert [c.rank for c in cands] == [0, 1, 2]
    assert seen[0][0] == "https://www.tiktok.com/search/video?q=horseshoe%20crab"
    assert platform.language == "en"


def test_blocked_platform_stays_blocked():
    calls = []

    def capture(url, patterns):
        calls.append(url)
        raise PlatformBlocked("tiktok", "captcha/login")

    platform = make_platform(capture)
    with pytest.raises(PlatformBlocked):
        platform.search("a")
    with pytest.raises(PlatformBlocked, match="captcha"):
        platform.search("b")
    assert len(calls) == 1
    assert platform.blocked_reason == "captcha/login"


def test_browser_launch_error_marks_platform_blocked():
    def capture(url, patterns):
        raise PipelineError("browser", "Chrome gagal dibuka")

    platform = make_platform(capture)
    with pytest.raises(PlatformBlocked, match="Chrome gagal dibuka"):
        platform.search("a")


def test_search_limit_per_run():
    platform = make_platform(lambda url, patterns: [{"item_list": []}], max_searches=2)
    platform.search("a")
    platform.search("b")
    with pytest.raises(PlatformBlocked, match="batas 2 search"):
        platform.search("c")


def test_photo_without_url_cannot_be_downloaded(tmp_path):
    from tests.factories import cand

    photo = cand("rednote", "x", kind="photo")
    photo = type(photo)(**{**photo.__dict__, "renditions": ()})
    with pytest.raises(PipelineError, match="URL gambar"):
        make_platform(lambda u, p: []).download(photo, tmp_path / "x.jpg")
```

- [ ] **Step 2: Jalanin test, pastiin gagal**

Run: `uv run pytest tests/test_ytdlp.py tests/test_browser_platform.py -q`
Expected: FAIL dengan `ModuleNotFoundError: No module named 'mayzfact.ytdlp'`.

- [ ] **Step 3: Implementasi**

`mayzfact/ytdlp.py`:

```python
"""Download video pakai yt-dlp: video source YouTube dan klip platform login."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from mayzfact.errors import PipelineError
from mayzfact.store import tmp_path_for

FORMAT = "bv*[height<=1080][ext=mp4]+ba[ext=m4a]/b[height<=1080][ext=mp4]/bv*[height<=1080]+ba/b"


def youtube_url(video_id: str) -> str:
    return f"https://www.youtube.com/watch?v={video_id}"


def ytdlp_command(url: str, dest: Path, cookies: Path | None = None) -> list[str]:
    cmd = [
        sys.executable, "-m", "yt_dlp", "--no-playlist", "--quiet", "--no-warnings", "--no-progress",
        "-f", FORMAT, "--merge-output-format", "mp4", "-o", str(dest),
    ]
    if cookies is not None:
        cmd += ["--cookies", str(cookies)]
    return cmd + [url]


def run_ytdlp(url: str, dest: Path, *, cookies: Path | None = None, step: str = "hook") -> Path:
    if dest.exists():
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = tmp_path_for(dest)
    result = subprocess.run(
        ytdlp_command(url, tmp, cookies), capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    if result.returncode != 0 or not tmp.exists():
        tmp.unlink(missing_ok=True)
        raise PipelineError(step, f"yt-dlp gagal download {url}:\n{(result.stderr or result.stdout)[-800:]}")
    tmp.replace(dest)
    return dest
```

`mayzfact/platforms/browser.py`:

```python
"""Platform login lewat Chrome (Playwright): search dengan nangkep JSON, download pakai yt-dlp + cookies."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Callable

from mayzfact.config import BROWSER_PROFILES_DIR
from mayzfact.errors import PipelineError
from mayzfact.net import download
from mayzfact.platforms.base import (
    PlatformBlocked, Throttle, cookies_to_netscape, looks_blocked, platform_info, url_blocked,
)
from mayzfact.platforms.parsers import PARSERS, SEARCH_PAGES, search_url
from mayzfact.providers.types import Candidate
from mayzfact.ytdlp import run_ytdlp

MAX_SEARCHES = 12
WAIT_S = 20.0

Capture = Callable[[str, tuple[str, ...]], list[dict]]


def _launch(name: str, root: Path, headless: bool) -> tuple[Any, Any]:
    try:
        from playwright.sync_api import sync_playwright

        playwright = sync_playwright().start()
    except Exception as exc:
        raise PipelineError("browser", f"Playwright gagal jalan: {exc}") from exc
    try:
        context = playwright.chromium.launch_persistent_context(
            str(root / name), channel="chrome", headless=headless, viewport={"width": 1280, "height": 900},
        )
    except Exception as exc:
        playwright.stop()
        raise PipelineError(
            "browser", f"Chrome gagal dibuka buat {name}: {str(exc)[:200]}. Tutup jendela Chrome profil ini kalau masih kebuka."
        ) from exc
    return playwright, context


class BrowserPlatform:
    def __init__(
        self,
        name: str,
        *,
        client: Any,
        root: Path = BROWSER_PROFILES_DIR,
        headless: bool = False,
        capture: Capture | None = None,
        throttle: Throttle | None = None,
        max_searches: int = MAX_SEARCHES,
        log: Callable[[str], None] = print,
    ) -> None:
        self.info = platform_info(name)
        self.name = name
        self.language = self.info.language
        self.blocked_reason: str | None = None
        self._client = client
        self._root = root
        self._headless = headless
        self._capture_fn = capture
        self._throttle = throttle or Throttle()
        self._max = max_searches
        self._count = 0
        self._log = log
        self._playwright: Any = None
        self._context: Any = None

    def _ctx(self) -> Any:
        if self._context is None:
            self._playwright, self._context = _launch(self.name, self._root, self._headless)
        return self._context

    def search(self, query: str) -> list[Candidate]:
        if self.blocked_reason:
            raise PlatformBlocked(self.name, self.blocked_reason)
        if self._count >= self._max:
            self.blocked_reason = f"batas {self._max} search per run"
            raise PlatformBlocked(self.name, self.blocked_reason)
        self._count += 1
        self._throttle.wait()
        _, patterns = SEARCH_PAGES[self.name]
        capture = self._capture_fn or self._capture
        try:
            payloads = capture(search_url(self.name, query), patterns)
        except PlatformBlocked as exc:
            self.blocked_reason = exc.reason
            raise
        except PipelineError as exc:
            self.blocked_reason = exc.message
            raise PlatformBlocked(self.name, exc.message) from exc
        parse = PARSERS[self.name]
        candidates: list[Candidate] = []
        for payload in payloads:
            candidates += parse(payload, len(candidates))
        return candidates

    def _capture(self, url: str, patterns: tuple[str, ...]) -> list[dict]:
        from playwright.sync_api import Error as PlaywrightError

        page = self._ctx().new_page()
        responses: list[Any] = []
        page.on("response", lambda r: responses.append(r) if any(p in r.url for p in patterns) else None)
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=WAIT_S * 1000)
            deadline = time.monotonic() + WAIT_S
            while not responses and time.monotonic() < deadline:
                if url_blocked(self.info, page.url):
                    raise PlatformBlocked(self.name, "diarahin ke halaman login/captcha")
                page.mouse.wheel(0, 2500)
                page.wait_for_timeout(700)
            page.wait_for_timeout(800)
            payloads = []
            for response in responses:
                try:
                    payloads.append(response.json())
                except Exception:
                    continue
            if not payloads:
                reason = "captcha/login" if looks_blocked(self.info, page.url, page.content()) else "hasil search nggak kebaca"
                raise PlatformBlocked(self.name, reason)
            return payloads
        except PlaywrightError as exc:
            raise PlatformBlocked(self.name, f"browser error: {str(exc)[:120]}") from exc
        finally:
            page.close()

    def _cookies_file(self) -> Path:
        path = self._root / f"{self.name}.cookies.txt"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(cookies_to_netscape(self._ctx().cookies()), encoding="utf-8")
        return path

    def download(self, candidate: Candidate, dest: Path) -> Path:
        if candidate.kind == "photo":
            if not candidate.renditions:
                raise PipelineError("hook", f"{self.name} {candidate.id} nggak punya URL gambar.")
            return download(self._client, candidate.renditions[0].url, dest, step="hook")
        return run_ytdlp(candidate.page_url, dest, cookies=self._cookies_file())

    def close(self) -> None:
        if self._context is not None:
            self._context.close()
        if self._playwright is not None:
            self._playwright.stop()
        self._context = self._playwright = None


def read_profile_cookies(name: str, root: Path = BROWSER_PROFILES_DIR) -> list[dict]:
    playwright, context = _launch(name, root, headless=True)
    try:
        return context.cookies()
    finally:
        context.close()
        playwright.stop()


def open_login_browser(name: str, root: Path = BROWSER_PROFILES_DIR, prompt: Callable[[str], str] = input) -> None:
    info = platform_info(name)
    playwright, context = _launch(name, root, headless=False)
    try:
        page = context.pages[0] if context.pages else context.new_page()
        page.goto(info.home_url)
        prompt(f"Login ke {name} di jendela Chrome, terus tekan Enter di sini...")
    finally:
        context.close()
        playwright.stop()
```

- [ ] **Step 4: Jalanin test, pastiin lolos**

Run: `uv run pytest tests/test_ytdlp.py tests/test_browser_platform.py -q`
Expected: 8 PASS.

- [ ] **Step 5: Commit**

```bash
git add mayzfact/ytdlp.py mayzfact/platforms/browser.py tests/test_ytdlp.py tests/test_browser_platform.py
git commit -m "feat: add browser platform search and ytdlp download"
```

---

### Task 10: Command `login` + README

**Files:**

- Modify: `mayzfact/cli.py`, `README.md`
- Test: `tests/test_cli.py`

**Interfaces:**

- Consumes:
  - `PLATFORMS`, `platform_info`, `is_logged_in` (Task 7)
  - Modul `mayzfact.platforms.browser`: `read_profile_cookies`, `open_login_browser` (Task 9)
  - `Settings.hook_platforms` (Task 1)
- Produces:
  - `mayzfact login <platform>` dan `mayzfact login --check`
  - Exit code 0 kalau semua platform udah login, 1 kalau belum.

- [ ] **Step 1: Tulis test yang gagal**

Tambahin ke `tests/test_cli.py`:

```python
def test_login_check_reports_each_platform(monkeypatch, capsys):
    monkeypatch.setattr(cli, "load_settings", lambda: Settings(hook_platforms=("tiktok", "pinterest")))
    cookies = {"tiktok": [{"name": "sessionid", "value": "x", "domain": ".tiktok.com"}], "pinterest": []}
    monkeypatch.setattr(cli.browser, "read_profile_cookies", lambda name: cookies[name])
    assert cli.main(["login", "--check"]) == 1
    out = capsys.readouterr().out
    assert "tiktok: login" in out
    assert "pinterest: belum login (jalanin: mayzfact login pinterest)" in out


def test_login_opens_browser_then_checks(monkeypatch, capsys):
    opened = []
    monkeypatch.setattr(cli, "load_settings", lambda: Settings())
    monkeypatch.setattr(cli.browser, "open_login_browser", lambda name: opened.append(name))
    monkeypatch.setattr(cli.browser, "read_profile_cookies", lambda name: [{"name": "sessionid", "value": "x", "domain": ".douyin.com"}])
    assert cli.main(["login", "douyin"]) == 0
    assert opened == ["douyin"]
    assert "douyin: login" in capsys.readouterr().out


def test_login_needs_platform_or_check(monkeypatch, capsys):
    monkeypatch.setattr(cli, "load_settings", lambda: Settings())
    assert cli.main(["login"]) == 1
    assert "mayzfact login tiktok" in capsys.readouterr().err
```

- [ ] **Step 2: Jalanin test, pastiin gagal**

Run: `uv run pytest tests/test_cli.py -q`
Expected: FAIL dengan `SystemExit: 2` (argparse belum kenal `login`).

- [ ] **Step 3: Implementasi**

Di `mayzfact/cli.py`:

- Tambahin import:

```python
from mayzfact.platforms import browser
from mayzfact.platforms.base import PLATFORMS, is_logged_in, platform_info
```

- Di `build_parser`, sebelum `return parser`:

```python
    login = sub.add_parser("login", help="Login ke platform buat hook (TikTok/Douyin/RedNote/Pinterest)")
    login.add_argument("platform", nargs="?", choices=sorted(PLATFORMS))
    login.add_argument("--check", action="store_true", help="Cek status login semua platform di HOOK_PLATFORMS")
```

- Di `main`, setelah blok `voices`:

```python
        if args.command == "login":
            return _login(args, settings)
```

- Tambahin fungsi:

```python
def _login(args: argparse.Namespace, settings: Settings) -> int:
    if args.check:
        all_ok = True
        for name in settings.hook_platforms:
            ok = is_logged_in(platform_info(name), browser.read_profile_cookies(name))
            all_ok = all_ok and ok
            print(f"{name}: login" if ok else f"{name}: belum login (jalanin: mayzfact login {name})")
        return 0 if all_ok else 1
    if not args.platform:
        raise PipelineError("login", "Sebutin platform-nya, misal: mayzfact login tiktok. Atau pakai --check.")
    browser.open_login_browser(args.platform)
    ok = is_logged_in(platform_info(args.platform), browser.read_profile_cookies(args.platform))
    print(f"{args.platform}: login" if ok else f"{args.platform}: belum login, coba lagi")
    return 0 if ok else 1
```

`README.md`: tambahin section ini setelah `## Pakai`:

````markdown
## Hook (Fase 2)

Login sekali per platform. Sesinya disimpan di `browser-profiles/`, jangan di-share.

```bash
uv run mayzfact login tiktok      # juga: douyin, rednote, pinterest
uv run mayzfact login --check
uv run mayzfact run <id> --from hook   # cari ulang klip hook; suara nggak dibuat ulang
```

Kalau platform kena captcha atau login expired, platform itu di-skip dan run tetap jalan. Log-nya nyebut platform mana yang perlu login ulang.
````

- [ ] **Step 4: Jalanin test, pastiin lolos**

Run: `uv run pytest tests/test_cli.py -q`
Expected: 7 PASS.

- [ ] **Step 5: Commit**

```bash
git add mayzfact/cli.py README.md tests/test_cli.py
git commit -m "feat: add login command for hook platforms"
```

---

### Task 11: Orkestrasi step `hook`

**Files:**

- Create: `mayzfact/steps/hook.py`
- Test: `tests/test_hook.py`

**Interfaces:**

- Consumes:
  - Embedding: `Encoder`, `can_open_image`, `mean_unit` (Task 4)
  - Segmen & frame: `detect_cuts`, `merge_cuts`, `segments`, `extract_frame`, `sample_frames` (Task 3), `probe` (Fase 1)
  - Query: `describe_segments`, `transcript_near` (Task 6)
  - Ranking: `top_k`, `match_label` (Task 5)
  - Platform: `PlatformBlocked` (Task 7), `BrowserPlatform` (Task 9), `run_ytdlp`, `youtube_url` (Task 9)
  - Stock: `StockSearch` (Fase 1), `pick_rendition`, `download` (Fase 1)
  - Store: `RunPaths.source_mp4/hook_dir/hook_json` (Task 1)
- Produces:
  - Protocol `Searcher` (`name`, `language`, `search(query)`, `download(candidate, dest)`)
  - `HookDeps(download_source, encoder, describe, searchers, fetch_thumb, log=print, close=lambda: None)`
  - `StockSearcher(stock, client, fg_min_ratio)`
  - `run_hook(paths, source: dict, deps: HookDeps, *, hook_seconds, exact_threshold, media_cache: Path) -> dict` (format `hook.json` sesuai spec 4.6)
  - `real_hook_deps(settings, client, stock, encoder, fetch_thumb, log) -> HookDeps`

- [ ] **Step 1: Tulis test yang gagal**

`tests/test_hook.py`:

```python
import shutil
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from mayzfact.embed import unit
from mayzfact.platforms.base import PlatformBlocked
from mayzfact.steps.hook import HookDeps, run_hook
from mayzfact.store import RunPaths, read_json
from tests.factories import cand

E = np.eye(4, dtype=np.float32)
SEGMENT_VECTORS = {1: E[0], 2: E[1]}
TABLE = {
    "tiktok_t1": E[0],
    "tiktok_t2": unit(0.6 * E[0] + 0.8 * E[2]),
    "pexels_p1": unit(0.8 * E[0] + 0.6 * E[3]),
    "pexels_photo_p1": unit(0.8 * E[0] + 0.6 * E[3]),
    "tiktok_n1": unit(0.9 * E[1] + 0.43589 * E[2]),
}
SOURCE = {"video_id": "abc", "duration_s": 2.0, "transcript": [{"text": "five ancient creatures", "start": 0.0, "duration": 2.0}]}


class FakeEncoder:
    """Vektor ditentuin dari nama file: frame segmen, frame verifikasi, thumbnail, atau foto."""

    def images(self, paths):
        return unit(np.stack([self._vector(Path(p)) for p in paths]))

    def texts(self, texts):
        raise AssertionError("hook nggak pakai teks")

    def _vector(self, path):
        if path.name.startswith("seg_"):
            return SEGMENT_VECTORS[int(path.name[4:6])]
        if path.parent.parent.name == "verify":
            return TABLE[path.parent.name] if path.stem == "f_0003" else E[3]
        return TABLE[path.stem]


class FakeSearcher:
    def __init__(self, name, language, results, *, video, photo, blocked=False):
        self.name, self.language = name, language
        self.results, self.video, self.photo, self.blocked = results, video, photo, blocked
        self.queries = []

    def search(self, query):
        self.queries.append(query)
        if self.blocked:
            raise PlatformBlocked(self.name, "captcha/login")
        return list(self.results.get(query, []))

    def download(self, candidate, dest):
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(self.video if candidate.kind == "video" else self.photo, dest)
        return dest


def make_deps(tmp_path, cut_video, make_photo, searchers, queries):
    thumbs = tmp_path / "thumbs"
    thumbs.mkdir()
    downloads = []

    def fetch_thumb(candidate):
        path = thumbs / f"{candidate.provider}_{candidate.id}.jpg"
        if candidate.id == "bad":
            path.write_bytes(b"<html>403</html>")
        else:
            Image.new("RGB", (8, 8)).save(path)
        return path

    def download_source(video_id, dest):
        downloads.append(video_id)
        shutil.copyfile(cut_video, dest)
        return dest

    deps = HookDeps(
        download_source=download_source,
        encoder=FakeEncoder(),
        describe=lambda infos, frames: queries,
        searchers=searchers,
        fetch_thumb=fetch_thumb,
        log=lambda message: None,
    )
    return deps, downloads


def test_run_hook_picks_best_verified_clip_per_segment(tmp_path, cut_video, make_photo):
    photo = make_photo(640, 480)
    tiktok = FakeSearcher("tiktok", "en", {
        "crab": [cand("tiktok", "t1"), cand("tiktok", "t2"), cand("tiktok", "bad")],
        "nautilus": [cand("tiktok", "t1"), cand("tiktok", "n1")],
    }, video=cut_video, photo=photo)
    douyin = FakeSearcher("douyin", "zh", {}, video=cut_video, photo=photo, blocked=True)
    stock = FakeSearcher("stock", "en", {"crab": [cand("pexels", "p1", kind="photo")]}, video=cut_video, photo=photo)
    queries = {0: {"en": ["crab"], "zh": ["鲎"]}, 1: {"en": ["nautilus"], "zh": ["鹦鹉螺"]}}
    deps, downloads = make_deps(tmp_path, cut_video, make_photo, [tiktok, douyin, stock], queries)
    paths = RunPaths(tmp_path / "run")

    data = run_hook(paths, SOURCE, deps, hook_seconds=10.0, exact_threshold=0.95, media_cache=tmp_path / "media")

    assert downloads == ["abc"]
    assert read_json(paths.hook_json) == data
    assert data["skipped_platforms"] == [{"platform": "douyin", "reason": "captcha/login"}]
    assert douyin.queries == ["鲎"]
    first, second = data["segments"]
    assert [c["provider_id"] for c in first["candidates"]] == ["t1", "p1", "t2"]
    assert first["winner"] == {
        "source": "tiktok", "provider": "tiktok", "provider_id": "t1", "kind": "video", "file": "hook/winner_01.mp4",
        "offset_s": 1.0, "score": 1.0, "label": "exact", "page_url": "https://tiktok.test/t1", "author": "tester",
    }
    assert (paths.root / "hook" / "winner_01.mp4").exists()
    assert second["winner"]["provider_id"] == "n1"
    assert second["winner"]["label"] == "similar"
    assert second["winner"]["score"] == pytest.approx(0.9, abs=1e-3)
    assert all(c["provider_id"] != "t1" for c in second["candidates"])


def test_run_hook_without_candidates_keeps_winner_empty(tmp_path, cut_video, make_photo):
    deps, downloads = make_deps(tmp_path, cut_video, make_photo, [], {0: {"en": [], "zh": []}, 1: {"en": [], "zh": []}})
    paths = RunPaths(tmp_path / "run")
    paths.root.mkdir(parents=True)
    shutil.copyfile(cut_video, paths.source_mp4)
    data = run_hook(paths, SOURCE, deps, hook_seconds=10.0, exact_threshold=0.85, media_cache=tmp_path / "media")
    assert downloads == []
    assert len(data["segments"]) == 2
    assert all(segment["winner"] is None for segment in data["segments"])


def test_source_download_error_tells_how_to_retry(tmp_path, cut_video, make_photo):
    from mayzfact.errors import PipelineError

    deps, _ = make_deps(tmp_path, cut_video, make_photo, [], {})

    def broken_download(video_id, dest):
        raise PipelineError("hook", "yt-dlp gagal download")

    deps.download_source = broken_download
    with pytest.raises(PipelineError, match="--from hook"):
        run_hook(RunPaths(tmp_path / "run"), SOURCE, deps, hook_seconds=10.0, exact_threshold=0.85, media_cache=tmp_path / "media")
```

- [ ] **Step 2: Jalanin test, pastiin gagal**

Run: `uv run pytest tests/test_hook.py -q`
Expected: FAIL dengan `ModuleNotFoundError: No module named 'mayzfact.steps.hook'`.

- [ ] **Step 3: Implementasi**

`mayzfact/steps/hook.py`:

```python
"""Step hook: cari klip HOOK_SECONDS awal yang sama/mirip source (spec Fase 2 bagian 4)."""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Protocol
from urllib.parse import urlparse

import numpy as np

from mayzfact.embed import Encoder, can_open_image, mean_unit
from mayzfact.errors import PipelineError
from mayzfact.ffmpeg import extract_frame, probe, sample_frames
from mayzfact.hook_queries import describe_segments, transcript_near
from mayzfact.matching import match_label, top_k
from mayzfact.media import pick_rendition
from mayzfact.net import download
from mayzfact.platforms.base import PlatformBlocked
from mayzfact.providers.types import Candidate
from mayzfact.scenes import detect_cuts, merge_cuts, segments
from mayzfact.store import RunPaths, write_json_atomic

FRAME_POSITIONS = (0.25, 0.5, 0.75)
TOP_PER_SOURCE = 8
MIN_RESULTS_BEFORE_SECOND_QUERY = 3
VERIFY_TOP = 3
VERIFY_EVERY_S = 0.5
VERIFY_MAX_S = 30.0
KEEP_CANDIDATES = 5
PHOTO_EXTS = {".jpg", ".jpeg", ".png", ".webp"}


class Searcher(Protocol):
    name: str
    language: str

    def search(self, query: str) -> list[Candidate]: ...

    def download(self, candidate: Candidate, dest: Path) -> Path: ...


@dataclass
class HookDeps:
    download_source: Callable[[str, Path], Path]
    encoder: Encoder
    describe: Callable[[list[dict], list[Path]], dict[int, dict]]
    searchers: list[Any]
    fetch_thumb: Callable[[Candidate], Path | None]
    log: Callable[[str], None] = print
    close: Callable[[], None] = lambda: None


class StockSearcher:
    """Pexels + Pixabay (video & foto) sebagai satu sumber hook."""

    name = "stock"
    language = "en"

    def __init__(self, stock: Any, client: Any, fg_min_ratio: float) -> None:
        self._stock, self._client, self._fg = stock, client, fg_min_ratio

    def search(self, query: str) -> list[Candidate]:
        return self._stock.candidates("video", query) + self._stock.candidates("photo", query)

    def download(self, candidate: Candidate, dest: Path) -> Path:
        return download(self._client, pick_rendition(candidate, self._fg).url, dest, step="hook")


def _media_ext(candidate: Candidate) -> str:
    if candidate.kind == "video":
        return ".mp4"
    suffix = Path(urlparse(candidate.renditions[0].url).path).suffix.lower() if candidate.renditions else ""
    return suffix if suffix in PHOTO_EXTS else ".jpg"


def _gather(queries: dict, deps: HookDeps, skipped: dict[str, str], used: set) -> list[tuple[Any, Candidate]]:
    found: list[tuple[Any, Candidate]] = []
    seen = set(used)
    for searcher in deps.searchers:
        if searcher.name in skipped:
            continue
        for query in queries.get(searcher.language, [])[:2]:
            try:
                results = searcher.search(query)
            except PlatformBlocked as exc:
                skipped[searcher.name] = exc.reason
                deps.log(f"[hook] {searcher.name} di-skip ({exc.reason}). Login ulang: mayzfact login {searcher.name}")
                break
            except PipelineError as exc:
                deps.log(f"[hook] search {searcher.name} gagal: {exc.message[:120]}")
                break
            fresh = [c for c in results if (c.provider, c.id) not in seen][:TOP_PER_SOURCE]
            for candidate in fresh:
                seen.add((candidate.provider, candidate.id))
                found.append((searcher, candidate))
            if len(results) >= MIN_RESULTS_BEFORE_SECOND_QUERY:
                break
    return found


def _verify(searcher: Any, candidate: Candidate, seg_vec: np.ndarray, deps: HookDeps, paths: RunPaths, media_cache: Path):
    media = media_cache / f"{candidate.provider}_{candidate.kind}_{candidate.id}{_media_ext(candidate)}"
    try:
        media = searcher.download(candidate, media)
        if candidate.kind == "video":
            frames = sample_frames(
                media, paths.hook_dir / "verify" / f"{candidate.provider}_{candidate.id}",
                every_s=VERIFY_EVERY_S, max_s=VERIFY_MAX_S,
            )
            if not frames:
                raise PipelineError("hook", f"{media.name} nggak punya frame")
            sims = deps.encoder.images([p for _, p in frames]) @ seg_vec
            best = int(np.argmax(sims))
            return float(sims[best]), frames[best][0], media
        if not can_open_image(media):
            raise PipelineError("hook", f"{media.name} bukan gambar")
        return float((deps.encoder.images([media]) @ seg_vec)[0]), 0.0, media
    except (PipelineError, PlatformBlocked, OSError) as exc:
        deps.log(f"[hook] {candidate.provider} {candidate.id} gagal diverifikasi: {str(exc)[:120]}")
        if isinstance(exc, PipelineError):
            media.unlink(missing_ok=True)  # file rusak jangan dipakai ulang dari cache
        return None


def _match_segment(info, seg_vec, queries, deps, skipped, used, paths, media_cache, threshold) -> dict:
    record = {
        "index": info["index"], "start_s": info["start_s"], "end_s": info["end_s"],
        "queries": queries, "candidates": [], "winner": None,
    }
    thumbs = []
    for searcher, candidate in _gather(queries, deps, skipped, used):
        path = deps.fetch_thumb(candidate)
        if path is not None and can_open_image(path):
            thumbs.append((searcher, candidate, path))
    if not thumbs:
        deps.log(f"[hook] segmen {info['index'] + 1}: nggak ada kandidat")
        return record
    scores = [float(s) for s in deps.encoder.images([t[2] for t in thumbs]) @ seg_vec]
    order = top_k(scores, max(VERIFY_TOP, KEEP_CANDIDATES))
    record["candidates"] = [
        {"source": thumbs[j][0].name, "provider_id": thumbs[j][1].id, "thumb_score": round(scores[j], 4)}
        for j in order[:KEEP_CANDIDATES]
    ]
    best = None
    for j in order[:VERIFY_TOP]:
        searcher, candidate, _ = thumbs[j]
        verified = _verify(searcher, candidate, seg_vec, deps, paths, media_cache)
        if verified and (best is None or verified[0] > best[0]):
            best = (*verified, searcher, candidate)
    if best is None:
        deps.log(f"[hook] segmen {info['index'] + 1}: semua kandidat gagal diverifikasi")
        return record
    score, offset, media, searcher, candidate = best
    dest = paths.hook_dir / f"winner_{info['index'] + 1:02d}{media.suffix}"
    shutil.copyfile(media, dest)
    used.add((candidate.provider, candidate.id))
    record["winner"] = {
        "source": searcher.name, "provider": candidate.provider, "provider_id": candidate.id, "kind": candidate.kind,
        "file": f"hook/{dest.name}", "offset_s": offset, "score": round(score, 4),
        "label": match_label(score, threshold), "page_url": candidate.page_url, "author": candidate.author,
    }
    deps.log(f"[hook] segmen {info['index'] + 1}: {searcher.name} {candidate.id} skor {score:.3f} ({record['winner']['label']})")
    return record


def run_hook(
    paths: RunPaths, source: dict, deps: HookDeps, *, hook_seconds: float, exact_threshold: float, media_cache: Path
) -> dict:
    src = paths.source_mp4
    try:
        if not src.exists():
            deps.download_source(source["video_id"], src)
        end_s = min(hook_seconds, probe(src, "hook")["duration_s"] or 0.0)
        segs = segments(merge_cuts(detect_cuts(src, end_s)), end_s)
    except PipelineError as exc:
        raise PipelineError(
            "hook", f"{exc.message}\nUlang step ini pakai: mayzfact run {source['video_id']} --from hook"
        ) from exc
    paths.hook_dir.mkdir(parents=True, exist_ok=True)
    infos: list[dict] = []
    seg_frames: list[list[Path]] = []
    for i, (start, end) in enumerate(segs):
        seg_frames.append([
            extract_frame(src, start + (end - start) * pos, paths.hook_dir / f"seg_{i + 1:02d}_{k}.jpg")
            for k, pos in enumerate(FRAME_POSITIONS)
        ])
        infos.append({"index": i, "start_s": start, "end_s": end, "transcript": transcript_near(source["transcript"], start, end)})
    deps.log(f"[hook] {len(segs)} segmen di {end_s:.1f} detik awal source")
    queries = deps.describe(infos, [frames[1] for frames in seg_frames]) if segs else {}
    skipped: dict[str, str] = {}
    used: set[tuple[str, str]] = set()
    results = []
    for info, frames in zip(infos, seg_frames):
        seg_vec = mean_unit(deps.encoder.images(frames))
        seg_queries = queries.get(info["index"], {"en": [], "zh": []})
        results.append(_match_segment(info, seg_vec, seg_queries, deps, skipped, used, paths, media_cache, exact_threshold))
    data = {
        "hook_seconds": hook_seconds,
        "skipped_platforms": [{"platform": name, "reason": reason} for name, reason in skipped.items()],
        "segments": results,
    }
    write_json_atomic(paths.hook_json, data)
    return data


def real_hook_deps(settings: Any, client: Any, stock: Any, encoder: Encoder, fetch_thumb: Callable, log: Callable) -> HookDeps:
    from mayzfact.platforms.browser import BrowserPlatform
    from mayzfact.providers.gemini import GeminiScriptWriter
    from mayzfact.ytdlp import run_ytdlp, youtube_url

    browsers = [BrowserPlatform(name, client=client, headless=settings.browser_headless, log=log) for name in settings.hook_platforms]
    writer = GeminiScriptWriter(settings.gemini_api_keys, settings.gemini_model) if settings.gemini_api_keys else None

    def close() -> None:
        for platform in browsers:
            platform.close()

    return HookDeps(
        download_source=lambda video_id, dest: run_ytdlp(youtube_url(video_id), dest),
        encoder=encoder,
        describe=lambda infos, frames: describe_segments(writer, infos, frames, log),
        searchers=[*browsers, StockSearcher(stock, client, settings.fg_min_height_ratio)],
        fetch_thumb=fetch_thumb,
        log=log,
        close=close,
    )
```

- [ ] **Step 4: Jalanin test, pastiin lolos**

Run: `uv run pytest tests/test_hook.py -q`
Expected: 2 PASS.

- [ ] **Step 5: Commit**

```bash
git add mayzfact/steps/hook.py tests/test_hook.py
git commit -m "feat: add hook step matching source clips"
```

---

### Task 12: Thumbnail, `ThumbScorer`, dan integrasi ke `clips`

**Files:**

- Create: `mayzfact/thumbs.py`, `mayzfact/scoring.py`
- Modify: `mayzfact/steps/clips.py`
- Test: `tests/test_scoring.py`, `tests/test_clips_hook.py`, `tests/test_clip_selection.py`

**Interfaces:**

- Consumes:
  - `Encoder`, `can_open_image` (Task 4)
  - `hook_slot_map`, `rerank_key` (Task 5)
  - `download` (Fase 1)
  - Fungsi Fase 1 di `steps/clips.py`
- Produces:
  - `thumb_path(root, candidate) -> Path` dan `fetch_thumbnail(client, root, candidate) -> Path | None`
  - `ThumbScorer(encoder, fetch)` dengan `.score(text, candidates) -> list[float]` (gagal = -1.0)
  - Protocol `Scorer` di `steps/clips.py`
  - `pick_for_slot(..., scorer=None)`
  - `run_clips(..., hook: dict | None = None, scorer: Scorer | None = None, hook_seconds: float = 10.0)`
  - Entry hook di `clips.json` punya field tambahan `hook_segment` dan `match`.

- [ ] **Step 1: Tulis test yang gagal**

`tests/test_scoring.py`:

```python
import httpx
import numpy as np
from PIL import Image

from mayzfact.embed import unit
from mayzfact.scoring import ThumbScorer
from mayzfact.thumbs import fetch_thumbnail
from tests.factories import cand


class FakeEncoder:
    def __init__(self, table):
        self.table = table

    def images(self, paths):
        return unit(np.stack([self.table[p.stem] for p in paths]))

    def texts(self, texts):
        return unit(np.array([[1.0, 0.0]]))


def test_thumb_scorer_scores_text_against_thumbnails(tmp_path):
    good = tmp_path / "good.jpg"
    Image.new("RGB", (8, 8)).save(good)
    other = tmp_path / "other.jpg"
    Image.new("RGB", (8, 8)).save(other)
    broken = tmp_path / "broken.jpg"
    broken.write_bytes(b"<html>")
    files = {"a": good, "b": other, "c": broken, "d": None}
    scorer = ThumbScorer(FakeEncoder({"good": np.array([1.0, 0.0]), "other": np.array([0.0, 1.0])}), lambda c: files[c.id])
    scores = scorer.score("a horseshoe crab", [cand("pexels", i) for i in "abcd"])
    assert scores[0] > scores[1]
    assert scores[2:] == [-1.0, -1.0]


def test_fetch_thumbnail(tmp_path):
    def handler(request):
        if request.url.path == "/ok.jpg":
            return httpx.Response(200, content=b"jpg-bytes")
        return httpx.Response(404)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    ok = fetch_thumbnail(client, tmp_path, cand("pexels", "1", thumbnail_url="https://cdn.test/ok.jpg"))
    assert ok == tmp_path / "pexels_1.jpg" and ok.read_bytes() == b"jpg-bytes"
    assert fetch_thumbnail(client, tmp_path, cand("pexels", "2", thumbnail_url="https://cdn.test/missing.jpg")) is None
    assert fetch_thumbnail(client, tmp_path, cand("pexels", "3", thumbnail_url="")) is None
```

Tambahin ke `tests/test_clip_selection.py`:

```python
class FixedScorer:
    def __init__(self, table):
        self.table = table
        self.calls = []

    def score(self, text, candidates):
        self.calls.append((text, [c.id for c in candidates]))
        return [self.table[c.id] for c in candidates]


def test_scorer_picks_best_scored_candidate_across_all_queries():
    low = cand("pexels", "low", rank=0)
    blurry = cand("pexels", "blurry", width=640, height=360, rank=1)
    high = cand("pixabay", "high", rank=3)
    search = FakeSearch({("video", "horseshoe crab"): [low, blurry], ("video", "crab beach"): [high]})
    scorer = FixedScorer({"low": 0.1, "blurry": 0.9, "high": 0.3})
    assert pick_for_slot(slot(), BEAT, "animals", search, set(), 0.5, scorer=scorer) == (high, "crab beach")
    assert search.calls == [("video", "horseshoe crab"), ("video", "crab beach")]
    assert scorer.calls == [("Look at this crab.", ["low", "blurry", "high"])]
```

`tests/test_clips_hook.py`:

```python
import shutil

import httpx

from mayzfact.ffmpeg import probe
from mayzfact.steps.clips import run_clips
from mayzfact.store import RunPaths
from tests.factories import cand, fake_alignment

SCRIPT = {
    "beats": [
        {"text": "Look at this.", "media": "video", "queries": ["crab"]},
        {"text": "It is old.", "media": "photo", "queries": ["fossil"]},
    ],
    "fallback_query": "animals",
}
TTS = {"duration_s": 3.0, "alignment": fake_alignment("Look at this. It is old.", 2.4)}


class FakeSearch:
    def candidates(self, kind, query):
        if (kind, query) == ("video", "crab"):
            return [cand("pexels", "v1", "video", 1080, 1920, duration_s=10.0, url="https://cdn.test/v1.mp4")]
        if (kind, query) == ("photo", "fossil"):
            return [cand("pixabay", "p1", "photo", 1600, 1000, url="https://cdn.test/p1.jpg")]
        return []


def hook_data(winner_file):
    return {"hook_seconds": 10.0, "skipped_platforms": [], "segments": [
        {"index": 0, "start_s": 0.0, "end_s": 1.9, "queries": {}, "candidates": [], "winner": None},
        {"index": 1, "start_s": 1.9, "end_s": 3.0, "queries": {}, "candidates": [], "winner": {
            "source": "tiktok", "provider": "tiktok", "provider_id": "w1", "kind": "video", "file": winner_file,
            "offset_s": 3.0, "score": 0.93, "label": "exact", "page_url": "https://www.tiktok.com/@a/video/w1", "author": "a",
        }},
    ]}


def run(tmp_path, make_video, make_photo, winner_seconds, logs):
    files = {"/v1.mp4": make_video(1080, 1920, 5.0).read_bytes(), "/p1.jpg": make_photo(1600, 1000).read_bytes()}
    client = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, content=files[r.url.path])))
    paths = RunPaths(tmp_path / "run")
    (paths.root / "hook").mkdir(parents=True)
    shutil.copyfile(make_video(1080, 1920, winner_seconds), paths.root / "hook" / "winner_02.mp4")
    data = run_clips(
        paths, SCRIPT, TTS, FakeSearch(), client, max_shot_s=2.5, fg_min_ratio=0.5,
        media_cache=tmp_path / "media", log=logs.append, hook=hook_data("hook/winner_02.mp4"), hook_seconds=10.0,
    )
    return paths, data


def test_hook_winner_fills_first_shot(tmp_path, make_video, make_photo):
    paths, data = run(tmp_path, make_video, make_photo, 5.0, [])
    first, second = data["shots"]
    assert (first["provider"], first["provider_id"], first["hook_segment"], first["match"]) == ("tiktok", "w1", 1, "exact")
    assert first["query"] == "hook:1"
    assert first["file"] == "clips/shot_01.mp4"
    assert abs(probe(paths.root / first["file"], "clips")["duration_s"] - 1.6) < 0.1
    assert second["provider"] == "pixabay"


def test_short_hook_video_falls_back_to_stock(tmp_path, make_video, make_photo):
    logs = []
    _, data = run(tmp_path, make_video, make_photo, 1.0, logs)
    assert data["shots"][0]["provider"] == "pexels"
    assert "hook_segment" not in data["shots"][0]
    assert any("gagal dipakai" in line for line in logs)
```

- [ ] **Step 2: Jalanin test, pastiin gagal**

Run: `uv run pytest tests/test_scoring.py tests/test_clips_hook.py tests/test_clip_selection.py -q`
Expected: FAIL dengan `ModuleNotFoundError: No module named 'mayzfact.scoring'` dan `TypeError: pick_for_slot() got an unexpected keyword argument 'scorer'`.

- [ ] **Step 3: Implementasi**

`mayzfact/thumbs.py`:

```python
"""Thumbnail kandidat: di-download sekali ke cache, terus dipakai hook dan rerank."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from mayzfact.errors import PipelineError
from mayzfact.net import download
from mayzfact.providers.types import Candidate


def thumb_path(root: Path, candidate: Candidate) -> Path:
    return root / f"{candidate.provider}_{candidate.id}.jpg"


def fetch_thumbnail(client: Any, root: Path, candidate: Candidate) -> Path | None:
    if not candidate.thumbnail_url:
        return None
    try:
        return download(client, candidate.thumbnail_url, thumb_path(root, candidate), step="clips")
    except PipelineError:
        return None
```

`mayzfact/scoring.py`:

```python
"""Skor relevansi kandidat stock: SigLIP teks beat vs thumbnail (spec Fase 2 bagian 6)."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from mayzfact.embed import Encoder, can_open_image
from mayzfact.providers.types import Candidate


class ThumbScorer:
    def __init__(self, encoder: Encoder, fetch: Callable[[Candidate], Path | None]) -> None:
        self._encoder = encoder
        self._fetch = fetch

    def score(self, text: str, candidates: list[Candidate]) -> list[float]:
        paths = [self._fetch(c) for c in candidates]
        valid = [i for i, p in enumerate(paths) if p is not None and can_open_image(p)]
        scores = [-1.0] * len(candidates)
        if valid:
            sims = self._encoder.images([paths[i] for i in valid]) @ self._encoder.texts([text])[0]
            for i, sim in zip(valid, sims):
                scores[i] = float(sim)
        return scores
```

Di `mayzfact/steps/clips.py`:

Langkah 1: Tambahin import `from mayzfact.matching import hook_slot_map, rerank_key`.
Langkah 2: Tambahin di bawah `MediaSearch`:

```python
class Scorer(Protocol):
    def score(self, text: str, candidates: list[Candidate]) -> list[float]: ...


def _usable(candidates: list[Candidate], used: set[tuple[str, str]], min_duration_s: float) -> list[Candidate]:
    return [
        c
        for c in candidates
        if (c.provider, c.id) not in used and c.renditions and (c.kind == "photo" or (c.duration_s or 0) >= min_duration_s)
    ]
```

Langkah 3: Isi `choose_candidate` diganti:

```python
    usable = _usable(candidates, used, min_duration_s)
    if not usable:
        return None
    return min(usable, key=lambda c: (tier(c, fg_min_ratio), c.rank, PROVIDER_ORDER.get(c.provider, 9)))
```

Langkah 4: `pick_for_slot` dapat parameter terakhir `scorer: Scorer | None = None`, dan isinya setelah rotasi `queries` diganti:

```python
    groups = [(slot.media, queries), (other, queries), (slot.media, [fallback_query]), (other, [fallback_query])]
    min_duration = slot.duration_s + MIN_EXTRA_S
    for kind, group_queries in groups:
        if scorer is None:
            for query in group_queries:
                found = choose_candidate(search.candidates(kind, query), used, min_duration, fg_min_ratio)
                if found is not None:
                    return found, query
            continue
        pool: dict[tuple[str, str], tuple[Candidate, str]] = {}
        for query in group_queries:
            for candidate in _usable(search.candidates(kind, query), used, min_duration):
                pool.setdefault((candidate.provider, candidate.id), (candidate, query))
        if pool:
            items = list(pool.values())
            scores = scorer.score(beat["text"], [c for c, _ in items])
            best = min(
                range(len(items)),
                key=lambda i: rerank_key(scores[i], tier(items[i][0], fg_min_ratio), PROVIDER_ORDER.get(items[i][0].provider, 9)),
            )
            return items[best]
    raise PipelineError(
        "clips",
        f'Beat {slot.beat + 1} ("{beat["text"][:50]}") nggak dapet klip video/foto sama sekali, termasuk pakai fallback_query.',
    )
```

Langkah 5: Tambahin fungsi di atas `run_clips`:

```python
def _hook_entry(slot: ShotSlot, segment: dict, paths: RunPaths, fg_min_ratio: float, log: Callable[[str], None]) -> dict | None:
    winner = segment["winner"]
    raw = paths.root / winner["file"]
    try:
        if winner["kind"] == "video":
            info = probe(raw, "clips")
            duration = info["duration_s"] or 0.0
            if duration < slot.duration_s + 0.2:
                raise PipelineError("clips", f"video cuma {duration:.1f} detik, shot butuh {slot.duration_s:.1f}")
            latest = duration - slot.duration_s - 0.2
            start = min(max(0.0, winner["offset_s"] - slot.duration_s / 2), latest)
            dest = paths.clips_dir / f"shot_{slot.index + 1:02d}.mp4"
            scale = downscale_factor(info["width"], info["height"], fg_min_ratio)
            normalize_video(raw, dest, start_s=start, duration_s=slot.duration_s + 0.2, scale=scale)
            out = probe(dest, "clips")
            width, height = out["width"], out["height"]
        else:
            dest = paths.clips_dir / f"shot_{slot.index + 1:02d}.jpg"
            width, height = normalize_photo(raw, dest, fg_min_ratio=fg_min_ratio)
    except (PipelineError, OSError, ValueError, KeyError) as exc:
        log(f"[clips] hook segmen {segment['index'] + 1} gagal dipakai, pakai klip biasa: {exc}")
        return None
    return {
        "index": slot.index, "beat": slot.beat, "start_s": slot.start_s, "end_s": slot.end_s,
        "kind": winner["kind"], "file": f"clips/{dest.name}", "width": width, "height": height,
        "provider": winner["provider"], "provider_id": winner["provider_id"],
        "page_url": winner["page_url"], "author": winner["author"],
        "query": f"hook:{segment['index']}", "hook_segment": segment["index"], "match": winner["label"],
    }
```

Langkah 6: `run_clips` dapat parameter keyword tambahan `hook: dict | None = None, scorer: Scorer | None = None, hook_seconds: float = 10.0`. Ganti bagian `used = ...` sampai sebelum `data = ...` jadi:

```python
    winners = [segment for segment in (hook or {}).get("segments", []) if segment.get("winner")]
    hook_map = hook_slot_map(slots, len(winners), hook_seconds)
    used: set[tuple[str, str]] = {(s["winner"]["provider"], s["winner"]["provider_id"]) for s in winners}
    shots = []
    for slot in slots:
        if slot.index in hook_map:
            entry = _hook_entry(slot, winners[hook_map[slot.index]], paths, fg_min_ratio, log)
            if entry is not None:
                log(f"[clips] shot {slot.index + 1}/{len(slots)}: hook {entry['provider']} {entry['provider_id']} ({entry['match']})")
                shots.append(entry)
                continue
        beat = script["beats"][slot.beat]
        for attempt in range(MAX_PICK_ATTEMPTS):
            candidate, query = pick_for_slot(slot, beat, script["fallback_query"], search, used, fg_min_ratio, scorer)
            used.add((candidate.provider, candidate.id))
            log(f"[clips] shot {slot.index + 1}/{len(slots)}: {candidate.provider} {candidate.kind} {candidate.id} ({query})")
            try:
                shots.append(materialize(slot, candidate, query, paths, client, media_cache, fg_min_ratio))
                break
            except PipelineError as exc:
                # Link mati / file rusak: ganti ke kandidat berikutnya, jangan stop seluruh step.
                if attempt == MAX_PICK_ATTEMPTS - 1:
                    raise
                log(f"[clips] {candidate.provider} {candidate.id} gagal dipakai, ganti klip: {exc.message[:120]}")
```

- [ ] **Step 4: Jalanin test, pastiin lolos**

Run: `uv run pytest tests/test_scoring.py tests/test_clips_hook.py tests/test_clip_selection.py tests/test_clips_step.py -q`
Expected: semua PASS.

- [ ] **Step 5: Commit**

```bash
git add mayzfact/thumbs.py mayzfact/scoring.py mayzfact/steps/clips.py tests/test_scoring.py tests/test_clips_hook.py tests/test_clip_selection.py
git commit -m "feat: use hook winners and siglip rerank in clips"
```

---

### Task 13: Wiring pipeline

**Files:**

- Modify: `mayzfact/pipeline.py`
- Test: `tests/test_pipeline.py`

**Interfaces:**

- Consumes:
  - `run_hook`, `real_hook_deps` (Task 11)
  - `ThumbScorer` (Task 12), `fetch_thumbnail` (Task 12)
  - `SiglipEncoder` (Task 4)
  - `run_clips(..., hook=, scorer=, hook_seconds=)` (Task 12)
- Produces:
  - `STEPS = ["source","script","tts","hook","clips","timeline","render"]`
  - `AFTER_VOICE = ("hook","clips","timeline","render")`
  - Field baru di `Deps`: `hook: Callable[[RunPaths, Callable[[str], None]], dict] | None = None` dan `scorer: Callable[[], Scorer | None] = lambda: None`

- [ ] **Step 1: Tulis test yang gagal**

Tambahin ke `tests/test_pipeline.py` (import `import mayzfact.pipeline as pipeline_mod` di blok atas):

```python
EMPTY_HOOK = {"hook_seconds": 10.0, "skipped_platforms": [], "segments": []}


def test_hook_runs_before_clips_and_feeds_it(world, monkeypatch):
    calls = []

    def fake_hook(paths, log):
        calls.append(paths.root.name)
        write_json_atomic(paths.hook_json, EMPTY_HOOK)
        return EMPTY_HOOK

    world.deps.hook = fake_hook
    seen = {}
    real_run_clips = pipeline_mod.run_clips

    def spy(*args, **kwargs):
        seen.update(kwargs)
        return real_run_clips(*args, **kwargs)

    monkeypatch.setattr(pipeline_mod, "run_clips", spy)
    run(world)
    assert calls == [VIDEO_ID]
    assert seen["hook"] == EMPTY_HOOK
    assert seen["hook_seconds"] == 10.0
    assert seen["scorer"] is None


def test_without_hook_runner_writes_empty_hook(world):
    paths = run(world)
    assert read_json(paths.hook_json) == EMPTY_HOOK


def test_from_hook_after_voice_does_not_call_tts(world):
    run(world)
    run(world, from_step="hook")
    assert world.tts.calls == 1
    assert world.renders == 2


def test_old_run_without_hook_json_resumes_from_hook(world):
    paths = run(world)
    paths.hook_json.unlink()
    run(world)
    assert paths.hook_json.exists()
    assert (world.tts.calls, world.renders) == (1, 2)
```

- [ ] **Step 2: Jalanin test, pastiin gagal**

Run: `uv run pytest tests/test_pipeline.py -q`
Expected: FAIL. Contohnya `AttributeError: 'RunPaths' ... hook_json` belum ditulis pipeline, atau `KeyError: 'hook'` di `seen`.

- [ ] **Step 3: Implementasi**

Di `mayzfact/pipeline.py`:

Langkah 1: Tambahin import:

```python
from mayzfact.scoring import ThumbScorer
from mayzfact.steps.clips import MediaSearch, Scorer, run_clips
from mayzfact.store import RunPaths, read_json, write_json_atomic
from mayzfact.thumbs import fetch_thumbnail
```

(gabung sama import `MediaSearch, run_clips` dan `RunPaths, read_json` yang udah ada)

Langkah 2: Ganti konstanta:

```python
STEPS = ["source", "script", "tts", "hook", "clips", "timeline", "render"]
AFTER_VOICE = ("hook", "clips", "timeline", "render")
```

Langkah 3: Di `step_outputs`, tambahin `"hook": [paths.hook_json],`.
Langkah 4: Di `Deps`, tambahin dua field terakhir:

```python
    hook: Callable[[RunPaths, Callable[[str], None]], dict] | None = None
    scorer: Callable[[], Scorer | None] = lambda: None
```

Langkah 5: Di `real_deps`, sebelum `return Deps(...)`:

```python
    encoders: dict[str, object] = {}

    def encoder():
        if "siglip" not in encoders:
            from mayzfact.embed import SiglipEncoder

            encoders["siglip"] = SiglipEncoder()
        return encoders["siglip"]

    def fetch_thumb(candidate):
        return fetch_thumbnail(http(), CACHE_DIR / "thumbs", candidate)

    def hook(paths: RunPaths, log: Callable[[str], None]) -> dict:
        from mayzfact.steps.hook import real_hook_deps, run_hook

        hook_deps = real_hook_deps(settings, http(), search(), encoder(), fetch_thumb, log)
        try:
            return run_hook(
                paths, read_json(paths.source_json), hook_deps,
                hook_seconds=settings.hook_seconds, exact_threshold=settings.hook_exact_threshold,
                media_cache=CACHE_DIR / "media",
            )
        finally:
            hook_deps.close()
```

Terus tambahin `hook=hook, scorer=lambda: ThumbScorer(encoder(), fetch_thumb),` ke `Deps(...)`.

Langkah 6: Di `_run_step`, tambahin cabang sebelum `clips`:

```python
    elif step == "hook":
        if deps.hook is None:
            write_json_atomic(paths.hook_json, {"hook_seconds": settings.hook_seconds, "skipped_platforms": [], "segments": []})
        else:
            deps.hook(paths, log)
```

Panggilan `run_clips` dapat argumen tambahan:

```python
            hook=read_json(paths.hook_json), scorer=deps.scorer(), hook_seconds=settings.hook_seconds,
```

Langkah 7: Pesan "Semua step ... udah selesai" diganti jadi `Pakai --from hook/clips/timeline/render buat bikin ulang.`

- [ ] **Step 4: Jalanin test, pastiin lolos**

Run: `uv run pytest tests/test_pipeline.py tests/test_cli.py -q`
Expected: semua PASS.

Run: `uv run pytest -q`
Expected: full suite PASS.

- [ ] **Step 5: Commit**

```bash
git add mayzfact/pipeline.py tests/test_pipeline.py
git commit -m "feat: wire hook step and siglip scorer into pipeline"
```

---

### Task 14: E2E `i2xag_1OJfM`, kalibrasi, handoff

**Files:**

- Modify (sesuai hasil):
  - `mayzfact/platforms/base.py`, `mayzfact/platforms/parsers.py`, dan test-nya (kalau payload asli beda)
  - `mayzfact/config.py`, `.env.example`, `docs/superpowers/specs/2026-10-03-fase2-hook-matching-design.md` (threshold)
  - `docs/DECISIONS.md`, `docs/HANDOFF.md`

**Interfaces:**

- Consumes: semua task sebelumnya
- Produces: bukti DoD spec bagian 11 dan `docs/HANDOFF.md` yang udah di-update

- [ ] **Step 1: Model + test lengkap**

Run: `uv run pytest -q`, `uv run pytest -m clip -q`, dan `uv run pytest -m render -q`
Expected: semua PASS.

- [ ] **Step 2: Akmal login 4 platform**

Minta Akmal jalanin `uv run mayzfact login tiktok`, terus `douyin`, `rednote`, dan `pinterest`, masing-masing login manual.

Run: `uv run mayzfact login --check`
Expected: 4 baris `login`.

Kalau ada yang `belum login` padahal udah login, cek nama cookie-nya. Script di bawah cuma nampilin nama cookie, bukan isinya:

```bash
uv run python -c "from mayzfact.platforms.browser import read_profile_cookies; print(sorted({c['name'] for c in read_profile_cookies('rednote')}))"
```

Habis itu benerin `login_cookie` di `PLATFORMS` + test-nya, terus catat ruling-nya.

- [ ] **Step 3: Rekam payload asli, cek parser**

```bash
uv run python - <<'EOF'
import json
from pathlib import Path
from mayzfact.net import make_client
from mayzfact.platforms.browser import BrowserPlatform
from mayzfact.platforms.parsers import PARSERS, SEARCH_PAGES, search_url

out = Path("runs/_platform_payloads")
out.mkdir(parents=True, exist_ok=True)
for name, query in [("tiktok", "horseshoe crab"), ("douyin", "鲎"), ("rednote", "鲎"), ("pinterest", "horseshoe crab")]:
    platform = BrowserPlatform(name, client=make_client())
    try:
        payloads = platform._capture(search_url(name, query), SEARCH_PAGES[name][1])
        (out / f"{name}.json").write_text(json.dumps(payloads, ensure_ascii=False, indent=1), encoding="utf-8")
        total = sum(len(PARSERS[name](p, 0)) for p in payloads)
        print(name, len(payloads), "payload,", total, "kandidat")
    except Exception as exc:
        print(name, "GAGAL:", type(exc).__name__, str(exc)[:200])
    finally:
        platform.close()
EOF
```

Expected: tiap platform dapat lebih dari 0 kandidat.

Kalau ada platform yang 0 kandidat atau gagal:

- Buka `runs/_platform_payloads/<name>.json`.
- Cocokin path field-nya dengan parser, terus benerin parser dan/atau pola di `SEARCH_PAGES`.
- Tambahin 1 item asli yang udah dipangkas (tanpa token/ID user) ke `tests/test_platform_parsers.py` sebagai regression test.
- Catat ruling-nya.

`runs/` gitignored, jadi payload mentah nggak ke-commit.

- [ ] **Step 4: Run hook beneran**

```bash
stat -c %Y runs/i2xag_1OJfM/voice.mp3
uv run mayzfact run i2xag_1OJfM --from hook > runs/hook1.log 2>&1; echo "exit=$?"
stat -c %Y runs/i2xag_1OJfM/voice.mp3
grep -v "Warning\|VersionedUnionType\|AFC" runs/hook1.log | grep "\[hook\]\|Selesai\|Error"
```

Expected:

- `exit=0`
- dua angka mtime sama
- log `[hook] 6 segmen ...` (±1), dengan skor dan label tiap segmen

- [ ] **Step 5: Contact sheet source vs pemenang (DoD 3–4)**

```bash
uv run python - <<'EOF'
import json, subprocess
from pathlib import Path
run = Path("runs/i2xag_1OJfM")
hook = json.loads((run / "hook.json").read_text(encoding="utf-8"))
rows = []
for seg in hook["segments"]:
    w = seg["winner"]
    print(seg["index"] + 1, f"{seg['start_s']}-{seg['end_s']}", seg["queries"].get("en"), "->",
          (w["source"], w["provider_id"], w["score"], w["label"]) if w else None)
    if not w:
        continue
    src = run / "hook" / f"seg_{seg['index'] + 1:02d}_1.jpg"
    win = run / "hook" / f"cmp_{seg['index'] + 1:02d}.jpg"
    if w["kind"] == "video":
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", str(w["offset_s"]), "-i", str(run / w["file"]), "-frames:v", "1", "-vf", "scale=448:-2", str(win)], check=True)
    else:
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(run / w["file"]), "-vf", "scale=448:-2", str(win)], check=True)
    row = run / "hook" / f"row_{seg['index'] + 1:02d}.jpg"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(src), "-i", str(win), "-filter_complex", "[0]scale=-2:400[a];[1]scale=-2:400[b];[a][b]hstack", str(row)], check=True)
    rows.append(row)
args = sum((["-i", str(r)] for r in rows), [])
subprocess.run(["ffmpeg", "-y", "-v", "error", *args, "-filter_complex", f"{''.join(f'[{i}]scale=600:-2[r{i}];' for i in range(len(rows)))}{''.join(f'[r{i}]' for i in range(len(rows)))}vstack=inputs={len(rows)}", str(run / "hook_compare.jpg")], check=True)
print("skipped:", hook["skipped_platforms"])
EOF
```

Buka `runs/i2xag_1OJfM/hook_compare.jpg` pakai tool Read. Kiri = source, kanan = pemenang. Hitung segmen yang nunjukin hewan/objek yang sama. DoD 4: minimal setengah dari semua segmen. Kalau jumlah row cuma 1, perintah `vstack` gagal. Dalam kasus itu, buka file `row_*.jpg` langsung.

- [ ] **Step 6: Kalibrasi `HOOK_EXACT_THRESHOLD`**

Dari Step 5:

- A = skor terendah dari pasangan yang **jelas klip yang sama**.
- B = skor tertinggi dari pasangan yang cuma mirip.

Threshold baru = `round((A + B) / 2, 2)`. Kalau semua pasangan ada di satu kelompok aja, biarin 0.85 dan catat alasannya.

Update default di `mayzfact/config.py`, `.env.example`, spec bagian 8, dan test default di `tests/test_config.py`. Tambahin `D-015` di `docs/DECISIONS.md` yang isinya angka A, B, dan threshold.

Run: `uv run pytest tests/test_config.py -q`
Expected: PASS.

- [ ] **Step 7: Bandingin shot non-hook (DoD 5)**

```bash
ffmpeg -y -v error -i runs/i2xag_1OJfM/final.mp4 -vf "fps=1/2,scale=200:356,tile=7x4" -frames:v 1 -q:v 3 runs/i2xag_1OJfM/contact_sheet_fase2.jpg
```

Buka pakai tool Read. Bandingin sama contact sheet Fase 1 di `runs/i2xag_1OJfM/contact_sheet.png`, terutama di bagian horseshoe crab dan tardigrade. Catat hasilnya apa adanya.

- [ ] **Step 8: Check terakhir + handoff**

Run: `uv run pytest -q`, `uv run pytest -m clip -q`, `uv run pytest -m render -q`, dan `(cd remotion && npx tsc --noEmit)`
Expected: semua lolos.

Tambahin section `## Fase 2` di `docs/HANDOFF.md` pakai format yang sama kayak section Fase 1. Isinya hasil **asli** Step 2–7:

- status login
- jumlah segmen, skor, dan label
- platform yang di-skip
- threshold akhir
- hasil contact sheet
- jawaban Akmal setelah nonton

Minta Akmal nonton `runs/i2xag_1OJfM/final.mp4`.

- [ ] **Step 9: Commit**

```bash
git add docs/HANDOFF.md docs/DECISIONS.md mayzfact/config.py .env.example docs/superpowers/specs/2026-10-03-fase2-hook-matching-design.md tests/test_config.py mayzfact/platforms tests/test_platform_parsers.py tests/test_platform_base.py
git commit -m "docs: record fase 2 e2e results and threshold"
```
