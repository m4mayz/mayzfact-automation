# Fase 3B Audio Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans.

**Goal:** BGM yang dipilih sesuai konteks dari `assets/bgm/`, plus SFX myinstants di 4 momen. Semuanya dirender Remotion.

**Spec:** [`docs/superpowers/specs/2026-10-13-fase3b-audio-design.md`](../specs/2026-10-13-fase3b-audio-design.md)

> **Ruling (eksekutor):** sama kayak plan 3A. Akmal minta langsung dikerjain, jadi plan ini cuma berisi interface + test kunci. Kode ditulis TDD pas eksekusi.

## Global Constraints

- **Branch:** `fase3b-audio`.
- **Commit:** pakai `caveman-commit`, 1 baris, tanpa atribusi AI.
- **Test:** nggak boleh ada network beneran. `voice.mp3` nggak boleh disentuh.
- **Render:** jangan render final. Review dulu di Studio.

## Review Focus

1. Folder `assets/bgm/` kosong atau nggak ada: timeline tetap jadi tanpa BGM.
2. `audio.json` nunjuk file yang udah dihapus: BGM dipilih ulang.
3. myinstants down: SFX yang gagal dilewat, timeline tetap jadi.
4. SFX `cut` jangan dobel sama SFX `number` di frame yang sama.

---

### Task 1: `mayzfact/audio.py`

- **Isi:**
  - `SFX_DEFAULTS`, `MYINSTANTS`
  - `load_sfx_map(sfx_dir)`: kalau `sfx.json` belum ada, bikin dari default
  - `ensure_sfx(sfx_dir, client, mapping, log) -> dict[str, Path]`
  - `list_bgm(bgm_dir) -> list[str]`
  - `pick_bgm(choices, script, writer, log) -> str | None`
  - `prepare_audio(paths, script, *, bgm_dir, sfx_dir, client, writer, log) -> dict`
- **Model:** `BgmChoice(file: str)` di `models.py`. Prompt di `prompts/pick_bgm.md`.
- **Test:** `tests/test_audio.py`.
- **Commit:** `feat: add bgm picker and sfx library`

### Task 2: SFX + BGM di timeline + pipeline

- `build_timeline(..., audio=None)` → `bgm` + `sfx`. `run_timeline(..., audio=None)`.
- `Deps.audio` + `real_deps`. Step timeline manggil `deps.audio`.
- `.gitignore`: tambah `assets/bgm/*` dan `assets/sfx/*.mp3`.
- **Test:** `tests/test_timeline.py`, `tests/test_pipeline.py`.
- **Commit:** `feat: place sfx and bgm in timeline`

### Task 3: Remotion `SoundLayer`

- **Type:** `Sfx`, `Bgm`. `ShortVideo` dapat `SoundLayer`.
- **Check:** `tsc` + render marker (fixture SFX + BGM).
- **Commit:** `feat: add sound layer for bgm and sfx`

### Task 4: E2E i2xag + Studio + review

- Jalanin `--from timeline --no-render`.
- Restart Studio.
- Final review Opus, terus fix Important.
- Update HANDOFF.
