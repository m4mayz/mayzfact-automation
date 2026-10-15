# Revisi Brief: Audio Naskah, Download Duluan, Frame Wajib — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Tombol waktu di tiap shot muter `voice.mp3`; link di-download begitu disimpan dengan status per shot; tiap shot punya frame referensi dan `brief` nolak jalan kalau belum.

**Architecture:** `page.py` ganti `seekSourceVideo` jadi `<audio id="voice">` + play/stop per shot. `server.py` nambah worker thread (antrean URL) yang manggil `Obtainer.obtain` dan nulis `prefetch.json`; `/api/progress` ikut ngirim isinya. `steps/plan.py` ngisi `ref_frames` per shot (hook / rentang subjek / proporsional); `cli._brief` ngecek semua shot punya frame.

**Tech Stack:** Python 3.14 + uv, `http.server`, `threading`, pytest, vanilla JS di string Python.

**Spec:** `docs/superpowers/specs/2026-10-15-brief-revisi-design.md`

## Global Constraints

- Server brief tetap tanpa dependency baru; worker pakai `threading.Thread` + `queue.Queue`.
- Download lewat `Obtainer.obtain(entry, run_root)` yang sama kayak fetch, cache `cache/manual/` sama, jadi fetch kena cache.
- Nggak ngulang download yang gagal otomatis; simpan ulang link yang sama = coba lagi.
- `group.ref_frames` dihapus dari plan dan halaman; frame per shot (3 per shot).
- Komentar kode bahasa Indonesia santai. Commit 1 baris, tanpa atribusi AI.
- Jangan ngubah format `links.json` dan `fetch` (run 4735 lagi diisi).

## Review Focus

1. Worker nggak boleh nahan `serve_forever`/shutdown: Ctrl+C harus berhenti walau antrean masih ada → test Task 2.
2. URL yang sama disimpan 2× cuma di-download 1× (dedup antrean + cache) → test Task 2.
3. Shot yang subjeknya nggak ketemu di transcript (CTA/intro) tetap dapat 3 frame proporsional, dan posisi di luar durasi source dipotong ke frame terakhir → test Task 3.
4. `brief` dengan plan lama (format `group.ref_frames`, shot tanpa `ref_frames`) harus nolak dengan pesan `--from plan`, bukan traceback → test Task 4.
5. Tombol audio: `voice.mp3` nggak ada → tombol disabled, bukan error JS → test Task 1 (HTML).

---

### Task 1: Tombol waktu muter `voice.mp3`

**Files:**
- Modify: `mayzfact/brief/page.py`, `mayzfact/brief/server.py` (kirim `voice` ke `render_page`), `tests/test_brief_server.py`

**Interfaces:**
- Produces: `render_page(run_id, plan, links, status, source=None, voice=None)`; HTML punya `<audio id="voice" src="/files/voice.mp3" preload="metadata">` kalau `voice`; tombol `.time-seek-pill` jadi `onclick="playBeat(this, START, END)"` dan `disabled` kalau `voice` None.

- [ ] **Step 1: Tulis test yang gagal** (`tests/test_brief_server.py`)

```python
def test_shot_time_buttons_play_the_narration_not_the_source(server):
    paths, base = server
    html = httpx.get(base + "/").text
    assert "seekSourceVideo" not in html
    assert 'class="time-seek-pill" disabled' in html  # voice.mp3 belum ada
    paths.voice_mp3.write_bytes(b"mp3")
    html = httpx.get(base + "/").text
    assert '<audio id="voice" src="/files/voice.mp3" preload="metadata">' in html
    assert 'onclick="playBeat(this, 2.0, 4.0)"' in html and "disabled" not in html.split("time-seek-pill")[2][:40]
```

- [ ] **Step 2: Jalanin, pastiin gagal**

Run: `uv run pytest tests/test_brief_server.py -q -p no:cacheprovider -k time_buttons`
Expected: FAIL (`seekSourceVideo` masih ada).

- [ ] **Step 3: Implementasi**

`server.py` di `do_GET` `/`: `voice = paths.voice_mp3.name if paths.voice_mp3.exists() else None`, teruskan `voice=voice`.

`page.py`:
- `render_page(..., source=None, voice=None)`. Tambah `<audio id="voice" src="/files/{voice}" preload="metadata"></audio>` di dalam `<body>` (sebelum `<main>`) kalau `voice`.
- `_shot_row(shot, group, entry, state, voice_ok: bool)`; tombol:

```python
    pill_attr = f'onclick="playBeat(this, {shot["start_s"]:.1f}, {shot["end_s"]:.1f})"' if voice_ok else 'disabled title="suara belum ada"'
    ...
          <button type="button" class="time-seek-pill" {pill_attr}>
```

(ganti `onclick="seekSourceVideo(...)"`; teruskan `voice_ok` dari `_card` → `render_page`.)
- JS: hapus `seekSourceVideo`, tambah:

```js
let beatStop = null;
function playBeat(btn, start, end) {
  const a = document.getElementById('voice');
  if (!a) return;
  const active = document.querySelector('.time-seek-pill.is-playing');
  if (active === btn) { a.pause(); btn.classList.remove('is-playing'); beatStop = null; return; }
  if (active) active.classList.remove('is-playing');
  a.currentTime = start; beatStop = end; btn.classList.add('is-playing');
  a.play().catch(() => {});
}
document.addEventListener('DOMContentLoaded', () => {
  const a = document.getElementById('voice');
  if (!a) return;
  a.addEventListener('timeupdate', () => {
    if (beatStop !== null && a.currentTime >= beatStop) { a.pause(); beatStop = null;
      document.querySelectorAll('.time-seek-pill.is-playing').forEach(b => b.classList.remove('is-playing')); }
  });
  a.addEventListener('ended', () => document.querySelectorAll('.time-seek-pill.is-playing').forEach(b => b.classList.remove('is-playing')));
});
```

- CSS: `.time-seek-pill.is-playing{background:var(--blue-main);color:#fff}` dan `.time-seek-pill:disabled{opacity:.45;cursor:not-allowed}`. Ikon di dalam tombol tetap segitiga; pas `is-playing` ganti ke kotak lewat CSS `::before` nggak perlu, cukup warna.
- Hapus blok `const sourceVideoEl = ...` kalau cuma dipakai seek.

- [ ] **Step 4: Jalanin, pastiin lolos**

Run: `uv run pytest tests/test_brief_server.py -q -p no:cacheprovider`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add mayzfact/brief/page.py mayzfact/brief/server.py tests/test_brief_server.py
git commit -m "feat(brief): shot time buttons play the narration audio"
```

---

### Task 2: Download duluan pas Simpan (worker + `prefetch.json`)

**Files:**
- Create: `mayzfact/brief/prefetch.py`, `tests/test_brief_prefetch.py`
- Modify: `mayzfact/brief/server.py`, `mayzfact/brief/page.py`, `mayzfact/cli.py`, `mayzfact/store.py` (`prefetch_json`)

**Interfaces:**
- Produces: `Prefetcher(paths, obtain: Callable[[dict, Path], list[Path]], log)` dengan `.enqueue(urls: list[str])`, `.start()`, `.stop(timeout_s=30.0)`, `.snapshot() -> dict[str, dict]`. State per URL di `runs/<id>/prefetch.json`: `{url: {"state": "antre"|"download"|"siap"|"gagal", "message": str, "files": [nama file]}}`. `make_server(..., prefetcher=None)`: kalau ada, `/api/links` sukses → `prefetcher.enqueue([url yang baru/berubah])`; `/api/progress` nambah key `"prefetch": snapshot`. `RunPaths.prefetch_json`.

- [ ] **Step 1: Tulis test yang gagal** (`tests/test_brief_prefetch.py`)

```python
import threading
import time
from pathlib import Path

import httpx
import pytest

from mayzfact.brief.prefetch import Prefetcher
from mayzfact.brief.server import make_server
from mayzfact.errors import PipelineError
from mayzfact.store import RunPaths, read_json, write_json_atomic
from tests.test_brief_server import PLAN


def wait_until(cond, timeout=5.0):
    end = time.time() + timeout
    while time.time() < end:
        if cond():
            return True
        time.sleep(0.02)
    return False


def test_prefetcher_downloads_each_url_once_and_records_state(tmp_path):
    paths = RunPaths(tmp_path / "run")
    paths.root.mkdir()
    calls = []

    def obtain(entry, run_root):
        calls.append(entry["url"])
        if "bad" in entry["url"]:
            raise PipelineError("fetch", "Link tiktok nggak bisa di-download")
        return [Path("cache/manual/abc_0.mp4")]

    pf = Prefetcher(paths, obtain, log=lambda m: None)
    pf.start()
    pf.enqueue(["https://a/ok", "https://a/bad", "https://a/ok"])
    assert wait_until(lambda: all(s["state"] in ("siap", "gagal") for s in pf.snapshot().values()) and len(pf.snapshot()) == 2)
    snap = pf.snapshot()
    assert snap["https://a/ok"] == {"state": "siap", "message": "", "files": ["abc_0.mp4"]}
    assert snap["https://a/bad"]["state"] == "gagal" and "nggak bisa" in snap["https://a/bad"]["message"]
    assert calls.count("https://a/ok") == 1
    assert read_json(paths.prefetch_json) == snap
    pf.enqueue(["https://a/bad"])  # simpan ulang link yang sama = coba lagi
    assert wait_until(lambda: calls.count("https://a/bad") == 2)
    pf.stop()


def test_prefetcher_stop_does_not_hang_on_pending_queue(tmp_path):
    paths = RunPaths(tmp_path / "run")
    paths.root.mkdir()
    started = threading.Event()

    def slow(entry, run_root):
        started.set()
        time.sleep(0.3)
        return []

    pf = Prefetcher(paths, slow, log=lambda m: None)
    pf.start()
    pf.enqueue([f"https://a/{i}" for i in range(20)])
    assert started.wait(2.0)
    t0 = time.time()
    pf.stop(timeout_s=1.0)
    assert time.time() - t0 < 2.0
    assert not pf.is_alive()


def test_saving_links_queues_downloads_and_progress_shows_them(tmp_path):
    paths = RunPaths(tmp_path / "abc")
    (paths.root / "plan").mkdir(parents=True)
    write_json_atomic(paths.shots_plan_json, PLAN)
    seen = []
    pf = Prefetcher(paths, lambda entry, root: seen.append(entry["url"]) or [Path("x_0.mp4")], log=lambda m: None)
    pf.start()
    srv = make_server(paths, 0, prefetcher=pf)
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{srv.server_address[1]}"
    try:
        ok = httpx.post(base + "/api/links", json={"shots": {"0": "https://vt.tiktok.com/ZS1/", "1": "https://vt.tiktok.com/ZS1/", "2": "file:manual/x.mp4"}})
        assert ok.status_code == 200
        assert wait_until(lambda: seen == ["https://vt.tiktok.com/ZS1/"])
        assert wait_until(lambda: httpx.get(base + "/api/progress").json().get("prefetch", {}).get("https://vt.tiktok.com/ZS1/", {}).get("state") == "siap")
        html = httpx.get(base + "/").text
        assert 'data-prefetch-url="https://vt.tiktok.com/ZS1/"' in html
    finally:
        srv.shutdown()
        srv.server_close()
        pf.stop()
```

Cek dulu format body `/api/links` per shot di `test_save_links_per_shot` (baris 74) dan samain (nilai string per shot, `file:` prefix buat upload). Kalau formatnya beda, ikutin yang ada.

- [ ] **Step 2: Jalanin, pastiin gagal**

Run: `uv run pytest tests/test_brief_prefetch.py -q -p no:cacheprovider`
Expected: FAIL (`mayzfact.brief.prefetch` nggak ada).

- [ ] **Step 3: Implementasi**

`store.py`: `@property def prefetch_json(self) -> Path: return self.root / "prefetch.json"`.

`mayzfact/brief/prefetch.py`:

```python
"""Download link klip di background begitu disimpan di brief, biar fetch tinggal motong (spec brief revisi §2)."""

from __future__ import annotations

import queue
import threading
from pathlib import Path
from typing import Callable

from mayzfact.errors import PipelineError
from mayzfact.store import RunPaths, read_json, write_json_atomic


class Prefetcher:
    def __init__(self, paths: RunPaths, obtain: Callable[[dict, Path], list[Path]], log: Callable[[str], None] = print) -> None:
        self._paths, self._obtain, self._log = paths, obtain, log
        self._queue: queue.Queue[str | None] = queue.Queue()
        self._lock = threading.Lock()
        self._state: dict[str, dict] = read_json(paths.prefetch_json) if paths.prefetch_json.exists() else {}
        self._thread = threading.Thread(target=self._run, name="brief-prefetch", daemon=True)

    def start(self) -> None:
        self._thread.start()

    def is_alive(self) -> bool:
        return self._thread.is_alive()

    def enqueue(self, urls: list[str]) -> None:
        with self._lock:
            for url in dict.fromkeys(urls):
                if self._state.get(url, {}).get("state") in ("antre", "download"):
                    continue  # lagi jalan, jangan dobel
                self._state[url] = {"state": "antre", "message": "", "files": []}
                self._queue.put(url)
            self._save()

    def snapshot(self) -> dict[str, dict]:
        with self._lock:
            return {k: dict(v) for k, v in self._state.items()}

    def stop(self, timeout_s: float = 30.0) -> None:
        """Berhenti rapi: antrean sisa dibuang, download yang lagi jalan ditunggu maksimal timeout_s."""
        while True:
            try:
                self._queue.get_nowait()
            except queue.Empty:
                break
        self._queue.put(None)
        self._thread.join(timeout_s)
        with self._lock:
            for url, st in self._state.items():
                if st["state"] in ("antre", "download"):
                    st.update(state="gagal", message="server brief ditutup sebelum selesai")
            self._save()

    def _set(self, url: str, **fields) -> None:
        with self._lock:
            self._state.setdefault(url, {"state": "antre", "message": "", "files": []}).update(fields)
            self._save()

    def _save(self) -> None:
        write_json_atomic(self._paths.prefetch_json, self._state)

    def _run(self) -> None:
        while True:
            url = self._queue.get()
            if url is None:
                return
            self._set(url, state="download", message="")
            try:
                files = self._obtain({"url": url}, self._paths.root)
                self._set(url, state="siap", message="", files=[f.name for f in files])
                self._log(f"[brief] siap: {url}")
            except PipelineError as exc:
                self._set(url, state="gagal", message=exc.message.splitlines()[0][:160])
                self._log(f"[brief] gagal: {url}: {exc.message.splitlines()[0][:120]}")
            except Exception as exc:  # resolver pihak ketiga bisa ngelempar apa aja; worker jangan mati
                self._set(url, state="gagal", message=f"{type(exc).__name__}: {str(exc)[:120]}")
```

(Daemon thread: `stop()` dengan timeout nggak nunggu download yang nyangkut; `.part` yang ketinggalan udah ditangani `download()`/yt-dlp di run berikutnya.)

`server.py`:
- `make_server(..., prefetcher=None)`.
- `/api/links` setelah `save_links`: `urls = [e["url"] for e in data.get("shots", {}).values() if isinstance(e, dict) and e.get("url")]` (kalau format `groups`: semua `url` di tiap list); `if prefetcher: prefetcher.enqueue(urls)`.
- `/api/progress`: `payload = read_json(progress) if progress.exists() else {}`; `if prefetcher: payload["prefetch"] = prefetcher.snapshot()`.
- `/`: `render_page(..., prefetch=prefetcher.snapshot() if prefetcher else {})`.

`page.py`:
- `render_page(..., prefetch: dict | None = None)`, `_shot_row(..., prefetch_state: dict | None)`. Di shot-box, setelah badge state: `<span class="prefetch" data-prefetch-url="{escape(url, quote=True)}">{label}</span>` kalau entry-nya URL (label: `antre` / `download…` / `siap` / `gagal: pesan`; class `pf-siap`/`pf-gagal`).
- JS `pollProgress`: `if (p.prefetch) for (const [url, st] of Object.entries(p.prefetch)) document.querySelectorAll(`[data-prefetch-url="${CSS.escape(url)}"]`).forEach(el => { el.textContent = label(st); el.className = 'prefetch pf-' + st.state; })`. Hapus syarat `if (p.state)` buat bagian prefetch (progress fetch boleh kosong).
- CSS: `.prefetch{font-size:11px;padding:2px 8px;border-radius:99px;background:var(--border-subtle)} .pf-siap{background:#dcfce7;color:#166534} .pf-gagal{background:#fee2e2;color:#991b1b} .pf-download{background:#dbeafe;color:#1e40af}`.

`cli.py` `_brief`: bikin `Obtainer` (sama kayak `real_deps.fetch`: `httpx.Client(headers={"User-Agent": DESKTOP_UA}, timeout=httpx.Timeout(120.0, connect=15.0), follow_redirects=True)`, `Obtainer(CACHE_DIR / "manual", client, log=print)`), `pf = Prefetcher(paths, obtainer.obtain)`, `pf.start()`, `make_server(..., prefetcher=pf)`; di `finally`: `pf.stop()`, `client.close()`. Pas start, enqueue URL yang udah ada di `links.json` tapi belum `siap` (biar link yang disimpan sebelum fitur ini ada ikut ke-download).

- [ ] **Step 4: Jalanin, pastiin lolos**

Run: `uv run pytest tests/test_brief_prefetch.py tests/test_brief_server.py tests/test_cli.py -q -p no:cacheprovider`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add mayzfact/brief/prefetch.py mayzfact/brief/server.py mayzfact/brief/page.py mayzfact/cli.py mayzfact/store.py tests/test_brief_prefetch.py
git commit -m "feat(brief): download links in the background as soon as they are saved"
```

---

### Task 3: Frame referensi per shot (hook / subjek / proporsional)

**Files:**
- Modify: `mayzfact/steps/plan.py`, `tests/test_plan.py`

**Interfaces:**
- Produces: tiap `shot["ref_frames"]` berisi 3 path (`plan/seg_XX_K.jpg` buat hook, `plan/shot_NN_K.jpg` buat lainnya). `group["ref_frames"]` dihapus. `_shot_frames(paths, source, shots, tts_duration_s, download_source)`.

- [ ] **Step 1: Tulis test yang gagal** (`tests/test_plan.py`)

Ganti `test_plan_gives_source_frames_to_content_groups` jadi:

```python
def test_every_shot_gets_three_reference_frames(tmp_path, cut_video):
    source = {**SOURCE, "transcript": [{"text": "intro words", "start": 0.0, "duration": 0.8},
                                       {"text": "Number five, horseshoe crab.", "start": 0.8, "duration": 1.0}]}
    paths, data = plan_with(tmp_path, cut_video, hook_seconds=1.5, source=source)
    for shot in data["shots"]:
        assert len(shot["ref_frames"]) == 3 and all((paths.root / f).exists() for f in shot["ref_frames"])
    assert data["shots"][0]["ref_frames"][0].startswith("plan/seg_")  # hook: dari segmen
    assert data["shots"][1]["ref_frames"] == ["plan/shot_02_0.jpg", "plan/shot_02_1.jpg", "plan/shot_02_2.jpg"]
    assert "ref_frames" not in data["groups"][0]


def test_shot_without_subject_match_gets_proportional_frames(tmp_path, cut_video):
    script = {"beats": [{"text": "Smash like and subscribe!", "media": "video", "queries": ["phone"], "subject": ""},
                        {"text": "Number five, horseshoe crab.", "media": "photo", "queries": ["crab"]}], "fallback_query": "x"}
    source = {**SOURCE, "transcript": [{"text": "unrelated opening", "start": 0.0, "duration": 2.0}]}  # subjek nggak ketemu
    paths, data = plan_with(tmp_path, cut_video, hook_seconds=0.0, source=source, script=script)
    for shot in data["shots"]:
        assert len(shot["ref_frames"]) == 3 and all((paths.root / f).exists() for f in shot["ref_frames"])
```

(`plan_with` udah nerima `script=`; `cut_video` durasinya ≥ 2 s, `SOURCE["duration_s"]` = 2.0. Kalau `cut_video` lebih pendek dari posisi yang dihitung, implementasi harus clamp ke `total - 0.05`.)

Hapus assertion `data["groups"][0]["ref_frames"] == []` di `test_plan_groups_shots_by_context` dan key `"ref_frames": []` di dict ekspektasi groups-nya.

- [ ] **Step 2: Jalanin, pastiin gagal**

Run: `uv run pytest tests/test_plan.py -q -p no:cacheprovider`
Expected: FAIL (shot non-hook `ref_frames` kosong).

- [ ] **Step 3: Implementasi** (`mayzfact/steps/plan.py`)

Ganti `_source_frames` jadi:

```python
def _shot_frames(paths: RunPaths, source: dict, shots: list[dict], voice_total_s: float,
                 download_source: Callable[[str, Path], Path]) -> None:
    """3 frame source per shot buat referensi nyari klip: rentang subjeknya di transcript, atau posisi proporsional."""
    todo = [s for s in shots if not s["ref_frames"]]
    if not todo:
        return
    src = paths.source_mp4
    paths.plan_dir.mkdir(parents=True, exist_ok=True)
    if not src.exists():
        download_source(source["video_id"], src)
    total = probe(src, "plan")["duration_s"] or source.get("duration_s") or 0.0
    # urut card countdown: beat pembuka bisa nyebut subjek nomor 1 duluan, padahal di source dibahas paling akhir
    order = sorted({s["subject"] for s in shots if s.get("subject")},
                   key=lambda name: next((s["index"] for s in shots if s.get("subject") == name and s.get("countdown")),
                                         next(s["index"] for s in shots if s.get("subject") == name)))
    ranges = subject_ranges(source["transcript"], order, total)
    for shot in todo:
        span = ranges.get(shot.get("subject") or "")
        if span is None:  # CTA/intro/subjek nggak ketemu: posisi beat di naskah dipetain ke durasi source
            scale = total / voice_total_s if voice_total_s else 0.0
            span = (shot["start_s"] * scale, shot["end_s"] * scale)
        start, end = span
        shot["ref_frames"] = [
            extract_frame(src, max(0.0, min(start + (end - start) * pos, total - 0.05)),
                          paths.plan_dir / f"shot_{shot['index'] + 1:02d}_{k}.jpg").relative_to(paths.root).as_posix()
            for k, pos in enumerate(SOURCE_FRAMES)
        ]
```

Di `run_plan`: ganti `_source_frames(paths, source, groups, shots, download_source)` jadi `_shot_frames(paths, source, shots, tts["duration_s"], download_source)` **sebelum** `groups = _groups(shots)`; di `_groups` hapus `group["ref_frames"] = []`. Kalau `extract_frame` gagal buat 1 shot (`PipelineError`), log dan biarin `ref_frames` kosong (brief yang nolak nanti).

- [ ] **Step 4: Jalanin, pastiin lolos**

Run: `uv run pytest tests/test_plan.py tests/test_brief_server.py -q -p no:cacheprovider`
Expected: PASS (`test_brief_server` masih pakai `group.ref_frames` di fixture PLAN; halaman tetap boleh nampilin kalau ada, jadi nggak rusak. Kalau test halaman nge-assert `/files/plan/fossil_0.jpg`, biarin: strip kelompok tetap dirender kalau key-nya ada).

- [ ] **Step 5: Commit**

```bash
git add mayzfact/steps/plan.py tests/test_plan.py
git commit -m "feat(plan): reference frames for every shot"
```

---

### Task 4: `brief` nolak jalan kalau ada shot tanpa frame + halaman per shot

**Files:**
- Modify: `mayzfact/cli.py`, `mayzfact/brief/page.py`, `tests/test_cli.py`, `tests/test_brief_server.py`

**Interfaces:**
- Produces: `missing_frames(paths, plan) -> list[int]` di `mayzfact/brief/server.py` (index shot yang `ref_frames` kosong atau file-nya nggak ada). `_brief` raise `PipelineError("brief", "Shot X, Y belum punya frame referensi. Jalanin: mayzfact run <id> --from plan")`.

- [ ] **Step 1: Tulis test yang gagal**

`tests/test_cli.py`:

```python
def test_brief_refuses_shots_without_reference_frames(monkeypatch, tmp_path, capsys):
    from mayzfact.store import write_json_atomic
    from tests.test_brief_server import PLAN

    paths = RunPaths(tmp_path / "i2xag_1OJfM")
    (paths.root / "plan").mkdir(parents=True)
    (paths.root / "plan" / "seg_01_0.jpg").write_bytes(b"jpg")
    write_json_atomic(paths.shots_plan_json, PLAN)  # shot 2 dan 3 ref_frames kosong
    monkeypatch.setattr(cli, "load_settings", lambda: Settings())
    monkeypatch.setattr(cli, "RUNS_DIR", tmp_path)
    assert cli.main(["brief", "i2xag_1OJfM"]) == 1
    err = capsys.readouterr().err
    assert "Shot 2, 3" in err and "--from plan" in err
```

`tests/test_brief_server.py`: di `test_page_lists_groups_and_escapes_text`, hapus assertion `"/files/plan/fossil_0.jpg" in html` (strip kelompok dihapus) dan tambah: `assert html.count('class="refs"') >= 1`.

- [ ] **Step 2: Jalanin, pastiin gagal**

Run: `uv run pytest tests/test_cli.py tests/test_brief_server.py -q -p no:cacheprovider -k "refuses or lists_groups"`
Expected: FAIL (brief jalan / strip kelompok masih ada).

- [ ] **Step 3: Implementasi**

`server.py`:

```python
def missing_frames(paths: RunPaths, plan: dict) -> list[int]:
    """Shot yang belum punya 3 frame referensi (atau file-nya hilang)."""
    return [s["index"] for s in plan.get("shots", [])
            if not s.get("ref_frames") or not all((paths.root / f).exists() for f in s["ref_frames"])]
```

`cli.py` `_brief`, setelah cek plan ada:

```python
    missing = missing_frames(paths, read_json(paths.shots_plan_json))
    if missing:
        raise PipelineError("brief", f"Shot {', '.join(str(i + 1) for i in missing)} belum punya frame referensi. "
                            f"Jalanin: mayzfact run {paths.root.name} --from plan")
```

(Test `test_brief_opens_lan_by_default` nulis `shots_plan.json` isinya `{}`: `missing_frames` dengan `shots` kosong = `[]`, jadi tetap lolos.)

`page.py` `_card`: hapus blok `refs-strip-wrap` kelompok dan variabel `refs` di `_card`. Frame per shot udah dirender di `_shot_row` (`shot.get("ref_frames")`).

- [ ] **Step 4: Jalanin, pastiin lolos + full suite**

Run: `uv run pytest -q -p no:cacheprovider`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add mayzfact/cli.py mayzfact/brief/server.py mayzfact/brief/page.py tests/test_cli.py tests/test_brief_server.py
git commit -m "feat(brief): refuse to start until every shot has reference frames"
```

---

### Task 5: Docs + regen frame 4735

**Files:**
- Modify: `.agents/skills/bikin-short/SKILL.md`, `AGENTS.md`, `docs/HANDOFF.md`, `docs/DECISIONS.md`

- [ ] **Step 1: Skill** — langkah 5 (brief): tambah "Tombol waktu di tiap shot muter suara naskah beat itu. Link yang disimpan langsung di-download di background; status per shot kelihatan (`antre`/`download…`/`siap`/`gagal`). Kalau ada yang `gagal`, Akmal ganti link-nya sebelum bilang udah." Langkah 6 (fetch): "Link yang udah `siap` nggak di-download lagi." Tambah: "Kalau `brief` nolak karena frame referensi, jalanin `uv run mayzfact run <id> --from plan`."
- [ ] **Step 2: AGENTS.md** — file penting: `prefetch.json` (status download link dari brief). Perintah brief: catatan "download link jalan di background selama server hidup".
- [ ] **Step 3: DECISIONS** — D-029 "Brief: audio naskah, download duluan, frame per shot wajib" (3 poin spec + "gagal nggak diulang otomatis"). **HANDOFF** — section baru + hapus item 2 di "Masalah terbuka" handoff D-028.
- [ ] **Step 4: Regen frame 4735** (run yang lagi diisi Akmal, `links.json` jangan disentuh): `uv run mayzfact run 4735ZE89GXQ --from plan --no-render` bakal nulis ulang `shots_plan.json` dengan frame per shot, terus berhenti exit 3 nunggu link. Cek `links.json` tetap ada dan brief (restart) nampilin link yang udah diisi. Kalau brief 4735 lagi jalan di port 3100, matiin dulu, lalu start lagi.
- [ ] **Step 5: Full suite + commit**

Run: `uv run pytest -q -p no:cacheprovider`

```bash
git add .agents/skills/bikin-short/SKILL.md AGENTS.md docs/HANDOFF.md docs/DECISIONS.md
git commit -m "docs: brief plays narration, prefetches links, requires shot frames"
```
