# AGENTS.md — mayzfact-automation

Panduan buat AI agent (Claude Code, Codex, OpenCode, Antigravity, dan lainnya) yang bantu Akmal di repo ini. Baca sampai habis sebelum mulai kerja.

## Project ini apa

Pipeline YouTube Shorts. Input-nya video YouTube source, output-nya `runs/<id>/final.mp4`:

source → naskah (ditulis agent, direview Akmal) → suara (ElevenLabs) → klip → edit gaya `i2xag_1OJfM` (caption, BGM, SFX, card countdown, panah, emoji, CTA) → render Remotion.

Target kualitasnya setara source `i2xag_1OJfM`. Peta besarnya ada di `flow.svg`.

Peran agent di sini:

- **Operator:** jalanin CLI, berhenti di checkpoint yang butuh Akmal, ngecek hasilnya.
- **Developer:** benerin bug dan nambah fitur.

Naskah, keyword klip, tanda emoji/panah, dan BGM ditulis **agent** ke `runs/<id>/script.json`, dicek pakai `mayzfact check-script`, dan harus di-review Akmal sebelum suara dibikin. Nggak ada LLM eksternal di pipeline. Aturan nulis naskahnya ada di skill `bikin-short` langkah 2.

## Bikin video

Ikutin skill `.agents/skills/bikin-short/SKILL.md`. Codex, OpenCode, dan Antigravity nemu skill ini otomatis. Agent lain baca file-nya langsung.

## Struktur

| Path | Isi |
| --- | --- |
| `mayzfact/` | package Python: CLI `mayzfact`, step pipeline di `steps/`, aturan naskah di `steps/script.py` |
| `remotion/` | komponen video (React + Remotion 4) |
| `runs/<id>/` | hasil per video (di-gitignore) |
| `assets/bgm/<mood>.mp3` | BGM dari Akmal. Mood: mystery, suspense, dark, epic, space, tech, nature, playful, funny, inspiring, sad, energetic |
| `assets/sfx/sfx.json` | momen → nama file SFX myinstants. File mp3-nya ke-download otomatis |
| `assets/emoji/`, `models/` | cache yang ke-download otomatis: Lottie Noto, model SigLIP + OWLv2 (±1,4 GB) |
| `docs/DECISIONS.md` | keputusan project (D-001, D-002, …) |
| `docs/HANDOFF.md` | status tiap fase + masalah terbuka |
| `docs/superpowers/specs/`, `plans/` | spec + plan per fase |

File penting di `runs/<id>/`:

- `script.json`: naskah per beat (ditulis agent), termasuk `queries`/`queries_zh`, tanda `point`/`emoji`/`emoji_word`, `bgm`, dan `hook_queries`.
- `voice.mp3` + `tts.json`: suara. **Dibikin pakai kredit ElevenLabs, jangan dihapus.**
- `links.json`: link klip per shot dari halaman brief (plus start/end detik kalau diisi).
- `clips.json`: klip per shot, termasuk sumbernya (`provider`, `page_url`, `author`).
- `timeline.json`: props buat Remotion.
- `overlays.json`: cache deteksi subjek.
- `final.mp4`: hasil render.
- `upload.json`: metadata YouTube yang ditulis agent.
- `tiktok.json`: caption + cover + label AI buat TikTok. Akmal upload ke TikTok manual.
- `youtube.json`: hasil upload (video ID, link, jadwal). Jangan dihapus tanpa izin Akmal.
- `prefetch.json`: status download link dari halaman brief (`antre`/`download`/`siap`/`gagal` per URL).

## Perintah

```bash
uv sync                                               # setup Python
uv run mayzfact run <url|id> --no-render              # lanjut dari step yang belum ada; exit 3 = nunggu naskah / nunggu link
uv run mayzfact check-script <id>                     # cek script.json yang ditulis agent
uv run mayzfact brief <id>                            # halaman isi link, port 3100, kebuka ke LAN + ngrok ber-password; link di-download di background
uv run mayzfact tunnel 3000                           # tunnel ngrok ber-password ke Studio (atau port lain)
uv run mayzfact run <id> --from fetch --no-render     # download + potong klip, terus timeline
uv run mayzfact run <id> --from timeline --no-render  # bikin ulang timeline aja
uv run mayzfact run <id> --from render                # render final.mp4 (5–8 menit)
uv run mayzfact login youtube                         # login Google sekali, token masuk .env
uv run mayzfact next-slot                             # slot tayang kosong berikutnya (04.00/21.00 WIB)
uv run mayzfact upload <id> --at "YYYY-MM-DD HH:MM"  # upload terjadwal, jam WIB
uv run mayzfact upload <id> --now                     # langsung public (cuma kalau Akmal minta)
cd remotion && npx remotion studio src/index.ts --public-dir=../runs/<id> --props=../runs/<id>/timeline.json --port=3000 --no-open
```

Exit code CLI:

- `0`: beres.
- `3`: nunggu naskah dari agent, atau nunggu link klip dari Akmal (pesannya nyebut yang mana).
- `1`: error, pesannya di stderr.

## Test dan cek

```bash
uv run pytest                                   # semua test, tanpa API beneran (±3 menit)
uv run pytest -m render                         # render Remotion beneran (butuh Node 22)
uvx ruff check --select F,I <file yang diubah>
cd remotion && npx tsc --noEmit -p .
```

## Aturan

### Keamanan (wajib)

- Jangan print, log, atau commit isi `.env` (API key, termasuk `YOUTUBE_CLIENT_SECRET_JSON` dan `YOUTUBE_TOKEN_JSON`), cookie, atau apa pun di `browser-profiles/`.
- Upload ke YouTube itu aksi keluar yang nggak bisa ditarik. Jalanin `mayzfact upload` cuma setelah Akmal konfirmasi jam tayangnya.
- Jangan solve captcha yang butuh manusia. Jangan rotasi proxy/IP. Jangan spoof fingerprint, termasuk impersonation `curl_cffi` di yt-dlp.
- Kalau platform minta captcha atau login ulang, berhenti. Minta Akmal jalanin `uv run mayzfact login <platform>`.
- Challenge yang diselesaiin browser biasa tanpa manusia (WAF proof-of-work Douyin) boleh (D-018).
- Jangan ubah atau hapus `flow.svg` dan `sources/`.
- Halaman brief selalu kebuka ke LAN dan ke internet lewat ngrok (biar bisa diisi dari HP). Brief sendiri nggak punya login; yang ngunci cuma basic-auth ngrok dari `NGROK_BASIC_AUTH`. Jangan pernah buka ngrok tanpa basic-auth, jangan print isi `NGROK_BASIC_AUTH`, dan matiin brief + tunnel kalau udah selesai. Siapa aja di WiFi yang sama tetap bisa buka alamat LAN, jadi jangan jalanin brief di WiFi publik.
- Jangan commit file audio, emoji, atau model: `assets/bgm/*`, `assets/sfx/*` (kecuali `sfx.json`), `assets/emoji/`, `models/`. Semuanya udah di-gitignore, jangan dipaksa masuk.

### Biaya

- Suara dibikin pakai kredit ElevenLabs. Bikin suara buat video baru itu normal.
- Kalau `voice.mp3` udah ada, jangan hapus `script.json`/`voice.mp3` atau jalanin `--from tts` tanpa izin Akmal.

### Review video

- Habis ngubah apa pun yang kelihatan di video, jangan langsung render. Jalanin `--no-render`, restart Studio, terus minta Akmal review di <http://localhost:3000>.
- Render cuma setelah Akmal bilang oke.
- Studio cuma baca `--props` pas start. Kalau `timeline.json` berubah, matiin dulu proses lama di port 3000, baru start lagi.
- Toggle layer di Studio bisa nulis ke `remotion/src/`. Cek `git diff remotion/src` setelah Akmal review.
- Jangan nyetir Studio Akmal pakai browser automation.
- Buat ngecek visual sendiri, pakai `npx remotion still` atau `npx remotion render ... --sequence --frames=<a>-<b>`.

### Laporan bug visual

- Fix yang dilaporin aja. Jangan redesain yang udah disetujui.
- Kalau laporannya ambigu, tanya 1 kali.
- Animasi baru ditiru dari source frame per frame. Ekstrak frame source pakai ffmpeg, terus bandingin sama hasil render.

### Pilihan kreatif

- SFX dan BGM yang milih Akmal. Jangan milih atau download sendiri.
- Kalau butuh SFX baru, minta link myinstants ke Akmal.

### Kode

- Komentar kode pakai bahasa Indonesia santai, sama kayak kode yang udah ada. Istilah teknis tetap English.
- Fitur baru: spec → plan → TDD (test merah dulu) → review → merge.
- Satu branch per fase. Di akhir fase, update `docs/HANDOFF.md` dan `docs/DECISIONS.md`.
- Langkah yang cuma hiasan (BGM, SFX, emoji, panah) nggak boleh bikin run gagal. Bungkus pakai try/except, terus tulis log.

### Git

- Commit boleh langsung tanpa nanya. Push harus nanya dulu.
- Pesan commit pakai Conventional Commits, bahasa Inggris, 1 baris, tanpa body.
- Jangan tambahin trailer `Co-Authored-By` atau atribusi AI dalam bentuk apa pun.

### Ngobrol sama Akmal

- Bahasa Indonesia santai, istilah teknis tetap English.
- Singkat. Kalimat pertama langsung langkah berikutnya.
- Jujur soal verifikasi: bilang mana yang udah dites dan mana yang belum.

## Windows (mesin Akmal)

- Shell yang dipakai Git Bash dan PowerShell.
- Python Windows nggak bisa baca path `/tmp/...`. Pakai `cygpath -m` atau path Windows.
- Escape kayak `\n` dan `\b` bisa rusak di heredoc Bash. Kalau patch-nya ada escape, tulis jadi file script dulu, baru dijalanin.
- Node 22: `nvm use 22.23.1`.
- Step yang lama (deteksi OWLv2 ±3 menit, render 5–8 menit) jalanin di background.
