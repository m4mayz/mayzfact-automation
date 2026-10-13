# mayzfact-automation

Pipeline YouTube Shorts. Naskah ditulis ulang pakai Gemini, suaranya dari ElevenLabs, klip video/foto diambil dari Pexels/Pixabay, lalu di-render pakai Remotion.

- Spec Fase 1: [docs/superpowers/specs/2026-09-30-fase1-pipeline-design.md](docs/superpowers/specs/2026-09-30-fase1-pipeline-design.md)
- Keputusan project: [docs/DECISIONS.md](docs/DECISIONS.md)

## Setup

1. `uv sync`
2. `nvm use 22.23.1`, lalu `cd remotion && npm install && npx remotion browser ensure`
3. Copy `.env.example` jadi `.env`, terus isi semua key-nya.
4. `GEMINI_API_KEYS` dan `ELEVENLABS_API_KEYS` boleh lebih dari 1 key, dipisah koma tanpa spasi. Key dipakai berurutan, dan kalau satu key ditolak (kuota habis/izin kurang), otomatis pindah ke key berikutnya.
5. `uv run mayzfact voices` buat nyari `ELEVENLABS_VOICE_ID` (butuh key dengan izin "Voices: Read").

## Pakai

```bash
uv run mayzfact run <video_id atau URL>        # jalanin semua step yang belum ada
uv run mayzfact run <id> --from clips          # ulang klip + timeline + render; suara nggak dibuat ulang
uv run mayzfact run <id> --new-voice           # naskah + suara baru (pakai kredit ElevenLabs)
uv run mayzfact run <id> --from clips --no-render   # berhenti di timeline.json, review di Remotion Studio dulu
```

Hasilnya ada di `runs/<id>/final.mp4`. Jangan hapus `runs/<id>/voice.mp3`, soalnya kalau kehapus suara harus dibuat ulang dan kredit kepakai lagi.

## Mode manual (default)

Klip dicari sendiri, terus pipeline yang download + milih bagian terbaik.

```bash
uv run mayzfact run <id> --no-render        # sampai plan, terus berhenti (exit 3): nunggu link
uv run mayzfact brief <id>                  # buka http://127.0.0.1:3100, isi link/upload per kelompok, Simpan
uv run mayzfact run <id> --from fetch --no-render   # download + potong; kelompok gagal muncul lagi di brief
```

Link diisi per kelompok konteks (semua shot hook = 1 kelompok, sisanya per subjek). 1 baris = 1 link, boleh banyak; pipeline yang ngebagi potongan ke tiap shot tanpa tumpang tindih. Link boleh teks share Douyin apa adanya. Link RedNote ditolak (butuh login), save file-nya dari app terus upload. Tambahin ` #3` buat cuma pakai foto ke-3 dari post foto ganda. Mode lama: `CLIP_SOURCE=auto`.

## Hook (Fase 2)

Login sekali per platform. Sesinya disimpan di `browser-profiles/`, jangan di-share.

```bash
uv run mayzfact login tiktok      # juga: douyin, rednote, pinterest
uv run mayzfact login --check
uv run mayzfact run <id> --from hook   # cari ulang klip hook; suara nggak dibuat ulang
```

Kalau platform kena captcha atau login expired, platform itu di-skip dan run tetap jalan. Log-nya nyebut platform mana yang perlu login ulang.

## Test

```bash
uv run pytest              # semua test, tanpa API beneran
uv run pytest -m render    # render Remotion beneran (butuh Node 22)
```
