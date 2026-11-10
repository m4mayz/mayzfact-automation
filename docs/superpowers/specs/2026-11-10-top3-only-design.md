# Spec — Pipeline cuma format top3

- **Tanggal:** 2026-11-10
- **Status:** diminta Akmal lewat lead, nunggu review spec ini.
- **Keputusan baru:** D-050 (ditulis di task docs, lihat plan Task 10).
- **Branch:** `fase-top3-only`

## 1. Kenapa

Semua video sekarang pakai format Top 3 + scene CTA (D-045, D-046, D-048, D-049). Mode `source` (naskah ngikutin panjang source, CTA like/subscribe di overlay kecil) dan dua varian lama di dalam top3 (top3 tanpa `cta_scene`, tema CTA `word`) udah nggak dipakai, tapi masih bikin cabang `if narration_mode == "top3"` di 6 file dan test yang ngetes jalur mati.

Nanti Akmal mau bikin format baru buat channel lain di project yang sama, jadi field `narration_mode` tetap ada sebagai pemilih format. Sekarang isinya cuma satu nilai: `"top3"`.

## 2. Keputusan yang udah disepakati Akmal

- **(a)** Run lama tanpa `narration_mode` (`4735ZE89GXQ`, `NSua7RPoFJg`, `i2xag_1OJfM`, `piD9Fjp-mG8`, `ydA5gOdKvfc`) file-nya dibiarin. Pipeline nolak run itu dengan error yang jelas. Udah dicek di checkout utama: kelima run ini punya `script.json` + `voice.mp3`, nggak ada `narration_mode`, nggak ada `cta_scene`. Run lain di `runs/` cuma punya `youtube.json`.
- **(b)** Varian lama di dalam top3 ikut dihapus: top3 tanpa `cta_scene` (overlay like/subscribe legacy) dan tema `word`. `cta_scene` jadi wajib.
- **(c)** `narration_mode` tetap ada. Jangan bikin abstraksi multi-channel (registry format, strategy class, config per channel) sekarang.

## 3. Tujuan, non-tujuan, anti-tujuan

**Tujuan**
- `Script` cuma nerima `narration_mode: "top3"` dan wajib punya `cta_scene` dengan tema ilustrasi.
- Semua cabang `narration_mode != "top3"` dan kode khusus mode source hilang dari `mayzfact/`.
- Overlay CTA legacy (`Cta` di Remotion, `timeline.cta`) hilang. Scene CTA jadi satu-satunya visual CTA.
- Run lama ditolak dengan pesan yang nyebut alasannya dan apa yang harus dilakuin, sebelum ada file yang dihapus.

**Non-tujuan**
- Perilaku top3 + `cta_scene` nggak berubah: anggaran kata, validasi, plan, timing scene, click SFX, render.
- Nggak migrasi atau ngubah file di `runs/`.
- Nggak ngubah format `links.json` lama (`mayzfact/manual/links.py:138`, legacy `groups`) dan cache pending TTS lama (`mayzfact/steps/tts.py:62`). Dua-duanya "legacy" yang beda urusan, bukan format narasi.
- Nggak nyentuh field `bgm` sisa lama di `Script` (`mayzfact/models.py:52`).

**Anti-tujuan (gagal walaupun test hijau)**
- Run lama ke-resume terus output-nya (`shots_plan.json`, `clips.json`, `timeline.json`, `final.mp4`) kehapus sebelum error keluar.
- `voice.mp3`/`script.json` run mana pun diubah atau dihapus.
- Click SFX like/subscribe di video top3 hilang gara-gara `_top3_cta` ikut kehapus bareng overlay legacy.
- `Thumb`/`Cursor` ikut kehapus bareng `Cta.tsx`, terus `CtaScene` rusak.

## 4. Kontrak baru

### `Script` (`mayzfact/models.py`)

```python
class CtaScene(BaseModel):
    model_config = ConfigDict(extra="forbid")
    theme: Literal["volcano", "unicorn", "honey", "puppy", "lion", "shark"]
    transform_word: str = Field(min_length=1, max_length=40, pattern=r"^\w+$")
    comment_text: str = Field(min_length=1, max_length=24, pattern=r"\S")


class Script(BaseModel):
    narration_mode: Literal["top3"]  # pemilih format; format channel lain nanti nambah nilai di sini (D-050)
    approved_word_count: int | None = Field(default=None, strict=True, ge=1, le=500)
    cta_scene: CtaScene
    beats: list[Beat]
    bgm: str = ""
    hook_queries: dict[str, HookQuery] = {}
```

- `label` dan validator `check_label` hilang (cuma dipakai tema `word`). Karena `extra="forbid"`, `script.json` yang masih punya `"label"` jadi ditolak. Nggak ada run top3 di disk yang punya `script.json` (dicek), jadi ini aman. Lihat risiko R6.
- Validator `check_scene_mode` hilang karena mode cuma satu.

### Pesan error run lama (`mayzfact/steps/script.py`, `load_script`)

`load_script` ngecek JSON mentah sebelum `Script(**raw)`:

| Kondisi | `PipelineError("script", ...)` |
| --- | --- |
| `narration_mode` nggak ada atau bukan `"top3"` | `script.json pakai format lama (narration_mode: <nggak ada \| 'source' \| ...>). Pipeline sekarang cuma support narration_mode "top3" (D-050). File run ini dibiarin apa adanya; bikin run baru pakai format top3.` |
| `narration_mode == "top3"` tapi `cta_scene` nggak ada | `script.json belum punya cta_scene. Format top3 sekarang wajib cta_scene (D-050). Tambahin cta_scene sesuai skill bikin-short langkah 2; ini metadata visual, hash suara nggak berubah.` |
| tema `word`, `label`, atau field lain salah | tetap pesan generik yang udah ada: `script.json nggak valid (cek JSON/field-nya): ...` |

Pesan pertama wajib ngandung `narration_mode` (dipakai test `tests/test_top3_review_regressions.py:87,119`).

Tempat pesan ini keluar (semua lewat `load_script`):
- `mayzfact/pipeline.py:255-256`: run yang udah punya `voice.mp3`, dicek sebelum output resume dihapus (`pipeline.py:278-281`). Ini jalur kelima run lama.
- `mayzfact/pipeline.py:303` (`_require_script`, sebelum TTS) dan `pipeline.py:77` (`check_voice`).
- `mayzfact/cli.py:98` (`check-script` lewat `check_script_file`).

`brief`, `upload`, `next-slot`, dan `tunnel` nggak baca `script.json`, jadi nggak ikut nolak. Itu sengaja.

### Timeline (`mayzfact/steps/timeline.py`)

- Key `"cta"` hilang dari output `build_timeline`. `ctaScene` tetap.
- `_top3_cta` tetap ada, cuma dipakai internal buat click SFX (`timeline.py:261-262`) dan nentuin tabrakan emoji (`_emojis`).
- Scene dict (`mayzfact/cta_scene.py:74`) nggak ngirim `label` lagi.

### Remotion (`remotion/src/types.ts`)

- `CtaAction` dan `TimelineProps.cta` hilang.
- `CtaSceneData.theme` tanpa `'word'`, `CtaSceneData.label` hilang.
- `timeline.json` lama yang masih punya `cta`/`label` cuma jadi prop yang nggak dibaca. Run lama tetap nggak bisa sampai render karena ditolak `load_script` duluan.

## 5. Yang dihapus atau diubah

### Code Python

| Lokasi | Perubahan |
| --- | --- |
| `mayzfact/models.py:9-21` | `CtaScene`: buang `"word"`, `label`, `check_label`; docstring jadi soal ilustrasi aja |
| `mayzfact/models.py:41-50` | `narration_mode: Literal["top3"]` wajib, `cta_scene: CtaScene` wajib, buang `check_scene_mode` |
| `mayzfact/steps/script.py:161-167` | `load_script`: cek mode + `cta_scene` di JSON mentah, pesan di bagian 4 |
| `mayzfact/steps/script.py:45-57` | `narration_word_range`: buang cabang `!= "top3"` (`:48-49`) |
| `mayzfact/steps/script.py:66-87` | `check_script`: blok top3 jadi tanpa `if`; buang cabang tema `word` (`:70-73`); `elif` jadi selalu jalan |
| `mayzfact/steps/script.py:120-126` | hitung `explanation_count` selalu pakai `ctas`; buang cabang source |
| `mayzfact/steps/script.py:133-138` | `present_cta` selalu `cta_kinds_for_beats`; import `cta_kinds` (`:9`) tetap dipakai buat `missing_cta` (`:139`) |
| `mayzfact/pipeline.py:29` | hapus `MIN_AUDIO_SECONDS` |
| `mayzfact/pipeline.py:82-96` | `check_voice`: blok top3 jadi tanpa `if`, buang `elif` audio < 30 detik |
| `mayzfact/steps/plan.py:182-191` | clear subject CTA dan filter hook `eligible` selalu jalan |
| `mayzfact/steps/plan.py:202` | `ctas = set(cta_beat_indices(beats))` tanpa syarat |
| `mayzfact/steps/plan.py:226-230` | `source_rank` selalu diisi; `auto_cta` cuma syarat `slot.beat in ctas` |
| `mayzfact/steps/plan.py:110-112,127-129,231-232` | buang parameter `ranked` di `_shot_frames`; `ranks` selalu dihitung |
| `mayzfact/steps/plan.py:240-241` | `data['cta_scene'] = script['cta_scene']` tanpa syarat |
| `mayzfact/cta_scene.py:15` | buang cek `narration_mode`; `if not config: return None` tetap (test timeline lama kirim script tanpa scene) |
| `mayzfact/cta_scene.py:74` | buang `label=` |
| `mayzfact/steps/timeline.py:347-365` | hapus `_cta` |
| `mayzfact/steps/timeline.py:477-478` | `cta = _top3_cta(...)` tanpa syarat |
| `mayzfact/steps/timeline.py:485-489,516` | key `"cta"` hilang dari `data`; `sound_cta` jadi `cta` langsung; kalau script punya `cta_scene` tapi `build_scene` balik `None`, tulis 1 log `[timeline] scene CTA dilewat: blok CTA nggak kebentuk` |

### Rantai durasi mode source (Task 6, butuh oke lead)

Setelah cabang source hilang, `duration_s` di `narration_word_range` nggak kepake. Yang ikut mati:

| Lokasi | Isi |
| --- | --- |
| `mayzfact/steps/script.py:15-16` | `WORDS_PER_SECOND`, `WORD_TOLERANCE` |
| `mayzfact/steps/script.py:22-28` | `target_duration`, `word_range` |
| `mayzfact/steps/script.py:45,60-61,90,170-177` | parameter `duration_s` (`narration_word_range`, `check_script`) dan `ratio`/`minimum_s` (`check_script_file`) |
| `mayzfact/pipeline.py:304-305` | argumen `ratio`/`minimum_s` |
| `mayzfact/cli.py:84-89,98,105-106` | import + pemanggilan `target_duration` |
| `mayzfact/config.py:39-40` | `target_duration_ratio`, `min_duration_seconds` |

### Remotion

| Lokasi | Perubahan |
| --- | --- |
| `remotion/src/Cta.tsx:6-11,41-233` | hapus konstanta, `Burst`, `CURSOR_REST`, `Like`, `Subscribe`, `Cta`. **`Thumb` (`:16-20`) dan `Cursor` (`:23-39`) tetap** karena dipakai `CtaScene.tsx:3` |
| `remotion/src/CtaScene.tsx:64-69` | hapus `case 'word'` |
| `remotion/src/ShortVideo.tsx:5,16,47` | hapus import `Cta`, prop `cta`, dan `<Cta actions={cta} />` |
| `remotion/src/Root.tsx:21` | hapus `cta: []` dari default props |
| `remotion/src/types.ts:85-90,101-102,132` | hapus `CtaAction`, `'word'`, `label`, `cta?` |

### Test

| File | Perubahan |
| --- | --- |
| `tests/top3_fixtures.py` | tambah `cta_scene` di `top3_script` dan `playful_script`; teks CTA `top3_script` beat 7 dapat klausa transformasi (detail di plan Task 1) |
| `tests/factories.py:8,11-21` | hapus `make_script` + import `Beat, Script` setelah semua pemakainya pindah |
| `tests/test_script_rules.py` | test aturan umum pindah ke fixture top3; test khusus source dihapus (daftar di plan Task 2) |
| `tests/test_cli.py:254-260` | test `check-script` source dihapus; versi top3 udah ada di `tests/test_top3_script.py:101` |
| `tests/test_pipeline.py:20,25,82-105,174-175,220-226` | `write_voice_state` dan `write_fake_script` jadi top3 + `TRANSCRIPT` dengan heading 3/2/1; hapus `test_check_voice_rejects_short_audio` dan `test_short_audio_stops_before_plan` |
| `tests/test_top3_script.py:9-16` | ganti jadi test penolakan format lama |
| `tests/test_approved_word_count.py:19-22` | hapus `test_legacy_budget_ignores_top3_approval`; `Script(...)` lain dapat `cta_scene` |
| `tests/test_top3_playful_cta.py:132-138` | hapus `test_short_legacy_cta_does_not_reduce_base_word_budget` (gaya CTA top3 tanpa scene) |
| `tests/test_cta_illustration_policy.py:9-13,64-70` | tema `word` sekarang ditolak schema, bukan cuma `check_script` |
| `tests/test_cta_illustration_policy.py:16-41` | buang assert `scene.label == ''` |
| `tests/test_cta_scene.py:200,234-241,339-347` | buang assert `timeline['cta']`, test scene absence versi source/legacy, assert `label` |
| `tests/test_top3_timeline.py:11-28` | assert urutan CTA pindah dari `timeline['cta']` ke `_top3_cta(...)` atau click SFX |
| `tests/test_timeline.py:491-522` | hapus 4 test `_cta` legacy (`test_cta_like_then_subscribe_with_clicks`, `test_subscribe_waits_until_like_finishes`, `test_cta_ignores_like_meaning_similar_and_subscribers`, `test_cta_fits_before_the_video_ends`). `CTA_TEXT`/`CTA_SCRIPT`/`CTA_CLIPS` (`:486-488`) tetap karena dipakai `:527` dan `:534` |
| `tests/test_timeline.py:532-537` | `test_emoji_that_collides_with_cta_starts_after_it`: frame CTA sekarang dari `_top3_cta`, angka expected mungkin geser; hitung ulang dari aturan `_top3_cta`, jangan longgarin assert |
| `tests/test_plan.py` | fixture script dict dapat `narration_mode`/`cta_scene` kalau perlu; fixture countdown `Number five` mungkin kena error rank (R3) |
| `tests/test_cta_scene.py:293` | angka `11 CTA visual cases passed` ikut berubah kalau case `word` dihapus |
| `remotion/tests/cta-scene.cjs:38-40,62,82-84,105,126,147,168,172-179,181` | case `word` dihapus; pembanding "stage nggak tergantung tema" pakai tema ilustrasi lain; tema `word` masuk daftar yang wajib dilempar `Unsupported CTA transform theme` |

### Docs

| File | Perubahan |
| --- | --- |
| `.agents/skills/bikin-short/SKILL.md:16` | `narration_mode: "top3"` wajib; run tanpa field ini format lama dan ditolak pipeline |
| `.agents/skills/bikin-short/SKILL.md:28` | `cta_scene` wajib, bukan "naskah baru aja" |
| `.agents/skills/bikin-short/SKILL.md:36` | hapus kalimat `theme: "word"` legacy |
| `.agents/skills/bikin-short/SKILL.md:77` | hapus "tanpa metadata, animasi legacy..." dan contoh konektor mode `source` |
| `AGENTS.md:40` (baris `script.json` di "File penting") | sebut `narration_mode` cuma `top3` + `cta_scene` wajib; run format lama ditolak (D-050) |
| `docs/DECISIONS.md` | tambah D-050; D-045 s/d D-049 nggak diedit, cukup dirujuk dari D-050 |
| `docs/HANDOFF.md` | section baru fase top3-only |

## 6. Yang dipertahankan

- Field `narration_mode` di `Script` dan di `script.json` (keputusan c).
- `approved_word_count`, `top3_word_range`, `top3_problems`, `cta_beat_indices`, `cta_kinds_for_beats`, `validate_video_speed` (`mayzfact/narration.py`).
- `source_countdown_entries` dan `source_countdowns` (`mayzfact/narration.py:24-32`). Namanya "source", tapi isinya heading dari transcript source YouTube, dipakai top3 di `top3_problems` dan `_source_rank_ranges`. **Jangan dihapus walaupun namanya muncul di grep.**
- `cta_kinds`, `is_like_cta`, `SUBSCRIBE`, `COMMENT` (`mayzfact/cta.py`): dipakai `_top3_cta`, `cta_scene.py`, dan `check_script`.
- `CTA_FRAMES`/`CTA_CLICK` (`mayzfact/steps/timeline.py:64-65`): dipakai `_top3_cta`.
- `_top3_cta`: sumber click SFX dan batas emoji.
- `Thumb` dan `Cursor` di `remotion/src/Cta.tsx`.
- `timing: 'word' | 'structure'` di `CtaStage` (`types.ts:96`, `cta_scene.py:69`). Ini label timing cue, bukan tema `word`.
- File `runs/` semuanya, termasuk 5 run lama.

## 7. Risiko

- **R1 — Helper bersama yang namanya mirip source.** `source_countdown_entries`, `source_countdowns`, `_source_rank_ranges`, `subject_ranges`, `cta_kinds` kepake di jalur top3. Grep `source`/`legacy` bakal nemu mereka. Plan nandain mana yang tetap.
- **R2 — Overlay CTA legacy dan click SFX.** Overlay `cta` dan click SFX sama-sama dari `_top3_cta`. Yang dihapus cuma output `data["cta"]` + komponen Remotion; `_top3_cta` dan `_sound(..., cta, ...)` tetap. Test click SFX top3 harus tetap hijau.
- **R3 — `plan` selalu ranked.** Sekarang `_shot_frames(ranked=True)` jalan buat semua script. Shot setelah `Number N` butuh heading `Number N` di transcript; kalau nggak ada, `PipelineError` di `plan.py:131-132`. Fixture `tests/test_plan.py` (`Number five, horseshoe crab`, teaser `Number one is wild`) bisa kena. Fix-nya di fixture, bukan di guard.
- **R4 — Fixture test.** `top3_script()` sekarang nggak punya klausa `into <tema>`. Begitu `cta_scene` wajib, semua `check_script(top3_script()) == []` gagal kalau teks CTA nggak dibenerin. Test yang ngubah teks beat 7/8 lalu assert `== []` (`tests/test_top3_review_regressions.py:15-30`) juga perlu klausa transformasi di teks barunya.
- **R5 — Teks error dan test yang nyebut mode source.** `tests/test_top3_script.py:13` assert default `'source'`; `tests/test_approved_word_count.py:20-21` pakai `narration_mode='source'`; `tests/test_cta_scene.py:240` pop mode buat ngetes jalur source. Semua diganti atau dihapus. Pesan baru wajib tetap ngandung `narration_mode`.
- **R6 — `label` di `script.json` top3.** Kalau Akmal punya `script.json` top3 di luar `runs/` (backup, mesin lain) yang masih punya `"label": ""`, file itu bakal ditolak `extra="forbid"`. Fix-nya hapus key `label`; hash suara nggak berubah.
- **R7 — Remotion test butuh `node_modules`.** Worktree ini belum punya `remotion/node_modules`, jadi `test_cta_visual_markup_cases_run_in_node` gagal `MODULE_NOT_FOUND` di baseline. Task Remotion harus `npm ci` dulu (Node 22).
- **R8 — Rawan conflict merge.** `mayzfact/steps/script.py`, `mayzfact/steps/timeline.py`, `tests/test_pipeline.py`, `tests/top3_fixtures.py`, `.agents/skills/bikin-short/SKILL.md`, `docs/HANDOFF.md`, `docs/DECISIONS.md` sering disentuh fase lain. Kerjain di satu branch, merge sekali.

**Belum dicek:** render beneran (`pytest -m render`), dan apakah `tests/test_audio.py`, `tests/test_marks.py`, `tests/test_overlay.py` punya assert yang tergantung `timeline["cta"]` (grep nggak nemu, tapi baru dicek pakai grep).

## 8. Pilihan yang ditolak

- **`narration_mode` tetap default `"source"` tapi ditolak di validator.** Ditolak: default yang selalu salah cuma bikin bingung. Field wajib lebih jujur.
- **Hapus field `narration_mode` sekalian.** Ditolak karena keputusan (c): format channel lain nanti butuh pemilih.
- **Enum/registry format (`FORMATS = {"top3": ...}`) buat persiapan channel lain.** Ditolak: cuma ada 1 format. Abstraksi dibikin pas format kedua beneran ada.
- **`cta_scene` wajib cuma di `check_script` (pra-TTS), schema tetap opsional.** Ditolak: run top3 tanpa scene tetap bisa lolos `--from plan` dan render overlay legacy, padahal varian itu yang mau dihapus.
- **Pesan error lewat `model_validator(mode="before")` di `Script`.** Ditolak: pesan pydantic dibungkus prefix `script.json nggak valid` dan dipotong 300 karakter. Cek di `load_script` lebih jelas dan cuma satu tempat.
- **`timeline.cta` tetap dikirim tapi selalu `[]`.** Ditolak: field yang selalu kosong itu sisa. Remotion udah aman kalau prop-nya nggak ada.
- **Pindahin `Thumb`/`Cursor` ke `CtaScene.tsx` terus hapus `Cta.tsx`.** Ditolak di fase ini: diff lebih gede tanpa perubahan perilaku. Boleh nanti kalau `Cta.tsx` ganggu.
