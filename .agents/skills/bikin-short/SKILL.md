---
name: bikin-short
description: Bikin 1 video YouTube Shorts dari video source (URL/ID YouTube) pakai pipeline mayzfact, dari naskah sampai final.mp4 dan upload terjadwal ke YouTube, dengan checkpoint buat Akmal (isi link klip, review di Remotion Studio, oke render, konfirmasi jam tayang). Pakai kalau Akmal minta bikin video baru, lanjutin video yang setengah jadi, atau revisi video (make a short, new video, render).
---

# Bikin short

Alurnya:

source → naskah → suara → plan → **[Akmal isi link]** → fetch → timeline → **[Akmal review di Studio]** → render → **[Akmal cek final]** → metadata → **[Akmal konfirmasi jam]** → upload

Jangan lompatin checkpoint. Di tiap checkpoint, berhenti dan bilang ke Akmal persis apa yang harus dia lakuin. Aturan umum ada di `AGENTS.md`, terutama bagian Keamanan, Biaya, dan Review video.

## 1. Naskah, suara, plan

```bash
uv run mayzfact run <url atau id> --no-render
```

- CLI otomatis lanjut dari step yang belum ada. Kalau `runs/<id>/` udah ada, perintah yang sama ngelanjutin video itu, nggak mulai dari awal.
- Video baru makan kredit ElevenLabs sekali buat suaranya. Itu normal.
- Exit 3 dengan pesan "Nunggu input" artinya plan udah jadi. Lanjut ke langkah 2.
- Exit 1: baca pesan error-nya, lapor ke Akmal. Jangan retry berkali-kali.
- Buka `runs/<id>/script.json`. Tiap beat harus punya `point`, `emoji`, dan `emoji_word`, dan minimal beberapa beat ada isinya. Kalau semuanya kosong, lapor ke Akmal (jalur ini baru dites sekali, lihat HANDOFF 3C-2).

## 2. Checkpoint: Akmal isi link

Jalanin di background (servernya jalan terus):

```bash
uv run mayzfact brief <id>
```

CLI nge-print 2 alamat: `Lokal PC` (http://127.0.0.1:3100) dan `HP / LAN` (IP WiFi). Bilang ke Akmal:

1. Buka salah satu alamat itu. Video source ada di halaman, bisa diputer sambil ngisi.
2. Isi 1 link per shot (Douyin/TikTok/Pinterest/YouTube), atau upload file. Kolom Mulai/Selesai (detik) opsional, buat milih potongan tertentu dari klip.
3. Klik Simpan, terus kabarin.

Tunggu sampai Akmal bilang udah.

## 3. Fetch dan timeline

```bash
uv run mayzfact run <id> --from fetch --no-render
```

- Kalau ada shot yang gagal, run berhenti dengan exit 3 dan shot itu muncul lagi di brief. Kasih tau Akmal shot mana dan pesan error-nya, minta link lain atau upload, terus ulang langkah 3.
- Kalau udah nggak butuh isi link lagi, matiin server brief (dia kebuka ke LAN).
- Deteksi subjek (OWLv2) makan ±3 menit kalau belum ke-cache, jadi jalanin di background.
- Kalau log nyebut BGM/SFX/emoji/panah dilewat, video tetap jadi. Sebutin ke Akmal apa yang dilewat.

## 4. Checkpoint: review di Studio

1. Matiin proses lama di port 3000 kalau ada.
2. Start Studio di background:

   ```bash
   cd remotion && npx remotion studio src/index.ts --public-dir=../runs/<id> --props=../runs/<id>/timeline.json --port=3000 --no-open
   ```

3. Kasih Akmal tabel frame penting dari `timeline.json`: `countdown` (card), `emojis`, `cta`, `overlays` (panah). Tulis frame + detiknya (frame / 30).
4. Kalau Akmal minta revisi, ikutin aturan "Laporan bug visual" di `AGENTS.md`. Habis ngubah:
   - Kalau timeline berubah, jalanin `--from timeline --no-render` terus restart Studio.
   - Kalau cuma komponen Remotion yang berubah, Studio reload sendiri.
   - Minta Akmal review lagi.
5. Setelah Akmal oke, cek `git diff remotion/src`, karena Studio bisa nulis ke situ.

## 5. Render

Jalanin di background (5–8 menit):

```bash
uv run mayzfact run <id> --from render
```

Cek pakai `ffprobe`: resolusinya 1080×1920 dan durasinya masuk akal. Terus minta Akmal nonton `runs/<id>/final.mp4`.

## 6. Metadata YouTube

Agent nulis `runs/<id>/upload.json` dari `script.json` dan `clips.json`:

```json
{"title": "...", "description": "...", "tags": ["..."], "category_id": "15", "language": "en"}
```

- **title:** bahasa Inggris, maksimal 100 karakter, ada `#Shorts`, tanpa `<` `>`. Jangan clickbait yang nggak ada di video.
- **description:** 1–2 kalimat ringkasan, hashtag, terus credit: satu baris per sumber klip yang beda dari `clips.json` (`provider` + `page_url`, + `author` kalau ada; lewati `upload` tanpa `page_url`). Maksimal 5000 byte, tanpa `<` `>`.
- **tags:** 5–10 tag topik, total maksimal 500 karakter.
- **category_id:** pilih sesuai isi, misal `15` Pets & Animals, `27` Education, `28` Science & Technology, `24` Entertainment.

## 7. Checkpoint: konfirmasi jadwal

Jalanin `uv run mayzfact next-slot`. Tunjukin ke Akmal judul + jam usulan (WIB), terus tanya: jadwalin jam segitu atau jam lain? Tunggu jawabannya. Jangan upload sebelum Akmal konfirmasi.

## 8. Upload

Jalanin di background:

```bash
uv run mayzfact upload <id> --at "<YYYY-MM-DD HH:MM>"
```

- Kalau error "Belum login YouTube" atau "Token YouTube ditolak": minta Akmal jalanin `uv run mayzfact login youtube` (browser kebuka buat izin akun), terus ulang.
- Kalau error "udah pernah di-upload": jangan hapus `youtube.json` sendiri, tanya Akmal.
- Sukses: kasih Akmal link video dan link YouTube Studio dari output-nya.
