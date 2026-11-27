# Audio klip per shot + mode SFX transisi — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Shot bisa di-unmute dengan volume 0–200 %, dan bunyi transisi per video bisa dipilih: klik + random, klik aja, atau tanpa SFX.

**Architecture:** Pilihan disimpan di `links.json`. Fetch motong audio cuma buat shot yang di-unmute, `clips.json` bawa `volume` ke timeline, terus Remotion muter `<Video>` dengan volume itu. `transition_sfx` dibaca pipeline dan dikirim lewat dict `audio` ke `_sound`.

**Tech Stack:** Python 3 (pytest), ffmpeg, Remotion 4.0.538 (`@remotion/media` Video), HTML/JS brief bawaan.

**Spec:** `docs/superpowers/specs/2026-11-28-shot-audio-design.md`

## Global Constraints

- Volume disimpan sebagai fraksi 0–2 di `links.json`/`clips.json`/timeline. Brief ngirim dalam persen (0–200).
- `transition_sfx` ∈ {`click_random`, `click`, `none`}. Default `click_random` nggak ditulis ke file.
- Shot foto: volume diabaikan di semua lapisan.
- Komentar kode bahasa Indonesia santai, 1 baris.

## Review Focus

1. Source video tanpa track audio + shot di-unmute: fetch nggak boleh gagal (`-map 0:a:0?`).
2. Speed 0.5×/2× + unmute: durasi audio harus sama kayak video (`atempo`).
3. Simpan dari tab brief lama tanpa key `audio`: volume lama harus tetap ada.
4. Layout blur: cuma satu `<Video>` yang bunyi, biar suaranya nggak dobel.
5. Shot lanjutan link yang sama dengan volume beda: tetap dianggap klip yang sama.

---

### Task 1: links.json — `volume` per shot + `transition_sfx`

**Files:** Modify `mayzfact/manual/links.py`, `mayzfact/brief/server.py`. Test `tests/test_brief_sfx.py`, `tests/test_manual_links.py`.

**Interfaces — Produces:**
- `attach_audio(data: dict, raw: dict | None) -> None`: `{idx: persen | None}` → `entry["volume"] = persen / 100`. `None` = hapus `volume`. Persen di luar 0–200 → `ValueError` dengan kata "volume".
- `TRANSITION_SFX = ("click_random", "click", "none")`.
- `attach_transition_sfx(data: dict, value) -> None`: nilai valid selain default ditulis ke `data["transition_sfx"]`, nilai lain → `ValueError`.
- `same_clip` juga ngabaiin `volume`.

- [ ] Test: `test_saving_audio_volume` (`{"0": 150, "1": None}` → shot 0 `volume == 1.5`, shot 1 tanpa `volume`; 250 → 400 dengan "volume").
- [ ] Test: `test_save_without_audio_key_keeps_volume`, `test_upload_keeps_volume`.
- [ ] Test: `test_saving_transition_sfx` (`click` tersimpan, `click_random` nggak ditulis, `bogus` → 400) dan `test_save_without_transition_key_keeps_it`.
- [ ] Test: `test_same_clip_ignores_volume` di `test_manual_links.py`.
- [ ] Jalanin, harus FAIL.
- [ ] Implementasi. Di server, key yang dibawa dari nilai lama digabung jadi loop `("sfx", "speed", "volume")`, dan upload ikut bawa `volume`.
- [ ] Jalanin, harus PASS, terus commit.

### Task 2: brief UI — checkbox Mute, input Volume, label BGM, radio SFX transisi

**Files:** Modify `mayzfact/brief/page.py`, `mayzfact/brief/server.py`. Test `tests/test_brief_sfx.py`.

**Interfaces:**
- Consumes: Task 1 body keys `audio`, `transition_sfx`.
- Produces: `GET /api/bgm-volume` → `{"percent": float}`. FaktaCuil pakai `faktacuil_bgm_volume(song, ref, durasi tts)`, kalau nggak ada pilihan atau bukan FaktaCuil pakai volume dasar. Di-cache per (track, durasi).

- [ ] Test: `test_audio_controls_render_and_photo_disabled`. Shot video ada `data-mute="0" checked`, shot dengan `volume 1.5` nggak dicentang dan `data-volume="0" value="150"`, shot foto checkbox-nya `disabled`.
- [ ] Test: `test_transition_radio_shows_saved_choice` (`name="transition-sfx" value="click" checked`).
- [ ] Test: `test_bgm_volume_endpoint` (tanpa pilihan → `percent == 6.0`).
- [ ] Jalanin, harus FAIL.
- [ ] Implementasi:
  - `_clip_tools` dapet blok audio.
  - Card radio ditaruh di bawah BGM picker, muncul juga di brief top3.
  - JS: `collectAudio()`, `collectTransition()` dikirim di 3 body save, autosave pas checkbox/input/radio berubah, toggle input volume + label, fetch `/api/bgm-volume` pas load dan setelah `saveBgm`, preview `<video>` ikut mute/volume.
- [ ] Jalanin, harus PASS. Cek di Playwright di lebar 390 px, terus commit.

### Task 3: fetch — potong audio buat shot yang di-unmute

**Files:** Modify `mayzfact/ffmpeg.py` (`normalize_video(..., audio: bool = False)`), `mayzfact/steps/fetch.py` (`normalize_local(..., audio=...)`, clips entry `volume`). Test `tests/test_fetch.py` atau `tests/test_ffmpeg*.py`.

- [ ] Test: `test_normalize_video_keeps_audio_with_atempo`. Source lavfi testsrc + sine 3 detik, `audio=True, speed=2` → ada stream audio, durasi audio ±durasi video (≤0,1 detik). `audio=False` → nggak ada stream audio.
- [ ] Test: `test_normalize_video_audio_on_silent_source` (`audio=True` di source tanpa audio → sukses, nggak ada stream audio).
- [ ] Test: fetch nulis `"volume": 1.5` ke clips buat shot video ber-volume, dan nggak nulis buat foto. Ikutin pola fixture `test_fetch.py`.
- [ ] Jalanin, harus FAIL. Implementasi. Jalanin, harus PASS, terus commit.

### Task 4: timeline + Remotion — `volume` per shot dan mode SFX transisi

**Files:** Modify `mayzfact/steps/timeline.py` (`_shot_entries` copy `volume` buat video, `_sound` baca `audio.get("transition_sfx")`), `mayzfact/pipeline.py` (`audio()` isi `transition_sfx` dari links), `remotion/src/types.ts` (`Shot.volume?: number`), `remotion/src/ShotView.tsx`. Test `tests/test_timeline.py` / `tests/test_faktacuil_timeline.py`.

- [ ] Test: `test_shot_entry_carries_volume` (clip video `volume 1.5` → entry `volume 1.5`, foto nggak).
- [ ] Test: `test_transition_sfx_modes`. `click_random` = perilaku sekarang (ada `cut` + extra). `click` = ada `cut`, nggak ada `extra_*`. `none` = nggak ada `cut`/`extra_*`, tapi klik CTA dan SFX kustom tetap ada.
- [ ] Test: pipeline ngirim `transition_sfx` dari links ke timeline. Ikutin pola `test_faktacuil_pipeline`.
- [ ] Jalanin, harus FAIL.
- [ ] Implementasi. `Media` dapet prop `audible`: full = audible, blur foreground = audible, blur background/dekoratif = muted.
- [ ] Jalanin `tsc` dan render potongan pendek satu shot ber-volume. Pakai `ffprobe`/`volumedetect` buat mastiin audio klip kedengeran. Terus commit.

### Task 5: docs + review + merge

- [ ] Update skill `bikin-faktacuil` (opsi brief), `AGENTS.md` (`links.json` keys), `DECISIONS.md` D-071, `HANDOFF.md`.
- [ ] Full `uv run pytest`, `node` CTA tests, `tsc`, ruff.
- [ ] Reviewer subagent (non-Fable) di diff branch. Beresin temuan, merge `--no-ff` ke master.
