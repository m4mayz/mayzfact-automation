# Brief v2 (fase-brief-v2) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Brief lebih cepat diisi dari HP: speed per shot (T1), preview langsung aktif tanpa refresh (T2), shot urut 1..N (T3), dan satu kartu frame referensi dari shot asli source buat FaktaCuil (T5).

**Architecture:** Speed disimpan di entry shot `links.json`, divalidasi lewat `attach_speed` (pola sama kayak `attach_sfx`), terus dipakai fetch waktu motong: window source = `durasi_shot × speed`, `normalize_video` nge-`setpts` ke durasi shot, jadi Remotion/textblur/overlay nggak berubah. Brief nge-render semua shot dalam 1 kartu urut index; preview-box selalu ada dan tombolnya diaktifin JS dari polling `/api/progress`. Plan FaktaCuil bikin `source_shots` (cut detection seluruh `source.mp4`, 2 frame acak per shot, seed `video_id`) gantiin `ref_frames` per shot; top3 nggak disentuh.

**Tech Stack:** Python 3.12 + pytest (`uv run`), ffmpeg/ffprobe, HTML + vanilla JS yang di-generate `mayzfact/brief/page.py`. Nggak ada dependency baru.

**Spec:** `docs/superpowers/specs/2026-11-21-faktacuil-brief-cta-v2-design.md`, bagian "Branch 1: `fase-brief-v2`" (T1, T2, T3, T5) + "Kompatibilitas run lama".

## Global Constraints

- Kerja di branch `fase-brief-v2`. Jangan sentuh file milik branch paralel `fase-cta-v2`: `mayzfact/models.py`, `mayzfact/faktacuil.py`, `mayzfact/steps/script.py`, `mayzfact/cta_scene.py`, `mayzfact/narration.py`, `remotion/`. Di `page.py`, loop keyword `en`/`zh` di `_shot_row` itu wilayah T4 (sibling); jangan diubah, biar konflik merge-nya kecil.
- Pilihan speed persis `0.5, 0.75, 1, 1.25, 1.5, 2`, default `1`. Disimpan sebagai `speed` (float) di entry shot `links.json`. Entry tanpa `speed` = 1; speed 1 nggak ditulis.
- Fetch: durasi source = `durasi_shot × speed` dari `start_s`. `end_s` tetap nggak dibaca fetch (dan nggak dipakai preview). Foto: speed diabaikan. Hook top3 lewat `_continuous`: speed diabaikan.
- Frame referensi cuma buat `narration_mode == "faktacuil"`. Top3 tetap pakai `ref_frames` per shot, `_shot_frames`, dan `missing_frames` kayak sekarang; test top3 yang ada nggak boleh diubah kecuali yang disebut di task (cuma `test_page_shows_sfx_pills_and_preview`, karena T2 sengaja ngubah perilaku itu).
- `source.mp4` nggak ada / cut detection gagal = kartu nampilin pesan, plan nggak gagal (langkah hiasan: try/except + log).
- `plan["groups"]` tetap ditulis dan perilaku fetch per grup nggak berubah.
- Nggak ada endpoint baru. Speed lewat `POST /api/links` yang udah kena host check + Origin check.
- `links.json` lama (tanpa `speed`) dan `plan.json` lama (tanpa `narration_mode`/`source_shots`) tetap kebaca; plan tanpa `narration_mode` diperlakukan kayak sekarang.
- TDD: test merah dulu tiap task. Komentar kode bahasa Indonesia santai, 1 baris, istilah teknis English.
- Commit per task: Conventional Commits, bahasa Inggris, 1 baris, tanpa body, tanpa `Co-Authored-By` atau atribusi AI apa pun.
- Cek tiap task: test file task-nya, `uvx ruff check --select F,I <file yang diubah>`. Catat baseline `uv run pytest -q` di awal (±3 menit, jalanin di background) dan bandingin di Task 7.

## Review Focus

- Speed bikin window source lebih panjang dari video (misal shot 1 detik × 2 di video 2 detik) → shot itu error dengan pesan jelas di status, shot lain tetap jalan. Test: Task 2 `test_speed_window_longer_than_video_marks_shot_error`.
- Tab brief lama (dibuka sebelum update) nge-POST tanpa key `speed` → speed yang udah kesimpen nggak boleh ilang. Test: Task 1 `test_save_without_speed_key_keeps_saved_speed`.
- Link yang sama dipakai lagi nggak berurutan setelah shot ber-speed → `_first_free` harus ngelewatin window source yang beneran kepakai (`durasi × speed`), bukan durasi shot. Test: Task 2 `test_first_free_skips_sped_up_window`.
- Source panjang dengan cut ratusan → kartu dibatasi 60 shot source yang nyebar sampai akhir video, bukan 60 pertama. Test: Task 5 `test_spread_covers_whole_source`.
- Ganti link di shot yang preview-nya lagi kebuka, atau atur SFX dari preview pas speed ≠ 1 → preview nutup, dan detik SFX dihitung dalam detik shot (dibagi speed), bukan detik source. JS, dicek manual: Task 4 Step 6.

---

### Task 1: Speed di links.json + API brief

**Files:**
- Modify: `mayzfact/manual/links.py` (`normalize_links`, `same_clip`, `preview_starts`, tambah `SPEEDS`, `attach_speed`)
- Modify: `mayzfact/brief/server.py` (`/api/links` sekitar baris 250-257, `/api/upload` sekitar baris 303-310)
- Test: `tests/test_manual_links.py`, `tests/test_brief_sfx.py`

**Interfaces:**
- Produces: `SPEEDS: tuple[float, ...] = (0.5, 0.75, 1.0, 1.25, 1.5, 2.0)` di `mayzfact/manual/links.py`.
- Produces: `attach_speed(data: dict, raw_speed: dict | None) -> None` — `{idx: speed}` dari brief → `entry["speed"]`; speed 1 / shot tanpa link = nggak ditulis; nilai di luar `SPEEDS` → `ValueError("shot {n}: speed {x} nggak ada di pilihan")`.
- Produces: body `POST /api/links` boleh punya `speed: {idx: float}`. Tanpa key `speed` → speed lama dibawa (sama kayak `sfx`).

- [ ] **Step 1: Write the failing tests**

`tests/test_manual_links.py`:
```python
def test_attach_speed_validates_and_skips_default():
    from mayzfact.manual.links import attach_speed
    data = normalize_links({"shots": {"0": "https://a.b/v", "1": "https://a.b/w"}}, shot_count=5)
    attach_speed(data, {"0": 1.5, "1": 1, "3": 2})
    assert data["shots"]["0"]["speed"] == 1.5
    assert "speed" not in data["shots"]["1"] and "3" not in data["shots"]
    with pytest.raises(ValueError, match="shot 1: speed 3"):
        attach_speed(data, {"0": 3})

def test_normalize_links_drops_unchecked_speed_from_raw_entries():
    res = normalize_links({"shots": {"0": {"url": "https://a.b/v", "speed": 9}}}, shot_count=5)
    assert res == {"shots": {"0": {"url": "https://a.b/v"}}}

def test_same_clip_ignores_speed():
    from mayzfact.manual.links import same_clip
    assert same_clip({"url": "u", "speed": 2.0}, {"url": "u"})

def test_preview_starts_use_source_duration():
    from mayzfact.manual.links import preview_starts
    links = {"shots": {"1": {"url": "https://a.b/v", "start_s": 4.0, "speed": 2.0},  # shot 1,5 detik → 3 detik source
                       "2": {"url": "https://a.b/v"}}}
    assert preview_starts(SFX_PLAN, links) == {1: 4.0, 2: 7.0}
```

`tests/test_brief_sfx.py` (fixture `brief`):
```python
def test_saving_speed(brief):
    paths, base, _ = brief
    ok = httpx.post(base + "/api/links", json={"shots": {"0": "https://a.b/v", "1": "https://a.b/w"},
                                               "speed": {"0": 1.25, "1": 1}})
    assert ok.status_code == 200
    shots = read_json(paths.links_json)["shots"]
    assert shots["0"]["speed"] == 1.25 and "speed" not in shots["1"]
    bad = httpx.post(base + "/api/links", json={"shots": {"0": "https://a.b/v"}, "speed": {"0": 3}})
    assert bad.status_code == 400 and "speed" in bad.json()["error"]

def test_save_without_speed_key_keeps_saved_speed(brief):
    paths, base, _ = brief
    httpx.post(base + "/api/links", json={"shots": {"0": "https://a.b/v"}, "speed": {"0": 2}})
    httpx.post(base + "/api/links", json={"shots": {"0": "https://a.b/v"}})
    assert read_json(paths.links_json)["shots"]["0"]["speed"] == 2

def test_upload_keeps_speed(brief):
    paths, base, _ = brief
    httpx.post(base + "/api/links", json={"shots": {"1": "https://a.b/v"}, "speed": {"1": 0.5}})
    httpx.post(base + "/api/upload?shot=1", content=b"mp4", headers={"X-Filename": "a.mp4"})
    assert read_json(paths.links_json)["shots"]["1"] == {"file": "manual/shot_2.mp4", "speed": 0.5}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_manual_links.py tests/test_brief_sfx.py -q -k "speed"`
Expected: FAIL (`ImportError: attach_speed`, speed key nggak kesimpen).

- [ ] **Step 3: Implement**

- `links.py`: tambah `SPEEDS` + `attach_speed` (validasi pakai `float(value) in SPEEDS`, simpan `float`). `normalize_links` cabang dict: buang `"sfx"` dan `"speed"`. `same_clip.strip`: tambah `"speed"`. `preview_starts`: `duration = (end_s - start_s) * float(entry.get("speed") or 1)`.
- `server.py` `/api/links`: setelah `attach_sfx`, `attach_speed(data, body.get("speed"))` kalau `"speed" in body`. Cabang "request tanpa key" dibikin per key: buat `sfx` dan `speed` masing-masing, kalau key itu nggak ada di body, bawa nilai lama dari `links.json`. `/api/upload?shot=`: `speed` lama ikut dibawa kayak `start_s`/`end_s`/`sfx`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_manual_links.py tests/test_brief_sfx.py tests/test_brief_server.py -q`
Expected: PASS semua (test lama ikut lolos).

- [ ] **Step 5: Commit**

```bash
git add mayzfact/manual/links.py mayzfact/brief/server.py tests/test_manual_links.py tests/test_brief_sfx.py
git commit -m "feat(brief): store per-shot clip speed in links.json"
```

---

### Task 2: Speed di fetch

**Files:**
- Modify: `mayzfact/ffmpeg.py:44-58` (`normalize_video`)
- Modify: `mayzfact/steps/fetch.py:51-73` (`normalize_local`), per-shot loop `fetch.py:357-424`
- Test: `tests/test_normalize.py`, `tests/test_fetch.py`

**Interfaces:**
- Consumes: entry `links.json` dengan `speed` opsional (Task 1).
- Produces: `normalize_video(src: Path, dest: Path, *, start_s: float, duration_s: float, scale: float, speed: float = 1.0) -> None` — `duration_s` = detik source yang dibaca; output = `duration_s / speed` detik.
- Produces: `normalize_local(index, start_s, end_s, raw, kind, offset_s, paths, fg_min_ratio, speed: float = 1.0) -> dict` — `offset_s` itu tengah window di detik source; window source = `(end_s - start_s) * speed + TAIL_S`.
- Produces: tiap clip dari per-shot loop di `clips.json` punya `"speed": float` (foto selalu `1.0`). Clip dari `_continuous`, `_run_group` (links legacy per grup), dan `reuse_backgrounds` nggak punya `speed` (= 1).

- [ ] **Step 1: Write the failing tests**

`tests/test_normalize.py`:
```python
def test_normalize_video_speed_compresses_output(tmp_path, make_video):
    dest = tmp_path / "shot_01.mp4"
    normalize_video(make_video(1080, 1920, 3.0), dest, start_s=0.5, duration_s=2.0, scale=1.0, speed=2.0)
    assert abs(probe(dest, "clips")["duration_s"] - 1.0) < 0.1
```

`tests/test_fetch.py` (pakai `make_plan`, `FakeEncoder`, `QUIET`, `photos`, `cut_video` 2 detik):
```python
def test_normalize_local_speed_reads_longer_source(tmp_path, make_video):
    from mayzfact.errors import PipelineError
    from mayzfact.steps.fetch import normalize_local
    paths = RunPaths(tmp_path / "run")
    out = normalize_local(0, 0.0, 1.0, make_video(1080, 1920, 5.0), "video", 2.5, paths, 0.5, speed=2.0)
    assert abs(probe(paths.root / out["file"], "clips")["duration_s"] - 1.1) < 0.1  # (2.0 + 0.2) / 2
    with pytest.raises(PipelineError, match="cuma"):
        normalize_local(0, 0.0, 2.5, make_video(1080, 1920, 5.0), "video", 2.5, paths, 0.5, speed=2.0)

def test_speed_uses_source_duration_for_start_and_continuation(tmp_path, cut_video):
    # shots 2 (0.0-0.4) + 3 (0.4-0.8), media video, grup "content" kayak test_consecutive_shots_*
    # links: "2": {"url": U, "start_s": 0.2, "speed": 2.0}, "3": {"url": U}
    s2, s3 = data["shots"]
    assert s2["speed"] == 2.0 and abs(s2["source_s"] - 0.2) < 1e-3
    assert abs(s3["source_s"] - 1.0) < 1e-3 and s3["speed"] == 1.0  # lanjut dari 0.2 + 0.4×2
    assert abs(probe(paths.root / s2["file"], "clips")["duration_s"] - 0.5) < 0.1  # (0.8 + 0.2) / 2

def test_speed_start_clamped_by_source_window(tmp_path, cut_video):
    # "2": {"url": U, "start_s": 1.5, "speed": 2.0}, shot 0.4 detik → clamp ke 2.0 - 0.8 - 0.2
    assert abs(data["shots"][0]["source_s"] - 1.0) < 1e-3

def test_first_free_skips_sped_up_window(tmp_path, cut_video):
    # grup [1, 2, 3]: shot 1 (0.0-0.4) link A speed 2, shot 2 (0.4-0.8) link B foto, shot 3 (0.8-1.2) link A tanpa speed
    assert abs(by_index[3]["source_s"] - 1.0) < 1e-3  # window shot 1 = 0..0.8 + ekor 0.2

def test_photo_ignores_speed(tmp_path):
    # shot foto, links {"2": {"url": P, "speed": 2.0}} ke photos(tmp_path, "x")
    assert clip["kind"] == "photo" and clip["speed"] == 1.0

def test_speed_window_longer_than_video_marks_shot_error(tmp_path, cut_video):
    # shot 2 (0.0-1.0) link video speed 2.0 → butuh 2.2 detik source dari video 2 detik
    with pytest.raises(AwaitingInput):
        run_fetch(...)
    assert read_json(paths.links_status_json)["shots"]["2"]["state"] == "error"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_normalize.py tests/test_fetch.py -q -k "speed or sped"`
Expected: FAIL (`unexpected keyword argument 'speed'`).

- [ ] **Step 3: Implement**

- `normalize_video`: kalau `speed != 1`, tambah `setpts=(PTS-STARTPTS)/{speed}` di depan `vf`; `-t` (output) jadi `duration_s / speed`. Speed 1 = command persis sama kayak sekarang.
- `normalize_local`: `src_s = (end_s - start_s) * speed` buat video; cek panjang `total < src_s + TAIL_S`, clamp `start` pakai `src_s`, panggil `normalize_video(..., duration_s=src_s + TAIL_S, speed=speed)`. Pesan error "cuma" nyebut detik source. Foto: speed nggak dipakai.
- Per-shot loop `run_fetch`: setelah `sources` ada, `speed = float(entry.get("speed") or 1) if sources and sources[0].kind == "video" else 1.0`; `duration = (s["end_s"] - s["start_s"]) * speed`. Sisanya (manual `start_s`, lanjutan, `_first_free`, `_best`, `source.used`, `prev_end_time`, offset `start + duration / 2`) udah pakai `duration` dan otomatis ikut. Oper `speed=speed` ke `normalize_local`, tulis `"speed": speed` ke dict clip.
- `_continuous` dan `_run_group` nggak diubah.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_normalize.py tests/test_fetch.py tests/test_faktacuil_pipeline.py tests/test_pipeline.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add mayzfact/ffmpeg.py mayzfact/steps/fetch.py tests/test_normalize.py tests/test_fetch.py
git commit -m "feat(fetch): apply per-shot speed when cutting clips"
```

---

### Task 3: Shot urut index di brief (T3)

**Files:**
- Modify: `mayzfact/brief/page.py` (`_card` → `_shots_card`, `_shot_row` badge grup, `render_page` sekitar baris 2255-2258)
- Test: `tests/test_brief_server.py`

**Interfaces:**
- Produces: `_shots_card(plan: dict, links: dict, status: dict, voice_ok: bool, prefetch: dict | None, sfx_names: list[str] | None, previews: dict | None) -> str` — 1 `<section class="card-group card" data-group="all">` berisi semua shot urut `index`. `_card` dihapus.
- Produces: tiap shot non-AUTO-CTA punya `<span class="z-badge group">{label grup}</span>` di `shot-meta-left`.

- [ ] **Step 1: Write the failing test**

```python
def test_shots_render_in_index_order_with_group_label():
    from mayzfact.brief.page import render_page
    plan = {**PLAN, "groups": [{"id": "kucing", "label": "kucing", "shots": [0, 2], "keywords": {"en": [], "zh": []}},
                               {"id": "kardus", "label": "kardus", "shots": [1], "keywords": {"en": [], "zh": []}}]}
    html = render_page("abc", plan, {"shots": {}}, {})
    assert html.index('data-shot-box="0"') < html.index('data-shot-box="1"') < html.index('data-shot-box="2"')
    assert html.count('class="z-badge group"') == 3 and ">kardus</span>" in html
    assert "0/2 kelompok" in html  # metric per grup di header tetap ada
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_brief_server.py::test_shots_render_in_index_order_with_group_label -q`
Expected: FAIL (shot 2 dirender sebelum shot 1).

- [ ] **Step 3: Implement `_shots_card`**

Loop `sorted(plan["shots"], key=index)`. Grup tiap shot = `next(g for g in plan["groups"] if shot["index"] in g["shots"])`. Lookup `entry` (per shot, atau posisi di links legacy `groups`) dan `st` (status per shot, fallback status grup) dipindah apa adanya dari `_card`. Header kartu cuma judul "Shot" + jumlah shot. Metric bar per grup di sidebar dan `filled_groups` di header nggak diubah.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_brief_server.py tests/test_brief_sfx.py tests/test_brief_prefetch.py tests/test_cta_scene.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add mayzfact/brief/page.py tests/test_brief_server.py
git commit -m "fix(brief): render shots in index order"
```

---

### Task 4: Preview tanpa refresh + pilihan speed di brief (T2 + UI T1)

**Files:**
- Modify: `mayzfact/brief/page.py` (`_clip_tools`, `_shot_row`, `_JS`: `windowStart`, `togglePreview`, `sfxFromPreview`, `setPrefetchUrls`, `renderPrefetch`, `scheduleAutoSave`, `save`, `uploadShot`, listener `input`; CSS kecil buat `select`)
- Test: `tests/test_brief_sfx.py`

**Interfaces:**
- Consumes: `SPEEDS`, `IMAGE_EXTS`, body `speed` di `/api/links` (Task 1); urutan kartu (Task 3).
- Produces: `_clip_tools(s_idx: int, dur: float, entry: dict | str | None, sfx_names: list[str], start: float | None, ready: bool) -> str`. `ready` = entry punya `file`, atau `url` dengan state prefetch `siap`. `preview-box` selalu ada; `data-preview-btn` dapat `disabled` kalau `not ready`.
- Produces markup: `<select data-speed="{idx}"{" disabled" kalau entry `file` ber-ekstensi IMAGE_EXTS}>` berisi `<option value="{s:g}"{" selected"}>{s:g}x</option>` per `s` di `SPEEDS`; yang `selected` = `entry["speed"]` (default 1).
- Produces JS: `speedOf(idx)`, `srcDur(idx)`, `collectSpeed()`, `syncPreviewButtons()`.

- [ ] **Step 1: Write the failing tests**

```python
import re

def preview_disabled(html, idx):
    return bool(re.search(rf'data-preview-btn="{idx}"[^>]*\bdisabled\b', html))

def test_preview_box_always_rendered_and_enabled_when_ready(brief):
    paths, base, pf = brief
    (paths.root / "manual").mkdir()
    (paths.root / "manual" / "shot_3.jpg").write_bytes(b"jpg")
    write_json_atomic(paths.links_json, {"shots": {"0": {"url": "https://a.b/v"}, "2": {"file": "manual/shot_3.jpg"}}})
    html = httpx.get(base + "/").text
    assert all(f'data-preview="{i}"' in html for i in range(3))
    assert preview_disabled(html, 0) and preview_disabled(html, 1) and not preview_disabled(html, 2)
    httpx.post(base + "/api/links", json={"shots": {"0": "https://a.b/v", "2": "file:manual/shot_3.jpg"}})
    assert wait_until(lambda: pf.snapshot().get("https://a.b/v", {}).get("state") == "siap")
    assert not preview_disabled(httpx.get(base + "/").text, 0)

def test_speed_select_shows_saved_speed_and_is_off_for_photos(brief):
    paths, base, _ = brief
    write_json_atomic(paths.links_json, {"shots": {"0": {"url": "https://a.b/v", "speed": 1.5},
                                                   "2": {"file": "manual/shot_3.jpg", "speed": 2.0}}})
    html = httpx.get(base + "/").text
    assert re.search(r'<select data-speed="0"[^>]*>.*?value="1.5" selected', html, re.S)
    assert re.search(r'<select data-speed="1"[^>]*>.*?value="1" selected', html, re.S)
    assert re.search(r'<select data-speed="2"[^>]*\bdisabled\b', html)
    for name in ("syncPreviewButtons", "playbackRate", "collectSpeed"):
        assert name in html
```

Ubah test lama `test_page_shows_sfx_pills_and_preview`: baris `'data-preview="1"' not in html` jadi `'data-preview="1"' in html and preview_disabled(html, 1)`. Assertion `"<video" not in html` tetap.

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_brief_sfx.py -q`
Expected: FAIL (`data-preview="1"` nggak ada, `data-speed` nggak ada).

- [ ] **Step 3: Implement markup**

`_shot_row` ngitung `ready` dari `entry` + `(prefetch or {}).get(url)` (state yang sama dipakai `_prefetch_badge`) dan ngoper ke `_clip_tools`. `_clip_tools` selalu render `preview-box` + `<select data-speed>` di dalam `clip-tools`.

- [ ] **Step 4: Implement JS**

Aturan yang harus dipegang (test nggak bisa nentuin ini, jadi ditulis di sini):
- `speedOf(idx)` = value `select[data-speed]` (fallback 1). `srcDur(idx) = shotDur(idx) * speedOf(idx)`. `windowStart` pakai `srcDur` di dua tempat yang sekarang pakai `shotDur`.
- `togglePreview` tick: `video.playbackRate = speedOf(idx)` (assign cuma kalau beda); loop di `start + srcDur(idx)`; `rel = (t - start) / speedOf(idx)` buat SFX dan teks posisi (`rel` tetap detik shot, dibandingin ke `shotDur`). Kalau media-nya gambar: `select[data-speed]` di-disable.
- `sfxFromPreview`: `rel = (currentTime - start) / speedOf(idx)`.
- `collectSpeed()` = `{idx: speed}` dari tiap select yang nggak disabled. Body semua POST `/api/links` (`scheduleAutoSave`, `save`, `uploadShot`) ikut kirim `speed: collectSpeed()`. `change` di `select[data-speed]` → `scheduleAutoSave()`.
- `input` di `input[data-shot]`: tandai `inp.dataset.dirty = '1'`, tutup preview shot itu kalau kebuka, terus `syncPreviewButtons()`. Autosave sukses → hapus semua `dirty`, `setPrefetchUrls`, `syncPreviewButtons()`.
- `syncPreviewButtons()`: tombol aktif kalau input nggak `dirty` dan (value diawali `file:` atau badge `.prefetch[data-shot-badge=idx]` punya `data-prefetch-url` dan class `pf-siap`). Tombol yang jadi nonaktif sementara preview-nya kebuka → `closePreview(idx)`. Dipanggil di akhir `renderPrefetch` (tiap poll 2 detik) dan `setPrefetchUrls`.

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/test_brief_sfx.py tests/test_brief_server.py tests/test_brief_prefetch.py tests/test_cta_scene.py -q`
Expected: PASS.

- [ ] **Step 6: Cek manual di browser**

Jalanin `uv run mayzfact brief <id run FaktaCuil yang ada> --no-ngrok` (tanya Akmal run mana; jangan pakai run yang lagi dia isi). Di `http://127.0.0.1:3100`, cek:
1. Paste link baru → badge `download…` → `siap` → tombol Preview aktif tanpa refresh.
2. Preview kebuka, ganti link → preview nutup, tombol nonaktif sampai link baru `siap`.
3. Speed 2x → video muter 2x, loop sepanjang `durasi × 2` detik source; teks posisi tetap `x / durasi shot`.
4. Speed 2x, "Dari preview" di tengah loop → detik SFX ≤ durasi shot.
5. Shot foto: select speed disabled.
Matiin brief setelah selesai. Tulis hasilnya di laporan task (mana yang dicek, mana yang belum).

- [ ] **Step 7: Commit**

```bash
git add mayzfact/brief/page.py tests/test_brief_sfx.py
git commit -m "feat(brief): live clip preview and per-shot speed picker"
```

---

### Task 5: Frame referensi dari shot source di plan FaktaCuil (T5, sisi plan)

**Files:**
- Modify: `mayzfact/source_frames.py` (tambah `source_shot_frames`, `_spread`, konstanta)
- Modify: `mayzfact/steps/plan.py` (`run_plan` sekitar baris 230-240)
- Test: `tests/test_source_frames.py`, `tests/test_faktacuil_plan.py`, `tests/test_plan.py`

**Interfaces:**
- Produces: konstanta di `source_frames.py`: `REF_FRAMES_PER_SHOT = 2`, `MAX_SOURCE_SHOTS = 60`, `REF_EDGE = 0.15` (frame nggak diambil di 15% pinggir shot, biar nggak kena transisi).
- Produces: `_spread(n: int, cap: int) -> list[int]` — `list(range(n))` kalau `n <= cap`, selain itu `cap` index yang nyebar rata sampai ujung (`i * n // cap`).
- Produces: `source_shot_frames(paths: RunPaths, source: dict, download_source: Callable[[str, Path], Path], log: Callable[[str], None] = print) -> list[dict]` — `[{"index": int, "start_s": float, "end_s": float, "frames": [{"file": "plan/ref_XX_K.jpg", "t": float}]}]`. `XX` = `index + 1` 2 digit, `K` = 0..1, `t` = detik di source (2 desimal). Gagal apa pun (download, probe, `detect_cuts`) → log + `[]`; 1 shot gagal extract → shot itu dilewat.
- Produces: `plan.json` dapat `narration_mode` (`script.get("narration_mode", "top3")`) di semua mode, dan `source_shots` cuma di FaktaCuil. FaktaCuil nggak manggil `_shot_frames`, jadi `ref_frames` tiap shot `[]`.

- [ ] **Step 1: Write the failing tests**

`tests/test_source_frames.py`:
```python
def test_source_shot_frames_two_seeded_frames_per_cut(tmp_path, cut_video):
    paths = RunPaths(tmp_path / "run")
    copy = lambda vid, dest: shutil.copyfile(cut_video, dest) or dest
    shots = source_shot_frames(paths, SOURCE, copy, log=lambda m: None)
    assert [(s["index"], s["start_s"], s["end_s"]) for s in shots] == [(0, 0.0, 1.0), (1, 1.0, 2.0)]
    assert [f["file"] for f in shots[0]["frames"]] == ["plan/ref_01_0.jpg", "plan/ref_01_1.jpg"]
    assert all((paths.root / f["file"]).exists() and s["start_s"] <= f["t"] <= s["end_s"] for s in shots for f in s["frames"])
    assert source_shot_frames(paths, SOURCE, copy, log=lambda m: None) == shots  # seed video_id: sama tiap plan ulang
    other = source_shot_frames(paths, {**SOURCE, "video_id": "xyz"}, copy, log=lambda m: None)
    assert [f["t"] for s in other for f in s["frames"]] != [f["t"] for s in shots for f in s["frames"]]

def test_source_shot_frames_missing_source_returns_empty(tmp_path):
    def fail(vid, dest):
        raise PipelineError("source", "download gagal")
    logs = []
    assert source_shot_frames(RunPaths(tmp_path / "run"), SOURCE, fail, log=logs.append) == []
    assert logs

def test_spread_covers_whole_source():
    assert _spread(3, 60) == [0, 1, 2]
    picks = _spread(250, 60)
    assert len(picks) == 60 and picks[0] == 0 and picks[-1] >= 245 and picks == sorted(set(picks))
```

`tests/test_faktacuil_plan.py` (fixture `plan`):
```python
def test_faktacuil_plan_has_source_shot_card_not_per_shot_frames(plan, tmp_path):
    assert plan["narration_mode"] == "faktacuil"
    assert all(s["ref_frames"] == [] for s in plan["shots"])
    assert len(plan["source_shots"]) == 2 and len(plan["source_shots"][0]["frames"]) == 2
    assert not list((tmp_path / "run" / "plan").glob("shot_*.jpg"))

def test_faktacuil_plan_survives_missing_source(tmp_path):
    # run_plan sama kayak fixture, download_source raise PipelineError
    assert data["source_shots"] == [] and data["shots"]
```

`tests/test_plan.py`:
```python
def test_top3_plan_has_no_source_shot_card(tmp_path, cut_video):
    _, data = plan_with(tmp_path, cut_video, hook_seconds=0.0)
    assert data["narration_mode"] == "top3" and "source_shots" not in data
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_source_frames.py tests/test_faktacuil_plan.py tests/test_plan.py -q`
Expected: FAIL (`ImportError: source_shot_frames`, key `narration_mode` nggak ada).

- [ ] **Step 3: Implement**

`source_shot_frames`: download kalau `source_mp4` belum ada → `probe` → `segments(merge_cuts(detect_cuts(src, total)), total)` → ambil index dari `_spread(len(segs), MAX_SOURCE_SHOTS)` → `rng = random.Random(source["video_id"])`, per shot `sorted(rng.uniform(a + REF_EDGE * L, b - REF_EDGE * L) for _ in range(REF_FRAMES_PER_SHOT))`, clamp ke `total - 0.05`, `extract_frame` ke `paths.plan_dir / f"ref_{index + 1:02d}_{k}.jpg"`. Satu `try/except Exception` buat bagian deteksi, satu per shot buat extract.
`run_plan`: kalau `narration_mode == "faktacuil"` → `data["source_shots"] = source_shot_frames(...)`, lewati `_shot_frames`; selain itu `_shot_frames` kayak sekarang. `data["narration_mode"]` ditulis di dua mode.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_source_frames.py tests/test_faktacuil_plan.py tests/test_plan.py tests/test_faktacuil_pipeline.py tests/test_cta_scene.py -q`
Expected: PASS (test top3 lama nggak diubah).

- [ ] **Step 5: Commit**

```bash
git add mayzfact/source_frames.py mayzfact/steps/plan.py tests/test_source_frames.py tests/test_faktacuil_plan.py tests/test_plan.py
git commit -m "feat(plan): sample FaktaCuil reference frames from source cuts"
```

---

### Task 6: Kartu "Frame referensi source" di brief + `missing_frames` (T5, sisi brief)

**Files:**
- Modify: `mayzfact/brief/server.py:32-35` (`missing_frames`)
- Modify: `mayzfact/brief/page.py` (tambah `_source_frames_card`, panggil di `render_page` di dalam `main.cards-stack` sebelum kartu shot; CSS kecil `.ref-time`)
- Test: `tests/test_brief_server.py`

**Interfaces:**
- Consumes: `plan["narration_mode"]`, `plan["source_shots"]` (Task 5).
- Produces: `missing_frames(paths, plan) -> list[int]` balikin `[]` kalau `plan.get("narration_mode") == "faktacuil"`; top3 dan plan tanpa `narration_mode` nggak berubah. `cli._brief` nggak perlu diubah.
- Produces: `_source_frames_card(run_id: str, plan: dict) -> str` — `""` kalau bukan FaktaCuil. FaktaCuil: `<details class="z-card source-frames" id="source-frames">` (ketutup default, biar daftar shot di HP nggak kedorong), `<summary>Frame referensi source ({n} shot)</summary>`, per shot source label `Shot source {index+1} · {start_s:.1f}–{end_s:.1f}s`, gambar di `div.refs` pakai `onclick="openLightbox(this.src)" loading="lazy"`, tiap gambar ada caption `<span class="ref-time">{t:.1f}s</span>`. Kosong → pesan `Frame referensi belum ada (source.mp4 nggak ada atau cut detection gagal). Jalanin: mayzfact run {run_id} --from plan --no-render`. Bukan `.card-group[data-group]`, jadi `filterShots` nggak nyembunyiin kartu ini.

- [ ] **Step 1: Write the failing tests**

```python
def test_missing_frames_skipped_for_faktacuil(tmp_path):
    from mayzfact.brief.server import missing_frames
    plan = {**PLAN, "narration_mode": "faktacuil", "shots": [{**s, "ref_frames": []} for s in PLAN["shots"]]}
    assert missing_frames(RunPaths(tmp_path), plan) == []
    assert missing_frames(RunPaths(tmp_path), {**plan, "narration_mode": "top3"}) == [0, 1, 2]

def test_faktacuil_brief_shows_source_frame_card():
    from mayzfact.brief.page import render_page
    shots = [{"index": 0, "start_s": 0.0, "end_s": 1.0, "frames": [{"file": "plan/ref_01_0.jpg", "t": 0.42},
                                                                    {"file": "plan/ref_01_1.jpg", "t": 0.77}]}]
    html = render_page("abc", {**PLAN, "narration_mode": "faktacuil", "source_shots": shots}, {"shots": {}}, {})
    assert 'id="source-frames"' in html and "Frame referensi source (1 shot)" in html
    assert '/files/plan/ref_01_0.jpg' in html and "openLightbox(this.src)" in html and ">0.4s<" in html
    empty = render_page("abc", {**PLAN, "narration_mode": "faktacuil", "source_shots": []}, {"shots": {}}, {})
    assert "--from plan" in empty
    assert 'id="source-frames"' not in render_page("abc", PLAN, {"shots": {}}, {})  # top3 / plan lama
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_brief_server.py -q -k "faktacuil"`
Expected: FAIL.

- [ ] **Step 3: Implement** `missing_frames` early return + `_source_frames_card` sesuai Interfaces. Semua teks dan path lewat `escape`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_brief_server.py tests/test_brief_sfx.py tests/test_cta_scene.py tests/test_cli.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add mayzfact/brief/server.py mayzfact/brief/page.py tests/test_brief_server.py
git commit -m "feat(brief): show FaktaCuil source reference frame card"
```

---

### Task 7: Docs + verifikasi akhir fase

**Files:**
- Modify: `.agents/skills/bikin-faktacuil/SKILL.md` (bagian "## 5–7. Brief, fetch, timeline, render")
- Modify: `docs/DECISIONS.md`, `docs/HANDOFF.md`

- [ ] **Step 1: Update skill.** Tambah bullet di bagian 5–7: shot di brief urut 1..N (label grup cuma info); pilihan speed per shot (0.5x–2x, foto diabaikan, fetch ngambil `durasi × speed` detik source); tombol preview aktif sendiri pas badge `siap`; frame referensi ada di kartu "Frame referensi source" (2 frame acak per shot source, maks 60 shot), bukan per shot, dan brief tetap jalan walau kartunya kosong. Jangan sentuh bagian CTA/keyword (wilayah `fase-cta-v2`).
- [ ] **Step 2: DECISIONS.** Tambah 1 entry `D-060 — 2026-11-21 — Brief v2: speed per shot, preview live, shot urut, kartu frame source` (kalau pas merge nomornya udah dipakai `fase-cta-v2`, pakai nomor bebas berikutnya). Isi: speed dipasang di fetch (approach A spec), `end_s` tetap diabaikan fetch dan preview, frame card cuma FaktaCuil, batas 60 shot source nyebar rata, frame `t` disimpan per frame, `narration_mode` ditulis ke `plan.json`.
- [ ] **Step 3: HANDOFF.** Tambah baris status fase `fase-brief-v2`: yang udah dites (pytest + cek manual Task 4 Step 6) dan yang belum (brief dari HP lewat ngrok, render FaktaCuil dengan klip ber-speed).
- [ ] **Step 4: Verifikasi penuh**

Run (background, ±3 menit): `uv run pytest -q`
Expected: jumlah lolos = baseline + test baru, nggak ada gagal baru.
Run: `uvx ruff check --select F,I mayzfact/manual/links.py mayzfact/brief/server.py mayzfact/brief/page.py mayzfact/ffmpeg.py mayzfact/steps/fetch.py mayzfact/source_frames.py mayzfact/steps/plan.py`
Expected: `All checks passed!`
Run: `uv run pytest -m render -q` (butuh Node 22: `nvm use 22.23.1`)
Expected: PASS (Remotion nggak diubah; ini cuma jaga-jaga clip ber-`setpts`).

- [ ] **Step 5: Commit**

```bash
git add .agents/skills/bikin-faktacuil/SKILL.md docs/DECISIONS.md docs/HANDOFF.md
git commit -m "docs: record brief v2 decisions and handoff"
```

---

## Self-review

- **Spec coverage:** T1 brief (Task 1 + 4), fetch + `clips.json` + foto + `_continuous` (Task 2); T2 preview selalu ada, disabled sampai `siap`/upload, polling, nutup pas link ganti, start/SFX/speed live (Task 4; `end` sengaja nggak dipakai, sesuai call lead soal `end_s`); T3 urut index + label grup + `plan["groups"]` tetap + metric header tetap (Task 3); T5 FaktaCuil only, cut detection seluruh source, 2 frame acak seed `video_id`, `plan/ref_XX_K.jpg`, `source_shots`, detik + lightbox, `missing_frames` dilewat, batas 60, source hilang = pesan (Task 5 + 6); kompatibilitas `links.json`/`plan.json` lama (Global Constraints + Task 6 test plan lama); docs (Task 7). Bagian `queries_zh`/CTA = `fase-cta-v2`.
- **Type consistency:** `SPEEDS`, `attach_speed`, `speed=` di `normalize_video`/`normalize_local`, `source_shot_frames`, `_spread`, `_shots_card`, `_clip_tools(..., ready)`, `_source_frames_card(run_id, plan)` dipakai sama di semua task. Bentuk frame `{"file", "t"}` sama di Task 5 dan 6.
- **Review Focus:** 4 dari 5 punya test di task pemiliknya; poin JS (preview nutup, SFX dibagi speed) dicek manual di Task 4 Step 6 karena repo nggak punya test JS.
