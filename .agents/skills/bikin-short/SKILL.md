---
name: bikin-short
description: Bikin 1 video YouTube Shorts dari video source (URL/ID YouTube) pakai pipeline mayzfact, dari nulis naskah sampai final.mp4 dan upload terjadwal ke YouTube, dengan checkpoint buat Akmal (review naskah, isi link klip, cek preview render). Pakai kalau Akmal minta bikin video baru, lanjutin video yang setengah jadi, atau revisi video (make a short, new video, render).
---

# Bikin short

Alurnya:

source → **[agent tulis naskah]** → **[Akmal review naskah]** → suara → plan → **[Akmal isi link]** → fetch → timeline → render → **[Akmal cek preview]** → metadata → upload YouTube → metadata TikTok (Akmal upload manual)

Jangan lompatin checkpoint. Di tiap checkpoint, berhenti dan bilang ke Akmal persis apa yang harus dia lakuin. Aturan umum ada di `AGENTS.md`, terutama bagian Keamanan, Biaya, dan Review video.

## Pola video baru: Top 3 (D-045, revisi CTA D-046)

Di branch ini, semua **naskah baru** wajib menulis `"narration_mode": "top3"`. Run lama tanpa field ini berarti `source`: aturan lama tetap berlaku, jangan migrasi atau ubah naskah/audio yang sudah dikunci.

- Source Top 5 → ambil peringkat asli **3, 2, 1**; pembahasan 5/4 dibuang utuh. Jangan pilih ulang atau tukar subjek. Source harus punya heading 3/2/1 yang bisa diverifikasi; kalau tidak, laporkan, jangan mengarang ranking.
- Urutan **hook → Number three + ≥2 beat penjelasan → Number two + ≥2 beat penjelasan → CTA → Number one + ≥2 beat penjelasan → selesai**. CTA tidak dihitung sebagai penjelasan.
- Target baseline **final.mp4 30–40 detik setelah speed-up**, bukan 80% durasi source. Pada speed 1.1x: anggaran dasar **80 kata**, rentang **76–84**, dengan allowance CTA 10 kata. Total valid = anggaran dasar + **max(0, jumlah kata seluruh blok CTA − 10)** pada target, batas bawah, dan batas atas. Contoh CTA 21 kata → target 91, valid 87–95; bukan narasi unlimited. CLI menskalakan anggaran dasar jika speed berubah, lalu menambahkan delta kata CTA aktual tanpa diskala ulang. Jangan potong/ubah wording non-CTA pada revisi CTA, atau ubah speed/provider/stability otomatis untuk mengejar target.
- CTA satu blok **1–4 beat langsung sebelum Number one**, tiap beat **≤10 kata**, wajib mengajak **like, subscribe, comment**. Buka dengan transisi sebelum nomor satu, ajak like, tanyakan transformasi tombol fiktif yang lucu sesuai tema, subscribe kondisional jika berhasil, lalu ajak comment. Contoh empat beat yang disetujui: `But before number one, try tapping like.` / `Did the button turn into a volcano?` / `Subscribe if it worked,` / `and comment 'erupted'.` Variasikan gimmick sesuai topik video berikutnya, jangan selalu menyalin volcano. Ini hiburan yang diizinkan, bukan fitur platform yang diimplementasikan atau perilaku nyata yang diklaim sudah dites. Jangan pakai ancaman agama, hadiah/janji palsu, atau menahan nomor satu sampai penonton subscribe. Bentuk CTA lama tetap didukung secara struktural.
- Semua beat CTA (termasuk transisi/pertanyaan tanpa pemicu) memakai subject kosong, keyword visual CTA sendiri, tanpa point; hook menyebut tiga, bukan lima. Detektor bersama `cta_beat_indices` mengambil rentang antar-anchor ajakan/lead-in `But before number one` atau `Before number one` dalam satu bagian countdown. Jangan sisipkan body item di rentang ini atau menyisakan body setelah CTA sebelum Number one; pertanyaan gimmick bukan beat penjelasan. Sesudah suara jadi, laporkan estimasi final dari durasi nyata / speed: tambahan CTA boleh memperpanjang baseline 30–40 detik. Kalau di luar target, kabarkan dan pertahankan audio; perubahan yang memakai kredit perlu persetujuan. Durasi akhir hanya terverifikasi sesudah ffprobe pada render yang diminta.

Aturan fakta/hedges, ≤10 kata per beat, foto 15–45%, overlap ≤15%, emoji/keyword, serta checkpoint review tetap berlaku.

### Visual CTA baru: opt-in scene (D-048)

Semua naskah Top 3 **baru** menulis metadata visual `cta_scene` di root. Run lama tanpa metadata tetap legacy; jangan migrasi naskah/audio berbayar otomatis. Revisi visual saja tidak mengubah teks atau hash suara.

```json
"cta_scene": {"theme": "volcano", "transform_word": "turn", "comment_text": "ERUPTED"}
```

`transform_word` harus kata tunggal yang benar-benar ada di pertanyaan. Untuk contoh `Did the button turn into a volcano?`, mulai morph saat **turn**, sehingga gunung sudah utuh saat **volcano**. Background CTA memakai blur kaca ringan (10px, brightness 0.78), sehingga footage masih terlihat. Setiap elemen CTA wajib entrance/exit halus dalam durasi stage: like spring+klik/ripple/partikel, morph volcano, subscribe melebar+huruf stagger/klik/confetti, comment diketik lalu fade-out. Jangan muncul penuh pada frame pertama; jangan ubah cue/audio demi memperpanjang animasi. Like baru muncul saat frasa ajakan `try tapping like` mulai terdengar, bukan sejak transisi `But before number one`; klik tetap pada kata like. Subscribe dan comment pada kata aslinya. Semua stage selesai sebelum Number one, caption tetap di bawah. Jika alignment event tidak ada, batas struktural dilabeli `structure`, tidak boleh mengarang timestamp kata.

Tema CTA baru wajib ilustrasi objek yang benar-benar disebut dalam pertanyaan transformasi, bukan kartu kata. Tema ilustrasi yang didukung: `volcano`, `unicorn`, `honey`, `puppy`, `lion`, `shark`. Contoh madu: `{"theme":"honey","transform_word":"turn","comment_text":"HONEY"}` dengan narasi `Did the button turn into honey?`; gambar madu menetes dari honey dipper ke jar, bukan teks HONEY. `theme: "word"` hanya untuk membaca run legacy, ditolak `check-script` untuk naskah baru. Kalau objek belum didukung, STOP dan tambahkan ilustrasi + tes fixture sebelum TTS; jangan pilih tema lain atau kartu teks sebagai pengganti. Validator mencocokkan nama tema dengan objek frasa `into [a/an/the] <objek>` dalam beat transformasi. Renderer harus menolak tema tak dikenal, bukan fallback ke teks. Field metadata tak dikenal tetap ditolak. Revisi visual mempertahankan voice/ASR/speed/BGM/SFX, timing dan link; backup metadata, ubah tema di script/plan/timeline saja, lalu cocokkan hash dan diff sebelum render fixture terisolasi.

Plan tetap menyimpan shot/durasi blok detector bersama, tapi kelompok **AUTO CTA** tidak membutuhkan frame referensi, keyword pencarian manual, link, upload, trim atau SFX baru. Brief menandainya otomatis, tidak menampilkan kontrol input. Fetch meminjam hanya video lokal non-CTA yang sudah tampil sebelum scene, dipilih seeded deterministik; pemakaian berulang meneruskan offset dan loop klip pendek. Tidak memakai footage item satu atau meminta link CTA baru. Kalau belum ada video sebelumnya, fallback warna bergerak. `reused=true` dan `match=null` adalah dekorasi yang disengaja, bukan kegagalan relevansi/duplikasi. Link/timestamp non-CTA milik Akmal jangan diubah.

## 1. Source

```bash
uv run mayzfact run <url atau id> --no-render
```

Run pertama bikin `runs/<id>/source.json` (transcript + durasi), `source.mp4`, dan frame hook `runs/<id>/plan/seg_XX_K.jpg`, terus berhenti dengan exit 3 "Naskah belum ada". Kalau `source.mp4` gagal di-download (log `[source] video/frame hook dilewat`), lanjut aja: frame nyusul di step plan. Kalau `runs/<id>/` udah ada, perintah yang sama ngelanjutin video itu, nggak mulai dari awal.

## 2. Tulis naskah

Agent nulis `runs/<id>/script.json`. Ini tanggung jawab agent, nggak ada LLM lain di pipeline. Aturannya:

**Isi.** Nulis ulang source: fakta, urutan item terpilih, dan momen-momennya tetap, kata-katanya baru. Jangan nambah fakta dari luar source. Pertahankan kata pembatas source ("some species", "one of the"); jangan dilebih-lebihin. Mode `top3` hanya peringkat asli 3/2/1; mode `source` lama mempertahankan semua item. Tiap item diumumin "Number N, [subject]." dan dapat minimal 2 beat penjelasan non-CTA.

Tiap beat harus bisa ditunjuk kalimat source-nya (kolom "dasar dari source" di langkah 3). Beat yang nggak punya dasar itu rekaan, hapus. Pengecualiannya cuma beat CTA. Kesalahan yang sering kejadian:

- Intro/teaser rekaan. Kalau source langsung masuk item pertama, naskah juga langsung masuk. Jangan nambahin "Five crazy facts you never knew" atau "Wait until you see number five".
- Ganti kata yang ngubah arti. "Strong enough to sit on" ≠ "buoyant enough to sit on" (kuat ≠ ngapung). Kalau ragu, pakai kata kerja/sifat yang sama kayak source.
- Nambah perbandingan atau angka. "Easily digested" ≠ "digests faster". Jangan bikin "faster/bigger/most" kalau source nggak bilang.
- Ngerasin klaim. "Can die if kept underwater" ≠ "will suffocate when trapped". "Can/may/some" di source tetap "can/may/some". Jangan pakai "zero", "always", "never", "will" kalau source nggak bilang.
- Detail source yang dibuang. Kalau source bilang "sit on it and even walk on it", dua-duanya masuk.

**Hook (beat 1–2).** Di sini penonton mutusin nonton atau swipe. Label kategori → teaser nomor 1 tetap dari source; dalam mode `top3`, CTA tidak di hook, melainkan tepat sebelum pengumuman Number one. Mode `source` lama mempertahankan urutan source.

1. Beat 1 kalimat lengkap yang nunjuk ke layar: dibuka "These…" dan ada kata kerjanya. Jangan judul doang. Dalam mode `top3`, sesuaikan hitungan menjadi three: "These three animals can vanish in plain sight." Pertahankan pembatas source, jangan menambahkan "literally" jika source tidak mengatakannya.
2. Kata kerja dan kata pembatas source tetap (can, literally, probably, might, some of the).
3. Kalau source punya teaser nomor 1, jadiin beat 2 dan bagian paling ekstremnya jangan dilemahin: "number one is absolutely terrifying" → beat 1 diakhiri koma, beat 2 "and number one is absolutely terrifying."
4. Teaser jangan dibuka "Number one" + koma/titik/titik dua/strip, karena itu kebaca jadi card countdown (`mayzfact/countdown.py`). Yang aman: "and number one looks…", "Wait for number one."

**Nada.** Persis source. Kalau source santai dan pakai "bro", naskah juga. Tiap item ditutup celetukan atau perbandingan sehari-hari kayak source, tapi gambarannya bikin sendiri: jangan disalin, jangan cuma ganti sinonim (source "Bro, that's one unusual-looking cat" → "Bro, a cat in a wetsuit."). Hindari kata bombastis (terrifyingly, blazing, lightning-fast). Kalau mau beda dari source, ubah struktur kalimat dan sudut pandangnya, jangan cuma ganti sinonim.

**Alur.** Suara dibikin sekali jalan, tapi ElevenLabs v3 baca tiap titik/tanda tanya sebagai kalimat baru: nada dan emosinya mulai lagi dari nol, jadi tiap shot kedengeran kayak ganti konteks (D-036). Jadi:

1. Satu ide = satu kalimat yang dipecah ke beberapa beat. Beat yang ngelanjutin kalimat diakhiri koma dan dibuka kata sambung kalau perlu (and, so, for, with, which, but).
2. Titik cuma di akhir CTA, "Number N, [subject].", kalimat penjelasan sebelum celetukan, celetukan, dan beat terakhir. Pengecualian CTA hiburan Top 3 (D-046): transisi ajakan dan pertanyaan transformasi boleh berupa kalimat utuh seperti contoh di atas.
3. Jangan pakai tanya retoris atau potongan pendek di tengah item ("Result? …", "Plus wrinkles. …").
4. Tiap beat tetap ≤ 10 kata dan 1 ide visual; yang berubah cuma tanda baca dan kata sambungnya.
5. CTA juga mengalir, jangan ditempel sebagai "Like and subscribe." Dalam mode `top3`, pakai transisi → ajakan like → pertanyaan gimmick sesuai tema → subscribe jika berhasil + comment, maksimal empat beat tepat sebelum Number one. `try tapping like` dan `like if ...` pada awal klausa memicu animasi, termasuk sesudah koma; "if you like them, subscribe" tetap bukan ajakan like. Naskah baru memakai scene D-048 di atas; tanpa metadata, animasi legacy hanya like/subscribe. Mode `source` lama boleh memakai konektor seperti "So comment which one's most unique," / "and don't forget to like and subscribe."

Contoh: "Number four, Scottish Fold." / "Ears fold forward and down," / "for an adorable round face," / "almost like it's always eavesdropping."

**Panjang.** Mode `top3`: target baseline final **30–40 detik**, anggaran dasar **80 kata / 76–84** pada speed 1.1x, lalu tambah **max(0, kata blok CTA − 10)** untuk total (contoh 21 kata CTA → **91 / 87–95**). Maksimal CTA 4×10 kata, bukan pembebasan batas body. Pertahankan wording non-CTA saat hanya CTA direvisi. Jangan memotong fakta/hedges item terpilih hanya agar muat; padatkan kalimat pada penulisan baru, buang hiasan, dan laporkan jika detail penting tidak bisa dipertahankan. Teaser nomor satu dipertahankan kalau source punya. CTA ekstra boleh memperpanjang final; laporkan TTS nyata / speed, jangan menjanjikan durasi dari hitungan kata. ffprobe final memberi hasil akhir. Mode `source` lama: target ±80% durasi source, target CLI 2.2 kata/detik, tulis di bawah atau pas target lama.

**Format.** Tiap beat ≤ 10 kata, 1 ide visual:

```json
{
  "narration_mode": "top3",
  "beats": [
    {"text": "Number three, mantis shrimp.", "media": "video", "queries": ["mantis shrimp close up underwater"],
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

> "Number three, mantis shrimp." / "This little guy throws one of the fastest punches alive." / "The shockwave alone knocks its prey out cold." / "Bro, never pick a fight with this guy."

Contoh ini hanya bentuk beat; nama dan nomor wajib cocok dengan peringkat asli source, fakta/hedges tetap diaudit.

Terus:

```bash
uv run mayzfact check-script <id>
```

Perbaiki sampai keluar `OK`. Kalau cek jumlah kata gagal, tambah/kurangi beat, jangan nambah kata ke beat yang ada.

`OK` cuma berarti format dan jumlah kata lolos. Sebelum nunjukin ke Akmal, cek sendiri tiap beat terhadap aturan **Isi** di atas: ada dasar kalimat source-nya, artinya sama, nggak ada perbandingan/angka/klaim yang lebih keras.

## 3. Checkpoint: Akmal review naskah

Tunjukin ke Akmal di chat, per beat: teks baru | kalimat source yang jadi dasarnya | keyword. Tunggu "oke" atau koreksi. Edit sesuai koreksi, cek lagi, tunjukin lagi. **Jangan lanjut ke langkah 4 sebelum Akmal oke** (langkah 4 bikin suara, pakai kredit ElevenLabs).

## 4. Suara dan plan

**Delivery default (D-047):** Akmal memilih sample 2 `2-kalem-natural`: ElevenLabs `eleven_v3`, voice `TX3LPaxmHKxFdv7VOQHJ`, stability **0.5**, prefix request **`[calm] `**. Berlaku untuk short baru dan revoice penuh video saat ini yang sudah disetujui. Jangan tulis tag ke `script.json`, beat atau caption, dan jangan mengubah wording untuk delivery. `Settings.elevenlabs_delivery_tag="calm"`; string kosong menonaktifkan prefix untuk request baru saja. Override nonrahasia lewat `settings.local.json`, bukan `.env`. Voice lama tetap terkunci; revoice perlu backup + izin, bukan generate ulang otomatis. `run_tts` menyimpan audio/raw alignment sebelum validasi; mismatch menghentikan step dengan pending tetap aman, jangan bayar ulang atau mengarang timestamp. Timestamp ucapan tidak digeser saat entri prefix dibuang.

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

- **title (gaya @eunoiapicks):** bahasa Inggris, maksimal 100 karakter, tanpa `<` `>`. Wajib ada **1–2 kata ALL-CAPS** penekanan emosi (`MORE`, `RARE`, `KILL`, `UNREAL`, `STRANGEST`, `NEVER`) + **tanda seru `!`** + **3 hashtag** di akhir judul (`#animals #wildlife #shorts` atau hashtag spesifik topik + `#shorts`). Contoh: `3 Ocean Predators MORE Deadly Than Sharks! #animals #wildlife #shorts`. Jangan clickbait yang nggak ada di video.
- **description:** 2–3 kalimat ringkasan yang menyebut subjek spesifik di video (mengandung kata kunci pencarian US/UK), terus 3–5 hashtag. Jangan masukin daftar credit/link klip (Akmal nggak mau). Maksimal 5000 byte, tanpa `<` `>`.
- **tags (long-tail SEO ala @eunoiapicks):** **15–25 long-tail tags** (nama semua spesies di video + variasi frasa pencarian Bahasa Inggris seperti `"most powerful ocean predators"`, `"amazing animal facts"`, `"wildlife facts"`, `"US wildlife"`, `"UK wildlife"`), total maksimal ≤450 karakter termasuk tanda kutip untuk tag berspasi (YouTube API menghitung tag berspasi sebagai `"..."` + koma, batas keras API 500 char).
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
- Sukses: commit hasil upload lalu langsung push ke origin tanpa nanya lagi (izin tetap Akmal). Jangan ikutkan perubahan lain yang belum disetujui; kalau push gagal, laporkan tanpa force-push. Verifikasi commit ada di remote sebelum bilang sudah ke-push.
- Kabarin Akmal jam tayang, link video, dan link YouTube Studio dari output-nya.

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
