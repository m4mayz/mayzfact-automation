---
name: bikin-short
description: Bikin 1 video YouTube Shorts dari video source (URL/ID YouTube) pakai pipeline mayzfact, dari naskah sampai final.mp4 dan metadata upload, dengan checkpoint buat Akmal (isi link klip, review di Remotion Studio, oke render). Pakai kalau Akmal minta bikin video baru, lanjutin video yang setengah jadi, atau revisi video (make a short, new video, render).
---

# Bikin short

Alurnya:

source → naskah → suara → plan → **[Akmal isi link]** → fetch → timeline → **[Akmal review di Studio]** → render → **[Akmal cek final]** → metadata upload → **[Akmal upload]**

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

Bilang ke Akmal:

1. Buka <http://127.0.0.1:3100>.
2. Isi link per kelompok. Link Douyin/TikTok boleh lebih dari satu per kelompok, atau upload file.
3. Klik Simpan, terus kabarin.

Tunggu sampai Akmal bilang udah.

## 3. Fetch dan timeline

```bash
uv run mayzfact run <id> --from fetch --no-render
```

- Kalau ada kelompok yang gagal, run berhenti dengan exit 3 dan kelompok itu muncul lagi di brief. Kasih tau Akmal kelompok mana dan pesan error-nya, minta link lain atau upload, terus ulang langkah 3.
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

## 6. Metadata upload

Agent yang nulis `runs/<id>/upload.md`, berdasarkan `script.json` dan `clips.json`:

- **Judul:** bahasa Inggris, maksimal 70 karakter, sesuai isi naskah. Jangan clickbait yang nggak ada di video.
- **Deskripsi:** 1–2 kalimat ringkasan, terus `#shorts` plus 3–5 hashtag topik.
- **Credit:** satu baris per sumber klip yang beda dari `clips.json`: `provider` + `page_url` (+ `author` kalau ada). Lewati shot yang `provider`-nya `upload` dan nggak punya `page_url`.
- **Jadwal:** slot berikutnya yang masih kosong, jam 21.00 atau 04.00 WIB.

## 7. Checkpoint: Akmal upload

Akmal yang upload dan jadwalin sendiri di YouTube Studio pakai isi `upload.md`. Agent nggak upload sendiri, dan nggak ngakses akun YouTube Akmal.
