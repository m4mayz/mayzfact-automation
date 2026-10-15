# Spec — Naskah ditulis agent, Gemini dicabut

- **Tanggal:** 2026-10-15
- **Status:** disetujui Akmal lewat interview di chat, nunggu review spec ini.
- **Konteks:** Naskah dari Gemini kaku dan humornya hilang (contoh: run `4735ZE89GXQ`). Akmal mau naskah jadi tanggung jawab harness agent, dia review dulu, baru suara dibikin. Sekalian Gemini dicabut total. Ini ngegantiin D-003 dan D-010, dan ngubah bagian "agent nggak nulis teks pipeline" di `AGENTS.md`.

## 1. Tujuan

Setelah `mayzfact run <url>` ngambil transcript source, agent nulis naskah lengkap (teks, keyword, subject, emoji, panah), nunjukin ke Akmal di chat, dan setelah Akmal oke, pipeline lanjut ke suara. Nggak ada lagi panggilan ke Gemini di mana pun.

Berhasil kalau: naskah `4735ZE89GXQ` versi baru punya nada source (celetukan "bro", penutup lucu per item), CTA like + subscribe kebaca di naskah, `mayzfact check-script` lolos, dan `uv run mayzfact run` tanpa `GEMINI_API_KEYS` jalan sampai render.

## 2. Keputusan dari interview

| Topik | Keputusan |
| --- | --- |
| Kedekatan ke source | Nulis ulang source: fakta, urutan, momen tetap; kata-katanya beda. Nggak nambah fakta dari luar source. |
| Nada | Persis source, termasuk "bro" dan celetukan penutup tiap item. |
| Panjang | ±80% durasi source. Intro dipadetin. |
| CTA awal | Dipadetin ke comment + like + subscribe, 1–2 beat, pakai kata "like" dan "subscribe" beneran. |
| Panah / ajakan lihat | Agent yang nentuin, nggak ada kuota. |
| Review | Di chat, per beat, dibandingin sama source. Suara setelah Akmal bilang oke. |
| Gemini | Dicabut total: naskah, keyword klip, emoji/panah, BGM, keyword hook, terjemahan Mandarin. |

## 3. Alur baru

```
run <url>  → source.json → berhenti (exit 3: "nunggu naskah")
agent      → nulis runs/<id>/script.json
           → uv run mayzfact check-script <id>   (ulang sampai lolos)
           → tunjukin ke Akmal di chat, tunggu oke
run <id>   → tts → plan → [brief] → fetch → timeline → ...
```

- Step `script` dihapus dari `MANUAL_STEPS` dan `STEPS`. Step `source` selesai kalau `source.json` ada; step `tts` butuh `script.json`. Kalau `script.json` belum ada, `run` berhenti dengan `AwaitingInput` ("Naskah belum ada. Agent nulis `runs/<id>/script.json`, cek pakai `mayzfact check-script <id>`").
- `--new-voice` dan `--from script` dihapus. Mau naskah baru = hapus `script.json` + `voice.mp3` manual (D-007 tetap: suara dikunci).
- Naskah lama (`i2xag_1OJfM`, `NSua7RPoFJg`, `4735ZE89GXQ`) nggak disentuh. `annotations.json` dan `marks.py` jalur Gemini dihapus; `prepare_marks` tinggal baca tanda dari `script.json` (semua naskah sekarang punya `point`/`emoji`).

## 4. Format `script.json`

Sama kayak sekarang (`Script` di `models.py`), ditambah 2 field baru:

```json
{
  "beats": [
    {"text": "...", "media": "video", "queries": ["...", "..."], "subject": "mantis shrimp",
     "point": false, "emoji": "", "emoji_word": ""}
  ],
  "fallback_query": "ocean animals",
  "bgm": "mystery.mp3",
  "hook_queries": {"0": {"en": ["..."], "zh": ["..."]}}
}
```

- `bgm`: nama file di `assets/bgm/` yang mood-nya cocok. Boleh `""` kalau nggak ada yang cocok.
- `hook_queries`: keyword Inggris + Mandarin per segmen hook (index dari `runs/<id>/plan/seg_*.jpg`, dibikin step plan). Agent lihat frame-nya sendiri. Boleh `{}`, fallback-nya keyword beat pertama.
- `queries` tiap beat tetap Inggris; versi Mandarin buat brief ditulis agent di `queries_zh` (list, opsional, default `[]`).

## 5. `mayzfact check-script <id>`

Ngecek `script.json` pakai aturan yang sama kayak `check_script` sekarang, plus 2 baru. Output: daftar masalah, exit 1 kalau ada, exit 0 kalau bersih.

| Cek | Aturan |
| --- | --- |
| Jumlah kata | target = 80% durasi source × 2.6 kata/detik, toleransi ±15% (`TARGET_DURATION_RATIO` default jadi 0.8). |
| Per beat | ≤ 10 kata, ada `queries`, teks nggak kosong. |
| Porsi foto | 15–45% beat `media: photo`, beat pertama `video`. |
| Countdown | Kalau source ngitung ("Number five"), urutan dan jumlah item sama, tiap item ≥ 2 beat penjelasan. |
| Overlap | ≤ 15% frasa 4 kata sama persis dengan source. |
| Emoji | Dari daftar `EMOJI`; `emoji_word` ada di teks beat; nggak di beat countdown; nggak 2 beat berturut-turut. |
| **CTA (baru)** | Kalau transcript source nyebut "like" / "subscribe" / "comment", naskah juga harus nyebut kata yang sama (per kata). |
| **BGM (baru)** | `bgm` kosong atau ada di `assets/bgm/`. |

`normalize_script` tetap jalan sebelum cek (bersihin teks, beat pertama jadi video).

## 6. Prompt buat agent

`.agents/skills/bikin-short/SKILL.md` langkah 1 diganti jadi "tulis naskah". Isinya aturan dari bagian 2 dan 4, ditambah:

- Baca `source.json` (transcript + durasi) dan frame hook di `runs/<id>/plan/`.
- Nulis per beat ≤ 10 kata, 1 ide visual per beat.
- Pakai kata sehari-hari. Kalau mau beda dari source, ubah struktur kalimat dan sudut pandangnya, jangan cuma ganti sinonim.
- Pertahankan kata pembatas source ("some species", "one of the"). Jangan dilebih-lebihin.
- Teaser nomor 1 di hook dipertahankan kalau source punya.
- Tunjukin ke Akmal: tabel beat (teks baru | kalimat source yang jadi dasarnya), plus BGM yang dipilih. Tunggu "oke" atau koreksi.
- Contoh naskah yang bagus: 1 contoh pendek di skill, diambil dari source `4735ZE89GXQ` item mantis shrimp.

## 7. Yang dihapus

- `mayzfact/providers/gemini.py`, `mayzfact/prompts/{rewrite,mark_beats,pick_bgm,hook_queries,translate_queries}.md`.
- `mayzfact/hook_queries.py` (fungsi `transcript_near`, `fallback_queries` pindah ke `steps/plan.py` kalau masih dipakai).
- `mayzfact/marks.py`: `_ask_gemini`, cache `annotations.json`. Sisanya (`normalize_marks`, `prepare_marks` tanpa writer) tetap.
- `audio.py`: `pick_bgm` diganti baca `script["bgm"]`.
- `config.py`: `gemini_api_keys`, `gemini_model`, env `GEMINI_API_KEYS`, `GEMINI_MODEL`. Dependency `google-genai` dicabut dari `pyproject.toml`.
- `pipeline.py`: `Deps.script_writer`, pembuatan `GeminiScriptWriter` di `real_deps`, step `script`.
- Test: `test_gemini.py`, `test_hook_queries.py`, bagian Gemini di `test_marks.py`, `test_script_step.py` (yang ngetes `generate_script`), `test_pipeline.py`, `test_config.py`.

## 8. Error

| Kasus | Perilaku |
| --- | --- |
| `run` tanpa `script.json` | exit 3, pesan nyuruh agent nulis naskah. |
| `script.json` nggak valid (JSON rusak / field kurang) | `check-script` exit 1 dengan pesan field; `run` juga nolak sebelum TTS. |
| `bgm` nggak ada di folder | `check-script` nolak; kalau lolos cek tapi file kehapus belakangan, timeline log "BGM nggak ketemu" dan video tanpa BGM (hiasan, nggak boleh gagal). |
| `hook_queries` kosong | plan pakai keyword beat pertama (`fallback_queries` sekarang). |
| Frame hook belum ada pas agent nulis | `run` bikin `plan/seg_*.jpg` di step `source` (dipindah dari `plan`), jadi selalu ada sebelum naskah. |

## 9. Test

- `check_script`: CTA (source nyebut subscribe, naskah nggak → ditolak), BGM nggak ada → ditolak, jumlah kata 80%.
- `plan_steps`: tanpa `script.json` → berhenti `AwaitingInput`; dengan `script.json` + `voice.mp3` → lanjut.
- `prepare_marks` tanpa writer: tanda dari `script.json`, nggak ada `annotations.json`.
- `prepare_audio`: BGM dari `script["bgm"]`; nggak ada → log + None.
- `run_plan`: `hook_queries` dari script dipakai; kosong → fallback.
- `load_settings` tanpa `GEMINI_*` jalan; `missing_env` nggak minta Gemini di step mana pun.
- Suite lama yang ngetes Gemini dihapus, bukan di-skip.

## 10. Di luar scope

- Naskah video lama nggak ditulis ulang.
- Mode `CLIP_SOURCE=auto` (pencarian klip otomatis) tetap ada, tapi keyword Mandarin buat auto juga dari `queries_zh`.
- Nggak ada "AI reviewer" kedua buat naskah; reviewer-nya Akmal.
