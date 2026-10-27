---
name: bikin-short
description: Bikin 1 video YouTube Shorts dari video source (URL/ID YouTube) pakai pipeline mayzfact, dari nulis naskah sampai final.mp4 dan upload terjadwal ke YouTube, dengan checkpoint buat Akmal (review naskah, isi link klip, cek preview render). Pakai kalau Akmal minta bikin video baru, lanjutin video yang setengah jadi, atau revisi video (make a short, new video, render).
---

# Bikin short

Alurnya:

source → **[agent tulis naskah]** → **[Akmal review naskah]** → suara → plan → **[Akmal isi link]** → fetch → timeline → render → **[Akmal cek preview]** → metadata → upload YouTube → metadata TikTok (Akmal upload manual)

Jangan lompatin checkpoint. Di tiap checkpoint, berhenti dan bilang ke Akmal persis apa yang harus dia lakuin. Aturan umum ada di `AGENTS.md`, terutama bagian Keamanan, Biaya, dan Review video.

## 1. Source

```bash
uv run mayzfact run <url atau id> --no-render
```

Run pertama bikin `runs/<id>/source.json` (transcript + durasi), `source.mp4`, dan frame hook `runs/<id>/plan/seg_XX_K.jpg`, terus berhenti dengan exit 3 "Naskah belum ada". Kalau `source.mp4` gagal di-download (log `[source] video/frame hook dilewat`), lanjut aja: frame nyusul di step plan. Kalau `runs/<id>/` udah ada, perintah yang sama ngelanjutin video itu, nggak mulai dari awal.

## 2. Tulis naskah

Agent nulis `runs/<id>/script.json`. Ini tanggung jawab agent, nggak ada LLM lain di pipeline. Aturannya:

**Isi.** Nulis ulang source: fakta, urutan item, dan momen-momennya tetap, kata-katanya baru. Jangan nambah fakta dari luar source. Pertahankan kata pembatas source ("some species", "one of the"); jangan dilebih-lebihin. Kalau source ngitung ("Number five…"), urutan dan jumlah item sama, tiap item diumumin "Number N, [subject]." dan dapat minimal 2 beat penjelasan.

Tiap beat harus bisa ditunjuk kalimat source-nya (kolom "dasar dari source" di langkah 3). Beat yang nggak punya dasar itu rekaan, hapus. Pengecualiannya cuma beat CTA. Kesalahan yang sering kejadian:

- Intro/teaser rekaan. Kalau source langsung masuk item pertama, naskah juga langsung masuk. Jangan nambahin "Five crazy facts you never knew" atau "Wait until you see number five".
- Ganti kata yang ngubah arti. "Strong enough to sit on" ≠ "buoyant enough to sit on" (kuat ≠ ngapung). Kalau ragu, pakai kata kerja/sifat yang sama kayak source.
- Nambah perbandingan atau angka. "Easily digested" ≠ "digests faster". Jangan bikin "faster/bigger/most" kalau source nggak bilang.
- Ngerasin klaim. "Can die if kept underwater" ≠ "will suffocate when trapped". "Can/may/some" di source tetap "can/may/some". Jangan pakai "zero", "always", "never", "will" kalau source nggak bilang.
- Detail source yang dibuang. Kalau source bilang "sit on it and even walk on it", dua-duanya masuk.

**Hook (beat 1–2).** Di sini penonton mutusin nonton atau swipe (±40% swipe di video lama). Urutan source tetap (label kategori → teaser nomor 1 → CTA), kalimatnya yang dipoles:

1. Beat 1 kalimat lengkap yang nunjuk ke layar: dibuka "These…" dan ada kata kerjanya. Jangan judul doang: "Top five animals that can disappear in plain sight." → "These five animals can literally vanish in plain sight."
2. Kata kerja dan kata pembatas source tetap (can, literally, probably, might, some of the).
3. Kalau source punya teaser nomor 1, jadiin beat 2 dan bagian paling ekstremnya jangan dilemahin: "number one is absolutely terrifying" → beat 1 diakhiri koma, beat 2 "and number one is absolutely terrifying."
4. Teaser jangan dibuka "Number one" + koma/titik/titik dua/strip, karena itu kebaca jadi card countdown (`mayzfact/countdown.py`). Yang aman: "and number one looks…", "Wait for number one."

**Nada.** Persis source. Kalau source santai dan pakai "bro", naskah juga. Tiap item ditutup celetukan atau perbandingan sehari-hari kayak source, tapi gambarannya bikin sendiri: jangan disalin, jangan cuma ganti sinonim (source "Bro, that's one unusual-looking cat" → "Bro, a cat in a wetsuit."). Hindari kata bombastis (terrifyingly, blazing, lightning-fast). Kalau mau beda dari source, ubah struktur kalimat dan sudut pandangnya, jangan cuma ganti sinonim.

**Alur.** Suara dibikin sekali jalan, tapi ElevenLabs v3 baca tiap titik/tanda tanya sebagai kalimat baru: nada dan emosinya mulai lagi dari nol, jadi tiap shot kedengeran kayak ganti konteks (D-036). Jadi:

1. Satu ide = satu kalimat yang dipecah ke beberapa beat. Beat yang ngelanjutin kalimat diakhiri koma dan dibuka kata sambung kalau perlu (and, so, for, with, which, but).
2. Titik cuma di akhir CTA, "Number N, [subject].", kalimat penjelasan sebelum celetukan, celetukan, dan beat terakhir.
3. Jangan pakai tanya retoris atau potongan pendek di tengah item ("Result? …", "Plus wrinkles. …").
4. Tiap beat tetap ≤ 10 kata dan 1 ide visual; yang berubah cuma tanda baca dan kata sambungnya.
5. CTA juga disambung, jangan ditempel. "Like and subscribe." yang berdiri sendiri kedengeran tiba-tiba. Masuk ke CTA pakai kata penghubung, terus like/subscribe disambung ke ajakan comment: "So comment which one's most unique," / "and don't forget to like and subscribe." Polanya harus tetap kebaca `mayzfact/cta.py`: "like" diikuti and/or/subscribe/button, atau didahului hit/smash/tap/give/drop/leave. Contoh yang nggak kebaca: "if you like them, subscribe" (cuma subscribe yang kepicu).

Contoh: "Number four, Scottish Fold." / "Ears fold forward and down," / "for an adorable round face," / "almost like it's always eavesdropping."

**Panjang.** ±80% durasi source. `check-script` ngasih target kata; tulis **di bawah atau pas target**, jangan di atas, walaupun toleransinya ±15%. `check-script` ngitung 2.2 kata/detik (ElevenLabs v3 aslinya 1.9–2.3; makin banyak titik makin lambat), jadi naskah pas target hasilnya ±77–85% durasi source. Pendekin dengan buang kata hiasan ("actually", "just like", "way", "amazing", "for more"), bukan dengan buang fakta. Intro dipadetin. CTA source dipadetin ke comment + like + subscribe dalam 1–2 beat, dan **harus pakai kata "like" dan "subscribe" beneran** (itu pemicu animasi CTA). Teaser nomor 1 di hook dipertahankan kalau source punya.

**Format.** Tiap beat ≤ 10 kata, 1 ide visual:

```json
{
  "beats": [
    {"text": "Number five, mantis shrimp.", "media": "video", "queries": ["mantis shrimp close up underwater"],
     "queries_zh": ["螳螂虾 特写"], "subject": "mantis shrimp", "point": false, "emoji": "", "emoji_word": ""}
  ],
  "hook_queries": {"0": {"en": ["giant bird on radio tower"], "zh": ["巨鸟 铁塔"]}}
}
```

- `queries`: 2–3 keyword Inggris yang ngegambarin **yang kelihatan pas beat itu**, nyambung sama teksnya: subjek + aksi + tempat. Beat CTA/intro pakai visual yang cocok sama kalimatnya ("hand tapping phone like button"). `queries_zh`: versi Mandarin, cara orang nyari di Douyin.
- `media`: "photo" buat 15–45% beat (close-up subjek), beat pertama selalu "video". `subject`: 1–3 kata benda yang **kelihatan di gambar**, dipakai deteksi subjek buat posisi panah (misal "goat", bukan "goat milk"; "turtle", bukan "drowning reptiles"). "" buat intro/CTA.
- `point`: true kalau beat ngajak lihat sesuatu atau subjeknya baru muncul di layar; agent yang nentuin, nggak ada kuota. Jangan di beat countdown/teaser.
- `emoji`: dari daftar di `mayzfact/emoji.py` (`EMOJI`), kira-kira 1 dari 3 beat, nggak 2 beat berturut-turut, nggak di beat countdown. `emoji_word`: kata di beat itu tempat emoji muncul.
- `hook_queries`: lihat frame `runs/<id>/plan/seg_*.jpg` (index segmen = angka di nama file minus 1), tulis keyword Inggris + Mandarin buat nyari klip yang mirip. `{}` kalau frame belum ada.

Contoh beat yang bagus (source: "This tiny marine predator can throw one of the fastest strikes in the animal kingdom, creating a shockwave powerful enough to stun its prey. Bro, that's basically a living underwater punch machine."):

> "Number five, mantis shrimp." / "This little guy throws one of the fastest punches alive." / "The shockwave alone knocks its prey out cold." / "Bro, never pick a fight with this guy."

Terus:

```bash
uv run mayzfact check-script <id>
```

Perbaiki sampai keluar `OK`. Kalau cek jumlah kata gagal, tambah/kurangi beat, jangan nambah kata ke beat yang ada.

`OK` cuma berarti format dan jumlah kata lolos. Sebelum nunjukin ke Akmal, cek sendiri tiap beat terhadap aturan **Isi** di atas: ada dasar kalimat source-nya, artinya sama, nggak ada perbandingan/angka/klaim yang lebih keras.

## 3. Checkpoint: Akmal review naskah

Tunjukin ke Akmal di chat, per beat: teks baru | kalimat source yang jadi dasarnya | keyword. Tunggu "oke" atau koreksi. Edit sesuai koreksi, cek lagi, tunjukin lagi. **Jangan lanjut ke langkah 4 sebelum Akmal oke** (langkah 4 bikin suara, pakai kredit ElevenLabs).

## 4. Suara dan plan

```bash
uv run mayzfact run <id> --no-render
```

Exit 3 "Nunggu input" = plan udah jadi, lanjut ke brief (langkah 5). Exit 1: baca pesan error-nya, lapor ke Akmal. Jangan retry berkali-kali.

## 5. Checkpoint: Akmal isi link

Jalanin di background (servernya jalan terus):

```bash
uv run mayzfact brief <id>
```

Jalanin pakai `PYTHONUNBUFFERED=1` biar alamatnya langsung kebaca di log. Brief otomatis buka tunnel ngrok ber-password (`NGROK_BASIC_AUTH` di `.env`). CLI nge-print 3 alamat: `Internet` (URL ngrok, buat HP di jaringan mana aja), `HP / LAN` (IP WiFi), dan `Lokal PC` (http://127.0.0.1:3100). Kalau ada baris `ngrok gagal: ...`, brief tetap jalan lokal; kasih tau Akmal pesannya. Bilang ke Akmal:

1. Buka salah satu alamat itu (URL `Internet` minta login: user + password dari `NGROK_BASIC_AUTH`, Akmal udah tau). Video source ada di halaman, bisa diputer sambil ngisi. Tombol waktu di tiap shot muter suara naskah beat itu.
2. Isi 1 link per shot (Douyin/TikTok/Pinterest/YouTube), atau upload file. Kolom Mulai/Selesai (detik) opsional, buat milih potongan tertentu dari klip. Mulai kosong = video diambil dari detik 0, atau lanjut dari shot sebelumnya kalau link-nya sama (D-042). Tiap shot punya 3 frame source sebagai referensi. Kalau link-nya udah `siap`, tombol "Preview klip" nunjukin bagian yang bakal dipakai ("Pakai detik ini" ngisi Mulai). Pill SFX di tiap shot buat nambah 1 SFX kustom di detik tertentu (D-040).
3. Klik Simpan. Link langsung di-download di background; status per shot kelihatan (`antre` / `download…` / `siap` / `gagal`). Kalau ada yang `gagal`, ganti link-nya, atau klik Simpan lagi buat coba ulang (autosave nggak ngulang yang gagal).
4. Kalau semua `siap`, kabarin.

Tunggu sampai Akmal bilang udah. Kalau `brief` nolak jalan karena "belum punya frame referensi", jalanin `uv run mayzfact run <id> --from plan --no-render` dulu (`links.json` nggak disentuh).

## 6. Fetch dan timeline

```bash
uv run mayzfact run <id> --from fetch --no-render
```

- Link yang udah `siap` di brief nggak di-download lagi (cache sama), jadi fetch tinggal motong + nilai klip.
- Kalau Akmal cuma ganti SFX kustom di brief, cukup `--from timeline --no-render` (SFX-nya dibaca langsung dari `links.json`).
- Kalau ada shot yang gagal, run berhenti dengan exit 3 dan shot itu muncul lagi di brief. Kasih tau Akmal shot mana dan pesan error-nya, minta link lain atau upload, terus ulang langkah 6.
- Kalau udah nggak butuh isi link lagi, matiin server brief (dia kebuka ke LAN dan internet). Kalau brief dimatiin paksa (TaskStop), ngrok-nya bisa nyangkut: jalanin `Stop-Process -Name ngrok` di PowerShell.
- Deteksi subjek (OWLv2) makan ±3 menit kalau belum ke-cache, jadi jalanin di background.
- Kalau log nyebut BGM/SFX/emoji/panah dilewat, video tetap jadi. Sebutin ke Akmal apa yang dilewat.

## 7. Review di Studio (cuma kalau Akmal minta)

Default-nya dilewat: Akmal nggak review di Studio (D-035). Habis langkah 6 langsung ke langkah 8. Langkah di bawah cuma kalau dia minta Studio lagi.

1. Matiin proses lama di port 3000 kalau ada.
2. Start Studio di background:

   ```bash
   cd remotion && npx remotion studio src/index.ts --public-dir=../runs/<id> --props=../runs/<id>/timeline.json --port=3000 --no-open
   ```

3. Buka tunnel di background, terus kasih Akmal URL dari baris "kebuka di":

   ```bash
   PYTHONUNBUFFERED=1 uv run mayzfact tunnel 3000
   ```

   Akun ngrok gratis cuma boleh 1 sesi, jadi pastiin brief + ngrok-nya udah mati dulu (langkah 6). Habis review selesai, matiin tunnel-nya (`Stop-Process -Name ngrok` kalau dimatiin paksa).
4. Kasih Akmal tabel frame penting dari `timeline.json`: `countdown` (card), `emojis`, `cta`, `overlays` (panah). Tulis frame + detiknya (frame / 30).
5. Kalau Akmal minta revisi, ikutin aturan "Laporan bug visual" di `AGENTS.md`. Habis ngubah:
   - Kalau timeline berubah, jalanin `--from timeline --no-render` terus restart Studio.
   - Kalau cuma komponen Remotion yang berubah, Studio reload sendiri.
   - Minta Akmal review lagi.
6. Setelah Akmal oke, cek `git diff remotion/src`, karena Studio bisa nulis ke situ.

## 8. Render

Jalanin di background (5–8 menit):

```bash
uv run mayzfact run <id> --from render
```

Cek pakai `ffprobe`: resolusinya 1080×1920 dan durasinya masuk akal. Terus kirim preview 720p (`runs/<id>/preview.mp4`, maksimal 45 MB) ke Akmal, plus jam penting dari `timeline.json` (card `countdown`, `emojis`, `cta`, panah `overlays`; frame / 30 = detik), apa aja yang dilewat (BGM/SFX/emoji/panah), dan shot dengan skor relevansi < 0.10. Ini checkpoint review-nya: kalau Akmal minta revisi, ikutin "Laporan bug visual" di `AGENTS.md`, jalanin `--from timeline --no-render` kalau timeline berubah, render ulang, kirim preview lagi. Lanjut ke langkah 9 setelah Akmal oke.

## 9. Metadata YouTube

Agent nulis `runs/<id>/upload.json` dari `script.json` dan `clips.json`:

```json
{"title": "...", "description": "...", "tags": ["..."], "category_id": "15", "language": "en"}
```

- **title:** bahasa Inggris, maksimal 100 karakter, ada `#Shorts`, tanpa `<` `>`. Jangan clickbait yang nggak ada di video.
- **description:** 1–2 kalimat ringkasan, terus hashtag. Jangan masukin daftar credit/link klip (Akmal nggak mau). Maksimal 5000 byte, tanpa `<` `>`.
- **tags:** 5–10 tag topik, total maksimal 500 karakter.
- **category_id:** pilih sesuai isi, misal `15` Pets & Animals, `27` Education, `28` Science & Technology, `24` Entertainment.

## 10. Jadwal

Jalanin `uv run mayzfact next-slot` dan pakai slot kosong itu. Jangan nanya jam ke Akmal (D-037): langsung lanjut ke langkah 11, terus kabarin jam tayangnya setelah upload. Kalau Akmal nyebut jam sendiri, pakai jam itu. Kalau Akmal minta langsung public tanpa jadwal, pakai `--now` di langkah 11.

## 11. Upload

Jalanin di background:

```bash
uv run mayzfact upload <id> --at "<YYYY-MM-DD HH:MM>"   # terjadwal
uv run mayzfact upload <id> --now                         # langsung public, cuma kalau Akmal minta
```

- Kalau error "Belum login YouTube" atau "Token YouTube ditolak": minta Akmal jalanin `uv run mayzfact login youtube` (browser kebuka buat izin akun), terus ulang.
- Kalau error "udah pernah di-upload": jangan hapus `youtube.json` sendiri, tanya Akmal.
- Sukses: kabarin Akmal jam tayang, link video, dan link YouTube Studio dari output-nya.

## 12. Metadata TikTok

Akmal upload ke TikTok sendiri (manual). Begitu Akmal oke preview di langkah 8, agent sekalian nulis `runs/<id>/tiktok.json`:

```json
{"caption": "...", "cover_s": 1.0, "cover_text": "...", "ai_label": true}
```

- **caption:** bahasa Inggris, 1 kalimat hook + 1 pertanyaan buat komentar, terus 3–5 hashtag topik (tanpa `#fyp`/`#viral`). Maksimal 300 karakter biar kebaca tanpa "more".
- **cover_s:** detik di `final.mp4` buat cover (frame yang subjeknya paling jelas, biasanya di hook). **cover_text:** teks cover maksimal 40 karakter, boleh sama kayak judul YouTube tanpa `#Shorts`.
- **ai_label:** `true` (suara narasi dari ElevenLabs, dan TikTok minta label buat audio/visual AI yang realistis).

Habis upload YouTube sukses, tunjukin isi `tiktok.json` di chat biar Akmal tinggal copy, plus setting tetap ini:

- Who can watch: Everyone. Allow comments, Duet, Stitch: on.
- Disclose post content: off (bukan konten berbayar).
- AI-generated content: on.
- Jadwal: TikTok Studio desktop bisa jadwalin sampai 10 hari ke depan. Usulin jam yang sama kayak YouTube, Akmal yang mutusin.
