# Format FaktaCuil Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Nambah format video kedua `narration_mode: "faktacuil"` (Shorts fakta bahasa Indonesia, channel FaktaCuil) dari naskah sampai upload, tanpa ngubah perilaku top3.

**Architecture:** Semua logika murni FaktaCuil (aturan naskah, detektor CTA Indonesia, rentang kata, objek tema) masuk modul baru `mayzfact/faktacuil.py`. Step lain dapat cabang `if mode == "faktacuil"` di titik yang emang beda (check-script, settings TTS, plan, scene CTA, timeline, BGM, caption Remotion, upload/slot). Top3 dijaga test golden yang dibikin sebelum kode apa pun diubah.

**Tech Stack:** Python 3.12 + pydantic + pytest (`uv`), Remotion 4.0.538 (React, TypeScript), `@remotion/google-fonts` (udah ada), ElevenLabs API, YouTube Data API v3.

**Spec:** `docs/superpowers/specs/2026-11-10-faktacuil-format-design.md`. Baca dulu bagian 5 (kontrak + aturan F1–F11) dan bagian 6 (perubahan per step). Laporan riset T8 ada di luar repo: `E:\APROJECT\mayzfact-refs\faktacuil\LAPORAN-T8-format-faktabor-zonag2v.md`.

> **Catatan pasca-implementasi (2026-11-10).** Plan ini ditulis sebelum Akmal jawab Q1–Q8 dan sebelum sampel voice diukur. Yang dibangun beda dari draft:
> - Voice default **Eric** `cjVigY5qzO86Huf0OWal` (bukan `""`), dan FaktaCuil juga support VoiceStudio lewat `faktacuil_tts_provider` / `faktacuil_voicestudio_voice` / `faktacuil_voicestudio_instruct` (Task 6).
> - `faktacuil_max_shot_seconds = 2.0` (Task 6, 7), `FAKTACUIL_RAW_WPS = 2.27` jadi rentang kata `faktacuil_word_range(1.1) = (62, 50, 74)`, bukan 69/55/82 (Task 5).
> - Slot 12.00/18.00 WIB maksimal 2 per hari (Task 12). BGM Bully "Welcome to Bullworth" (117,5 BPM), lokal gitignored (Task 10).
> - Deviasi Task 12: `login` balikin token, `run_mode` melempar error kalau `script.json` rusak. Daftar lengkap di spec bagian 13.
> Task 6 dan Task 12 di bawah udah ditulis ulang/dikasih catatan sesuai itu; bagian lain cuma angka yang dikoreksi.

## Global Constraints

- Top3 nggak boleh berubah perilaku. File `tests/golden/*.json` dari Task 1 nggak boleh di-regenerate di task lain.
- Jangan jalanin TTS beneran, render, upload, brief, atau download apa pun. Semua test pakai fake/monkeypatch. Generate sampel voice beneran = lead (Task 2).
- Jangan sentuh `runs/`, `.env`, `flow.svg`, `sources/`, `browser-profiles/`. Jangan print isi secret.
- Nggak nambah dependency Python/npm.
- Komentar kode bahasa Indonesia santai, 1 baris, cuma alasan/constraint (aturan `AGENTS.md` + `CLAUDE.md`).
- Pesan `check-script` bahasa Inggris (biar bisa ditempel ke agent mana pun), pesan `PipelineError` lain bahasa Indonesia santai, sama kayak kode sekarang.
- Commit per task, Conventional Commits, bahasa Inggris, 1 baris, tanpa body, tanpa trailer `Co-Authored-By`.
- Cek tiap task: `uv run pytest -q` (baseline: 688 lolos, 1 gagal `tests/test_cta_scene.py::test_cta_visual_markup_cases_run_in_node` karena `remotion/node_modules` belum ada, 3 skip) dan `uvx ruff check --select F,I <file yang diubah>`.
- Nilai tetap dari spec: warna caption `#ffffff` (`CAPTION_WHITE`), kuning brand `#FFC53D`; final 20–30 detik, target 25; `FAKTACUIL_RAW_WPS = 2.27` (dikalibrasi dari sampel Eric; draft awal 2.5); slot `(12, 18)` (final, maks 2 video per hari); env secret `YOUTUBE_TOKEN_JSON_FAKTACUIL`; folder BGM lokal `assets/channels/faktacuil/bgm/`.

## Review Focus

- Naskah FaktaCuil dengan kata "like" di body (bukan CTA), misal "rasanya like permen" → ikut ke-anchor sebagai blok CTA. Harapannya `check-script` nolak dengan pesan F3/F6 yang jelas, bukan scene CTA muncul di tempat aneh. Test: Task 4 `test_like_word_outside_cta_makes_block_non_contiguous`.
- `transform_word` muncul juga di hook ("Kenapa warnanya berubah?"). Harapannya cuma beat di blok CTA yang dihitung transform. Test: Task 5 `test_transform_word_in_hook_is_not_cta`.
- `youtube.json` lama tanpa `channel` + FaktaCuil di jam yang sama → slot MayzFact nggak keblok, slot FaktaCuil nggak keblok MayzFact. Test: Task 12 `test_slots_are_separate_per_channel`.
- Upload FaktaCuil dengan token akun yang salah → berhenti sebelum `videos().insert`. Test: Task 12 `test_faktacuil_upload_refuses_wrong_channel`.
- Folder BGM FaktaCuil berisi file non-audio (misal `README.txt`) → diabaikan, fallback `main.mp3`. Test: Task 10 `test_faktacuil_bgm_ignores_non_audio_files`.

---

## Urutan dan pembagian

Kerjain berurutan di satu branch `fase-faktacuil-format`. Task 1 wajib pertama. Task 2 (sampel voice) dan Task 13 (skill) boleh dikerjain implementer lain kapan aja setelah Task 1, karena file-nya beda. Sisanya urut karena interface-nya nyambung (3 → 4 → 5 → 6 → 7 → 8 → 9 → 10 → 11), Task 12 (upload) bebas setelah Task 3.

File rawan conflict: `mayzfact/config.py` (Task 6, 12), `mayzfact/cli.py` (Task 2, 12), `mayzfact/pipeline.py` (Task 6, 9), `AGENTS.md` + `docs/*` (Task 13, 14).

---

### Task 1: Golden top3

**Files:**
- Create: `tests/test_top3_golden.py`, `tests/golden/top3_timeline_scene.json`, `tests/golden/top3_timeline_fixture.json`, `tests/golden/top3_check_script.json`

**Interfaces:**
- Produces: golden yang dipakai semua task berikutnya buat mastiin top3 nggak berubah.

- [ ] **Step 1: Tulis test golden + generator**

```python
# tests/test_top3_golden.py
GOLDEN = Path(__file__).parent / "golden"

def _scene_timeline():
    from tests.test_cta_scene import timeline_fixture
    script, alignment, clips = timeline_fixture(24)
    return build_timeline(clips, 24, .5, script=script, alignment=alignment,
                          audio={"bgm": "audio/bgm/mystery.mp3", "bgm_main": "audio/bgm/main.mp3",
                                 "sfx": {k: f"audio/sfx/{k}.mp3" for k in
                                         ["hook", "number", "subject", "cut", "click", "hook_cut", "item_reveal", "extra_a"]}},
                          log=lambda _: None)

def _fixture_timeline():
    script = top3_script().model_dump()
    alignment = fake_alignment(script_text(script["beats"]), 38.5)
    times = beat_timings([b["text"] for b in script["beats"]], alignment, 38.5)
    clips = {"shots": [dict(file=f"clips/shot_{i}.mp4", kind="video", start_s=t["start_s"], end_s=t["end_s"],
                            width=1080, height=1920, beat=i) for i, t in enumerate(times)]}
    return build_timeline(clips, 38.5, .5, script=script, alignment=alignment, log=lambda _: None)

def _check_messages():
    cases = {"valid": top3_script(), "playful": playful_script(), "multi": _multi_rule_invalid()}
    return {name: check_script(s, SOURCE_TEXT)[0] for name, s in cases.items()}

CASES = {"top3_timeline_scene.json": _scene_timeline, "top3_timeline_fixture.json": _fixture_timeline,
         "top3_check_script.json": _check_messages}

@pytest.mark.parametrize("name", CASES)
def test_top3_output_matches_golden(name):
    assert CASES[name]() == json.loads((GOLDEN / name).read_text(encoding="utf-8"))
```

`_multi_rule_invalid()`: `top3_script()` yang semua beat-nya `media="video"`, beat 2 dapat 11+ kata, dan beat 3 `queries=[]`. Case ini gagal di banyak aturan sekaligus, buat jagain urutan pesan top3.

Tambah blok `if __name__ == "__main__":` yang nulis tiap `CASES[name]()` ke `GOLDEN / name` (`json.dumps(..., indent=2, ensure_ascii=False)`). Kalau `playful_script()` ngelempar error di fixture, ganti dengan varian valid lain yang udah dipakai di `tests/test_top3_review_regressions.py`.

- [ ] **Step 2: Generate golden dari kode sekarang (sebelum kode lain diubah)**

Run: `uv run python -m tests.test_top3_golden`
Expected: 3 file di `tests/golden/`. Cek `top3_timeline_scene.json` punya key `ctaScene`, `countdown` 3 item, `sfx` nggak kosong.

- [ ] **Step 3: Run test**

Run: `uv run pytest tests/test_top3_golden.py -v`
Expected: 3 PASS.

- [ ] **Step 4: Commit**

```bash
git add tests/test_top3_golden.py tests/golden
git commit -m "test: pin top3 timeline and script check output"
```

---

### Task 2: CLI sampel voice (`mayzfact voice-sample`)

Implementer cuma bikin CLI + test pakai fake. **Jangan jalanin ke ElevenLabs beneran.** Lead yang jalanin 3x setelah Akmal ngasih 3 voice ID (spec Q1).

**Files:**
- Create: `mayzfact/faktacuil.py` (cuma konstanta di task ini)
- Modify: `mayzfact/cli.py` (parser + handler baru)
- Test: `tests/test_voice_sample.py`

**Interfaces:**
- Produces: `mayzfact.faktacuil.VOICE_SAMPLE_TEXT_ID: str` (teks persis dari spec bagian 8), `mayzfact.faktacuil.FAKTACUIL_RAW_WPS: float = 2.5`, `mayzfact.cli.VOICE_SAMPLE_DIR = CACHE_DIR / "voice-samples"`.

- [ ] **Step 1: Tulis test yang gagal**

```python
def test_voice_sample_writes_mp3_and_reports_tempo(monkeypatch, tmp_path, capsys):
    calls = []
    class Fake:
        def __init__(self, keys, voice_id, model_id, client, stability=None, delivery_tag=""):
            calls.append((voice_id, model_id, stability, delivery_tag))
        def synthesize(self, text):
            assert text == VOICE_SAMPLE_TEXT_ID
            return b"ID3fake", {}
    monkeypatch.setattr(cli, "ElevenLabsTTS", Fake)
    monkeypatch.setattr(cli, "VOICE_SAMPLE_DIR", tmp_path)
    monkeypatch.setattr(cli, "audio_duration", lambda path: 16.0)
    monkeypatch.setattr(cli, "load_settings", lambda: Settings(elevenlabs_api_keys=("k",)))
    assert cli.main(["voice-sample", "VOICE123", "--name", "cewek-1"]) == 0
    assert (tmp_path / "cewek-1.mp3").read_bytes() == b"ID3fake"
    assert calls == [("VOICE123", "eleven_v3", 0.5, "")]
    out = capsys.readouterr().out
    assert "kata/detik" in out and f"{len(words(VOICE_SAMPLE_TEXT_ID)) / 16.0:.2f}" in out

def test_voice_sample_refuses_to_overwrite(monkeypatch, tmp_path, capsys):
    (tmp_path / "cewek-1.mp3").write_bytes(b"old")
    monkeypatch.setattr(cli, "VOICE_SAMPLE_DIR", tmp_path)
    monkeypatch.setattr(cli, "ElevenLabsTTS", lambda *a, **k: pytest.fail("nggak boleh request"))
    monkeypatch.setattr(cli, "load_settings", lambda: Settings(elevenlabs_api_keys=("k",)))
    assert cli.main(["voice-sample", "VOICE123", "--name", "cewek-1"]) == 1
    assert (tmp_path / "cewek-1.mp3").read_bytes() == b"old"

def test_voice_sample_rejects_unsafe_name(monkeypatch, tmp_path):
    monkeypatch.setattr(cli, "VOICE_SAMPLE_DIR", tmp_path)
    monkeypatch.setattr(cli, "load_settings", lambda: Settings(elevenlabs_api_keys=("k",)))
    assert cli.main(["voice-sample", "VOICE123", "--name", "../x"]) == 1
```

- [ ] **Step 2: Run, pastiin gagal**

Run: `uv run pytest tests/test_voice_sample.py -v`
Expected: FAIL (`invalid choice: 'voice-sample'` / import error).

- [ ] **Step 3: Implement**

- `mayzfact/faktacuil.py`: docstring modul + `VOICE_SAMPLE_TEXT_ID` (teks spec bagian 8 persis) + `FAKTACUIL_RAW_WPS = 2.5` (komentar: asumsi, dikalibrasi dari sampel yang dipilih Akmal).
- `mayzfact/cli.py`: subcommand `voice-sample <voice_id> --name <slug>`; import `ElevenLabsTTS` (udah di-import modul ini lewat `list_voices`? kalau belum, import di level modul biar bisa di-monkeypatch) dan `audio_duration` dari `mayzfact.ffmpeg` di level modul. `--name` wajib cocok `^[a-z0-9-]{1,40}$`, selain itu `PipelineError`. File udah ada → `PipelineError("voice-sample", "... udah ada, sampel nggak di-generate ulang")`. Provider: `ElevenLabsTTS(settings.elevenlabs_api_keys, voice_id, "eleven_v3", make_client(), stability=0.5, delivery_tag="")`. Tulis pakai `write_bytes_atomic`. Print: path, `len(VOICE_SAMPLE_TEXT_ID)` karakter, durasi, dan `kata/detik mentah: {n/durasi:.2f}` dengan `n = len(words(VOICE_SAMPLE_TEXT_ID))`.

- [ ] **Step 4: Run test + full suite**

Run: `uv run pytest tests/test_voice_sample.py -v && uv run pytest -q`
Expected: 3 PASS; full suite sama kayak baseline + test baru.

- [ ] **Step 5: Commit**

```bash
git add mayzfact/faktacuil.py mayzfact/cli.py tests/test_voice_sample.py
git commit -m "feat: add voice-sample command for FaktaCuil voice pick"
```

**Setelah merge (lead, bukan implementer):** jalanin `uv run mayzfact voice-sample <id> --name <slug>` 3x dengan voice dari Akmal, kirim 3 mp3 + kata/detik ke Akmal. Hasil pilihan masuk Task 6 (voice ID) dan `FAKTACUIL_RAW_WPS`.

---

### Task 3: Schema + `load_script` nerima `faktacuil`

**Files:**
- Modify: `mayzfact/models.py:17-25` (Beat), `:34` (narration_mode)
- Modify: `mayzfact/steps/script.py:136-141` (`load_script`)
- Create: `tests/faktacuil_fixtures.py`
- Test: `tests/test_faktacuil_script.py`, update assert pesan di `tests/test_top3_script.py` kalau ada yang ngecek teks persis

**Interfaces:**
- Produces: `Beat.keyword: str = ""`; `Script.narration_mode: Literal["top3", "faktacuil"]`; `tests.faktacuil_fixtures.faktacuil_script(total_words: int = 69) -> Script` dan `tests.faktacuil_fixtures.SOURCE_TEXT_EN: str`.

- [ ] **Step 1: Tulis fixture + test**

`tests/faktacuil_fixtures.py`: naskah valid 9 beat dengan struktur spec: beat 0–1 hook (`"Kenapa kucing suka banget,"` / `"masuk ke kardus yang sempit?"`), beat 2–3 salah kaprah (`"Padahal kardus itu keras dan nggak empuk,"`, …), beat 4–5 CTA (`"Tapi coba tekan like dulu,"` / `"apakah like-mu berubah jadi madu?"`), beat 6–8 jawaban (`"Ternyata …"`). `cta_scene=CtaScene(theme="honey", transform_word="berubah", comment_text="MADU")`. Foto di 2–3 beat non-CTA. `keyword` diisi di 2 beat non-CTA dengan kata yang ada di teksnya. Isi kata filler sampai `total_words` pakai pola yang sama kayak `tests/top3_fixtures.py:22-27`, cuma di beat non-CTA. `SOURCE_TEXT_EN`: 3–4 kalimat Inggris soal kucing dan kardus.

```python
def test_faktacuil_mode_loads(tmp_path):
    paths = RunPaths(tmp_path)
    write_json_atomic(paths.script_json, faktacuil_script().model_dump())
    assert load_script(paths).narration_mode == "faktacuil"

def test_unknown_mode_still_rejected_with_both_modes_named(tmp_path):
    paths = RunPaths(tmp_path)
    write_json_atomic(paths.script_json, {**top3_script().model_dump(), "narration_mode": "source"})
    with pytest.raises(PipelineError) as exc:
        load_script(paths)
    assert "narration_mode" in exc.value.message and '"top3"' in exc.value.message and '"faktacuil"' in exc.value.message

def test_keyword_defaults_empty():
    assert Beat(text="a", media="video", queries=["q"]).keyword == ""
```

- [ ] **Step 2: Run, pastiin gagal**

Run: `uv run pytest tests/test_faktacuil_script.py -v`
Expected: FAIL (validation error `narration_mode`).

- [ ] **Step 3: Implement**

- `Beat.keyword: str = ""` dengan komentar 1 baris.
- `narration_mode: Literal["top3", "faktacuil"]`.
- `load_script`: `if mode not in ("top3", "faktacuil")`; pesan: `script.json pakai format lama (narration_mode: {shown}). Pipeline sekarang cuma support narration_mode "top3" dan "faktacuil" (D-050, D-051). File run ini dibiarin apa adanya; bikin run baru pakai salah satu format itu.` Pesan `cta_scene` belum ada: ganti `Format top3` jadi `Format {mode}`.

- [ ] **Step 4: Run test + golden + full suite**

Run: `uv run pytest tests/test_faktacuil_script.py tests/test_top3_golden.py tests/test_top3_script.py tests/test_top3_review_regressions.py -v && uv run pytest -q`
Expected: PASS. Kalau test lama ngecek teks pesan lama persis, update assert-nya ke teks baru (assert `narration_mode` tetap ada).

- [ ] **Step 5: Commit**

```bash
git add mayzfact/models.py mayzfact/steps/script.py tests/faktacuil_fixtures.py tests/test_faktacuil_script.py tests/test_top3_script.py
git commit -m "feat: accept faktacuil narration mode in script schema"
```

---

### Task 4: Detektor CTA Indonesia + blok CTA

**Files:**
- Modify: `mayzfact/faktacuil.py`
- Modify: `mayzfact/narration.py` (tambah dispatcher, `cta_beat_indices` nggak diubah)
- Test: `tests/test_faktacuil_cta.py`

**Interfaces:**
- Consumes: `mayzfact.cta.clean`, `SUBSCRIBE`.
- Produces:
  - `ID_LIKE_VERBS = {"tekan", "pencet", "klik", "kasih", "tekanlah"}`, `ID_COMMENT = {"komen", "komentar", "comment"}`
  - `id_like_positions(tokens: list[str]) -> list[int]`: index token `like` yang jadi ajakan
  - `id_like_begin(tokens: list[str], j: int) -> int`: index awal frasa ajakan (mundur ke kata kerja, lalu `coba`)
  - `faktacuil_cta_indices(beats: list) -> list[int]` (beat dict atau `Beat`)
  - `mayzfact.narration.cta_indices(script: dict | Script) -> list[int]`: `faktacuil_cta_indices` kalau mode `faktacuil`, selain itu `cta_beat_indices(beats)`

- [ ] **Step 1: Tulis test**

```python
@pytest.mark.parametrize("text,expected", [
    ("Tapi coba tekan like dulu,", [3]),
    ("tekan tombol like sekarang", [2]),
    ("pencet like ya", [1]),
    ("apakah like-mu berubah jadi madu?", []),
    ("aku like video ini", []),
    ("like video ini", []),
])
def test_id_like_positions(text, expected):
    assert id_like_positions(text.split()) == expected

def test_like_begin_walks_back_to_coba():
    tokens = "Tapi coba tekan like dulu,".split()
    assert id_like_begin(tokens, 3) == 1

def test_cta_block_includes_gimmick_question():
    assert faktacuil_cta_indices(faktacuil_script().model_dump()["beats"]) == [4, 5]

def test_like_word_outside_cta_makes_block_non_contiguous():
    beats = faktacuil_script().model_dump()["beats"]
    beats[7]["text"] = "rasanya like permen buat kucing."
    assert faktacuil_cta_indices(beats) == [4, 5, 6, 7]  # anchor terakhir narik blok; validator yang nolak

def test_cta_indices_dispatch_keeps_top3():
    top = top3_script()
    assert cta_indices(top) == cta_beat_indices(top.beats)
    assert cta_indices(faktacuil_script()) == [4, 5]
```

- [ ] **Step 2: Run, pastiin gagal** — `uv run pytest tests/test_faktacuil_cta.py -v` → FAIL import.

- [ ] **Step 3: Implement** fungsi di atas sesuai aturan spec bagian 5 ("Blok CTA FaktaCuil", "Pemicu like Indonesia"). Anchor = beat yang punya token (`clean`) berawalan `like`, atau ada di `SUBSCRIBE | ID_COMMENT`. Blok = `range(anchor pertama, anchor terakhir + 1)`.

- [ ] **Step 4: Run test + golden** — `uv run pytest tests/test_faktacuil_cta.py tests/test_top3_golden.py -v` → PASS.

- [ ] **Step 5: Commit** — `git commit -m "feat: detect Indonesian like CTA for faktacuil"` (add `mayzfact/faktacuil.py mayzfact/narration.py tests/test_faktacuil_cta.py`).

---

### Task 5: Aturan naskah FaktaCuil di `check-script`

**Files:**
- Modify: `mayzfact/faktacuil.py`
- Modify: `mayzfact/steps/script.py:33-122` (`narration_word_range`, `check_script`)
- Test: `tests/test_faktacuil_script.py`

**Interfaces:**
- Consumes: Task 4.
- Produces:
  - `faktacuil_word_range(video_speed: float) -> tuple[int, int, int]` → `(round(25*k), ceil(20*k), floor(30*k))` dengan `k = video_speed * FAKTACUIL_RAW_WPS`; panggil `validate_video_speed` dulu.
  - `THEME_NOUNS_ID: dict[str, tuple[str, ...]]` (tabel spec bagian 5).
  - `faktacuil_problems(script: Script) -> list[str]`: F1–F10 (pesan persis dari tabel spec). F11 (panjang) dicek di `check_script`.
  - `mayzfact.steps.script._beat_problems(script: Script) -> list[str]`: foto 15–45%, beat kosong, ≤10 kata, queries. Dipakai top3 (di posisi yang sama kayak sekarang) dan FaktaCuil. Overlap tetap di akhir `check_script` buat dua mode.
  - `faktacuil_word_range` baca `FAKTACUIL_RAW_WPS` pas dipanggil (bukan default argumen), biar bisa di-monkeypatch.

- [ ] **Step 1: Tulis test**

```python
def test_valid_faktacuil_script_passes():
    assert check_script(faktacuil_script(), SOURCE_TEXT_EN)[0] == []

def test_word_range_at_default_speed():
    assert faktacuil_word_range(1.1) == (62, 50, 74)  # tempo 2.27 (draft awal 2.5 = (69, 55, 82))

@pytest.mark.parametrize("mutate,needle", [
    (lambda b: b[0].update(text="Kucing suka masuk kardus,"), 'open with "Kenapa"'),
    (lambda b: b[4].update(text="Tapi coba tekan like dan subscribe,"), "must not ask to subscribe"),
    (lambda b: b[5].update(text="apakah like-mu berubah jadi singa?"), "does not match the narrated transformation"),
    (lambda b: b[2].update(point=True), "point=false"),
    (lambda b: b[3].update(emoji="😱", emoji_word="keras"), "empty emoji fields"),
    (lambda b: b[2].update(keyword="gajah"), "keyword"),
    (lambda b: b[1].update(text="Number one, kardus."), '"Number N," countdown'),
])
def test_faktacuil_rules(mutate, needle):
    data = faktacuil_script().model_dump(); mutate(data["beats"])
    assert any(needle in p for p in check_script(Script(**data), SOURCE_TEXT_EN)[0])

def test_cta_needs_misconception_before_and_two_answers_after():
    data = faktacuil_script().model_dump()
    data["beats"] = data["beats"][:2] + data["beats"][4:7]   # buang salah kaprah + 1 jawaban
    problems = check_script(Script(**data), SOURCE_TEXT_EN)[0]
    assert any("misconception" in p for p in problems) and any("two answer beats" in p for p in problems)

def test_transform_word_in_hook_is_not_cta():
    data = faktacuil_script().model_dump()
    data["beats"][0]["text"] = "Kenapa warna kucing bisa berubah,"
    assert check_script(Script(**data), SOURCE_TEXT_EN)[0] == []

def test_word_count_outside_range_reports_bounds(monkeypatch):
    monkeypatch.setattr("mayzfact.faktacuil.FAKTACUIL_RAW_WPS", 2.0)   # rentang jadi 44-66, fixture 69 kata
    assert any("between 44 and 66" in p for p in check_script(faktacuil_script(), SOURCE_TEXT_EN)[0])

def test_hyphenated_keyword_allowed():
    data = faktacuil_script().model_dump()
    data["beats"][6]["text"] = "Ternyata kardus mirip sarang kupu-kupu,"; data["beats"][6]["keyword"] = "kupu-kupu"
    assert not any("keyword" in p for p in check_script(Script(**data), SOURCE_TEXT_EN)[0])

def test_top3_rejects_keyword():
    s = top3_script(); s.beats[2].keyword = "water"
    assert "Top 3 beats must not set keyword." in check_script(s, SOURCE_TEXT)[0]
```

(Kalau teks fixture beda, sesuaikan index beat; struktur fixture dari Task 3.)

- [ ] **Step 2: Run, pastiin gagal** — FAIL (aturan top3 dipakai buat FaktaCuil).

- [ ] **Step 3: Implement**
  - `check_script`: ekstrak cek foto/beat/queries ke `_beat_problems` tanpa ngubah urutan pesan top3 (golden case `multi` harus tetap PASS). Di awal fungsi: kalau `script.narration_mode == "faktacuil"` → `faktacuil_problems(script)` + cek panjang (`narration_word_range`) + `_beat_problems` + overlap, return. Top3: tambah cek `keyword` di akhir daftar.
  - `narration_word_range`: `approved_word_count` tetap duluan; lalu cabang FaktaCuil → `faktacuil_word_range`.
  - F7 regex: `\bjadi\s+(?:seekor\s+|sebuah\s+)?(?:<frasa1>|<frasa2>)\b` di beat blok CTA yang ngandung `transform_word` (kata utuh) dan diakhiri `?`.

- [ ] **Step 4: Run test + golden + full suite** — `uv run pytest tests/test_faktacuil_script.py tests/test_top3_golden.py -v && uv run pytest -q` → PASS.

- [ ] **Step 5: Commit** — `git commit -m "feat: add faktacuil script rules to check-script"`.

---

### Task 6: Voice FaktaCuil di Settings + pipeline

**Files:**
- Modify: `mayzfact/config.py` (Settings), tambah `settings_for_mode`; `load_settings` nerima field `faktacuil_*` di `settings.local.json`
- Modify: `mayzfact/pipeline.py` (`check_voice`, `real_deps().tts`, `run_pipeline`, `_require_script`)
- Test: `tests/test_faktacuil_pipeline.py`

**Interfaces (versi yang dibangun, keputusan Akmal 2026-11-10 ngalahin draft "FaktaCuil cuma ElevenLabs, voice kosong"):**
- Produces: `Settings.faktacuil_elevenlabs_voice_id = "cjVigY5qzO86Huf0OWal"` (Eric), `faktacuil_elevenlabs_delivery_tag = ""`, `faktacuil_tts_provider = "elevenlabs"`, `faktacuil_voicestudio_voice = ""`, `faktacuil_voicestudio_instruct = ""`, `faktacuil_max_shot_seconds = 2.0`, `settings_for_mode(settings, mode) -> Settings`.
- `settings_for_mode(s, "top3")` identity. `"faktacuil"` ganti `tts_provider`, `voicestudio_voice`, `voicestudio_instruct`, `elevenlabs_voice_id`, `elevenlabs_delivery_tag`, `hook_seconds=0.0`, `max_shot_seconds` dari field `faktacuil_*`. `tts_provider` global nggak kebawa.
- `__post_init__` nge-bump `video_speed` 1,1 → 1,15 kalau voicestudio: FaktaCuil voicestudio dapat 1,15; 1,15 hasil bump MayzFact voicestudio diturunin ke 1,1 buat FaktaCuil ElevenLabs.
- `_require_script` nolak FaktaCuil + voicestudio kalau `faktacuil_voicestudio_voice` kosong (pesan nyebut `settings.local.json`); provider selain elevenlabs/voicestudio ditolak di `run_pipeline`.
- `check_voice` FaktaCuil: label `FaktaCuil`, jendela 20–30 detik; top3 tetap 30–40 dan teks lognya sama persis.

- [x] **Step 1: Tulis test** (`tests/test_faktacuil_pipeline.py`): top3 identity; default Eric + field lain; swap voice/tag/hook/shot; voice id kosong berhenti sebelum provider dibikin (`faktacuil_elevenlabs_voice_id` di pesan); `tts_provider` global nggak bocor; FaktaCuil voicestudio pakai field `faktacuil_*`; `video_speed` (1,15 / 1,1 / override 1,2 kebawa); `_require_script` nolak dan nerima voicestudio; provider tak dikenal ditolak sebelum TTS; `check_voice` 20–30; `run_pipeline` manggil `settings_for_mode` sebelum `_require_script` dan `check_voice`; `real_deps().plan` baca `max_shot_seconds` + `hook_seconds` dari settings; `settings.local.json` nerima/nolak field `faktacuil_*`; field `faktacuil_*` bukan `ENV_FIELDS`.
- [x] **Step 2: Run, pastiin gagal.**
- [x] **Step 3: Implement** sesuai spec bagian 6 "tts".
- [x] **Step 4: Run** — `uv run pytest tests/test_faktacuil_pipeline.py tests/test_pipeline.py tests/test_config.py tests/test_top3_golden.py -v && uv run pytest -q` → PASS.
- [x] **Step 5: Commit** — `git commit -m "feat: per-mode voice, provider and shot settings for faktacuil"` (1043c0c).

---

### Task 7: Plan pakai blok CTA per mode

**Files:**
- Modify: `mayzfact/steps/plan.py:181-184`, `:196`
- Test: `tests/test_faktacuil_plan.py`

**Interfaces:**
- Consumes: `mayzfact.narration.cta_indices(script)` (Task 4).

- [ ] **Step 1: Tulis test** — `run_plan` dengan `faktacuil_script()` + `fake_alignment` + `cut_video` fixture (pola `tests/test_top3_plan.py:14-40`), `hook_seconds=0` (nilai dari `settings_for_mode`):

```python
assert [s["beat"] for s in plan["shots"] if s.get("auto_cta")] == [4, 5]   # semua shot beat CTA
assert all(s["keywords"] == {"en": [], "zh": []} and s["subject"] == "" for s in plan["shots"] if s.get("auto_cta"))
assert all(s["countdown"] is None and s["source_rank"] is None for s in plan["shots"])
assert any(g.get("auto_cta") for g in plan["groups"])
assert all(s["hook_segment"] is None for s in plan["shots"]) and plan["segments"] == []
```

(Kalau beat CTA kepecah jadi beberapa shot, assert-nya pakai `set`.)

- [ ] **Step 2: Run, pastiin gagal** (shot CTA FaktaCuil belum `auto_cta`).
- [ ] **Step 3: Implement** — ganti dua pemanggilan `cta_beat_indices(beats)` jadi `cta_indices(script)`.
- [ ] **Step 4: Run** — `uv run pytest tests/test_faktacuil_plan.py tests/test_top3_plan.py tests/test_plan.py -v` → PASS.
- [ ] **Step 5: Commit** — `git commit -m "feat: mark faktacuil CTA shots as auto CTA in plan"`.

---

### Task 8: Scene CTA FaktaCuil (`build_scene`)

**Files:**
- Modify: `mayzfact/cta_scene.py:12-76`
- Test: `tests/test_faktacuil_scene.py`

**Interfaces:**
- Consumes: `faktacuil_cta_indices`, `id_like_positions`, `id_like_begin` (Task 4).
- Produces: `build_scene` signature nggak berubah. Untuk mode `faktacuil`: `allowed = faktacuil_cta_indices(beats)`; `stop` = `from` entry pertama yang shot-nya `beat > max(allowed)` (fallback `total`); cue `like` cuma dari `id_like_positions`; `like_begin` dari `id_like_begin`; loop `bounds` (`cta_scene.py:49-58`) pakai `id_like_positions` + regex `transform_word`, bukan `cta_kinds`; nggak ada cue/stage `subscribe`/`comment`. Tambah juga fungsi kecil `faktacuil_cta_stop(shots, entries, allowed, total) -> int` di `cta_scene.py` biar Task 9 bisa pakai.

- [ ] **Step 1: Tulis test** — fixture `faktacuil_timeline_fixture(duration=25)` (pola `tests/test_cta_scene.py:169-177`, pakai `faktacuil_script()`):

```python
scene = build_scene(script, clips["shots"], entries, words, beat_of, [], total)
assert [s["kind"] for s in scene["stages"]] == ["like", "transform"]
assert {c["kind"] for c in scene["cues"]} == {"like", "transform"}
like_cue = next(c for c in scene["cues"] if c["kind"] == "like")
assert like_cue["word"].strip(",").lower() == "like"
assert scene["stages"][0]["from"] == to_frame(word_start("coba"))      # stage mulai di "coba"
answer_start = next(e["from"] for e, s in zip(entries, clips["shots"]) if s["beat"] == 6)
assert scene["from"] + scene["durationInFrames"] == answer_start      # berhenti pas jawaban mulai
```

Plus golden top3 tetap PASS.

- [ ] **Step 2: Run, pastiin gagal.**
- [ ] **Step 3: Implement** — cabang di 4 titik (spec R2). Kode top3 di jalur `else` nggak diubah urutannya.
- [ ] **Step 4: Run** — `uv run pytest tests/test_faktacuil_scene.py tests/test_cta_scene.py tests/test_top3_golden.py -v` → PASS (kecuali test node yang emang gagal di baseline).
- [ ] **Step 5: Commit** — `git commit -m "feat: build like-only CTA scene for faktacuil"`.

---

### Task 9: Timeline FaktaCuil + skip panah/emoji

**Files:**
- Modify: `mayzfact/steps/timeline.py` (`_captions` `:156-174`, `_sound` `:177-267`, `build_timeline` `:416-503`, fungsi baru `_faktacuil_cta`)
- Modify: `mayzfact/pipeline.py:321-333`
- Test: `tests/test_faktacuil_timeline.py`

**Interfaces:**
- Consumes: Task 8 (`faktacuil_cta_stop`), Task 4.
- Produces: root key `timeline["captionStyle"] = "faktacuil"` (cuma FaktaCuil); konstanta `CAPTION_KEYWORD = "#FFC53D"`; `_captions(..., keywords: dict[int, str] | None = None, beat_of: list[int] | None = None)` (top3 manggil tanpa argumen baru); `_sound(..., intro_sfx: bool = True)`.

- [ ] **Step 1: Tulis test**

```python
def test_faktacuil_timeline_shape():
    tl = build_timeline(clips, 25, .5, script=script, alignment=alignment, audio=AUDIO_ALL_SFX, log=lambda _: None)
    assert tl["captionStyle"] == "faktacuil"
    assert tl["countdown"] == [] and tl["overlays"] == [] and tl["emojis"] == []
    assert tl["intro"] is None and tl["flashes"] == [] and tl["transitions"] == []
    srcs = [s["src"] for s in tl["sfx"]]
    assert "audio/sfx/hook.mp3" not in srcs and "audio/sfx/hook_cut.mp3" not in srcs
    assert srcs.count("audio/sfx/click.mp3") == 1                     # 1 klik di kata like
    assert "audio/sfx/cut.mp3" in srcs

def test_faktacuil_caption_colors_only_keywords():
    tl = build_timeline(...)
    colored = {c["text"] for c in tl["captions"] if c["color"] != "#ffffff"}
    assert colored == {kw.upper() for kw in KEYWORDS_IN_FIXTURE}
    assert all(c["color"] in ("#ffffff", "#FFC53D") for c in tl["captions"])

def test_faktacuil_single_bgm_whole_video():
    tl = build_timeline(..., audio={"bgm": None, "bgm_main": "audio/bgm/main.mp3", "sfx": {}})
    assert tl["bgm"] == [{"src": "audio/bgm/main.mp3", "from": 0, "durationInFrames": tl["durationInFrames"],
                          "volume": 0.12, "fadeOutFrames": 30}]

def test_pipeline_skips_marks_and_overlay_for_faktacuil(tmp_path):
    # Deps fake: marks/overlay = pytest.fail; run step timeline dengan script faktacuil → nggak dipanggil
```

Kalau `_sound` cabang 1 BGM sekarang ngeluarin dict (bukan list), sesuaikan assert ke bentuk yang dikeluarin kode sekarang (`timeline.py:210-212`); jangan ubah bentuk itu.

- [ ] **Step 2: Run, pastiin gagal.**
- [ ] **Step 3: Implement** sesuai tabel spec bagian 6 "timeline":
  - mode dari `script.get("narration_mode")`;
  - caption: putih + kata `keyword` beat itu kuning, tanpa pewarnaan kata panjang/subjek;
  - CTA: `_faktacuil_cta` (like doang, `CTA_FRAMES["like"]`, `CTA_CLICK["like"]`, berhenti di `faktacuil_cta_stop`);
  - `_sound(..., intro_sfx=False)` nggak nambah `hook`; `hook_end` dikirim 0;
  - `intro: None`; `captionStyle`;
  - `pipeline._run_step` timeline: kalau mode FaktaCuil, `marks`/`overlays` = `None` tanpa manggil deps.
- [ ] **Step 4: Run** — `uv run pytest tests/test_faktacuil_timeline.py tests/test_timeline.py tests/test_top3_timeline.py tests/test_top3_golden.py tests/test_pipeline.py -v && uv run pytest -q` → PASS.
- [ ] **Step 5: Commit** — `git commit -m "feat: faktacuil timeline with keyword captions and no decorations"`.

---

### Task 10: BGM lokal FaktaCuil

**Files:**
- Modify: `mayzfact/audio.py:105-155` (`prepare_audio`)
- Modify: `.gitignore`
- Test: `tests/test_audio.py` (tambah test)

**Interfaces:**
- Produces: `FAKTACUIL_BGM_DIR = PROJECT_ROOT / "assets" / "channels" / "faktacuil" / "bgm"`; `prepare_audio(..., faktacuil_bgm_dir: Path = FAKTACUIL_BGM_DIR)` (parameter biar bisa dites).

- [ ] **Step 1: Tulis test**

```python
def test_faktacuil_bgm_uses_local_song(tmp_path):
    local = tmp_path / "fc"; local.mkdir(); (local / "lagu.mp3").write_bytes(b"x")
    out = prepare_audio(paths, {"narration_mode": "faktacuil", "beats": []}, bgm_dir=BGM, sfx_dir=SFX,
                        client=client, log=logs.append, faktacuil_bgm_dir=local)
    assert out["bgm"] is None and out["bgm_main"] == "audio/bgm/lagu.mp3"
    assert read_json(paths.root / "audio.json") == {"bgm": None, "bgm_main": "lagu.mp3"}

def test_faktacuil_bgm_falls_back_to_main(tmp_path):  # folder nggak ada → main.mp3 + log "sementara pakai main.mp3"
def test_faktacuil_bgm_ignores_non_audio_files(tmp_path):  # cuma README.txt → fallback main.mp3
def test_top3_bgm_unchanged(tmp_path):  # mode top3 → bgm mystery + bgm_main main, sama kayak sebelumnya
```

Pakai `client` fake / `sfx.json` kosong biar nggak ada request (pola test yang udah ada di `tests/test_audio.py`).

- [ ] **Step 2: Run, pastiin gagal.**
- [ ] **Step 3: Implement** sesuai spec bagian 6 "BGM". Pakai `list_bgm()` buat nyaring ekstensi. `.gitignore` tambah `assets/channels/faktacuil/bgm/` dengan komentar 1 baris (lagu berhak cipta, repo public).
- [ ] **Step 4: Run** — `uv run pytest tests/test_audio.py -v` → PASS; `git check-ignore assets/channels/faktacuil/bgm/x.mp3` → path ke-print.
- [ ] **Step 5: Commit** — `git commit -m "feat: single local BGM for faktacuil videos"`.

---

### Task 11: Caption Fredoka di Remotion

**Files:**
- Modify: `remotion/src/fonts.ts`, `remotion/src/types.ts:107-125`, `remotion/src/ShortVideo.tsx:15,45`, `remotion/src/Captions.tsx`
- Test: typecheck + still manual

**Interfaces:**
- Consumes: `timeline.captionStyle` (Task 9).
- Produces: `TimelineProps.captionStyle?: 'faktacuil'`; `export const {fontFamily: FREDOKA}` dari `@remotion/google-fonts/Fredoka` weight `'700'`, subset `latin`; `Captions` prop `style?: 'faktacuil'`.

- [ ] **Step 1: Setup** — `nvm use 22.23.1 && cd remotion && npm ci`. Setelah ini `tests/test_cta_scene.py::test_cta_visual_markup_cases_run_in_node` harus ikut lolos.
- [ ] **Step 2: Still top3 sebelum diubah** — pakai `tests/golden/top3_timeline_scene.json` sebagai props: `npx remotion still src/index.ts ShortVideo out/caption-top3-before.png --props=../tests/golden/top3_timeline_scene.json --frame=<frame caption pertama>`. (Kalau asset audio/klip nggak ada dan still gagal, pakai props kecil buatan sendiri di `out/` yang cuma punya `captions`; `out/` nggak di-commit.)
- [ ] **Step 3: Implement** sesuai spec bagian 6 "Remotion": pop scale 0.6 → 1.12 → 1 dalam 5 frame, opacity 0 → 1 dalam 2 frame, tanpa blur; Fredoka 700; outline hitam + shadow; `top: 75%`; font size turun buat kata panjang biar muat 960 px, 1 baris. Jalur tanpa `style` nggak diubah sama sekali.
- [ ] **Step 4: Verifikasi**
  - `npx tsc --noEmit -p .` → bersih.
  - Still top3 lagi → `out/caption-top3-after.png` identik sama before (bandingin pakai `ffmpeg -i a -i b -filter_complex psnr -f null -` → `inf` atau `average:inf`).
  - Still FaktaCuil pakai props dengan `captionStyle: "faktacuil"`, caption `MEMBERSIHKANNYA` dan `AMAN` (kuning) di frame +0, +2, +5 → kirim 3 PNG ke lead buat dicek visual.
  - `uv run pytest -q` → semua lolos termasuk test node.
- [ ] **Step 5: Commit** — `git commit -m "feat: Fredoka pop captions for faktacuil"` (cuma `remotion/src/*`).

---

### Task 12: Upload, login, dan slot FaktaCuil

**Files:**
- Modify: `mayzfact/config.py` (Settings + `ENV_FIELDS`), `mayzfact/youtube.py:83-87,144-164,222-261`, `mayzfact/cli.py:27-29,118-156`
- Test: `tests/test_faktacuil_upload.py`

**Interfaces:**
- Produces:
  - `Settings.youtube_token_json_faktacuil: str = field(default="", repr=False)`, env `YOUTUBE_TOKEN_JSON_FAKTACUIL`
  - `Settings.faktacuil_slot_hours: tuple[int, ...] = (12, 18)`, `Settings.faktacuil_youtube_channel_id: str = ""`
  - `youtube.login(client_secret_json, env_file, token_env: str = "YOUTUBE_TOKEN_JSON") -> None`
  - `youtube.channel_info(service) -> tuple[str, str]` (id, judul) dari `channels().list(part="id,snippet", mine=True)`
  - `youtube.taken_slots(runs_dir: Path, channel: str = "mayzfact") -> list[datetime]`
  - `youtube.next_slot(taken, now, hours: tuple[int, ...] = SLOT_HOURS) -> datetime`
  - `youtube.upload_video(..., channel: str = "mayzfact", expected_channel_id: str = "")`
  - `youtube.run_mode(paths: RunPaths) -> str`: `narration_mode` dari `script.json` mentah, default `"top3"` kalau file/field nggak ada
  - CLI: `login youtube [--channel faktacuil]`, `next-slot [--channel faktacuil]`

**Deviasi dari draft ini (dibangun beda, spec bagian 13):**
- `youtube.login(..., token_env)` balikin token (`-> str`), bukan `None`, biar CLI bisa nge-print channel tanpa baca `.env`.
- `channel_info` pakai `part="id,snippet"`.
- `run_mode` melempar `PipelineError` kalau `script.json` rusak atau mode di luar `top3`/`faktacuil`; tanpa file = `top3`.
- `faktacuil_slot_hours = (12, 18)` itu final (Akmal 2026-11-10: maksimal 2 video per hari), bukan kandidat. `next_slot` ngurutin jam.
- `tests/test_config.py::test_env_holds_only_secrets` ikut diubah (set `ENV_FIELDS` nambah `YOUTUBE_TOKEN_JSON_FAKTACUIL`), jadi "test lama nggak diubah" nggak berlaku buat satu test itu.

- [ ] **Step 1: Tulis test**

```python
def test_slots_are_separate_per_channel(tmp_path):
    write(tmp_path / "a/youtube.json", {"publish_at": "2026-11-12T12:00:00+07:00", "channel": "faktacuil"})
    write(tmp_path / "b/youtube.json", {"publish_at": "2026-11-12T01:00:00+07:00"})
    assert youtube.taken_slots(tmp_path, "faktacuil") == [wib("2026-11-12 12:00")]
    assert youtube.taken_slots(tmp_path) == [wib("2026-11-12 01:00")]
    now = wib("2026-11-11 23:00")
    assert youtube.next_slot(youtube.taken_slots(tmp_path, "faktacuil"), now, hours=(12, 18)) == wib("2026-11-12 18:00")
    assert youtube.next_slot(youtube.taken_slots(tmp_path), now) == wib("2026-11-12 04:00")

def test_next_slot_cli_faktacuil_uses_settings_hours(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(cli, "load_settings", lambda: Settings(faktacuil_slot_hours=(12,)))
    monkeypatch.setattr(cli, "RUNS_DIR", tmp_path)
    assert cli.main(["next-slot", "--channel", "faktacuil"]) == 0
    assert capsys.readouterr().out.strip().endswith("12:00")

def test_faktacuil_upload_uses_second_token_and_marks_channel(...):
    # script.json mode faktacuil, upload.json language "id", final.mp4 dummy, service fake:
    # channels().list → id "UCfakta"; Settings(faktacuil_youtube_channel_id="UCfakta", youtube_token_json_faktacuil=TOKEN2)
    assert seen_token == TOKEN2
    assert read_json(paths.root / "youtube.json")["channel"] == "faktacuil"

def test_faktacuil_upload_refuses_wrong_channel(...):
    # channels().list → "UCmayz" → PipelineError, videos().insert nggak dipanggil, youtube.json nggak ada

def test_faktacuil_upload_refuses_empty_channel_id(...):  # faktacuil_youtube_channel_id "" → PipelineError sebelum service dibikin
def test_faktacuil_upload_requires_indonesian_metadata(...):  # language "en" → PipelineError
def test_top3_upload_unchanged(...):  # token youtube_token_json, youtube.json tanpa key "channel"
def test_login_faktacuil_writes_second_token_and_prints_channel(monkeypatch, capsys):
    # youtube.login dipanggil dengan token_env="YOUTUBE_TOKEN_JSON_FAKTACUIL"; channel_info fake → output ngandung judul + id
def test_secret_not_in_repr():
    assert "TOK2" not in repr(Settings(youtube_token_json_faktacuil="TOK2"))
```

- [ ] **Step 2: Run, pastiin gagal.**
- [ ] **Step 3: Implement** sesuai spec bagian 6 "upload, login, next-slot". Urutan di upload FaktaCuil: cek `faktacuil_youtube_channel_id` nggak kosong → cek `meta.language == "id"` → bikin service → cek `channel_info(service)[0]` → baru `videos().insert`. Pesan error nyebut apa yang harus dilakuin (`jalanin: uv run mayzfact login youtube --channel faktacuil`, isi `Settings.faktacuil_youtube_channel_id`). Jangan print token.
- [ ] **Step 4: Run** — `uv run pytest tests/test_faktacuil_upload.py tests/test_youtube.py tests/test_cli.py tests/test_config.py -v && uv run pytest -q` → PASS, test lama nggak diubah.
- [ ] **Step 5: Commit** — `git commit -m "feat: upload faktacuil to its own channel and slots"`.

---

### Task 13: Skill `bikin-faktacuil` + catatan agent

**Files:**
- Create: `.agents/skills/bikin-faktacuil/SKILL.md`
- Modify: `AGENTS.md` (baris `script.json` di "File penting", tabel Struktur `assets/`, bagian "Bikin video"), `.agents/skills/bikin-short/SKILL.md` (1 baris di atas: "Format FaktaCuil pakai skill `bikin-faktacuil`")

Nggak ada kode; dicek pakai baca ulang + `rg` path/command yang disebut beneran ada.

- [ ] **Step 1: Tulis `SKILL.md`** dengan frontmatter `name: bikin-faktacuil` + `description` (kapan dipakai: Akmal minta video FaktaCuil / channel Indonesia). Isi, ngikutin struktur `bikin-short` tapi cuma bagian yang beda; langkah yang sama cukup dirujuk ke `bikin-short` nomor langkahnya:
  1. Alur + checkpoint sama kayak `bikin-short`.
  2. Source: video Inggris; kalau Top N, ambil 1 item (sesuai jawaban Q3).
  3. Naskah: aturan F1–F11 dari spec bagian 5 dalam bahasa agent; struktur hook "Kenapa…?" → salah kaprah ("Padahal…", "Kamu mungkin mengira…") → CTA → jawaban ("Ternyata…", "Karena itu…", "Jadi…") → penutup; bahasa Indonesia santai (nggak/udah/banget boleh, tanpa slang dipaksa); terjemahan nggak boleh nambah fakta, angka, atau ngerasin klaim; contoh CTA `Tapi coba tekan like dulu,` / `apakah like-mu berubah jadi madu?`; tabel objek tema; `keyword` 1 kata per beat, ±1 dari 3 beat, bukan beat CTA; `point`/`emoji` selalu kosong; `queries` tetap Inggris + `queries_zh`; rentang kata dari `check-script`.
  4. Review naskah Akmal: tabel per beat `teks Indonesia | kalimat source Inggris | keyword visual`.
  5. Suara: voice dari `Settings.faktacuil_elevenlabs_voice_id`; kalau kosong, STOP dan minta lead jalanin sampel (Task 2).
  6. Brief/fetch/timeline/render: sama; nggak ada panah/emoji/card; BGM dari `assets/channels/faktacuil/bgm/` (jangan download, Akmal yang naruh file; jangan commit).
  7. Metadata `upload.json`: `language: "id"`, judul bahasa Indonesia ≤100 karakter, deskripsi 1–2 kalimat + hashtag `#faktaunik #faktamenarik #<topik> #shorts`, tags Indonesia.
  8. Jadwal: `uv run mayzfact next-slot --channel faktacuil`; upload otomatis ke channel FaktaCuil (mode dibaca dari `script.json`); error token → minta Akmal `uv run mayzfact login youtube --channel faktacuil`.
  9. TikTok: dilewat (Q5).
- [ ] **Step 2: Update `AGENTS.md`** — `narration_mode` sekarang `top3` atau `faktacuil` (D-051); `assets/channels/faktacuil/bgm/` lokal, di-gitignore; bagian "Bikin video" nyebut dua skill.
- [ ] **Step 3: Cek** — tiap command di skill ada di `uv run mayzfact --help` / subcommand help; tiap path ada (`rg`/`ls`).
- [ ] **Step 4: Commit** — `git commit -m "docs: add bikin-faktacuil skill"`.

---

### Task 14: D-051 + HANDOFF

**Files:**
- Modify: `docs/DECISIONS.md` (tambah D-051 setelah D-050), `docs/HANDOFF.md` (section baru)

- [ ] **Step 1: D-051** — format sama kayak D-050: status, authority (Akmal 2026-11-10 lewat lead, keputusan 1–8), kontrak (`narration_mode: "faktacuil"`, `Beat.keyword`, aturan F1–F11), apa yang dimatiin, BGM lokal, upload/slot terpisah, voice yang dipilih + `FAKTACUIL_RAW_WPS` hasil kalibrasi (isi setelah Akmal milih; kalau belum, tulis "belum dipilih"), link spec + plan.
- [ ] **Step 2: HANDOFF** — status tiap task, hasil `uv run pytest -q` terakhir, yang belum dicek (render beneran, suara Indonesia, upload beneran), pertanyaan Q1–Q7 yang masih kebuka.
- [ ] **Step 3: Commit** — `git commit -m "docs: record faktacuil format decision D-051"`.

---

## Self-review (architect)

- Spec bagian 5 → Task 3, 4, 5. Bagian 6: source (nggak berubah), script (3, 5), tts (2, 6), plan (7), brief/fetch (nggak berubah, dicek Task 7 lewat `auto_cta`), timeline (8, 9, 10), Remotion (11), render (nggak berubah), upload/slot (12). Bagian 7 → Task 1 + golden di tiap task. Bagian 8 → Task 2. Docs → 13, 14.
- Nama dipakai konsisten: `faktacuil_cta_indices`, `id_like_positions`, `id_like_begin`, `cta_indices`, `faktacuil_word_range`, `faktacuil_problems`, `settings_for_mode`, `faktacuil_cta_stop`, `captionStyle`, `FAKTACUIL_RAW_WPS`.
