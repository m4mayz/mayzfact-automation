# FaktaCuil CTA v2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** CTA FaktaCuil jadi opsional dengan 3 format CTA-1 baru (`lucky`, `subscribe`, `emoji`) plus CTA-2 kuis (`cta_quiz`), aturan struktur ikut posisi CTA, dan keyword klip English only. Top3 nggak berubah.

**Architecture:** Deteksi blok CTA tetap di `mayzfact/faktacuil.py` (anchor kata `like`/`subscribe`/komen) ditambah "kata penghubung" (`muncul*`, `emoji`) dan pengecualian beat kuis. Schema `Script.cta_scene` jadi union strict `CtaScene` (top3, wajib) | `FaktaCuilCtaScene` (opsional), plus `cta_quiz`. Scene FaktaCuil dibangun fungsi sendiri `build_faktacuil_scene` (cabang `fk` di `build_scene` dihapus), klik SFX FaktaCuil diturunin dari cue scene. Remotion: `FaktaCuilCta.tsx` dapat pill SUBSCRIBE dan emoji Lottie, tipe scene FaktaCuil dipisah dari tipe top3.

**Tech Stack:** Python 3.12 + pydantic v2 + pytest (`uv`), httpx (`MockTransport` di test), Remotion 4 (React/TS, `@remotion/lottie`), Node 22 (`nvm use 22.23.1`), esbuild SSR test `remotion/tests/faktacuil-cta.cjs`.

**Spec:** `docs/superpowers/specs/2026-11-21-faktacuil-brief-cta-v2-design.md`, cuma bagian "Branch 2: `fase-cta-v2`" (T4, T6, T7, T8), "Kompatibilitas run lama", dan "Dokumen yang ikut diupdate". T1/T2/T3/T5 punya branch `fase-brief-v2` (plan terpisah), jangan dikerjain di sini.

## Global Constraints

- Branch `fase-cta-v2`. Branch `fase-brief-v2` jalan paralel dan banyak ngubah `mayzfact/brief/page.py`, `mayzfact/steps/fetch.py`, dan `_shot_frames` di `mayzfact/steps/plan.py`. Plan ini **nggak nyentuh** `page.py`/`fetch.py`, dan di `plan.py` cuma 1 baris (Task 3).
- Top3 nggak boleh berubah perilaku. `tests/golden/*.json` jangan di-regenerate. Test top3 (`tests/test_top3_*.py`, `tests/test_cta_scene.py`, `tests/test_cta_illustration_policy.py`, `tests/test_approved_word_count.py`, `tests/test_plan.py`) nggak boleh diubah.
- Baseline `master` (2026-11-21, `uv run pytest -q`): 848 lolos, 5 gagal, 3 skip. Yang gagal:
  - `tests/test_top3_golden.py` `[top3_timeline_scene.json]` dan `[top3_timeline_fixture.json]`: `build_scene` top3 ngeluarin key `format: "question"` yang nggak ada di golden. Task 2 ngilangin key itu, jadi dua test ini harus lolos lagi.
  - `tests/test_faktacuil_timeline.py::test_faktacuil_ignores_marks_but_uses_first_shot_detection_for_arrow`, `tests/test_pipeline.py::test_timeline_step_uses_overlay_deps_and_survives_errors`, `tests/test_pipeline.py::test_timeline_step_uses_beat_marks_for_emoji_and_arrows`: di luar scope plan ini. Jangan dibenerin, tapi jangan nambah gagal lain. "Full suite hijau" di tiap task artinya cuma 3 ini yang boleh gagal.
- Nama format: `lucky`, `subscribe`, `emoji`. Schema:
  - `"cta_scene": {"format": "lucky"|"subscribe", "theme": "<tema>"}` atau `{"format": "emoji", "emoji": "<karakter emoji>"}`, opsional buat FaktaCuil.
  - `"cta_quiz": {"word": "<kata>", "answer": <int>}`, opsional, cuma FaktaCuil.
  - Top3 tetap `{"theme", "transform_word", "comment_text"}` dan wajib. Semua model `extra="forbid"`.
- Format lama `question`/`reveal`/`escape`/`escalate` ditolak dengan pesan jelas; file run dibiarin.
- Kombinasi valid: tanpa CTA, `lucky`, `subscribe`, `emoji`, kuis, `lucky`+kuis, `subscribe`+kuis. `emoji` nggak pernah digabung.
- Kalimat kunci: ajakan like Indonesia (`id_like_positions`), `muncul` (boleh `munculin`/`munculnya`), `subscribe`, `emoji`, frasa kuis `berapa kali aku bilang`.
- Emoji: karakter apa aja (nggak dibatasi `EMOJI` di `mayzfact/emoji.py`), codepoint diturunin dari karakter. Lottie Noto nggak ada → peringatan di log + emoji statis. Nggak boleh bikin run gagal.
- Pesan `check-script` bahasa Inggris (pola sekarang). Pesan `PipelineError` dan log bahasa Indonesia santai.
- Komentar kode bahasa Indonesia santai, 1 baris, cuma alasan/constraint. Istilah teknis English.
- Langkah hiasan (stiker, emoji, SFX) dibungkus try/except + log.
- Nggak nambah dependency Python/npm.
- Jangan sentuh `runs/`, `.env`, `flow.svg`, `sources/`, `browser-profiles/`. Jangan jalanin TTS/upload/brief beneran.
- Commit per task: Conventional Commits, English, 1 baris, tanpa body, tanpa `Co-Authored-By` atau atribusi AI apa pun.
- Cek tiap task: test yang disebut task itu, `uv run pytest -q` di akhir task, `uvx ruff check --select F,I <file yang diubah>`. Task Remotion: `cd remotion && npx tsc --noEmit -p .`.

## Review Focus

- CTA `lucky` dipecah 2 beat dan beat objeknya nggak nyebut "like" ("jika beruntung bisa muncul madu.") → tetap masuk blok CTA, bukan dihitung jawaban. Test: Task 1 `test_lucky_object_beat_joins_block_via_muncul`.
- Beat jawaban persis setelah CTA yang juga nyebut "muncul" ("Ternyata bulunya muncul lagi.") padahal blok CTA udah punya "muncul" → nggak ikut kesedot ke blok. Test: Task 1 `test_answer_with_muncul_is_not_absorbed_when_block_has_muncul`.
- Hitungan kuis sama kayak telinga: "Kardus," dan "KARDUS" dihitung, "kardusnya" dan "kardus-kardus" nggak, kalimat kuis sendiri nggak. Test: Task 1 `test_count_word_is_whole_word_case_insensitive`, `test_quiz_count_excludes_quiz_beat`.
- Run FaktaCuil lama (format `escape`, `voice.mp3` + `timeline.json` + `final.mp4` udah ada) dijalanin `--from timeline` → ditolak sebelum output lama dihapus. Test: Task 3 `test_legacy_faktacuil_run_is_rejected_before_outputs_are_deleted`.
- Emoji tanpa Lottie Noto, atau pakai variation selector (`❤️` = `2764_fe0f`) → coba tanpa `fe0f`, kalau tetap nggak ada: timeline jadi, scene tanpa `emojiSrc`, Remotion nampilin emoji statis tanpa nge-hang. Test: Task 4 `test_prepare_cta_emoji_retries_without_fe0f`, `test_pipeline_emoji_cta_failure_falls_back_to_static`; Task 5 kasus `emoji static` di `faktacuil-cta.cjs`.

---

## File Structure

| File | Perubahan |
| --- | --- |
| `mayzfact/faktacuil.py` | Helper kuis + hitung kata, `faktacuil_cta_indices` pakai kata penghubung dan skip beat kuis, aturan F3–F12 v2. Hapus `CTA_FORMATS`, `CTA_TRIGGERS`, `pick_cta_format`. |
| `mayzfact/models.py` | `FaktaCuilTheme`, `FaktaCuilCtaScene`, `CtaQuiz`, `Script.cta_scene` opsional + validator per mode. `CtaScene.format` dihapus. |
| `mayzfact/steps/script.py` | `load_script`: tolak format lama FaktaCuil, `cta_scene` wajib cuma top3. |
| `mayzfact/cta_scene.py` | `build_faktacuil_scene` baru; `build_scene` top3 tanpa cabang FaktaCuil dan tanpa key `format`. |
| `mayzfact/steps/timeline.py` | `_faktacuil_clicks(scene)` ganti `_faktacuil_cta`; `cta_emoji_src` di `build_timeline`/`run_timeline`. |
| `mayzfact/emoji.py` | `emoji_codepoint`, `prepare_cta_emoji`. |
| `mayzfact/pipeline.py` | `Deps.cta_emoji` + wiring step timeline. |
| `mayzfact/steps/plan.py` | 1 baris: `zh` kosong buat FaktaCuil. |
| `remotion/src/types.ts` | `StickerTheme`, `FaktaCuilSceneData`; `CtaSceneData` balik jadi tipe top3. |
| `remotion/src/FaktaCuilCta.tsx` | Gerak stiker tunggal, pill SUBSCRIBE, emoji Lottie/statis. |
| `remotion/src/Emojis.tsx` | Ekstrak `useLottieJson(src)` (dipakai ulang). |
| `remotion/src/FaktaCuilStickers.tsx`, `ShortVideo.tsx` | Tipe aja. |
| `remotion/tests/faktacuil-cta.cjs` | Ditulis ulang buat format baru. |
| `tests/faktacuil_fixtures.py` | `faktacuil_script(total_words=69, cta="lucky")` dengan 7 varian. |
| Docs | `.agents/skills/bikin-faktacuil/SKILL.md`, `docs/DECISIONS.md` (D-061), `docs/HANDOFF.md`. |

Urutan task sengaja: Task 2 (scene/timeline) dikerjain sebelum Task 3 (schema), biar suite tetap hijau di tiap commit. `build_faktacuil_scene` baca `format`; config lama `question` di fixture lama jatuh ke cabang stiker-tengah (sama kayak `lucky`) sampai fixture diganti di Task 3.

---

### Task 1: Helper deteksi blok CTA v2 dan kuis

**Files:**
- Modify: `mayzfact/faktacuil.py:48-55` (`faktacuil_cta_indices`), tambah helper di bawahnya
- Test: `tests/test_faktacuil_cta.py`

**Interfaces:**
- Produces (semua di `mayzfact/faktacuil.py`):
  - `QUIZ_PHRASE: str = "berapa kali aku bilang"`
  - `LINK_WORDS: tuple[str, ...] = ("muncul", "emoji")` (dicocokkan pakai `clean(token).startswith(...)`)
  - `quiz_index(beats: list) -> int | None` — index beat pertama yang teksnya mengandung `QUIZ_PHRASE` (case-insensitive). `beats` boleh list dict atau `Beat`.
  - `count_word(text: str, word: str) -> int` — jumlah token `clean(t) == word.lower()` di `text.split()`.
  - `quiz_count(beats: list, word: str) -> int` — `count_word` di semua beat sebelum `quiz_index(beats)` (0 kalau nggak ada beat kuis).
  - `faktacuil_cta_indices(beats: list) -> list[int]` — blok CTA-1 (tanpa beat kuis).

- [ ] **Step 1: Tulis test merah di `tests/test_faktacuil_cta.py`**

```python
def beats_of(*texts):
    return [{"text": t} for t in texts]

def test_lucky_object_beat_joins_block_via_muncul():
    b = beats_of("Hook,", "Padahal salah,", "Tapi sebelum lanjut, coba tekan like,", "jika beruntung bisa muncul madu.", "Ternyata a,", "jadi b.")
    assert faktacuil_cta_indices(b) == [2, 3]

def test_emoji_lead_in_joins_block_backwards():
    b = beats_of("Hook,", "Ternyata a,", "Tapi mengapa ada emoji madu", "saat tekan like?")
    assert faktacuil_cta_indices(b) == [2, 3]

def test_answer_with_muncul_is_not_absorbed_when_block_has_muncul():
    b = beats_of("Hook,", "Padahal salah,", "Tapi coba tekan like, nanti muncul madu,", "Ternyata bulunya muncul lagi.", "jadi b.")
    assert faktacuil_cta_indices(b) == [2]

def test_quiz_beat_is_never_a_cta_anchor():
    b = beats_of("Hook kardus,", "kardus lagi,", "Nah coba tebak berapa kali aku bilang kardus di video like ini?")
    assert faktacuil_cta_indices(b) == []
    assert quiz_index(b) == 2

def test_count_word_is_whole_word_case_insensitive():
    assert count_word("Kardus, kardusnya, kardus-kardus, KARDUS.", "kardus") == 2

def test_quiz_count_excludes_quiz_beat():
    b = beats_of("Kenapa kucing suka kardus?", "Padahal Kardus itu keras,", "Nah coba tebak berapa kali aku bilang kardus")
    assert quiz_count(b, "kardus") == 2
    assert quiz_count(beats_of("tanpa kuis kardus"), "kardus") == 0
```

Test lama di file ini (`test_cta_block_includes_gimmick_question`, `test_like_word_outside_cta_makes_block_non_contiguous`, `test_subscribe_and_comment_words_are_cta_anchors`, `test_cta_indices_dispatch_keeps_top3`) tetap jalan tanpa diubah.

- [ ] **Step 2: Jalanin, pastiin gagal**

Run: `uv run pytest tests/test_faktacuil_cta.py -q`
Expected: FAIL, `ImportError: cannot import name 'quiz_index'`.

- [ ] **Step 3: Implement helper di `mayzfact/faktacuil.py`**

Algoritma `faktacuil_cta_indices` (nggak ketentu dari signature):

```python
quiz = quiz_index(beats)
anchors = [i for i, toks in enumerate(tokens) if i != quiz and any(t.startswith("like") or t in SUBSCRIBE or t in ID_COMMENT for t in toks)]
if not anchors: return []
lo, hi = anchors[0], anchors[-1]
for word in LINK_WORDS:  # beat objek/emoji yang nggak nyebut like tetap bagian CTA
    if not any(t.startswith(word) for i in range(lo, hi + 1) for t in tokens[i]):
        if hi + 1 < len(beats) and hi + 1 != quiz and any(t.startswith(word) for t in tokens[hi + 1]): hi += 1
        elif lo > 0 and any(t.startswith(word) for t in tokens[lo - 1]): lo -= 1
return list(range(lo, hi + 1))
```

`tokens[i] = [clean(t) for t in text.split()]`.

- [ ] **Step 4: Jalanin test FaktaCuil**

Run: `uv run pytest tests/test_faktacuil_cta.py tests/test_faktacuil_script.py tests/test_faktacuil_scene.py tests/test_faktacuil_review_fixes.py -q`
Expected: PASS semua (aturan lama masih kepakai sampai Task 3).

- [ ] **Step 5: Commit**

```bash
git add mayzfact/faktacuil.py tests/test_faktacuil_cta.py
git commit -m "feat(faktacuil): detect cta v2 blocks and quiz beat"
```

---

### Task 2: Scene dan klik CTA FaktaCuil v2 (Python)

**Files:**
- Modify: `mayzfact/cta_scene.py` (seluruh cabang `fk` di `build_scene`, tambah `build_faktacuil_scene`)
- Modify: `mayzfact/steps/timeline.py:428-444` (`_faktacuil_cta` → `_faktacuil_clicks`), `:493-591` (`build_timeline`), `:594-615` (`run_timeline`)
- Test: `tests/test_faktacuil_scene.py`, `tests/test_faktacuil_timeline.py`

**Interfaces:**
- Consumes: `faktacuil_cta_indices`, `id_like_positions`, `id_like_begin` (Task 1 / existing), `faktacuil_cta_stop` (existing).
- Produces:
  - `build_faktacuil_scene(script: dict, shots: list[dict], entries: list[dict], words: list[dict], beat_of: list[int], total: int) -> dict | None` di `mayzfact/cta_scene.py`. Balikin `None` kalau `cta_scene` kosong atau blok/spans kosong. Bentuk:
    `{"style": "faktacuil", "format": str, "theme"?: str, "emoji"?: str, "from": int, "durationInFrames": int, "stages": [{"kind": "like"|"subscribe", "from", "durationInFrames", "timing": "word"|"structure", "triggerAt"?}], "cues": [{"kind", "from", "word"}]}`. `theme` cuma ada kalau config punya theme, `emoji` cuma kalau format `emoji`. Nggak ada `commentText`.
  - `build_scene(...)` signature tetap; baris pertama dispatch ke `build_faktacuil_scene` kalau `narration_mode == "faktacuil"`. Dict top3 nggak punya key `format` lagi.
  - `FAKTACUIL_SUBSCRIBE_CLICK = 12` di `mayzfact/steps/timeline.py` (frame dari cue `subscribe` ke klik; harus sama dengan `SUB_CLICK` di `FaktaCuilCta.tsx`, Task 5).
  - `_faktacuil_clicks(scene: dict) -> list[dict]` → action `{"kind", "from", "durationInFrames", "clickAt"}` per cue `like`/`subscribe`, `clickAt` = `CTA_CLICK["like"]` buat like, `FAKTACUIL_SUBSCRIBE_CLICK` buat subscribe, dipotong ke akhir scene (pola `_faktacuil_cta` lama).
  - `build_timeline(..., cta_emoji_src: str | None = None)` dan `run_timeline(..., cta_emoji_src: str | None = None)`: kalau scene format `emoji` dan `cta_emoji_src` ada → `scene["emojiSrc"] = cta_emoji_src`.

Aturan `build_faktacuil_scene`:
- `stop = total` kalau format `emoji` (scene akhir sampai video selesai), selain itu `faktacuil_cta_stop(...)` (berhenti di shot jawaban pertama; beat kuis setelah blok juga ngakhirin scene karena index-nya > blok).
- Cue `like`: kata di `id_like_positions` pertama dalam blok, frame `floor(start_s*30+.5)`, harus di `[start, stop)`. Stage `like` mulai di `id_like_begin` (jalan mundur ke "coba"), fallback frame shot pertama beat itu (`timing: "structure"`).
- Cue `subscribe` cuma buat format `subscribe`: token `clean(t) in SUBSCRIBE` pertama di blok. Stage `subscribe` dari cue itu (fallback: shot pertama beat yang nyebut subscribe) sampai `stop`; stage `like` berhenti di awal stage `subscribe`.
- Format lain (termasuk config lama `question` sebelum Task 3) = perilaku `lucky`.

- [ ] **Step 1: Tulis test merah**

Di `tests/test_faktacuil_scene.py` tambah helper lokal `v2(fmt)` yang ambil `faktacuil_script().model_dump()`, ganti `beats[4..5]` dan `cta_scene` (dict mentah, schema belum berubah di task ini):
- `lucky`: beat 4 `"Tapi sebelum lanjut, coba tekan like,"`, beat 5 `"jika beruntung bisa muncul madu."`, `{"format": "lucky", "theme": "honey"}`
- `subscribe`: beat 5 `"nanti muncul madu, subscribe jika berhasil."`, `{"format": "subscribe", "theme": "honey"}`
- `emoji`: hapus beat 4–5, tambah beat akhir `"Tapi mengapa ada emoji madu saat tekan like?"` (subject `""`), `{"format": "emoji", "emoji": "🍯"}`

```python
def test_lucky_scene_has_like_stage_only():
    scene = build(v2("lucky"))
    assert scene["style"] == "faktacuil" and scene["format"] == "lucky" and scene["theme"] == "honey"
    assert [s["kind"] for s in scene["stages"]] == ["like"] and [c["kind"] for c in scene["cues"]] == ["like"]
    assert "commentText" not in scene and "emoji" not in scene
    assert scene["stages"][0]["from"] == frame(words, "coba")

def test_subscribe_scene_cues_subscribe_word():
    scene = build(v2("subscribe"))
    assert [c["kind"] for c in scene["cues"]] == ["like", "subscribe"]
    assert next(c for c in scene["cues"] if c["kind"] == "subscribe")["from"] == frame(words, "subscribe")
    like, sub = scene["stages"]
    assert like["from"] + like["durationInFrames"] == sub["from"]

def test_emoji_scene_runs_to_video_end():
    scene = build(v2("emoji"))
    assert scene["from"] + scene["durationInFrames"] == total and scene["emoji"] == "🍯" and "theme" not in scene

def test_scene_is_none_without_cta_scene():
    s = v2("lucky"); s["cta_scene"] = None
    assert build(s) is None
```

Test lama `test_faktacuil_scene_has_like_and_transform_only` dan `test_faktacuil_scene_ignores_subscribe_and_comment_words` dihapus (transform udah nggak ada). `test_faktacuil_scene_stops_when_answer_starts` dan `test_faktacuil_cta_stop_falls_back_to_total` tetap.

Di `tests/test_faktacuil_timeline.py`:

```python
def test_subscribe_format_adds_second_click():
    script, alignment, _ = faktacuil_timeline_fixture(25, v2("subscribe"))
    sub = next(w for w in word_timings(alignment) if w["text"].strip(",.").lower() == "subscribe")
    tl = timeline(script=v2("subscribe"))
    clicks = [s for s in tl["sfx"] if s["src"] == "audio/sfx/click.mp3"]
    assert len(clicks) == 2
    assert abs(clicks[1]["from"] - (to_frame(sub["start_s"]) + FAKTACUIL_SUBSCRIBE_CLICK)) <= 8

def test_emoji_scene_gets_lottie_src_only_when_given():
    assert timeline(script=v2("emoji"), cta_emoji_src="emoji/1f36f.json")["ctaScene"]["emojiSrc"] == "emoji/1f36f.json"
    assert "emojiSrc" not in timeline(script=v2("emoji"))["ctaScene"]

def test_no_cta_scene_means_no_scene_and_no_click():
    s = v2("lucky"); s["cta_scene"] = None  # beat CTA tetap ada, tapi scene-nya nggak dibikin
    tl = timeline(script=s)
    assert "ctaScene" not in tl and not any(x["src"] == "audio/sfx/click.mp3" for x in tl["sfx"])
```

Taruh `v2` di `tests/faktacuil_fixtures.py` sebagai `faktacuil_v2_dict(fmt: str) -> dict` biar dua file test pakai yang sama (Task 3 ngehapus helper ini dan ganti ke `faktacuil_script(cta=...)`).

- [ ] **Step 2: Jalanin, pastiin gagal**

Run: `uv run pytest tests/test_faktacuil_scene.py tests/test_faktacuil_timeline.py -q`
Expected: FAIL (`KeyError: 'transform_word'` / `cta_emoji_src` unexpected keyword).

- [ ] **Step 3: Implement**

- `build_faktacuil_scene` sesuai aturan di atas. Hapus semua cabang `fk` di `build_scene` dan argumen `format=` di dict return-nya. Import `faktacuil_cta_indices`, `id_like_*` pindah ke fungsi baru.
- `build_timeline`: di blok `try`, `cta = [] if faktacuil else _top3_cta(...)`. Setelah `scene` jadi: `if faktacuil and scene: cta = _faktacuil_clicks(scene)` dan pasang `emojiSrc`. Baris `scene['style'] = 'faktacuil'` boleh dihapus karena udah dari `build_faktacuil_scene`. Hapus `_faktacuil_cta` dan import `faktacuil_cta_indices`, `id_like_positions`, `faktacuil_cta_stop` yang jadi nggak kepakai.

- [ ] **Step 4: Jalanin test FaktaCuil + top3**

Run: `uv run pytest tests/test_faktacuil_scene.py tests/test_faktacuil_timeline.py tests/test_faktacuil_revisi.py tests/test_faktacuil_review_fixes.py tests/test_cta_scene.py tests/test_top3_golden.py tests/test_top3_timeline.py -q`
Expected: PASS semua, termasuk 2 golden top3 yang tadinya gagal.

- [ ] **Step 5: Full suite + commit**

Run: `uv run pytest -q` → nggak ada gagal baru.

```bash
git add mayzfact/cta_scene.py mayzfact/steps/timeline.py tests/faktacuil_fixtures.py tests/test_faktacuil_scene.py tests/test_faktacuil_timeline.py
git commit -m "feat(faktacuil): build lucky, subscribe and emoji cta scenes"
```

---

### Task 3: Schema v2, `check-script`, keyword English, kompatibilitas run lama

**Files:**
- Modify: `mayzfact/models.py`
- Modify: `mayzfact/faktacuil.py:58-166` (hapus format lama, tulis ulang `faktacuil_problems` + `_cta_problems`, tambah `_quiz_problems`)
- Modify: `mayzfact/steps/script.py:138-151` (`_faktacuil_check`), `:158-177` (`load_script`)
- Modify: `mayzfact/steps/plan.py:215` (1 baris)
- Modify: `tests/faktacuil_fixtures.py`
- Test: `tests/test_faktacuil_cta_v2.py` (baru), edit `tests/test_faktacuil_script.py`, `tests/test_faktacuil_review_fixes.py`, `tests/test_faktacuil_scene.py`, `tests/test_faktacuil_timeline.py`, `tests/test_faktacuil_plan.py`

**Interfaces:**
- Consumes: semua helper Task 1.
- Produces:
  - `mayzfact/models.py`:
    - `FaktaCuilTheme = Literal["volcano", "unicorn", "honey", "puppy", "lion", "shark", "toilet", "cat", "zebra"]` (terpisah dari literal top3, biar stiker baru FaktaCuil nggak ikut ke top3).
    - `class FaktaCuilCtaScene(BaseModel)`: `extra="forbid"`; `format: Literal["lucky", "subscribe", "emoji"]`; `theme: FaktaCuilTheme | None = None`; `emoji: str = ""`. `model_validator(mode="after")`: `lucky`/`subscribe` wajib `theme` dan `emoji` kosong; `emoji` wajib `emoji` valid dan `theme` None. Emoji valid = 1–16 karakter, nggak ada ASCII/spasi, karakter pertama `unicodedata.category == "So"`.
    - `class CtaQuiz(BaseModel)`: `extra="forbid"`; `word: str = Field(min_length=1, max_length=40, pattern=r"^[\w-]+$")`; `answer: int = Field(strict=True, ge=1, le=99)`.
    - `CtaScene`: field `format` dihapus, sisanya tetap.
    - `Script.cta_scene: CtaScene | FaktaCuilCtaScene | None = None`, `Script.cta_quiz: CtaQuiz | None = None`, `model_validator(mode="after")`: top3 → `cta_scene` harus `CtaScene` dan `cta_quiz` None; faktacuil → `cta_scene` nggak boleh `CtaScene` (pesan nyebut format lama dihapus, pakai lucky/subscribe/emoji).
  - `mayzfact/faktacuil.py`: `LEGACY_CTA_FORMATS = ("question", "reveal", "escape", "escalate")`. Hapus `CTA_FORMATS`, `CTA_TRIGGERS`, `pick_cta_format`, import `random`.
  - `tests/faktacuil_fixtures.py`: `faktacuil_script(total_words: int = 69, cta: str = "lucky") -> Script`, `cta` salah satu `"none" | "lucky" | "subscribe" | "emoji" | "quiz" | "lucky+quiz" | "subscribe+quiz"`. Default `lucky` naruh CTA di beat 4–5 (index lain tetap kayak sekarang). Teks CTA:
    - lucky: `"Tapi sebelum lanjut, coba tekan like,"` + `"jika beruntung bisa muncul madu."`, `{"format": "lucky", "theme": "honey"}`
    - subscribe: `"Tapi sebelum lanjut, coba tekan like,"` + `"nanti muncul madu, subscribe jika berhasil."`, `{"format": "subscribe", "theme": "honey"}`
    - emoji: tanpa beat 4–5, beat akhir `"Tapi mengapa ada emoji madu saat tekan like?"`, `{"format": "emoji", "emoji": "🍯"}`
    - quiz: beat akhir `"Nah coba tebak berapa kali aku bilang kardus?"`, `cta_quiz={"word": "kardus", "answer": 2}`
    - Filler cuma di beat isi (bukan CTA/kuis), total tetap `total_words`; foto tetap di beat isi `[1, 3, 7]` versi lama. Hapus `faktacuil_v2_dict` dari Task 2 dan ganti pemakaiannya ke `faktacuil_script(cta=...).model_dump()`.

Aturan `faktacuil_problems(script)` (pesan English, needle dipakai test di bawah):

| Kondisi | Pesan berisi |
| --- | --- |
| beat CTA ada, `cta_scene` None | `"has CTA beats but no cta_scene"` |
| `cta_scene` ada, blok kosong | `"cta_scene is set but no CTA beat"` |
| beat kuis ada xor `cta_quiz` ada | `"cta_quiz and the quiz beat"` |
| format `emoji` + kuis | `"emoji CTA cannot be combined"` |
| `lucky`/`subscribe`: blok bukan 1–3 beat | `"one contiguous block of 1-3 beats"` (teks lama) |
| `emoji`: blok bukan 1–2 beat terakhir video | `"emoji CTA must be the last 1-2 beats"` |
| `lucky`/`subscribe`: nggak ada beat salah kaprah sebelum CTA (F4) | `"misconception beat"` (teks lama) |
| `lucky`/`subscribe`: < 2 beat jawaban setelah CTA, beat kuis nggak dihitung (F5) | `"two answer beats"` (teks lama) |
| ajakan like ≠ 1, atau ada komen, atau `subscribe` di format selain `subscribe` | `'must invite exactly one like ("tekan like")'` |
| format `subscribe` tanpa kata subscribe di blok | `"must ask to subscribe"` |
| `lucky`/`subscribe`: blok tanpa `muncul*` atau tanpa nama objek `THEME_NOUNS_ID[theme]` | `"must say 'muncul' and name the sticker object"` (+ saran bikin stiker baru) |
| `emoji`: blok tanpa kata `emoji`, atau beat CTA terakhir nggak diakhiri `?` | `"emoji CTA must say 'emoji'"` |
| beat CTA dengan token `like*` tanpa ajakan dan tanpa kata penghubung/subscribe | `"uses 'like' outside the CTA"` (teks lama) |
| beat CTA/kuis dengan `subject` | `"CTA beat N must have an empty subject"` (teks lama, kuis ikut) |
| beat kuis bukan beat terakhir | `"quiz beat must be the last beat"` |
| kata `cta_quiz.word` nggak ada di beat kuis | `"quiz beat must name cta_quiz.word"` |
| `quiz_count < 2` | `"must be said at least twice before the quiz"` |
| `answer != quiz_count` | `f"cta_quiz.answer is {a} but {w!r} is said {n} times before the quiz beat. Set answer to {n}."` |
| `keyword` di beat CTA atau kuis | pesan keyword lama |
| query < 2 per beat | `"needs at least 2 search queries"` |
| query non-ASCII | `"must be English (ASCII only)"` |

F2 (countdown), F9 (point/emoji), F11 (jumlah kata, di `_faktacuil_check`), ≤10 kata, overlap 4-gram tetap. `queries_zh` nggak dicek sama sekali.

`load_script`: sebelum `Script(**raw)`, kalau `mode == "faktacuil"` dan `cta_scene` dict yang punya `transform_word` atau `format in LEGACY_CTA_FORMATS` → `PipelineError("script", ...)` bahasa Indonesia yang nyebut format lamanya, "udah dihapus di CTA v2 (D-061)", contoh `lucky`/`subscribe`/`emoji`, opsi hapus `cta_scene`, dan "file run ini dibiarin apa adanya". Cek `cta_scene is None` yang sekarang cuma buat top3 (pesan D-050 lama tetap).

`plan.py:215`: `"zh": [] if script.get("narration_mode") == "faktacuil" else list(beat.get("queries_zh", []))`.

- [ ] **Step 1: Tulis test merah di `tests/test_faktacuil_cta_v2.py`**

```python
@pytest.mark.parametrize("cta", ["none", "lucky", "subscribe", "emoji", "quiz", "lucky+quiz", "subscribe+quiz"])
def test_every_valid_combo_passes(cta):
    assert check_script(faktacuil_script(cta=cta), SOURCE_TEXT_EN)[0] == []

def test_schema_shapes():
    FaktaCuilCtaScene(format="emoji", emoji="📦"); FaktaCuilCtaScene(format="lucky", theme="honey")
    for bad in [dict(format="emoji", emoji="box"), dict(format="emoji", emoji=""), dict(format="emoji", emoji="📦", theme="honey"),
                dict(format="lucky"), dict(format="lucky", theme="honey", emoji="📦"), dict(format="lucky", theme="honey", transform_word="x"),
                dict(format="question", theme="honey")]:
        with pytest.raises(ValidationError): FaktaCuilCtaScene(**bad)
    with pytest.raises(ValidationError): CtaQuiz(word="kardus", answer="2")

def test_top3_still_requires_its_own_cta_scene():
    raw = top3_script().model_dump()
    for scene in [None, {"format": "lucky", "theme": "honey"}]:
        with pytest.raises(ValidationError): Script(**{**raw, "cta_scene": scene})
    with pytest.raises(ValidationError): Script(**{**raw, "cta_quiz": {"word": "water", "answer": 2}})

def test_theme_nouns_cover_every_sticker_theme():
    assert set(THEME_NOUNS_ID) == set(get_args(FaktaCuilTheme))

def test_faktacuil_without_cta_loads(tmp_path):
    paths = RunPaths(tmp_path); write_json_atomic(paths.script_json, faktacuil_script(cta="none").model_dump())
    assert load_script(paths).cta_scene is None

@pytest.mark.parametrize("scene", [
    {"theme": "honey", "transform_word": "berubah", "comment_text": "MADU"},
    *({"theme": "honey", "transform_word": "muncul", "comment_text": "MADU", "format": f} for f in LEGACY_CTA_FORMATS)])
def test_legacy_faktacuil_format_is_rejected_with_clear_message(tmp_path, scene):
    paths = RunPaths(tmp_path); raw = {**faktacuil_script().model_dump(), "cta_scene": scene}
    write_json_atomic(paths.script_json, raw)
    with pytest.raises(PipelineError) as err: load_script(paths)
    msg = str(err.value)
    assert scene.get("format", "question") in msg and "CTA v2" in msg and "lucky" in msg and "dibiarin" in msg
    assert json.loads(paths.script_json.read_text(encoding="utf-8")) == raw
```

`test_legacy_faktacuil_run_is_rejected_before_outputs_are_deleted`: tiru `tests/test_top3_only.py::test_old_run_with_paid_voice_is_rejected_before_outputs_are_deleted` pakai naskah FaktaCuil `format: "escape"`, `from_step="timeline"`, plus `clips.json`/`timeline.json`/`final.mp4`; expect `PipelineError` dengan `"CTA v2"` dan isi folder run byte-per-byte sama.

Test aturan (satu `parametrize`, `(cta, mutate, needle)`, mutate ke `data = faktacuil_script(cta=cta).model_dump()`): satu baris per kondisi tabel di atas, misalnya:
- `("lucky", lambda d: d["beats"][5].update(text="jika beruntung bisa muncul singa."), "name the sticker object")`
- `("lucky", lambda d: d["beats"][5].update(text="jika beruntung bisa dapat madu."), "must say 'muncul'")`
- `("lucky", lambda d: d["beats"][5].update(text="muncul madu, subscribe ya."), "must invite exactly one like")`
- `("subscribe", lambda d: d["beats"][5].update(text="nanti muncul madu kalau berhasil."), "must ask to subscribe")`
- `("emoji", lambda d: d["beats"][-1].update(text="Tapi mengapa ada emoji madu saat tekan like."), "must say 'emoji'")`
- `("emoji", lambda d: d.update(cta_quiz={"word": "kardus", "answer": 2}), "cannot be combined")`
- `("none", lambda d: d.update(cta_scene={"format": "lucky", "theme": "honey"}), "no CTA beat")`
- `("lucky", lambda d: d.update(cta_scene=None), "no cta_scene")`
- `("quiz", lambda d: d.update(cta_quiz=None), "cta_quiz and the quiz beat")`
- `("quiz", lambda d: d["cta_quiz"].update(answer=3), "Set answer to 2")`
- `("quiz", lambda d: d["beats"][2].update(text=d["beats"][2]["text"].replace("kardus", "kotak")), "at least twice")`
- `("quiz", lambda d: d["beats"].append({**d["beats"][-2]}), "last beat")`
- `("lucky+quiz", lambda d: d["beats"].__delitem__(slice(7, 9)), "two answer beats")` (sisa 1 jawaban + kuis)
- `("lucky", lambda d: d["beats"][2].update(queries=["猫 纸箱", "cat box"]), "ASCII only")`
- `("lucky", lambda d: d["beats"][2].update(queries=["cat box"]), "at least 2 search queries")`

Plus:
- `test_end_cta_and_no_cta_skip_structure_rules`: varian `emoji`, `quiz`, `none` dengan beat salah kaprah dihapus (`d["beats"].pop(2)`) → nggak ada problem `"misconception"`/`"two answer beats"`.
- `test_queries_zh_is_ignored_for_faktacuil`: isi `queries_zh=["猫"]` di semua beat → tetap `[]`.
- `test_like_in_quiz_beat_is_allowed`: varian `quiz`, beat kuis `"Nah coba tebak berapa kali aku bilang kardus, like?"` → `[]`.

Di `tests/test_faktacuil_plan.py`: `test_faktacuil_plan_drops_queries_zh` — script fixture dengan `queries_zh=["猫"]` → semua `shot["keywords"]["zh"] == []` dan semua `group["keywords"]["zh"] == []`.

- [ ] **Step 2: Jalanin, pastiin gagal**

Run: `uv run pytest tests/test_faktacuil_cta_v2.py tests/test_faktacuil_plan.py -q`
Expected: FAIL (`ImportError: FaktaCuilCtaScene`).

- [ ] **Step 3: Implement schema, aturan, `load_script`, `plan.py`, fixture**

Sesuai Interfaces + tabel. Bersihin test FaktaCuil lama yang ngerujuk format lama: di `tests/test_faktacuil_script.py` hapus `CTA_FORMAT_TEXTS`, `test_all_cta_formats_pass`, `test_cta_format_needs_matching_trigger_word`, `test_cta_format_needs_theme_object`, `test_cta_format_question_still_requires_jadi_phrase`, `test_pick_cta_format_is_stable_and_covers_every_format`, `test_transform_word_in_hook_is_not_cta`; ganti needle lama `"does not match the narrated transformation"` ke `"name the sticker object"` dan mutasi `"apakah like-mu berubah jadi singa?"` ke `"jika beruntung bisa muncul singa."`. Di `tests/test_faktacuil_review_fixes.py::test_valid_three_beat_cta_with_lead_in_still_passes` ganti ke 3 beat format `subscribe` (`"Tapi sebelum lanjut, coba tekan like,"`, `"nanti muncul madu,"`, `"subscribe jika berhasil."`, `cta_scene` subscribe) → `[]`. Test top3 nggak disentuh.

- [ ] **Step 4: Jalanin semua test FaktaCuil + top3**

Run: `uv run pytest tests/test_faktacuil_cta_v2.py tests/test_faktacuil_*.py tests/test_top3_only.py tests/test_top3_script.py tests/test_top3_golden.py tests/test_approved_word_count.py tests/test_cta_illustration_policy.py tests/test_plan.py -q`
Expected: PASS.

- [ ] **Step 5: Full suite + ruff + commit**

Run: `uv run pytest -q` lalu `uvx ruff check --select F,I mayzfact/models.py mayzfact/faktacuil.py mayzfact/steps/script.py mayzfact/steps/plan.py tests/`

```bash
git add mayzfact/models.py mayzfact/faktacuil.py mayzfact/steps/script.py mayzfact/steps/plan.py tests/
git commit -m "feat(faktacuil): optional cta v2 schema and check-script rules"
```

---

### Task 4: Emoji Lottie buat format `emoji`

**Files:**
- Modify: `mayzfact/emoji.py`
- Modify: `mayzfact/pipeline.py:106-123` (`Deps`), `:219-243` (`real_deps`), `:345-373` (`_run_step` timeline)
- Modify: `tests/test_faktacuil_pipeline.py:18` (`write_faktacuil_run(paths, duration_s=None, script=None)`)
- Test: `tests/test_cta_emoji.py` (baru), `tests/test_faktacuil_timeline.py`

**Interfaces:**
- Consumes: `run_timeline(..., cta_emoji_src=...)` (Task 2), `ensure_emoji` (existing).
- Produces:
  - `emoji_codepoint(char: str) -> str` — `"_".join(f"{ord(c):x}" for c in char)`.
  - `prepare_cta_emoji(run_root: Path, cta_scene: dict | None, *, client: httpx.Client, emoji_dir: Path, log: Callable[[str], None], sleep: Callable[[float], None] = time.sleep) -> str | None`. `None` kalau format bukan `emoji`. Coba `emoji_codepoint(e)`, lalu versi tanpa `_fe0f` kalau beda. Yang pertama ketemu di-copy ke `run_root/"emoji"/<cp>.json`, balikin `"emoji/<cp>.json"`. Nggak ada → log `"[timeline] PERINGATAN: Lottie Noto buat emoji {e} ({cp}) nggak ada, CTA pakai emoji statis."` lalu `None`.
  - `Deps.cta_emoji: Callable[[RunPaths, Callable[[str], None]], str | None] | None = None`; `real_deps` ngisi pakai `http()` + `EMOJI_DIR` (pola `marks`).
  - `_run_step` timeline: kalau FaktaCuil dan `deps.cta_emoji`, panggil di `try/except Exception` (log `"[timeline] emoji CTA dilewat, pakai emoji statis: ..."`), terus oper `cta_emoji_src` ke `run_timeline`.

- [ ] **Step 1: Tulis test merah**

`tests/test_cta_emoji.py` (pakai `httpx.MockTransport`, pola `tests/test_marks.py`, `sleep=lambda s: None`, `emoji_dir=tmp_path/"cache"`):

```python
def test_emoji_codepoint():
    assert emoji_codepoint("📦") == "1f4e6"
    assert emoji_codepoint("❤️") == "2764_fe0f"
    assert emoji_codepoint("🇮🇩") == "1f1ee_1f1e9"

def test_prepare_cta_emoji_copies_lottie_into_run(tmp_path): ...  # 200 → "emoji/1f4e6.json", file ada di run
def test_prepare_cta_emoji_retries_without_fe0f(tmp_path): ...    # 2764_fe0f 404, 2764 200 → "emoji/2764.json"
def test_prepare_cta_emoji_missing_lottie_warns(tmp_path): ...    # 404 semua → None, log ada "PERINGATAN" dan "statis"
def test_prepare_cta_emoji_ignores_other_formats(tmp_path): ...   # {"format": "lucky", ...} dan None → None, 0 request
```

`tests/test_faktacuil_timeline.py` (pakai fixture `world` + `write_faktacuil_run(..., script=faktacuil_script(cta="emoji").model_dump())`):

```python
def test_pipeline_passes_cta_emoji_to_timeline(world): ...           # deps.cta_emoji = lambda p, log: "emoji/1f36f.json" → ctaScene.emojiSrc
def test_pipeline_emoji_cta_failure_falls_back_to_static(world): ... # deps.cta_emoji raise RuntimeError → timeline.json jadi, ctaScene tanpa emojiSrc, log "emoji CTA dilewat"
```

- [ ] **Step 2: Jalanin, pastiin gagal**

Run: `uv run pytest tests/test_cta_emoji.py tests/test_faktacuil_timeline.py -q`
Expected: FAIL (`ImportError: emoji_codepoint`).

- [ ] **Step 3: Implement** sesuai Interfaces.

- [ ] **Step 4: Jalanin test**

Run: `uv run pytest tests/test_cta_emoji.py tests/test_faktacuil_timeline.py tests/test_marks.py tests/test_pipeline.py -q`
Expected: PASS.

- [ ] **Step 5: Full suite + ruff + commit**

```bash
git add mayzfact/emoji.py mayzfact/pipeline.py tests/test_cta_emoji.py tests/test_faktacuil_timeline.py tests/test_faktacuil_pipeline.py
git commit -m "feat(faktacuil): fetch noto lottie for emoji cta with static fallback"
```

---

### Task 5: Visual Remotion CTA v2

**Files:**
- Modify: `remotion/src/types.ts:85-102`, `:126`
- Modify: `remotion/src/FaktaCuilCta.tsx`
- Modify: `remotion/src/Emojis.tsx`
- Modify: `remotion/src/FaktaCuilStickers.tsx:196` (tipe prop aja)
- Modify: `remotion/src/ShortVideo.tsx:45` (kalau narrowing butuh)
- Modify: `remotion/tests/faktacuil-cta.cjs` (tulis ulang)
- Test: `tests/test_faktacuil_scene.py` (wrapper node)

**Interfaces:**
- Consumes: bentuk scene dari Task 2 (`style`, `format`, `theme?`, `emoji?`, `emojiSrc?`, `stages`, `cues`), `FAKTACUIL_SUBSCRIBE_CLICK = 12`.
- Produces (`types.ts`):
  - `export type StickerTheme = 'volcano' | 'unicorn' | 'honey' | 'puppy' | 'lion' | 'shark' | 'toilet' | 'cat' | 'zebra';` (stiker FaktaCuil baru nambah di sini, bukan di tipe top3)
  - `CtaSceneData` (top3): hapus `format`, ganti `style?: 'faktacuil'` jadi `style?: undefined`. Sisanya tetap.
  - `export type FaktaCuilSceneData = {style: 'faktacuil'; format: 'lucky' | 'subscribe' | 'emoji'; theme?: StickerTheme; emoji?: string; emojiSrc?: string; from: number; durationInFrames: number; stages: CtaStage[]; cues: {kind: CtaStage['kind']; from: number; word: string}[]};`
  - `TimelineProps.ctaScene?: CtaSceneData | FaktaCuilSceneData;`
  - `Sticker` prop `theme: StickerTheme`.
  - `Emojis.tsx`: `export const useLottieJson = (src?: string): LottieAnimationData | null` (fetch + `delayRender`/`continueRender`, error → `null` + `console.error`; `delayRender` cuma kalau `src` ada). `EmojiAnim` pakai hook ini, perilaku top3 sama.
  - `FaktaCuilCtaVisual: React.FC<{scene: FaktaCuilSceneData; frame: number}>` dengan atribut markup buat test: `data-cta-pill="like"|"subscribe"`, `data-cta-sticker="true" data-cta-format="<format>"`, `data-cta-emoji="lottie"|"static"`.

Perilaku `FaktaCuilCtaVisual`:
- Pill LIKE/LIKED, kursor, klik di cue `like`, stiker: sama kayak sekarang. `stickerMotion` jadi satu gerak (isi cabang `default`/`question` sekarang); cabang `reveal`/`escape`/`escalate` dihapus.
- `subscribe`: pill SUBSCRIBE muncul di `subFrom = max(cue subscribe - scene.from, pillEnd)` (fallback stage `subscribe`), geometri = komponen `Pill` yang sama, warna merah YouTube `#ff0000` teks `SUBSCRIBE`, kursor masuk dan klik di `subFrom + SUB_CLICK` (`SUB_CLICK = 12`, sama dengan `FAKTACUIL_SUBSCRIBE_CLICK`), lalu abu gelap `rgba(28,28,30,0.94)` teks `SUBSCRIBED` selama `LIKED_HOLD`. Stiker tetap tampil selama itu. Detail ikon/rotate = pilihan builder, asal satu gaya sama pill LIKE.
- `emoji`: pill LIKE → klik → LIKED sama persis, terus di posisi stiker (`PILL_X`, `STICKER_Y`, `STICKER_SIZE`) emoji gede: `<Lottie>` kalau `emojiSrc` ke-load, selain itu teks karakter `scene.emoji` (font sistem). Pop masuk pakai gerak stiker, **tanpa fade-out**, tahan sampai frame terakhir scene.

- [ ] **Step 1: Tulis ulang `remotion/tests/faktacuil-cta.cjs` (merah)**

Stub modul `@remotion/lottie` (lottie-web butuh DOM) sama kayak stub `fonts.ts`, misalnya override `Module._load` buat request itu → `{Lottie: () => null}`. Scene dasar sama kayak sekarang (`from: 0`, `durationInFrames: 150`, cue like di 10). Assertion:

```js
// lucky: stiker tampil di frame 40, format ikut scene, posisi akhir top 1030px
assert.match(markup({format: 'lucky', theme: 'shark'}, 40), /data-cta-sticker="true" data-cta-format="lucky"/);
// subscribe: cue subscribe di 50 → pill SUBSCRIBE di 55, SUBSCRIBED di 64 (50 + 12 + 2), stiker tetap ada
const sub = {format: 'subscribe', theme: 'shark', cues: [...base.cues, {kind: 'subscribe', from: 50, word: 'subscribe'}]};
assert.match(markup(sub, 55), /data-cta-pill="subscribe"[^>]*>[\s\S]*SUBSCRIBE</);
assert.match(markup(sub, 64), /SUBSCRIBED/);
assert.match(markup(sub, 64), /data-cta-sticker="true"/);
// emoji: tanpa emojiSrc → statis, ada karakternya, nggak ada stiker, dan masih tampil penuh di frame terakhir
const emo = {format: 'emoji', emoji: '🍯'};
assert.match(markup(emo, 40), /data-cta-emoji="static"[\s\S]*🍯/);
assert.doesNotMatch(markup(emo, 40), /data-cta-sticker/);
assert.match(markup(emo, 149), /data-cta-emoji="static"[^>]*opacity:\s?1[;"]/);
// format lama udah nggak ada di source
assert.doesNotMatch(fs.readFileSync(path.join(__dirname, '../src/FaktaCuilCta.tsx'), 'utf8'), /escalate|escape|reveal/);
console.log('faktacuil cta: OK');
```

Wrapper pytest di `tests/test_faktacuil_scene.py` (pola `tests/test_cta_scene.py::test_cta_visual_markup_cases_run_in_node`, skip kalau `node` nggak ada):

```python
def test_faktacuil_cta_markup_runs_in_node():
    result = subprocess.run([node, "tests/faktacuil-cta.cjs"], cwd=remotion_root, capture_output=True, text=True, encoding="utf-8")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "faktacuil cta: OK" in result.stdout
```

- [ ] **Step 2: Jalanin, pastiin gagal**

Run: `nvm use 22.23.1` lalu `cd remotion && node tests/faktacuil-cta.cjs`
Expected: AssertionError di kasus `subscribe`/`emoji`.

- [ ] **Step 3: Implement** `types.ts`, `Emojis.tsx`, `FaktaCuilCta.tsx`, prop `Sticker`, narrowing `ShortVideo.tsx` sesuai Interfaces.

- [ ] **Step 4: Jalanin test + tsc**

Run:
```bash
cd remotion && node tests/faktacuil-cta.cjs && node tests/cta-scene.cjs && npx tsc --noEmit -p .
cd .. && uv run pytest tests/test_faktacuil_scene.py tests/test_cta_scene.py -q
```
Expected: `faktacuil cta: OK`, `13 CTA visual cases passed`, tsc tanpa error, pytest PASS.

- [ ] **Step 5: Commit**

```bash
git add remotion/src/types.ts remotion/src/FaktaCuilCta.tsx remotion/src/Emojis.tsx remotion/src/FaktaCuilStickers.tsx remotion/src/ShortVideo.tsx remotion/tests/faktacuil-cta.cjs tests/test_faktacuil_scene.py
git commit -m "feat(remotion): subscribe pill and emoji cta for faktacuil"
```

---

### Task 6: Dokumen

**Files:**
- Modify: `.agents/skills/bikin-faktacuil/SKILL.md`
- Modify: `docs/DECISIONS.md` (append D-061)
- Modify: `docs/HANDOFF.md` (section FaktaCuil paling atas)

**Interfaces:** nggak ada kode.

- [ ] **Step 1: Update skill `bikin-faktacuil`**

Yang diganti/ditambah (bahasa Indonesia santai, gaya skill sekarang):
- "Yang beda dari top3": CTA opsional, 3 format + kuis, bukan lagi "CTA cuma like gimmick di tengah".
- **Struktur**: urutan per posisi CTA. CTA tengah (`lucky`/`subscribe`): hook → salah kaprah ≥1 → CTA 1–3 beat → jawaban ≥2 (kuis nggak dihitung). CTA akhir (`emoji`, kuis) atau tanpa CTA: nggak ada cek salah kaprah/jawaban.
- **Format CTA**: tabel 4 baris dari spec T7 (contoh kalimat + kata kunci wajib + visual), aturan kombinasi, contoh JSON `cta_scene`/`cta_quiz`, cara ngisi `answer` (hitung manual, `check-script` yang mastiin). Kalimat panjang dipecah: beat objek boleh tanpa "like" asal nyebut `muncul`; beat lead-in `emoji` boleh tanpa "like" asal nyebut `emoji`. Jangan pakai kata `muncul` di beat jawaban yang nempel ke CTA kalau blok CTA belum nyebut `muncul`.
- Hapus semua yang soal `question`/`reveal`/`escape`/`escalate`, `transform_word`, `comment_text`, `pick_cta_format`.
- Tabel aturan `check-script`: ganti F3/F5/F6/F7 sesuai tabel Task 3, tambah baris kuis dan baris queries.
- **Per beat** `queries`: 2–4 query English, nyebut hal yang keliatan di kalimat beat itu (subjek + aksi/objek), contoh "Padahal kardus itu sempit dan nggak empuk" → `cat squeezing into small cardboard box`, bukan `cat`. Beat CTA: query buat background yang cocok sama kalimat CTA. `queries_zh` nggak dipakai FaktaCuil (diabaikan).
- **Stiker baru** (objek nggak cocok sama 9 tema): STOP sebelum render, kerjain dulu: (1) komponen SVG 200x200 di `remotion/src/FaktaCuilStickers.tsx` + `case` di `Sticker`, (2) literal di `StickerTheme` (`remotion/src/types.ts`), (3) literal di `FaktaCuilTheme` (`mayzfact/models.py`), (4) nama Indonesia di `THEME_NOUNS_ID` (`mayzfact/faktacuil.py`), (5) `uv run pytest tests/test_faktacuil_cta_v2.py`, `npx tsc --noEmit -p .`, `npx remotion still` buat ngecek gambarnya, (6) commit. Top3 nggak ikut berubah.
- Langkah 5–7 (timeline): visual tiap format (lucky/subscribe/emoji), scene tengah berhenti di shot jawaban pertama, scene akhir sampai video selesai, emoji Lottie Noto atau statis kalau Lottie-nya nggak ada (log `PERINGATAN`).
- Checkpoint naskah: Akmal ngecek emoji cocok sama kalimat ("emoji madu" ↔ 🍯), code nggak ngecek.

- [ ] **Step 2: Tambah D-061 di `docs/DECISIONS.md`** (format D-059: Status, Masalah, Keputusan, Pengaman, Verifikasi, Authority). Isi: CTA FaktaCuil opsional; format `lucky`/`subscribe`/`emoji` + `cta_quiz`; format lama ditolak dengan pesan, file dibiarin; deteksi blok pakai kata penghubung `muncul`/`emoji`; `FaktaCuilTheme`/`StickerTheme` dipisah dari tema top3; emoji karakter bebas + fallback statis; `queries` English only (ASCII, ≥2). Authority: Akmal, spec 2026-11-21.

- [ ] **Step 3: Update `docs/HANDOFF.md`** — bullet `**2026-11-21:**` di section FaktaCuil: apa yang berubah (link D-061 + plan ini), yang udah dites, yang belum (render beneran per format, lihat Task 7), masalah terbuka (kalau ada). Hapus masalah terbuka lama soal `has_trigger`/`transform_word` karena kodenya udah nggak ada.

- [ ] **Step 4: Cek konsistensi**

Run: `grep -n "question\|reveal\|escape\|escalate\|transform_word\|comment_text\|pick_cta_format\|queries_zh" .agents/skills/bikin-faktacuil/SKILL.md`
Expected: cuma kemunculan yang bilang `queries_zh` diabaikan / format lama ditolak.

- [ ] **Step 5: Commit**

```bash
git add .agents/skills/bikin-faktacuil/SKILL.md docs/DECISIONS.md docs/HANDOFF.md
git commit -m "docs(faktacuil): document cta v2 formats and sticker workflow"
```

---

### Task 7: Cek visual tiap format (tanpa commit)

**Files:** nggak ada perubahan repo. Semua file sementara di scratchpad.

- [ ] **Step 1: Siapin props per format**

Ambil `timeline.json` run FaktaCuil terakhir yang punya klip lengkap (misal `runs/xRdCrossVN1/`), copy ke scratchpad 4 kali, ganti `ctaScene` jadi bentuk Task 2 buat `lucky`, `subscribe` (tambah cue `subscribe`), `emoji` dengan `emojiSrc` (Lottie dari `assets/emoji/`), dan `emoji` tanpa `emojiSrc`. Varian tanpa CTA: hapus `ctaScene`. Jangan ubah file di `runs/`.

- [ ] **Step 2: Render still**

Run (Node 22, dari `remotion/`): `npx remotion still src/index.ts ShortVideo <scratch>/<format>.png --props=<scratch>/<format>.json --public-dir=../runs/<id> --frame=<frame>` di 3 titik per format: setelah klik like, saat stiker/emoji tampil, dan (subscribe) setelah klik SUBSCRIBE; emoji juga frame terakhir video.
Expected: pill/kursor/stiker/emoji kebaca, emoji statis nggak kosong, nggak ada error render. Laporin path PNG ke lead; ini input buat preview yang dikirim ke Akmal, bukan pengganti review Akmal.

---

## Self-Review

1. **Spec coverage:**
   - T4 keyword English: Task 3 (ASCII ≥2, `queries_zh` diabaikan di check, `zh` kosong di plan/brief), Task 6 (aturan nulis query).
   - T6 CTA opsional: Task 3 (schema + kecocokan beat↔`cta_scene`), Task 2 (tanpa scene/klik).
   - T7 format: Task 1 (deteksi), Task 2 (scene/klik), Task 3 (aturan + kombinasi + kuis read-only), Task 4 (Lottie), Task 5 (visual), Task 6 (stiker baru di skill).
   - T8 struktur: Task 3 (F4/F5 cuma tengah, kuis bukan jawaban).
   - Kompatibilitas run lama: Task 3 (`load_script` + test run lama nggak kehapus). `links.json`/`plan.json` = branch brief.
   - Docs: Task 6. Bagian "kartu frame referensi" di skill = branch `fase-brief-v2`.
2. **Step scan:** tiap step test punya nama + assertion; step kode punya signature/aturan; algoritma yang nggak ketentu (blok CTA) ditulis.
3. **Type consistency:** `faktacuil_cta_indices`, `quiz_index`, `quiz_count`, `count_word` (Task 1) dipakai Task 3; `build_faktacuil_scene` + `cta_emoji_src` (Task 2) dipakai Task 4; `FAKTACUIL_SUBSCRIBE_CLICK = 12` ↔ `SUB_CLICK = 12` (Task 5); `FaktaCuilTheme` ↔ `StickerTheme` ↔ `THEME_NOUNS_ID` dijaga `test_theme_nouns_cover_every_sticker_theme` + `never` di `Sticker`.
4. **Review Focus:** 5 baris di atas, masing-masing punya test di task pemiliknya.
5. **Proportion:** isinya signature, aturan, test, dan perintah; body fungsi cuma buat algoritma blok CTA.
