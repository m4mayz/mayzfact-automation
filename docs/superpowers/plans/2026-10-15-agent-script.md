# Naskah Ditulis Agent, Gemini Dicabut — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `mayzfact run <url>` berhenti setelah source (plus frame hook) sampai agent nulis `script.json`; `mayzfact check-script` ngecek naskahnya; semua panggilan Gemini dihapus.

**Architecture:** Step `script` dihapus dari pipeline. Step `source` sekalian download `source.mp4` + frame hook ke `plan/`. `check_script` jadi command CLI, ditambah cek CTA dan BGM. `script.json` bawa `bgm`, `hook_queries`, `queries_zh`; `plan` dan `audio` baca dari situ. `marks.py` tinggal normalisasi + copy emoji.

**Tech Stack:** Python 3.14 + uv, pydantic, pytest.

**Spec:** `docs/superpowers/specs/2026-10-15-agent-script-design.md`

## Global Constraints

- `TARGET_DURATION_RATIO` default 0.8 (spec §5).
- Aturan cek lama tetap: ≤ 10 kata/beat, foto 15–45%, countdown ≥ 2 beat penjelasan, overlap ≤ 15%, emoji dari `EMOJI`.
- Naskah lama di `runs/` nggak disentuh; nggak ada migrasi.
- Suara tetap dikunci (D-007): `VOICE_LOCKED = ("source", "tts")`.
- Komentar kode bahasa Indonesia santai. Commit Conventional Commits 1 baris, tanpa atribusi AI.
- Test Gemini dihapus, bukan di-skip. `google-genai` dicabut dari `pyproject.toml`.

## Review Focus

1. `run` di run baru tanpa `script.json` harus berhenti exit 3, bukan error, dan nggak manggil TTS → test di Task 3.
2. `script.json` lama tanpa `bgm`/`hook_queries`/`queries_zh` (i2xag, NSua7) tetap kebaca di `--from timeline` dan `--from plan` → test di Task 2, 4, 5.
3. `check-script` nolak naskah yang ngilangin "subscribe" padahal source nyebut → test di Task 1.
4. `check-script` dengan `script.json` rusak (bukan JSON / field kurang) keluar pesan bersih, bukan traceback → test di Task 3.
5. Step `source` gagal download `source.mp4` (offline) nggak boleh ngapus `source.json` yang udah ada → test di Task 2.

---

### Task 1: `check_script` jadi fungsi mandiri + cek CTA & BGM

**Files:**
- Modify: `mayzfact/steps/script.py`, `mayzfact/models.py`, `mayzfact/config.py`
- Modify: `tests/test_script_rules.py`, `tests/test_config.py`

**Interfaces:**
- Produces: `Script` nambah `bgm: str = ""`, `hook_queries: dict[str, HookQuery] = {}`; `Beat` nambah `queries_zh: list[str] = []`. `check_script(script: Script, source_text: str, duration_s: float, bgm_choices: list[str] | None = None) -> tuple[list[str], float]`. `CTA_WORDS = ("like", "subscribe", "comment")`.

- [ ] **Step 1: Tulis test yang gagal** (tambah ke `tests/test_script_rules.py`)

```python
def test_cta_words_from_source_must_survive():
    script = make_script()
    source = "Comment below, then like the video and subscribe. Number five, mantis shrimp."
    problems, _ = check_script(script, source, DURATION)
    assert any("subscribe" in p and "like" in p for p in problems)
    script.beats[1] = script.beats[1].model_copy(update={"text": "Smash like, comment, and subscribe now!"})
    problems, _ = check_script(script, source, DURATION)
    assert not [p for p in problems if "subscribe" in p]


def test_bgm_must_exist_when_choices_known():
    script = make_script().model_copy(update={"bgm": "epic.mp3"})
    problems, _ = check_script(script, SOURCE_TEXT, DURATION, bgm_choices=["mystery.mp3"])
    assert any("epic.mp3" in p for p in problems)
    assert not [p for p in check_script(script, SOURCE_TEXT, DURATION, bgm_choices=["epic.mp3"])[0] if "bgm" in p.lower()]
    assert not [p for p in check_script(script, SOURCE_TEXT, DURATION)[0] if "bgm" in p.lower()]  # choices None = nggak dicek


def test_script_accepts_new_optional_fields():
    data = make_script().model_dump()
    data["beats"][0]["queries_zh"] = ["螳螂虾"]
    data["bgm"] = "mystery.mp3"
    data["hook_queries"] = {"0": {"en": ["bird on tower"], "zh": ["鸟 塔"]}}
    script = Script(**data)
    assert script.hook_queries["0"].zh == ["鸟 塔"] and script.beats[0].queries_zh == ["螳螂虾"]
    assert Script(**make_script().model_dump()).bgm == ""  # naskah lama tanpa field baru tetap kebaca
```

`make_script` (dari `tests.factories`), `SOURCE_TEXT`, `DURATION` udah ada di file itu. `DURATION` dihitung pakai ratio 0.6; biarin, dia cuma angka target buat test. `make_script` beat ke-2 teksnya kata unik, jadi beat[1] bebas diganti.

Di `tests/test_config.py`, ganti assertion default ratio:

```python
def test_default_ratio_is_80_percent():
    assert Settings().target_duration_ratio == 0.8
```

- [ ] **Step 2: Jalanin, pastiin gagal**

Run: `uv run pytest tests/test_script_rules.py tests/test_config.py -q -p no:cacheprovider`
Expected: FAIL (`bgm_choices` unexpected kwarg, field `bgm` nggak ada, ratio masih 0.6).

- [ ] **Step 3: Implementasi**

`mayzfact/models.py`:

```python
class Beat(BaseModel):
    ...
    queries_zh: list[str] = []  # versi Mandarin buat nyari di Douyin, ditulis agent


class HookQuery(BaseModel):
    en: list[str] = []
    zh: list[str] = []


class Script(BaseModel):
    beats: list[Beat]
    fallback_query: str
    bgm: str = ""  # nama file di assets/bgm, dipilih agent; "" = tanpa BGM
    hook_queries: dict[str, HookQuery] = {}  # per index segmen hook (plan/seg_XX), ditulis agent
```

Hapus `BgmChoice`, `HookQueries`, `SegmentQueries`, `BeatMark`, `BeatMarks` dari `models.py` (cuma dipakai jalur Gemini; cek `grep` dulu, hapus kalau nggak ada pemakai lain selain file yang dihapus di Task 6).

`mayzfact/config.py`: `target_duration_ratio: float = 0.8`.

`mayzfact/steps/script.py`, di `check_script`:

```python
CTA_WORDS = ("like", "subscribe", "comment")


def check_script(script: Script, source_text: str, duration_s: float,
                 bgm_choices: list[str] | None = None) -> tuple[list[str], float]:
    """Balikin (daftar masalah, overlap). Pesan pakai English biar bisa ditempel balik ke agent mana pun."""
    ...  # cek lama tetap
    source_words = {w.lower() for w in words(source_text)}
    script_words = {w.lower() for w in words(full_text)}
    missing_cta = [w for w in CTA_WORDS if w in source_words and w not in script_words]
    if missing_cta:
        problems.append("The source asks viewers to " + " and ".join(missing_cta)
                        + f"; the script must use the exact word(s) {', '.join(missing_cta)} too (they trigger the on-screen CTA).")
    if bgm_choices is not None and script.bgm and script.bgm not in bgm_choices:
        problems.append(f"bgm {script.bgm!r} is not in assets/bgm. Choose one of: {', '.join(bgm_choices) or '(none)'}.")
    ...
```

`words()` di `mayzfact.text` udah ada; cek dia nge-strip tanda baca (kalau "subscribe." nggak jadi "subscribe", bersihin pakai `re.findall(r"[a-z']+", text.lower())`).

- [ ] **Step 4: Jalanin, pastiin lolos**

Run: `uv run pytest tests/test_script_rules.py tests/test_config.py tests/test_marks.py -q -p no:cacheprovider`
Expected: PASS (test_marks masih lolos karena model `BeatMark*` dihapus baru di Task 6 kalau masih dipakai).

- [ ] **Step 5: Commit**

```bash
git add mayzfact/steps/script.py mayzfact/models.py mayzfact/config.py tests/test_script_rules.py tests/test_config.py
git commit -m "feat(script): check cta words and bgm, add agent-written fields"
```

---

### Task 2: Step `source` sekalian download video + frame hook

**Files:**
- Modify: `mayzfact/steps/source.py`, `mayzfact/steps/hook.py` (pindahin `transcript_near`), `mayzfact/pipeline.py` (`_run_step` source)
- Modify: `tests/test_source.py` (atau bikin kalau belum ada), `tests/test_pipeline.py`

**Interfaces:**
- Consumes: `prepare_source_segments(paths, source, download_source, hook_seconds, out_dir, retry_step)` dari `steps/hook.py`.
- Produces: `run_source(video_id, paths, fetch, *, download_source=None, hook_seconds=0.0, log=print) -> dict`. Kalau `download_source` ada dan `hook_seconds > 0`: `source.mp4` + `plan/seg_XX_K.jpg` kebikin, dan `source.json` nambah `"hook_segments": [{"index", "start_s", "end_s", "frames": [rel paths]}]`.

- [ ] **Step 1: Pindahin `transcript_near`** dari `hook_queries.py` ke `steps/hook.py` (copy fungsinya, update import di `hook.py`). Jalanin `uv run pytest tests/test_hook.py -q` buat mastiin nggak rusak (test `transcript_near` di `test_hook_queries.py` ikut dipindah ke `tests/test_hook.py`).

- [ ] **Step 2: Tulis test yang gagal** (`tests/test_source.py`, tambah)

```python
import shutil

from mayzfact.steps.source import run_source
from mayzfact.store import RunPaths, read_json


def test_source_downloads_video_and_hook_frames(tmp_path, cut_video):
    paths = RunPaths(tmp_path / "abc")
    transcript = [{"text": "five birds with superpowers", "start": 0.0, "duration": 2.0}]
    data = run_source("abc", paths, fetch=lambda vid: transcript,
                      download_source=lambda vid, dest: shutil.copyfile(cut_video, dest) or dest, hook_seconds=1.5,
                      log=lambda m: None)
    assert paths.source_mp4.exists()
    assert data["hook_segments"] and (paths.root / data["hook_segments"][0]["frames"][0]).exists()
    assert read_json(paths.source_json)["hook_segments"] == data["hook_segments"]


def test_source_keeps_json_when_download_fails(tmp_path):
    paths = RunPaths(tmp_path / "abc")
    transcript = [{"text": "x", "start": 0.0, "duration": 1.0}]

    def offline(vid, dest):
        raise PipelineError("source", "offline")

    logs = []
    data = run_source("abc", paths, fetch=lambda vid: transcript, download_source=offline, hook_seconds=1.5, log=logs.append)
    assert paths.source_json.exists() and data["hook_segments"] == []
    assert any("offline" in m for m in logs)
```

(`cut_video` fixture udah ada di `tests/conftest.py`, dipakai `test_plan.py`. Import `PipelineError` dari `mayzfact.errors`.)

- [ ] **Step 3: Jalanin, pastiin gagal**

Run: `uv run pytest tests/test_source.py -q -p no:cacheprovider`
Expected: FAIL (`download_source` unexpected kwarg).

- [ ] **Step 4: Implementasi** (`mayzfact/steps/source.py`)

```python
def run_source(
    video_id: str, paths: RunPaths, fetch: Callable[[str], list[dict]] = youtube_transcript, *,
    download_source: Callable[[str, Path], Path] | None = None, hook_seconds: float = 0.0,
    log: Callable[[str], None] = print,
) -> dict:
    data = build_source(video_id, fetch(video_id))
    data["hook_segments"] = []
    if download_source is not None and hook_seconds > 0:
        from mayzfact.steps.hook import prepare_source_segments

        # Frame hook dibikin di sini biar udah ada pas agent nulis naskah (keyword hook butuh lihat frame-nya).
        try:
            segs = prepare_source_segments(paths, data, download_source, hook_seconds, paths.plan_dir, retry_step="source")
            data["hook_segments"] = [{"index": s["index"], "start_s": s["start_s"], "end_s": s["end_s"],
                                      "frames": [f.relative_to(paths.root).as_posix() for f in s["frames"]]} for s in segs]
        except PipelineError as exc:  # video gagal di-download: naskah tetap bisa ditulis, frame nyusul di --from plan
            log(f"[source] video/frame hook dilewat: {exc.message.splitlines()[0]}")
    write_json_atomic(paths.source_json, data)
    return data
```

`pipeline.py` `_run_step`:

```python
    if step == "source":
        from mayzfact.ytdlp import run_ytdlp, youtube_url

        run_source(paths.root.name, paths, fetch=deps.fetch_transcript,
                   download_source=lambda video_id, dest: run_ytdlp(youtube_url(video_id), dest),
                   hook_seconds=settings.hook_seconds, log=log)
```

Test pipeline yang pakai fake deps: `world` fixture di `test_pipeline.py` nggak punya `run_ytdlp`; tambah `download_source` ke `Deps` (`download_source: Callable[[str, Path], Path] | None = None`) dan pakai `deps.download_source` di `_run_step` (None = skip, kayak sekarang). Di `real_deps`, isi pakai `run_ytdlp`. Di `world`, biarin None.

- [ ] **Step 5: Jalanin, pastiin lolos**

Run: `uv run pytest tests/test_source.py tests/test_hook.py tests/test_pipeline.py -q -p no:cacheprovider`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add mayzfact/steps/source.py mayzfact/steps/hook.py mayzfact/pipeline.py tests/test_source.py tests/test_hook.py tests/test_hook_queries.py tests/test_pipeline.py
git commit -m "feat(source): download video and hook frames before the script is written"
```

---

### Task 3: Step `script` dihapus, `run` nunggu naskah, CLI `check-script`

**Files:**
- Modify: `mayzfact/pipeline.py`, `mayzfact/cli.py`, `mayzfact/steps/script.py`
- Modify: `tests/test_pipeline.py`, `tests/test_cli.py`
- Delete: `tests/test_script_step.py`

**Interfaces:**
- Produces: `STEPS = ["source", "tts", "hook", "clips", "timeline", "render"]`, `MANUAL_STEPS = ["source", "tts", "plan", "fetch", "timeline", "render"]`, `VOICE_LOCKED = ("source", "tts")`, `AWAIT_SCRIPT_HINT`. `plan_steps(done, voice_exists, from_step, steps)` (parameter `new_voice` dihapus). `steps/script.py`: `load_script(paths) -> Script` (raise `PipelineError("script", ...)` kalau nggak ada/rusak), `check_script_file(paths, source, *, ratio, minimum_s, bgm_choices) -> list[str]`. CLI `check-script <id>`.

- [ ] **Step 1: Tulis test yang gagal**

`tests/test_pipeline.py`: hapus `test_from_script_is_allowed_before_voice_exists`, `test_new_voice_reruns_script_and_after`, `test_from_script_is_rejected_after_voice`, `test_new_voice_regenerates_script_and_voice`; ganti `KEYS` tanpa `gemini_api_keys`; `done_until`/`NONE_DONE` ikut `STEPS` baru. Tambah:

```python
def test_run_waits_for_script_when_only_source_exists(world):
    paths = run(world)  # run pertama: cuma source
    assert paths.source_json.exists() and not paths.script_json.exists()
    with pytest.raises(AwaitingInput, match="check-script"):
        run(world)
    assert world.tts.calls == 0  # TTS nggak kepanggil tanpa naskah


def test_run_continues_once_script_is_written(world):
    paths = run(world)
    write_json_atomic(paths.script_json, make_script(n_beats=8, words_per_beat=10).model_dump())
    run(world)
    assert paths.voice_mp3.exists()
```

Di fixture `world`: hapus `FakeWriter`, `writer_calls`, dan `script_writer=` dari `Deps`. Test lama yang nge-assert `world.writer_calls` diubah jadi cuma `(world.tts.calls, world.renders)`. Run pertama sekarang berhenti di source, jadi test yang dulu "full run" harus nulis `script.json` sendiri dulu (pakai `make_script(n_beats=8, words_per_beat=10).model_dump()`) sebelum `run` kedua. Ganti `test_from_clips_does_not_need_gemini_or_elevenlabs_keys` jadi `..._does_not_need_elevenlabs_keys`.

`tests/test_cli.py`:

```python
def test_check_script_reports_problems_and_exit_code(monkeypatch, tmp_path, capsys):
    from mayzfact.store import write_json_atomic

    paths = RunPaths(tmp_path / "abc")
    paths.root.mkdir()
    write_json_atomic(paths.source_json, {"video_id": "abc", "duration_s": 40.0,
                                          "transcript": [{"text": "like and subscribe. " + "word " * 80, "start": 0.0, "duration": 40.0}]})
    monkeypatch.setattr(cli, "load_settings", lambda: Settings())
    monkeypatch.setattr(cli, "RUNS_DIR", tmp_path)
    assert cli.main(["check-script", "abc"]) == 1
    assert "script.json" in capsys.readouterr().err  # belum ada
    paths.script_json.write_text("{not json", encoding="utf-8")
    assert cli.main(["check-script", "abc"]) == 1
    assert "JSON" in capsys.readouterr().err
    write_json_atomic(paths.script_json, {"beats": [{"text": "Hello there.", "media": "video", "queries": ["q"]}], "fallback_query": "f"})
    assert cli.main(["check-script", "abc"]) == 1
    out = capsys.readouterr().out
    assert "subscribe" in out and "words" in out
```

Dan satu test lolos: naskah valid → exit 0, output "OK".

- [ ] **Step 2: Jalanin, pastiin gagal**

Run: `uv run pytest tests/test_pipeline.py tests/test_cli.py -q -p no:cacheprovider`
Expected: FAIL (`AwaitingInput` nggak muncul, `check-script` bukan command).

- [ ] **Step 3: Implementasi**

`mayzfact/steps/script.py`: hapus `PROMPT_PATH`, `build_user_prompt`, `ScriptWriter`, `generate_script`, `run_script`, import `allowed_emoji_line`. Tambah:

```python
AWAIT_SCRIPT_HINT = ("Naskah belum ada. Agent nulis runs/<id>/script.json (lihat .agents/skills/bikin-short/SKILL.md), "
                     "terus cek: uv run mayzfact check-script <id>")


def load_script(paths: RunPaths) -> Script:
    if not paths.script_json.exists():
        raise PipelineError("script", f"{paths.script_json} belum ada. {AWAIT_SCRIPT_HINT}")
    try:
        return normalize_script(Script(**read_json(paths.script_json)))
    except (ValueError, TypeError) as exc:  # JSON rusak atau field kurang (ValidationError juga ValueError)
        raise PipelineError("script", f"script.json nggak valid (cek JSON/field-nya): {str(exc)[:300]}") from exc


def check_script_file(paths: RunPaths, source: dict, *, ratio: float, minimum_s: float,
                      bgm_choices: list[str] | None) -> list[str]:
    script = load_script(paths)
    duration_s = target_duration(source["duration_s"], ratio, minimum_s)
    source_text = " ".join(s["text"] for s in source["transcript"])
    problems, _ = check_script(script, source_text, duration_s, bgm_choices)
    return problems
```

`mayzfact/pipeline.py`:
- `STEPS`, `MANUAL_STEPS`, `VOICE_LOCKED` sesuai Interfaces. `STEP_ENV` tanpa `"script"`. Hapus `NEW_VOICE_HINT`, ganti pesannya jadi "Hapus voice.mp3 + script.json kalau emang mau naskah + suara baru (pakai kredit ElevenLabs)." (`NEW_SCRIPT_HINT`).
- `step_outputs` tanpa `"script"`.
- `plan_steps(done, voice_exists, from_step, steps=STEPS)`: hapus cabang `new_voice`. `steps[3]` di pesan `--from` jadi `steps[2]`.
- `run_pipeline(..., new_voice=False)` → parameter dihapus. Setelah `steps` ditentuin: kalau `"tts" in steps` dan `not paths.script_json.exists()`, `raise AwaitingInput("script", AWAIT_SCRIPT_HINT)`. Kalau `script.json` ada tapi `voice.mp3` belum: `load_script(paths)` dulu (biar JSON rusak kena pesan bersih) dan jalanin `check_script_file`; kalau ada masalah, `raise PipelineError("script", "Naskah belum lolos cek: " + "; ".join(problems))`.
- `_run_step`: hapus cabang `"script"`. `Deps.script_writer` dihapus.

`mayzfact/cli.py`:
- `run`: hapus `--new-voice`; `--from` choices = `ALL_STEPS` (udah tanpa script).
- Tambah `check = sub.add_parser("check-script", help="Cek runs/<id>/script.json yang ditulis agent")`, `check.add_argument("video")`.
- `_check_script(args, settings)`: baca `source.json` (kalau nggak ada → `PipelineError`), `bgm_choices = list_bgm(BGM_DIR)`, panggil `check_script_file`. Kalau kosong: print `OK: naskah lolos cek (N kata, target T)` exit 0. Kalau ada: print tiap masalah dengan `- ` ke stdout, exit 1. `PipelineError` tetap ke stderr exit 1 (jalur `main` yang ada).

- [ ] **Step 4: Jalanin, pastiin lolos**

Run: `uv run pytest tests/test_pipeline.py tests/test_cli.py tests/test_script_rules.py -q -p no:cacheprovider` dan `git rm tests/test_script_step.py`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add -A mayzfact/pipeline.py mayzfact/cli.py mayzfact/steps/script.py tests/test_pipeline.py tests/test_cli.py tests/test_script_step.py
git commit -m "feat(pipeline): wait for agent-written script, add check-script command"
```

---

### Task 4: `plan` pakai `hook_queries` + `queries_zh` dari naskah

**Files:**
- Modify: `mayzfact/steps/plan.py`, `mayzfact/pipeline.py` (`plan` di `real_deps`), `tests/test_plan.py`

**Interfaces:**
- Produces: `run_plan(paths, script, tts, source, *, max_shot_s, hook_seconds, download_source, log)` (parameter `describe`, `translate` dihapus). Keyword hook: `script.get("hook_queries", {}).get(str(index))`, fallback `{"en": [8 kata pertama transcript segmen], "zh": []}`. Keyword beat: `{"en": beat["queries"], "zh": beat.get("queries_zh", [])}`.

- [ ] **Step 1: Tulis test yang gagal** (ubah `plan_with` di `tests/test_plan.py`: hapus `describe`/`translate`; tambah)

```python
def test_plan_takes_hook_and_zh_queries_from_script(tmp_path, cut_video):
    script = {**SCRIPT, "hook_queries": {"0": {"en": ["giant bird on tower"], "zh": ["巨鸟 铁塔"]}}}
    script["beats"][1] = {**script["beats"][1], "queries_zh": ["化石", "螃蟹"]}
    paths, data = plan_with(tmp_path, cut_video, hook_seconds=1.5, script=script)
    assert data["shots"][0]["keywords"] == {"en": ["giant bird on tower"], "zh": ["巨鸟 铁塔"]}
    assert data["shots"][1]["keywords"] == {"en": ["fossil", "crab"], "zh": ["化石", "螃蟹"]}


def test_plan_falls_back_to_transcript_for_hook_without_queries(tmp_path, cut_video):
    _, data = plan_with(tmp_path, cut_video, hook_seconds=1.5)  # SCRIPT lama tanpa hook_queries/queries_zh
    assert data["shots"][0]["keywords"]["en"] == ["five ancient creatures"] and data["shots"][0]["keywords"]["zh"] == []
    assert data["shots"][1]["keywords"] == {"en": ["fossil", "crab"], "zh": []}
```

(`plan_with` perlu parameter `script=SCRIPT`.)

- [ ] **Step 2: Jalanin, pastiin gagal**

Run: `uv run pytest tests/test_plan.py -q -p no:cacheprovider`
Expected: FAIL (`describe` masih wajib / keyword beda).

- [ ] **Step 3: Implementasi** (`mayzfact/steps/plan.py`)

Hapus parameter `describe`, `translate`. Ganti:

```python
    hook_queries = script.get("hook_queries", {})
    ...
        if segment is not None:
            given = hook_queries.get(str(segment))
            if given and (given.get("en") or given.get("zh")):
                keywords = {"en": list(given.get("en", [])), "zh": list(given.get("zh", []))}
            else:  # agent nggak ngisi: 8 kata pertama transcript segmen itu
                snippet = " ".join(words(segs[segment]["transcript"])[:8])
                keywords = {"en": [snippet] if snippet else [], "zh": []}
            ref_frames = [rel(f) for f in segs[segment]["frames"]]
        else:
            keywords = {"en": list(beat["queries"]), "zh": list(beat.get("queries_zh", []))}
            ref_frames = []
```

(import `words` dari `mayzfact.text`.) `pipeline.py` `real_deps.plan`: hapus `writer`, `describe`, `translate`, dan import `hook_queries`.

- [ ] **Step 4: Jalanin, pastiin lolos**

Run: `uv run pytest tests/test_plan.py tests/test_pipeline.py -q -p no:cacheprovider`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add mayzfact/steps/plan.py mayzfact/pipeline.py tests/test_plan.py
git commit -m "feat(plan): take hook and chinese queries from the script"
```

---

### Task 5: BGM dari naskah, marks tanpa Gemini

**Files:**
- Modify: `mayzfact/audio.py`, `mayzfact/marks.py`, `mayzfact/pipeline.py` (`audio`, `marks` di `real_deps`)
- Modify: `tests/test_audio.py`, `tests/test_marks.py`

**Interfaces:**
- Produces: `prepare_audio(paths, script, *, bgm_dir, sfx_dir, client, log)` (tanpa `writer`); BGM = `script.get("bgm")` kalau ada di folder, kalau nggak → log + None. `audio.json` tetap ditulis (`{"bgm": ...}`). `prepare_marks(paths, script, *, client, emoji_dir, log)` (tanpa `writer`): tanda = `normalize_marks(beats, beats)`.

- [ ] **Step 1: Tulis test yang gagal**

`tests/test_audio.py`: hapus `test_pick_bgm`; ubah `test_prepare_audio_copies_and_reuses_choice` jadi tanpa `writer`; tambah:

```python
def test_bgm_comes_from_script(tmp_path):
    bgm_dir = tmp_path / "bgm"
    bgm_dir.mkdir()
    (bgm_dir / "mystery.mp3").write_bytes(b"m")
    paths = RunPaths(tmp_path / "run")
    logs = []
    out = prepare_audio(paths, {"beats": [], "bgm": "mystery.mp3"}, bgm_dir=bgm_dir, sfx_dir=tmp_path / "sfx",
                        client=serving({})[0], log=logs.append)
    assert out["bgm"] == "audio/bgm/mystery.mp3"
    out = prepare_audio(paths, {"beats": [], "bgm": "epic.mp3"}, bgm_dir=bgm_dir, sfx_dir=tmp_path / "sfx",
                        client=serving({})[0], log=logs.append)
    assert out["bgm"] is None and any("epic.mp3" in m for m in logs)
    out = prepare_audio(paths, {"beats": []}, bgm_dir=bgm_dir, sfx_dir=tmp_path / "sfx", client=serving({})[0], log=logs.append)
    assert out["bgm"] is None  # naskah lama tanpa field bgm: tanpa BGM, nggak error
```

(`serving` helper udah ada di `test_audio.py`.)

`tests/test_marks.py`: hapus `FakeWriter`, `test_new_script_marks_need_no_gemini`, `test_old_script_marks_come_from_gemini_and_are_cached`, `test_old_script_without_working_gemini_has_no_marks`, `test_cached_marks_are_cleaned_like_fresh_ones`; `prepare_marks` dipanggil tanpa `writer`. Tambah:

```python
def test_old_script_without_marks_gets_none(tmp_path):
    paths = RunPaths(tmp_path / "run")
    out = prepare_marks(paths, OLD, client=lottie_client()[0], emoji_dir=tmp_path / "assets", **QUIET)
    assert out == {"beats": [NONE] * 3, "emoji": {}}
    assert not (paths.root / "annotations.json").exists()
```

- [ ] **Step 2: Jalanin, pastiin gagal**

Run: `uv run pytest tests/test_audio.py tests/test_marks.py -q -p no:cacheprovider`
Expected: FAIL (`writer` masih wajib / BGM nggak dibaca dari script).

- [ ] **Step 3: Implementasi**

`mayzfact/audio.py`: hapus `pick_bgm`, `PROMPT_PATH`, import `script_text`/`json` kalau nggak kepakai lagi. Di `prepare_audio`:

```python
    choices = list_bgm(bgm_dir)
    bgm = script.get("bgm") or None  # dipilih agent pas nulis naskah
    if bgm and bgm not in choices:
        log(f"[timeline] BGM {bgm!r} dari naskah nggak ada di assets/bgm, video tanpa BGM")
        bgm = None
    write_json_atomic(paths.root / "audio.json", {"bgm": bgm})
```

(Hapus logika "pakai audio.json kalau masih valid": sumbernya sekarang `script.json`, jadi nggak perlu cache.) Docstring modul: "BGM dari naskah (dipilih agent) + SFX dari myinstants".

`mayzfact/marks.py`: hapus `_ask_gemini`, `beat_marks`, `PROMPT_PATH`, import `json`, `Any`, `allowed_emoji_line`, `script_text`, `text_hash`, `PipelineError`. `prepare_marks(paths, script, *, client, emoji_dir, log)` → `marks = normalize_marks(script["beats"], script["beats"])`. Docstring modul diperbarui (nggak ada lagi jalur naskah lama).

`pipeline.py`: `audio` dan `marks` di `real_deps` tanpa `writer`; hapus import `GeminiScriptWriter`.

- [ ] **Step 4: Jalanin, pastiin lolos**

Run: `uv run pytest tests/test_audio.py tests/test_marks.py tests/test_pipeline.py -q -p no:cacheprovider`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add mayzfact/audio.py mayzfact/marks.py mayzfact/pipeline.py tests/test_audio.py tests/test_marks.py
git commit -m "feat: take bgm and beat marks from the agent-written script"
```

---

### Task 6: Cabut Gemini: file, dependency, env, model sisa

**Files:**
- Delete: `mayzfact/providers/gemini.py`, `mayzfact/hook_queries.py`, `mayzfact/prompts/rewrite.md`, `mayzfact/prompts/mark_beats.md`, `mayzfact/prompts/pick_bgm.md`, `mayzfact/prompts/hook_queries.md`, `mayzfact/prompts/translate_queries.md`, `tests/test_gemini.py`, `tests/test_hook_queries.py`
- Modify: `mayzfact/config.py`, `mayzfact/emoji.py` (`allowed_emoji_line` hapus kalau nggak ada pemakai), `mayzfact/models.py`, `.env.example`, `pyproject.toml` (`uv remove google-genai`), `tests/test_config.py`, `tests/test_pipeline.py` (`KEYS`)

- [ ] **Step 1: Tulis test yang gagal** (`tests/test_config.py`)

```python
def test_gemini_settings_are_gone():
    assert not hasattr(Settings(), "gemini_api_keys")
    assert "GEMINI_API_KEYS" not in ENV_FIELDS
```

(import `ENV_FIELDS` dari `mayzfact.config`.) Ubah test lama yang pakai `GEMINI_*` jadi pakai `PEXELS_API_KEY` / `ELEVENLABS_MODEL`.

- [ ] **Step 2: Jalanin, pastiin gagal**

Run: `uv run pytest tests/test_config.py -q -p no:cacheprovider`
Expected: FAIL.

- [ ] **Step 3: Implementasi**

```bash
git rm mayzfact/providers/gemini.py mayzfact/hook_queries.py mayzfact/prompts/rewrite.md mayzfact/prompts/mark_beats.md mayzfact/prompts/pick_bgm.md mayzfact/prompts/hook_queries.md mayzfact/prompts/translate_queries.md tests/test_gemini.py tests/test_hook_queries.py
uv remove google-genai
```

`config.py`: hapus `gemini_api_keys`, `gemini_model`, 2 entri `ENV_FIELDS`. `.env.example`: hapus 2 baris `GEMINI_*`. `models.py`: hapus model yang cuma dipakai Gemini (cek `grep -rn "BgmChoice\|HookQueries\|SegmentQueries\|BeatMarks\|BeatMark\b" mayzfact tests`). `emoji.py`: `allowed_emoji_line` hapus kalau nggak ada pemakai (grep dulu). `tests/test_pipeline.py` `KEYS`: tanpa gemini.

Terus: `grep -rn "gemini\|Gemini\|genai" mayzfact tests` harus kosong (kecuali docs).

- [ ] **Step 4: Full suite + lint**

Run: `uv run pytest -q -p no:cacheprovider` dan `uvx ruff check --select F,I mayzfact tests`
Expected: PASS, lint bersih (import yang nggak kepakai ketangkep di sini).

- [ ] **Step 5: Commit**

```bash
git add -A mayzfact tests pyproject.toml uv.lock .env.example
git commit -m "refactor: remove gemini provider, prompts and settings"
```

---

### Task 7: Skill, AGENTS, README, docs

**Files:**
- Modify: `.agents/skills/bikin-short/SKILL.md`, `AGENTS.md`, `README.md`, `docs/DECISIONS.md`, `docs/HANDOFF.md`

- [ ] **Step 1: Skill `bikin-short`** — langkah 1 diganti jadi 2 langkah:

```markdown
## 1. Source

```bash
uv run mayzfact run <url atau id> --no-render
```

Run pertama bikin `runs/<id>/source.json` (transcript + durasi), `source.mp4`, dan frame hook `runs/<id>/plan/seg_XX_K.jpg`, terus berhenti dengan exit 3 "Naskah belum ada". Kalau `source.mp4` gagal di-download (log `[source] video/frame hook dilewat`), lanjut aja: frame nyusul di step plan.

## 2. Tulis naskah

Agent nulis `runs/<id>/script.json`. Ini tanggung jawab agent, bukan Gemini. Aturannya:

**Isi.** Nulis ulang source: fakta, urutan item, dan momen-momennya tetap, kata-katanya baru. Jangan nambah fakta dari luar source. Pertahankan kata pembatas source ("some species", "one of the"); jangan dilebih-lebihin. Kalau source ngitung ("Number five…"), urutan dan jumlah item sama, tiap item diumumin "Number N, [subject]." dan dapat minimal 2 beat penjelasan.

**Nada.** Persis source. Kalau source santai dan pakai "bro", naskah juga. Tiap item ditutup celetukan atau perbandingan sehari-hari kayak source ("Bro, that's basically a living underwater punch machine"). Hindari kata bombastis (terrifyingly, blazing, lightning-fast). Kalau mau beda dari source, ubah struktur kalimat dan sudut pandangnya, jangan cuma ganti sinonim.

**Panjang.** ±80% durasi source (2.6 kata/detik). Intro dipadetin. CTA source dipadetin ke comment + like + subscribe dalam 1–2 beat, dan **harus pakai kata "like" dan "subscribe" beneran** (itu pemicu animasi CTA). Teaser nomor 1 di hook dipertahankan kalau source punya.

**Format.** Tiap beat ≤ 10 kata, 1 ide visual:

```json
{
  "beats": [
    {"text": "Number five, mantis shrimp.", "media": "video", "queries": ["mantis shrimp close up underwater"],
     "queries_zh": ["螳螂虾 特写"], "subject": "mantis shrimp", "point": false, "emoji": "", "emoji_word": ""}
  ],
  "fallback_query": "ocean animals",
  "bgm": "mystery.mp3",
  "hook_queries": {"0": {"en": ["giant bird on radio tower"], "zh": ["巨鸟 铁塔"]}}
}
```

- `queries`: 2–3 keyword Inggris yang ngegambarin **yang kelihatan pas beat itu**, nyambung sama teksnya: subjek + aksi + tempat. Beat CTA/intro pakai visual yang cocok sama kalimatnya ("hand tapping phone like button"). `queries_zh`: versi Mandarin, cara orang nyari di Douyin.
- `media`: "photo" buat 15–45% beat (close-up subjek), beat pertama selalu "video". `subject`: 1–3 kata, "" buat intro/CTA.
- `point`: true kalau beat ngajak lihat sesuatu atau subjeknya baru muncul di layar; agent yang nentuin, nggak ada kuota. Jangan di beat countdown/teaser.
- `emoji`: dari daftar di `mayzfact/emoji.py` (`EMOJI`), kira-kira 1 dari 3 beat, nggak 2 beat berturut-turut, nggak di beat countdown. `emoji_word`: kata di beat itu tempat emoji muncul.
- `bgm`: nama file di `assets/bgm/` yang mood-nya cocok (lihat `ls assets/bgm`). "" kalau nggak ada yang cocok.
- `hook_queries`: lihat frame `runs/<id>/plan/seg_*.jpg` (index segmen = angka di nama file minus 1), tulis keyword Inggris + Mandarin buat nyari klip yang mirip. `{}` kalau frame belum ada.

Contoh beat yang bagus (source: "This tiny marine predator can throw one of the fastest strikes in the animal kingdom, creating a shockwave powerful enough to stun its prey. Bro, that's basically a living underwater punch machine."):

> "Number five, mantis shrimp." / "This little guy throws one of the fastest punches alive." / "The shockwave alone knocks its prey out cold." / "Bro, it's basically an underwater boxing machine."

Terus:

```bash
uv run mayzfact check-script <id>
```

Perbaiki sampai keluar `OK`. Kalau cek jumlah kata gagal, tambah/kurangi beat, jangan nambah kata ke beat yang ada.

## 3. Checkpoint: Akmal review naskah

Tunjukin ke Akmal di chat, per beat: teks baru | kalimat source yang jadi dasarnya | keyword. Sebutin juga BGM yang dipilih. Tunggu "oke" atau koreksi. Edit sesuai koreksi, cek lagi, tunjukin lagi. **Jangan lanjut ke langkah 4 sebelum Akmal oke** (langkah 4 bikin suara, pakai kredit ElevenLabs).

## 4. Suara dan plan

```bash
uv run mayzfact run <id> --no-render
```

Exit 3 "Nunggu input" = plan udah jadi, lanjut ke brief (langkah 5).
```

Nomor langkah berikutnya digeser (brief jadi 5, dst). Alur di atas skill: `source → [agent tulis naskah] → [Akmal review naskah] → suara → plan → [Akmal isi link] → …`. Hapus kalimat soal `point`/`emoji` "jalur ini baru dites sekali".

- [ ] **Step 2: `AGENTS.md`**
  - Ganti paragraf "Teks di dalam pipeline … dibikin Gemini" jadi: naskah, keyword klip, tanda emoji/panah, dan BGM ditulis **agent** ke `runs/<id>/script.json`, dicek `mayzfact check-script`, dan harus di-review Akmal sebelum suara dibikin. Nggak ada LLM eksternal di pipeline.
  - Diagram alur: `source → naskah (agent, review Akmal) → suara (ElevenLabs) → …`.
  - Perintah: tambah `uv run mayzfact check-script <id>`; hapus `--new-voice`. Exit 3 sekarang juga = "nunggu naskah".
  - Biaya: ganti kalimat `--new-voice`/`--from script` jadi "Kalau `voice.mp3` udah ada, jangan hapus `script.json`/`voice.mp3` tanpa izin Akmal."
  - Struktur: `prompts/` dihapus dari tabel.
- [ ] **Step 3: `README.md`** — deskripsi awal ("Naskah ditulis ulang pakai Gemini") → "Naskah ditulis AI agent (Claude Code, Codex, dll) dan direview dulu"; setup: hapus `GEMINI_API_KEYS`; perintah: hapus `--new-voice`, tambah `check-script`.
- [ ] **Step 4: `docs/DECISIONS.md`** — D-028 "Naskah ditulis agent, Gemini dicabut" (ngegantiin D-003, D-010; isi keputusan interview bagian 2 spec; authority Akmal chat 2026-10-15). Tandain D-003 dan D-010 "diganti D-028".
- [ ] **Step 5: `docs/HANDOFF.md`** — section baru: yang selesai, test, dan "Belum dites: naskah beneran dari agent end-to-end buat 1 video baru".
- [ ] **Step 6: Full suite + commit**

Run: `uv run pytest -q -p no:cacheprovider`
Expected: PASS.

```bash
git add .agents/skills/bikin-short/SKILL.md AGENTS.md README.md docs/DECISIONS.md docs/HANDOFF.md
git commit -m "docs: agent writes the script, gemini removed"
```
