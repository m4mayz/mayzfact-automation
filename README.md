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
```

Hasilnya ada di `runs/<id>/final.mp4`. Jangan hapus `runs/<id>/voice.mp3`, soalnya kalau kehapus suara harus dibuat ulang dan kredit kepakai lagi.

## Test

```bash
uv run pytest              # semua test, tanpa API beneran
uv run pytest -m render    # render Remotion beneran (butuh Node 22)
```
