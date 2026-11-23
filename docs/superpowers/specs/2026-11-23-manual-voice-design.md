# Suara manual (upload dari web ElevenLabs) — desain

Tanggal: 2026-11-23. Disetujui Akmal di chat.

## Kenapa

API ElevenLabs akun free makin dibatasi: Voice Library nggak bisa lewat API, dan Default voice (Eric) dilaporkan dihapus 31 Desember 2026. Akmal mau generate suara sendiri di web ElevenLabs, terus pipeline lanjut dari file itu. Project jalan di server tanpa GUI, jadi upload harus bisa dari HP/PC lewat halaman brief.

## Bukan tujuan

- Otomasi browser ke web ElevenLabs (ditolak: Prohibited Use Policy §12).
- Multi-file per bagian. Satu video = satu file suara.
- Milih voice/model dari pipeline. Akmal yang milih di web.

## Alur

1. `faktacuil_tts_provider: "manual"` (atau `tts_provider`) di `settings.local.json`.
2. Step tts nulis `runs/<id>/tts-request.txt` (teks naskah persis, siap paste) lalu berhenti exit 3 "nunggu suara".
3. Akmal paste teks di web ElevenLabs, generate, download.
4. Upload lewat `mayzfact brief <id>` (mode suara: halaman kebuka walau plan belum ada), atau taruh file langsung di `runs/<id>/voice.upload.<ext>` (`.mp3`, `.wav`, `.m4a`).
5. `mayzfact run <id> --no-render` lagi: file diubah ke MP3 kalau perlu, Whisper lokal bikin timestamp kata, timestamp dipasangin ke kata naskah, hasilnya kontrak `alignment` per karakter yang sama dengan ElevenLabs API. Setelah itu step tts biasa: potong jeda FaktaCuil, `tts.json`, `voice.mp3`, lalu plan.

## Komponen

- `mayzfact/asr.py`
  - `transcribe_words(path, *, model, language, cache_dir) -> list[{"word","start","end"}]`: pipeline `transformers` Whisper, `return_timestamps="word"`, model di `models/`. Default `openai/whisper-small` (spike `gu2M14rfRlU`: 64/64 kata kepasang, selisih start vs ElevenLabs median 0,03 s, p90 0,08 s).
  - `align_heard(text, heard, duration) -> list[{"word","start","end"}]`: satu entri per kata naskah. Dipasangin pakai `difflib` di kata yang dinormalisasi. Blok `replace` (ejaan beda: `nggak`/`gak`, `like`/`laik`) dapat waktu dari kata yang kedengeran, dibagi proporsional panjang huruf. Kata naskah yang nggak kedengeran diisi di celah tetangganya. Kurang dari 70% kata naskah yang cocok persis atau sebagai pengganti 1:1 berarti file salah: `PipelineError`.
- `mayzfact/providers/manual.py` `ManualTTS`: `provider_name="manual"`, `voice_id`/`model_id` `"manual"`, `cache_identity={"provider": "manual"}`. `bind_run(paths)` dipanggil `run_tts`. `synthesize(text)` nulis request + `AwaitingInput` kalau belum ada upload; kalau ada, balikin `(mp3_bytes, alignment_from_words(text, align_heard(...)))`.
- Config: `tts_provider`/`faktacuil_tts_provider` nerima `"manual"`; `manual_asr_model` (bisa di-override lokal) dan `manual_language` (`"en"`, FaktaCuil `"id"`).
- Pipeline: provider manual nggak butuh `ELEVENLABS_API_KEYS`; audio pending manual bisa dilanjut.
- Brief mode suara: `GET /` nampilin teks + tombol copy + upload + player file yang udah ada. `POST /api/voice` nyimpen `voice.upload<ext>` (maks 50 MB), ditolak kalau `voice.mp3` udah ada.

## Aturan yang tetap

- `voice.mp3` + `script.json` tetap terkunci setelah jadi. File upload nggak dihapus pipeline.
- Durasi di luar target cuma warning (`check_voice`), nggak ditolak.
- Default provider tetap ElevenLabs API (D-062); manual opt-in per mesin.
