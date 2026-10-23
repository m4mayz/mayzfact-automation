# mayzfact-automation

Pipeline YouTube Shorts. Naskah ditulis AI agent (Claude Code, Codex, dll) dan direview dulu, suaranya dari ElevenLabs, klip dari link yang diisi lewat halaman brief, lalu di-render pakai Remotion.

- Spec Fase 1: [docs/superpowers/specs/2026-09-30-fase1-pipeline-design.md](docs/superpowers/specs/2026-09-30-fase1-pipeline-design.md)
- Keputusan project: [docs/DECISIONS.md](docs/DECISIONS.md)

## Setup

Install dulu (Windows):

- [uv](https://docs.astral.sh/uv/) buat Python 3.12+
- ffmpeg (`ffmpeg` dan `ffprobe` harus ada di PATH)
- Node 22 lewat nvm (`nvm install 22.23.1`)
- ngrok (`scoop install ngrok`), terus sekali: `ngrok config add-authtoken <token dari dashboard ngrok>`

Terus di folder project:

1. `uv sync`
2. `nvm use 22.23.1`, lalu `cd remotion && npm install && npx remotion browser ensure`
3. Copy `.env.example` jadi `.env`, terus isi. `.env` cuma buat rahasia: `ELEVENLABS_API_KEYS`, `YOUTUBE_CLIENT_SECRET_JSON`, `YOUTUBE_TOKEN_JSON`, `NGROK_BASIC_AUTH`.
4. `ELEVENLABS_API_KEYS` boleh lebih dari 1 key, dipisah koma tanpa spasi. Key dipakai berurutan, dan kalau satu key ditolak (kuota habis/izin kurang), otomatis pindah ke key berikutnya.
5. Setting lain (voice ID, model, durasi, port brief, dll.) ada di `Settings` di `mayzfact/config.py`, ubah langsung di situ. `uv run mayzfact voices` buat nyari voice ID (butuh key dengan izin "Voices: Read").
6. Cek: `uv run pytest` (±1 menit, tanpa API beneran).

Model SigLIP + OWLv2 (±1,4 GB), emoji Lottie, dan SFX ke-download otomatis pas pertama kali dipakai.

### Pindah komputer

`git clone` repo ini, terus ikutin Setup di atas. BGM, SFX, emoji, dan `runs/*/youtube.json` (jadwal tayang buat `next-slot`) udah ikut di git.

Yang nggak ada di git, jadi dibawa manual: `.env` (4 rahasia). Pindahin lewat flashdisk atau password manager, jangan lewat chat/email.

Yang nggak perlu dibawa (ke-download/dibikin ulang): `models/`, `cache/`, `remotion/node_modules/`, sisa isi `runs/` (kecuali mau revisi video yang belum final).

Token YouTube di `.env` tetap jalan di komputer baru. Kalau ditolak, jalanin `uv run mayzfact login youtube` lagi.

## Pakai

```bash
uv run mayzfact run <video_id atau URL>        # jalanin semua step yang belum ada
uv run mayzfact check-script <id>              # cek runs/<id>/script.json yang ditulis agent
uv run mayzfact run <id> --from fetch --no-render   # ulang klip + timeline, berhenti buat review di Remotion Studio
```

Hasilnya ada di `runs/<id>/final.mp4`. Jangan hapus `runs/<id>/voice.mp3`, soalnya kalau kehapus suara harus dibuat ulang dan kredit kepakai lagi.

## Isi link klip

Klip dicari sendiri, terus pipeline yang download + milih bagian terbaik. Nggak ada mode cari klip otomatis (dihapus di D-031).

```bash
uv run mayzfact run <id> --no-render        # run pertama berhenti nunggu naskah (exit 3); setelah naskah ada: sampai plan, nunggu link
uv run mayzfact brief <id>                  # buka alamat yang di-print (PC atau HP), isi link/upload per shot, Simpan
uv run mayzfact run <id> --from fetch --no-render   # download + potong; shot gagal muncul lagi di brief
```

Shot dikelompokin per konteks (semua shot hook = 1 kelompok, sisanya per subjek), tapi link diisi per shot: 1 shot = 1 link, plus kolom Mulai/Selesai (detik) kalau mau potongan tertentu. Shot berurutan yang pakai link sama videonya nyambung. Link boleh teks share Douyin apa adanya. Video source ikut tampil di halaman.

Server brief kebuka ke LAN, dan ke internet lewat ngrok yang dikunci `NGROK_BASIC_AUTH` (alamatnya di-print pas start; `--no-ngrok` buat skip). Halaman brief sendiri nggak punya login, jadi alamat LAN jangan dibuka di WiFi publik. Buat Studio: `uv run mayzfact tunnel 3000`. Link RedNote ditolak (butuh login), save file-nya dari app terus upload. Tambahin ` #3` buat cuma pakai foto ke-3 dari post foto ganda.

## Review di Remotion Studio

Habis `--no-render`, buka Studio. Render final cuma setelah hasilnya oke.

```bash
cd remotion && npx remotion studio src/index.ts --public-dir=../runs/<id> --props=../runs/<id>/timeline.json --port=3000
uv run mayzfact run <id> --from render      # setelah oke
```

Studio cuma baca `--props` pas start. Kalau `timeline.json` berubah, restart Studio.

## Aset

- `assets/bgm/`: 2 BGM dari Akmal, ikut di-commit. `mystery.mp3` di hook, `main.mp3` mulai "Number" pertama sampai akhir.
- `assets/sfx/sfx.json`: momen → nama file di myinstants. File mp3-nya ke-download otomatis.
- `assets/emoji/` (Lottie Noto) dan `models/` (SigLIP + OWLv2, ±1,4 GB) ke-download otomatis pas pertama kali dipakai.

## Pakai bareng AI agent

Aturan main buat agent ada di [`AGENTS.md`](AGENTS.md). Alur bikin 1 video ada di skill [`.agents/skills/bikin-short`](.agents/skills/bikin-short/SKILL.md).

- **Codex, OpenCode, Antigravity:** baca `AGENTS.md` dan nemu skill di `.agents/skills/` otomatis.
- **Claude Code:** baca `CLAUDE.md`, yang isinya import `AGENTS.md`.

Contoh: buka agent di folder ini, terus bilang `bikin short dari https://youtu.be/<id>`.

## Upload ke YouTube

Butuh `YOUTUBE_CLIENT_SECRET_JSON` di `.env` (JSON OAuth client dari Google Cloud, project yang udah lolos audit YouTube API).

```bash
uv run mayzfact login youtube                          # sekali: browser kebuka, token disimpan ke YOUTUBE_TOKEN_JSON di .env
uv run mayzfact next-slot                              # slot tayang kosong berikutnya (01.00/04.00 WIB)
uv run mayzfact upload <id> --at "2026-10-15 01:00"   # upload terjadwal (jam WIB)
uv run mayzfact upload <id> --now                      # langsung public, tanpa jadwal
```

Metadata-nya dibaca dari `runs/<id>/upload.json` (`title`, `description`, `tags`, `category_id`, `language`). Video di-upload sebagai private dengan `publishAt`, jadi YouTube yang bikin public di jamnya. Hasilnya (link video + Studio) disimpan di `runs/<id>/youtube.json`, dan run yang sama nggak bisa ke-upload 2 kali.

## Test

```bash
uv run pytest              # semua test, tanpa API beneran
uv run pytest -m render    # render Remotion beneran (butuh Node 22)
```
