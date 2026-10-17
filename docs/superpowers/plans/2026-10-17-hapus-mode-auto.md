# Hapus Mode Auto Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Pipeline cuma punya jalur manual (`source → tts → plan → fetch → timeline → render`); semua kode, setting, env, dependency, test, dan docs khusus auto hilang.

**Architecture:** Pertama pindahin 3 kelompok fungsi yang dipakai manual keluar dari `steps/hook.py` dan `steps/clips.py`, baru hapus modul auto. Setelah itu rapihin config/CLI/helper, cabut `fallback_query`, terakhir docs + `.env`.

**Tech Stack:** Python 3.14 + uv, pytest, ruff (`--select F,I`), pydantic.

**Spec:** `docs/superpowers/specs/2026-10-17-hapus-mode-auto-design.md`

## Global Constraints

- Branch: `hapus-mode-auto` dari `master`.
- Jalur manual nggak berubah perilaku; run di `runs/` tetap bisa dilanjutin.
- Jangan print/log/commit isi `.env`. Bersihin `.env` cuma pakai script yang nyocokin nama variabel di awal baris.
- Jangan sentuh `flow.svg`, `sources/`, `runs/*/voice.mp3`, `script.json`, `youtube.json`, `final.mp4`.
- Jangan hapus `browser-profiles/`, `cache/search|thumbs|media`, `runs/*/hook*` (Akmal yang mutusin, bagian 6 spec).
- Komentar kode bahasa Indonesia santai. Commit Conventional Commits, Inggris, 1 baris, tanpa body, tanpa `Co-Authored-By`.
- Tiap task: `uv run pytest -q` lolos + `uvx ruff check --select F,I <file yang diubah>` lolos.

## Review Focus

1. `script.json` lama yang masih punya `fallback_query` harus tetap kebaca dan lolos `check-script` (pinned di Task 4).
2. `--from hook` / `--from clips` harus ditolak argparse dengan exit 2, bukan crash (pinned di Task 2).
3. `import mayzfact.cli` nggak boleh narik `playwright` (pinned di Task 3: test cek `sys.modules`).
4. `.env` yang punya komentar, baris kosong, dan nilai ber-kutip: cuma baris variabel target yang hilang, sisanya byte-identik (pinned di Task 5: test script bersih-bersih pakai `.env` palsu).
5. Run lama `i2xag_1OJfM` (masih punya `hook.json`) tetap bisa `--from timeline` di salinan (dicek manual di Task 5).

---

### Task 1: Pindahin fungsi yang dipakai manual

**Files:**
- Create: `mayzfact/source_frames.py` (pindahan `FRAME_POSITIONS`, `transcript_near`, `prepare_source_segments` dari `steps/hook.py`, isi dan signature sama persis)
- Create: `mayzfact/shots.py` (pindahan `ShotSlot`, `split_shots`, `beat_subjects` dari `steps/clips.py`)
- Modify: `mayzfact/steps/fetch.py` (pindahan `normalize_local` dari `steps/clips.py`, taruh di atas `_target`)
- Modify importer: `steps/source.py:65`, `steps/plan.py:13-14`, `overlay.py:11`
- Test: `tests/test_source_frames.py` (pindahan `test_prepare_source_segments_writes_frames_to_out_dir` + `test_transcript_near` dari `test_hook.py`, plus fixture `SOURCE` yang dipakai), `tests/test_fetch.py` (pindahan `test_normalize_local_clamps_offset_and_rejects_short_video` dari `test_clips_hook.py`), `tests/test_countdown.py` + 3 test shared di `tests/test_clip_selection.py` pindah ke `tests/test_shots.py` (import dari `mayzfact.shots`)

**Interfaces:**
- Produces: `mayzfact.source_frames.prepare_source_segments`, `mayzfact.source_frames.transcript_near`, `mayzfact.shots.split_shots`, `mayzfact.shots.ShotSlot`, `mayzfact.shots.beat_subjects`, `mayzfact.steps.fetch.normalize_local` (signature sama kayak sekarang).

- [ ] **Step 1:** Pindahin test-test di atas ke file barunya dengan import dari lokasi baru. Hapus versi lama di `test_hook.py`/`test_clips_hook.py`/`test_clip_selection.py`/`test_countdown.py`.
- [ ] **Step 2:** `uv run pytest tests/test_source_frames.py tests/test_shots.py tests/test_fetch.py -q` → FAIL `ImportError`/`ModuleNotFoundError`.
- [ ] **Step 3:** Pindahin kodenya. `steps/hook.py` dan `steps/clips.py` sementara impor balik dari lokasi baru (biar auto masih jalan sampai Task 2).
- [ ] **Step 4:** `uv run pytest -q` → semua lolos.
- [ ] **Step 5:** `git commit -m "refactor: move manual-mode helpers out of hook and clips steps"`

### Task 2: Pipeline cuma manual, hapus modul auto

**Files:**
- Modify: `mayzfact/pipeline.py` (satu daftar `STEPS = ["source", "tts", "plan", "fetch", "timeline", "render"]`, `ALL_STEPS = STEPS`; hapus `MANUAL_STEPS`, cabang `clip_source`, `STEP_ENV["clips"]`, `CLIP_MAX_SEARCHES`, output hook/clips di `step_outputs`/`AFTER_VOICE`, branch hook/clips di `_run_step`, guard "butuh mode manual", field `Deps` `search`/`media_cache`/`hook`/`scorer`/`clip_search` + pembuatnya di `real_deps`, import auto, pesan yang nyebut auto/`--from hook|clips`)
- Modify: `mayzfact/steps/timeline.py:110` (pesan log jadi cuma `--from plan`)
- Delete: `mayzfact/steps/hook.py`, `mayzfact/steps/clips.py`, `mayzfact/providers/{pexels,pixabay,stock,types}.py`, `mayzfact/platforms/`, `mayzfact/thumbs.py`, `mayzfact/scoring.py`, `mayzfact/cache.py`
- Delete tests: `test_hook.py`, `test_clips_hook.py`, `test_clips_step.py`, `test_browser_platform.py`, `test_platform_base.py`, `test_platform_parsers.py`, `test_stock_providers.py`, `test_scoring.py`, `test_cache.py`, sisa auto di `test_clip_selection.py` (hapus file kalau kosong)
- Modify: `tests/test_pipeline.py` (world manual: `SETTINGS` tanpa `clip_source`/Pexels/Pixabay, `Deps` tanpa `search`; ganti `FakeSearch` dengan plan + fetch palsu yang nulis `shots_plan.json`/`clips.json`; test timeline/naskah yang ada tetap ngetes hal yang sama lewat jalur manual; hapus test khusus auto termasuk `test_manual_mode_rejects_auto_steps_and_auto_rejects_manual`)

**Interfaces:**
- Consumes: Task 1 (lokasi baru fungsi shared).
- Produces: `pipeline.STEPS == ["source", "tts", "plan", "fetch", "timeline", "render"]`, `pipeline.ALL_STEPS` sama; `Deps` tanpa field auto (field yang tersisa: yang dipakai manual, termasuk `http`, `encoder`, `download_source`, `fetch_transcript`, `tts`).

- [ ] **Step 1: Test baru di `tests/test_pipeline.py`**

```python
def test_only_manual_steps_exist():
    assert pipeline.ALL_STEPS == ["source", "tts", "plan", "fetch", "timeline", "render"]

@pytest.mark.parametrize("step", ["hook", "clips"])
def test_cli_rejects_removed_steps(step, capsys):
    with pytest.raises(SystemExit) as exc:
        cli.main(["run", "i2xag_1OJfM", "--from", step])
    assert exc.value.code == 2
```

- [ ] **Step 2:** `uv run pytest tests/test_pipeline.py -q -k "only_manual or removed_steps"` → FAIL.
- [ ] **Step 3:** Rapihin `pipeline.py` + `timeline.py`, hapus modul + test auto, tulis ulang world di `test_pipeline.py`.
- [ ] **Step 4:** `uv run pytest -q` → lolos. `rg -n "steps.hook|steps.clips|providers\.(pexels|pixabay|stock|types)|platforms|thumbs|scoring|SearchCache" mayzfact tests` → kosong.
- [ ] **Step 5:** `git commit -m "refactor: drop auto clip mode from pipeline"`

### Task 3: Config, CLI, dan helper

**Files:**
- Modify: `mayzfact/config.py` (hapus field `clip_source`, `pexels_api_key`, `pixabay_api_key`, `hook_platforms`, `clip_platforms`, `browser_headless`, `hook_exact_threshold`, `photo_ratio`; hapus `_clip_source`, `_flag`, `BROWSER_PROFILES_DIR`; `ENV_FIELDS` tinggal 4 rahasia; default baru sesuai tabel spec bagian 3: `elevenlabs_voice_id="TX3LPaxmHKxFdv7VOQHJ"`, `min_duration_seconds=32.0`, sisanya sama)
- Modify: `mayzfact/cli.py` (hapus import `platforms.*`; `login` cuma `youtube`: `login.add_argument("platform", choices=["youtube"])`, tanpa `--check`; deskripsi parser tanpa "klip stock")
- Modify: `mayzfact/ytdlp.py` (hapus param `cookies`, `max_seconds`; default `step` jadi `"source"`; docstring)
- Modify: `mayzfact/store.py` (hapus `hook_dir`, `hook_json`)
- Modify: `mayzfact/matching.py` (hapus `top_k`, `match_label`, `rerank_key`), `mayzfact/media.py` (hapus `best_rendition`, `tier`, `pick_rendition`, import `providers.types`)
- Modify: `pyproject.toml` (hapus `playwright`, deskripsi tanpa "klip stock"), terus `uv lock`
- Modify tests: `test_config.py`, `test_cli.py` (hapus 3 test login platform), `test_ytdlp.py`, `test_store.py`, `test_matching.py`, `test_media.py`, `tests/factories.py` (`cand()`), plus test lain yang pakai env auto/`GEMINI_MODEL` sebagai dummy (`test_tts_step.py`, `test_plan.py`, `test_script_rules.py`, `test_youtube.py`): ganti ke env yang masih ada.

**Interfaces:**
- Produces: `Settings` tanpa field auto; `ENV_FIELDS` keys = `ELEVENLABS_API_KEYS, YOUTUBE_CLIENT_SECRET_JSON, YOUTUBE_TOKEN_JSON, NGROK_BASIC_AUTH`. Setting lain cuma lewat default di kode.

- [ ] **Step 1: Test baru**

```python
# tests/test_config.py
def test_env_holds_only_secrets():
    assert set(ENV_FIELDS) == {"ELEVENLABS_API_KEYS", "YOUTUBE_CLIENT_SECRET_JSON", "YOUTUBE_TOKEN_JSON", "NGROK_BASIC_AUTH"}

def test_non_secret_settings_live_in_code(monkeypatch):
    monkeypatch.setenv("TARGET_DURATION_RATIO", "0.5")  # env nggak ngubah setting non-rahasia lagi
    s = settings_from_env({"TARGET_DURATION_RATIO": "0.5"})
    assert (s.elevenlabs_voice_id, s.elevenlabs_model, s.target_duration_ratio, s.min_duration_seconds,
            s.max_shot_seconds, s.fg_min_height_ratio, s.hook_seconds, s.brief_port) == (
        "TX3LPaxmHKxFdv7VOQHJ", "eleven_v3", 0.8, 32.0, 4.0, 0.5, 10.0, 3100)

# tests/test_cli.py
def test_login_only_accepts_youtube():
    with pytest.raises(SystemExit) as exc:
        cli.main(["login", "tiktok"])
    assert exc.value.code == 2

def test_cli_import_does_not_load_playwright():
    import subprocess, sys
    out = subprocess.run([sys.executable, "-c", "import sys, mayzfact.cli; print('playwright' in sys.modules)"],
                         capture_output=True, text=True, check=True)
    assert out.stdout.strip() == "False"
```

- [ ] **Step 2:** `uv run pytest tests/test_config.py tests/test_cli.py -q -k "only_secrets or live_in_code or only_accepts_youtube or playwright"` → FAIL.
- [ ] **Step 3:** Implement perubahan di atas, `uv lock`, `uv sync`.
- [ ] **Step 4:** `uv run pytest -q` → lolos. `uv run python -c "import playwright"` → `ModuleNotFoundError`.
- [ ] **Step 5:** `git commit -m "refactor: remove auto-only settings, login platforms, and playwright"`

### Task 4: Cabut `fallback_query`

**Files:**
- Modify: `mayzfact/models.py` (hapus `Script.fallback_query`; field ekstra di `script.json` lama tetap diabaikan, perilaku default pydantic)
- Modify: `mayzfact/steps/script.py:41,88-89` (hapus normalisasi + cek `fallback_query`)
- Modify: `.agents/skills/bikin-short/SKILL.md` (hapus `"fallback_query": ...` dari contoh JSON)
- Modify tests: `tests/factories.py`, `test_script_rules.py`, `test_plan.py`, `test_cli.py:249`, `test_pipeline.py` (hapus `fallback_query` dari data naskah, kecuali test di bawah)

- [ ] **Step 1: Test baru di `tests/test_script_rules.py`**

```python
def test_old_script_with_fallback_query_still_loads_and_passes():
    raw = {**good_script_dict(), "fallback_query": "animals"}  # pakai helper naskah valid yang udah ada di file ini
    script = Script.model_validate(raw)
    assert not hasattr(script, "fallback_query")
    assert check_script(script, SOURCE_TEXT, DURATION_S) == []  # sama kayak test naskah valid yang udah ada

def test_script_without_fallback_query_is_valid():
    assert check_script(Script.model_validate(good_script_dict()), SOURCE_TEXT, DURATION_S) == []
```

(Nama helper/konstanta sesuaiin sama yang udah ada di `test_script_rules.py`; intinya satu naskah valid dengan dan tanpa `fallback_query`.)

- [ ] **Step 2:** `uv run pytest tests/test_script_rules.py -q -k fallback` → FAIL (`fallback_query` masih wajib / masih ada atributnya).
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** `uv run pytest -q` → lolos. `uv run mayzfact check-script ydA5gOdKvfc` → `OK` (naskah lama masih punya `fallback_query`).
- [ ] **Step 5:** `git commit -m "refactor: drop fallback_query from script schema"`

### Task 5: Docs, `.env`, verifikasi akhir

**Files:**
- Script sekali pakai di scratchpad (bukan file repo): `keep_env_vars(path: Path, keep: set[str]) -> list[str]` yang hapus tiap baris `^NAME=` dengan `NAME` di luar `keep` (boleh diawali spasi), komentar/baris kosong/baris yang dipertahanin byte-identik, balikin daftar nama yang dihapus (bukan nilainya).
- Modify: `.env.example` dan `.env`: sisain cuma `ELEVENLABS_API_KEYS`, `YOUTUBE_CLIENT_SECRET_JSON`, `YOUTUBE_TOKEN_JSON`, `NGROK_BASIC_AUTH` (plus komentar penjelasnya di `.env.example`); semua variabel lain dihapus, termasuk `GEMINI_*`
- Modify: `README.md`, `AGENTS.md`, `docs/HANDOFF.md`, `docs/DECISIONS.md` (D-031) sesuai spec bagian 3 + 7

- [ ] **Step 1:** Tulis `drop_env_vars` + self-check `assert` di script yang sama: `.env` palsu berisi komentar, baris kosong, nilai `'...'` ber-kutip, `NGROK_BASIC_AUTH='a:b'`, dan `PEXELS_API_KEY=x` → cuma baris Pexels yang hilang, sisanya sama persis.
- [ ] **Step 2:** Jalanin self-check → lolos. Jalanin ke `.env.example` dan `.env`. Print cuma daftar nama yang dihapus.
- [ ] **Step 3:** Update docs:
  - `README.md`: hapus contoh `--from clips`, "Mode lama: `CLIP_SOURCE=auto`", dan bagian "Hook (Fase 2)".
  - `AGENTS.md`: ganti aturan "minta Akmal jalanin `mayzfact login <platform>`" jadi "link yang minta captcha/login = minta link lain ke Akmal". Larangan print `browser-profiles/` tetap.
  - `HANDOFF.md`: tambah handoff fase ini, tandain bagian Fase 2 "dihapus di D-031".
  - `DECISIONS.md`: tambah D-031 (teks di spec bagian 7).
- [ ] **Step 4: Verifikasi**
  - `uv run pytest -q` → lolos.
  - `rg -i "clip_source|pexels|pixabay|playwright|hook_platforms|clip_platforms|browser_headless|fallback_query|GEMINI" mayzfact tests .env.example README.md AGENTS.md .agents` → kosong.
  - `grep -oE '^[A-Za-z_]+=' .env | sort` dan `.env.example` → cuma 4 nama rahasia.
  - `uv run mayzfact run --help` → nggak ada `hook`/`clips`.
  - Salinan run: copy `runs/ydA5gOdKvfc` dan `runs/i2xag_1OJfM` ke scratchpad, jalanin `run_pipeline(<id>, settings=load_settings(), from_step="timeline", no_render=True, runs_dir=<scratchpad>)`, bandingin `timeline.json` ke aslinya (`json.load` sama, kecuali field yang emang dihitung ulang identik). Folder asli di `runs/` nggak disentuh.
  - Hitung ukuran `browser-profiles/`, `cache/search`, `cache/thumbs`, `cache/media` buat dilaporin ke Akmal.
- [ ] **Step 5:** `git commit -m "docs: record removal of auto clip mode"` (`.env` nggak ikut, udah di-gitignore).
