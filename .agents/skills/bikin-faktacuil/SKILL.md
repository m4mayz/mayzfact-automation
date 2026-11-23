---
name: bikin-faktacuil
description: Bikin 1 video YouTube Shorts format FaktaCuil (fakta unik bahasa Indonesia, channel FaktaCuil, `narration_mode` "faktacuil") dari video source Inggris sampai final.mp4 dan upload terjadwal ke channel FaktaCuil. Pakai kalau Akmal minta video FaktaCuil, video bahasa Indonesia, atau "channel kedua". Format MayzFact (Top 3, bahasa Inggris) pakai skill bikin-short.
---

# Bikin FaktaCuil

Format kedua pipeline mayzfact (D-051): satu video satu fakta, bahasa Indonesia santai, 20–30 detik. Alur, checkpoint, dan perintah dasarnya **sama kayak `bikin-short`**. Skill ini cuma nulis bagian yang beda; langkah yang sama dirujuk ke nomor langkah di `.agents/skills/bikin-short/SKILL.md`. Baca skill itu dulu kalau belum, dan aturan umum di `AGENTS.md` (Keamanan, Biaya, Review video) tetap berlaku.

Alurnya:

source → **[agent tulis naskah]** → **[Akmal review naskah]** → suara → plan → **[Akmal isi link]** → fetch → timeline → render → **[Akmal cek preview]** → metadata → upload ke channel FaktaCuil

Jangan lompatin checkpoint. Di tiap checkpoint, berhenti dan bilang ke Akmal persis apa yang harus dia lakuin.

## Yang beda dari top3

- Naskah wajib `"narration_mode": "faktacuil"`. Tanpa itu pipeline nolak.
- Source tetap video Inggris. Agent nerjemahin + nulis ulang ke bahasa Indonesia santai.
- Nggak ada card countdown, panah/lingkaran, emoji, intro, flash, dan SFX hook. Yang tetap: SFX transisi dan blur teks klip.
- Caption 1 kata, font Fredoka, kata `keyword` kuning (`#FFC53D`).
- Watermark bawaan render: logo + nama FaktaCuil di tengah atas, opacity 64%, tanpa pill. Tidak tampil di MayzFact.
- CTA opsional (D-061). Kalau dipakai: `lucky`/`subscribe` di tengah (like + `muncul` + stiker), `emoji` di akhir, plus CTA-2 kuis hitung kata di akhir. Subscribe/comment cuma boleh sesuai format itu.
- BGM 1 lagu sepanjang video, dari folder lokal.
- Suara, jadwal, dan channel upload sendiri.

## 1. Source

Sama kayak `bikin-short` langkah 1:

```bash
uv run mayzfact run <url atau id> --mode faktacuil --no-render
```

Source boleh video Inggris atau Indonesia. FaktaCuil adalah default sejak D-062. `mayzfact run <id> --no-render` coba transkrip Indonesia asli dulu; `--mode faktacuil` masih diterima. Run lama tetap mengikuti mode naskahnya.

Transkrip asli Indonesia tetap disimpan di `source.json` field `transcript_id`; kosong kalau videonya nggak punya (D-052).

Kalau source-nya Top N, boleh ambil **1 item** aja; semua fakta di naskah harus dari item itu. Step source jalan sebelum naskah ada, jadi dia tetap download `source.mp4` dan bikin frame `plan/seg_XX_K.jpg` walau format FaktaCuil. File itu nggak dipakai, abaikan.

## 2. Tulis naskah

Agent nulis `runs/<id>/script.json`. Kalau `transcript_id` nggak kosong, tulis dari teks Indonesia itu dan `check-script` ngebandingin overlap 4-gram ke teks itu (tulis ulang, jangan nyalin kalimat asli); kalau kosong, pakai `transcript` Inggris kayak biasa. Aturan **Isi** dari `bikin-short` langkah 2 tetap berlaku: tiap beat harus punya dasar kalimat di source, jangan nambah fakta, angka, atau perbandingan, jangan ngerasin klaim ("can/may/some" tetap "bisa/mungkin/sebagian"), dan pertahankan kata pembatas source. Terjemahan nggak boleh nambah apa pun.

**Rewrite saja.** Pakai transkrip yang dipilih sebagai satu-satunya rujukan narasi. Jangan riset tambahan, fact-check klaim, ganti angle buat membantah source, atau sisipkan "katanya" dan "belum terverifikasi" kalau pembatas itu nggak ada di source. Ringkas dengan kata baru tanpa mengubah isi atau urutan.

**Bahasa.** Indonesia santai: `nggak`, `udah`, `banget` boleh. Jangan maksa slang. Kata teknis yang biasa dipakai orang Indonesia tetap dipakai.

**Struktur.** Ikut posisi CTA:

- **CTA tengah (`lucky`/`subscribe`):** hook → salah kaprah (minimal 1 beat) → CTA 1–3 beat → jawaban minimal 2 beat. CTA-2 kuis (kalau ada) di beat paling akhir dan nggak dihitung sebagai beat jawaban.
- **CTA akhir (`emoji`, kuis) atau tanpa CTA:** hook → isi bebas. Nggak ada cek salah kaprah atau jumlah beat jawaban. Beat `emoji` (1–2 beat) dan beat kuis wajib jadi beat terakhir.

Kata pembuka "Padahal…"/"Ternyata…" cuma pola; kode nggak ngecek, jadi boleh divariasi. Hook juga bebas: satu-satunya patokan cuma ≤10 kata per beat.

**Aturan yang dicek `check-script`** (pesannya English):

| Aturan | Isi |
| --- | --- |
| F2 | Nggak ada beat "Number N,". |
| F3 | CTA opsional: `cta_scene` diisi = harus ada blok CTA; `cta_scene` kosong = jangan ada kata `like*`/`subscribe`/`komen`/`komentar`/`comment` di beat mana pun. Detektor blok pakai kata-kata itu sebagai anchor (nggak harus ajakan like), jadi "like" biasa pun bisa dianggap CTA. Kata `emoji` sendiri bukan anchor; dia cuma nempel ke blok yang udah ada. |
| F4 | `lucky`/`subscribe`: blok CTA 1–3 beat + minimal 1 beat salah kaprah sebelumnya. |
| F5 | `lucky`/`subscribe`: minimal 2 beat jawaban setelah CTA (beat kuis nggak dihitung). |
| F6 | Tepat 1 ajakan like Indonesia ("tekan/pencet/klik/kasih like", "tekan tombol like"). Nol `komen`/`komentar`/`comment`. `subscribe` cuma boleh di format `subscribe` dan harus **setelah** ajakan like. |
| F7 | Kecocokan format: `lucky`/`subscribe` wajib `muncul*` + nama objek tema di blok CTA; `subscribe` wajib kata `subscribe`; `emoji` wajib kata `emoji`, beat terakhir diakhiri `?`, dan bloknya 1–2 beat paling akhir. |
| F8 | Beat CTA dan beat kuis: `subject` kosong, `point` false, tanpa `keyword`. |
| F9 | Semua beat: `point` false, `emoji` dan `emoji_word` kosong. |
| F10 | `keyword` (kalau diisi) 1 kata yang ada di teks beat itu, bukan di beat CTA/kuis. |
| F11 | Jumlah kata total di rentang (lihat bawah). |
| kuis | `cta_quiz` dan beat kuis harus muncul bareng; beat kuis terakhir, nyebut `cta_quiz.word`, kata itu diucapin minimal 2x sebelum kuis, dan `answer` sama dengan hasil hitungan. `emoji` nggak boleh digabung kuis. |
| queries | Minimal 2 query English per beat, ASCII only. `queries_zh` diabaikan buat FaktaCuil. |
| umum | ≤10 kata per beat, foto 15–45% beat, overlap 4-gram dengan source ≤15%. |

**CTA opsional (D-061).** Kombinasi yang valid: tanpa CTA; `lucky`; `subscribe`; `emoji`; kuis; `lucky`+kuis; `subscribe`+kuis. `emoji` nggak pernah digabung CTA lain, termasuk kuis.

| format | posisi | contoh kalimat | kata kunci wajib | visual |
| --- | --- | --- | --- | --- |
| `lucky` | tengah | "tapi sebelum lanjut coba tekan like, jika beruntung bisa muncul madu" | ajakan like + `muncul` + nama objek tema | pill LIKE → klik → LIKED → stiker objek |
| `subscribe` | tengah | "tapi sebelum lanjut coba tekan like, nanti muncul madu, subscribe jika berhasil" | ajakan like + `muncul` + nama objek + `subscribe` **setelah** ajakan like | pill LIKE → LIKED → stiker → pill SUBSCRIBE → SUBSCRIBED |
| `emoji` | akhir, satu-satunya CTA | "tapi mengapa ada emoji madu saat tekan like?" | `emoji` + `tekan like` + diakhiri `?` | pill LIKE → klik → LIKED → emoji besar |
| kuis (CTA-2) | akhir | "nah coba tebak berapa kali aku bilang kardus" | `berapa kali aku bilang` + kata target | caption biasa, tanpa visual tambahan |

Kalimat contoh di tabel itu kepanjangan buat satu beat (maks 10 kata). **Wajib dipecah 2–3 beat**, contohnya:

- `lucky`: "Tapi sebelum lanjut, coba tekan like," / "jika beruntung bisa muncul madu."
- `subscribe`: "Tapi sebelum lanjut, coba tekan like," / "nanti muncul madu," / "subscribe jika berhasil."
- `emoji`: "Tapi mengapa ada emoji madu" / "saat tekan like?"

Urutannya tetap: beat yang nyebut `muncul` **selalu setelah** ajakan like, dan lead-in `emoji` **selalu sebelum** "tekan like". Beat objek/lead-in boleh tanpa kata "like" asal nyebut `muncul`/`emoji`. Urutan `subscribe` jangan dibalik: ajakan like dulu, baru `subscribe`.

`cta_scene` opsional:

```json
"cta_scene": {"format": "lucky", "theme": "honey"}
"cta_scene": {"format": "subscribe", "theme": "honey"}
"cta_scene": {"format": "emoji", "emoji": "🍯"}
```

`cta_quiz` opsional (cuma FaktaCuil, sendiri atau bareng `lucky`/`subscribe`):

```json
"cta_quiz": {"word": "kardus", "answer": 2}
```

- `answer` = jumlah kata `cta_quiz.word` sebelum beat kuis. Hitung manual, `check-script` yang mastiin (case-insensitive, kata utuh; "kardusnya" atau "kardus-kardus" nggak ikut, kalimat kuis sendiri nggak dihitung).
- `emoji` = karakter emoji apa aja, nggak dibatasi daftar `EMOJI`. Kecocokan "emoji madu" ↔ 🍯 dicek Akmal waktu review naskah, bukan code.
- Format lama (`question`/`reveal`/`escape`/`escalate`) udah dihapus. Naskah lama ditolak dengan pesan jelas dan file run-nya dibiarin.
- Objek stiker harus salah satu dari tema di bawah. Nggak ada yang cocok = **STOP**, bikin stiker baru dulu (lihat **Stiker baru**).

| theme | nama objek di kalimat CTA |
| --- | --- |
| `volcano` | `gunung berapi`, `gunung meletus`, `gunung api` |
| `unicorn` | `unicorn` |
| `honey` | `madu` |
| `puppy` | `anak anjing`, `anjing` |
| `lion` | `singa` |
| `shark` | `hiu`, `ikan hiu` |
| `toilet` | `kloset jongkok`, `toilet` |
| `cat` | `kucing`, `anak kucing` |
| `zebra` | `zebra`, `zebra cross` |
| `wheel` | `roda mobil`, `ban mobil` |

**Stiker baru.** Kalau objek nggak cocok sama tema yang ada, STOP sebelum render dan kerjain dulu:

1. Komponen SVG 200x200 di `remotion/src/FaktaCuilStickers.tsx` + `case` di `Sticker`.
2. Literal tema di `StickerTheme` (`remotion/src/types.ts`).
3. Literal tema di `FaktaCuilTheme` (`mayzfact/models.py`).
4. Nama Indonesia di `THEME_NOUNS_ID` (`mayzfact/faktacuil.py`).
5. Cek pakai `uv run pytest tests/test_faktacuil_cta_v2.py`, `cd remotion && npx tsc --noEmit -p .`, dan `npx remotion still` buat lihat gambarnya.

Top3 nggak ikut berubah.

**Per beat.**

- `keyword`: 1 kata yang ditekankan (caption-nya kuning), isi di ±1 dari 3 beat, bukan beat CTA/kuis. Kata yang dipilih sering bukan subjek ("ternyata", "aman"). Tanda hubung boleh (`kupu-kupu`).
- `point` selalu false, `emoji` dan `emoji_word` selalu kosong.
- `subject`: hewan/objek yang dibahas, kosong di beat CTA dan beat kuis.
- `queries`: minimal 2 query bahasa Inggris (ASCII) per beat; panduannya 2–4 query (`check-script` cuma ngecek minimal 2), nyebut hal yang beneran keliatan di kalimat beat itu (subjek + aksi/objek). Contoh beat "Padahal kardus itu sempit dan nggak empuk" → `cat squeezing into small cardboard box`, bukan cuma `cat`. Beat CTA juga wajib punya `queries`: isi background yang cocok sama kalimat CTA (shot CTA minta link di brief kayak shot lain, D-053). `queries_zh` nggak dipakai FaktaCuil (diabaikan).
- `hook_queries` selalu `{}`: FaktaCuil nggak punya segmen hook dari source.
- Beat pertama otomatis jadi video.

**Panjang.** Kata CTA ikut dihitung. Rumusnya `kata = detik_final × video_speed × FAKTACUIL_RAW_WPS` (2.27, dari sampel Eric). Default ElevenLabs dirender di **1,1×**, target **62 kata, rentang 50–74**. Pakai angka yang diprint `check-script` ("target T") kalau beda.

Selesai nulis:

```bash
uv run mayzfact check-script <id>
```

`OK` berarti cek format, jumlah kata, dan overlap lolos. Cocokkan isi tiap beat dengan transkrip, bukan dengan sumber luar, sebelum kirim naskah ke Akmal.

## 3. Checkpoint: Akmal review naskah

Kirim naskah final persis seperti yang bakal dibacain, per beat beserta dasar dari transkrip, `queries`, dan `keyword` caption. Beat CTA dasarnya "CTA gimmick" (kalau ada). Buat format `emoji`, cek karakternya cocok sama kalimat (misal "emoji madu" ↔ 🍯). **Tunggu Akmal okein versi naskah ini** sebelum bikin suara atau buka brief upload audio. Kalau naskah direvisi, kirim ulang dan tunggu approval baru. Approval angle atau konsep nggak cukup.

## 4. Suara dan plan

Perintahnya sama kayak `bikin-short` langkah 4:

```bash
uv run mayzfact run <id> --mode faktacuil --no-render
```

Bedanya:

- TTS baru pakai ElevenLabs dengan voice Eric (`cjVigY5qzO86Huf0OWal`), model `eleven_v3`, tanpa delivery tag. Butuh `ELEVENLABS_API_KEYS`. Kalau gagal, laporkan error; jangan fallback ke VoiceStudio.
- Kalau `settings.local.json` berisi `"faktacuil_tts_provider": "manual"` (D-067): run berhenti exit 3 "Nunggu suara" dan nulis `runs/<id>/tts-request.txt`. Jalanin `uv run mayzfact brief <id>` (mode suara), kasih link-nya ke Akmal. Dia paste teks di web ElevenLabs, generate, terus upload di halaman itu. Setelah Akmal bilang udah, jalanin lagi `uv run mayzfact run <id> --no-render` dan matiin brief. Kalau error "nggak cocok sama naskah", minta Akmal cek file-nya; jangan ubah naskah buat nyocokin suara.
- VoiceStudio tetap didukung buat run lama. Kalau audio sudah ada, pakai ulang; jangan ganti provider atau buat suara baru tanpa izin.
- Jangan generate ulang suara, dan jangan hapus `voice.mp3`/`script.json` tanpa izin Akmal.
- Log `[tts] FaktaCuil estimasi final …` ngasih peringatan kalau estimasi di luar 20–30 detik. Audio tetap disimpan; jangan regenerate atau ubah speed otomatis.
- Plan nggak bikin segmen hook. Shot maksimal 3 detik (`faktacuil_max_shot_seconds`, D-053), jadi biasanya 1 beat = 1 shot. Kalau beberapa shot pakai link yang sama, isi Mulai beda-beda biar dapet adegan lain dan SFX transisinya bunyi.

Exit 3 "Nunggu input" = plan udah jadi, lanjut ke brief.

## 5–7. Brief, fetch, timeline, render

Sama kayak `bikin-short` langkah 5, 6, 8 (langkah 7 Studio cuma kalau Akmal minta). Bedanya:

- Brief nggak punya grup HOOK dan badge CARD. Shot CTA masuk grup **CTA** dan minta link kayak shot lain (bukan AUTO CTA, D-053).
- Shot di brief urut 1..N dalam satu kartu; badge kelompok cuma info, bukan pemisah kartu.
- Tiap shot punya pilihan speed 0.5x–2x (default 1x). Foto diabaikan (pilihannya disabled). Fetch ngambil `durasi shot × speed` detik source lalu dipadatkan ke durasi shot, jadi caption/timeline nggak berubah.
- Tombol Preview klip aktif sendiri begitu badge unduhan `siap` (nggak perlu refresh). Ganti link nutup preview lama, dan "Dari preview" ngasih detik SFX dalam detik shot (dibagi speed).
- Frame referensi FaktaCuil ada di kartu "Frame referensi source" (2 frame acak per shot source, maksimal 60 shot yang nyebar sampai shot terakhir), bukan 3 frame per shot. Kartu ketutup default; brief tetap jalan walau kartunya kosong (pesannya nyuruh `--from plan`).
- Timeline nggak punya `countdown`, `emojis`, dan `overlays`. `intro` + SFX hook di detik 0 sama kayak MayzFact. `timeline.json` punya `captionStyle: "faktacuil"`; `ctaScene` cuma ada kalau `cta_scene` diisi. `lucky`/`subscribe`: pill LIKE gelap → kursor klik → "LIKED" biru → stiker flat objek tema (`FaktaCuilCta.tsx`, ditiru dari FaktaBor `pJe_Qok8qDA`); `subscribe` nambah pill merah SUBSCRIBE pas kata "subscribe" diucapin → "SUBSCRIBED". `emoji`: pill LIKE → LIKED → emoji besar yang tahan sampai video selesai; klik dan emoji muncul di kata "emoji". Stiker objek itu **SVG** (`FaktaCuilStickers.tsx`), bukan Lottie. Lottie Noto cuma buat emoji CTA: kalau nggak ada, log `PERINGATAN` dan CTA tetap jalan pakai emoji statis (nggak bikin run gagal). Pill + kursor selalu di atas stiker/emoji. Scene CTA tengah berhenti di shot jawaban pertama; scene `emoji` sampai akhir video. Klip CTA tampil normal, nggak di-blur.
- Caption: kalimat tanya kebawa "?", caption ngilang pas jeda ≥0,25 detik, lebar maksimal 60% frame.
- BGM: Akmal bisa pilih lagu di dropdown **Musik latar (BGM)** di brief. Pilihan tersimpan otomatis di `runs/<id>/bgm-choice.json`, terpisah dari `links.json`. Timeline pakai pilihan itu; kalau nggak ada pilihan atau file-nya hilang, pakai file pertama (urut nama) di `assets/channels/faktacuil/bgm/`. Kalau koleksi kosong, sementara pakai `assets/bgm/main.mp3` dan log bilang begitu; sebutin ke Akmal. Folder koleksi **lokal dan di-gitignore** (lagu berhak cipta, repo public); jangan commit. Kalau timeline udah ada dan BGM berubah, ulang timeline dulu sebelum render.
- Kirim preview dan jam penting dari `timeline.json` (`ctaScene`, klik like di `sfx`), plus apa yang dilewat.

## 8. Metadata YouTube

Tulis `runs/<id>/upload.json`. Cuma format judul yang berubah (D-063); deskripsi, hashtag, tags, kategori, dan bahasa tetap.

```json
{"title": "Kenapa Kawat Kandang Ayam Dicat Hitam?", "description": "...", "tags": ["fakta unik", "..."], "category_id": "22", "language": "id"}
```

- **language** wajib `"id"`. Upload ditolak kalau bukan.
- **title:** bahasa Indonesia, Title Case, langsung sebut objek atau aksi yang dibahas. Pakai pertanyaan atau pernyataan spesifik yang bikin penasaran dan dijawab di video. Contoh: "Kenapa Kawat Kandang Ayam Dicat Hitam?" atau "Cara Pakai Topi Renang Biar Nggak Lepas". Maksimal 100 karakter, tanpa emoji, hashtag, `<`, atau `>`. Jangan copy judul source; tulis sendiri. Pakai untuk upload baru, bukan untuk edit video yang sudah di-upload.
- **description:** 2–4 kalimat bahasa Indonesia: ulang hook, kasih jawaban singkat, tutup pakai kalimat seru atau pertanyaan + 1 emoji yang nyambung (misal 🇯🇵). Terus baris baru, hashtag: `#faktaunik #faktamenarik`, 3–8 hashtag topik huruf kecil (`#jepang #rumahjepang #arsitektur`), terus `#shorts #shortvideo #youtubeshorts #fyp #viral #viralshorts`. Maksimal 5000 byte, tanpa `<` `>`.
- **tags:** wajib diisi (Akmal, beda dari FaktaBor): tags bahasa Indonesia, topik + frasa pencarian (`fakta unik`, `rumah jepang`, `rumah tahan gempa`, …), total ≤450 karakter.
- **category_id:** `"22"` (People & Blogs), sama kayak FaktaBor.

## 9. Jadwal dan upload

```bash
uv run mayzfact next-slot --channel faktacuil
uv run mayzfact upload <id> --at "<YYYY-MM-DD HH:MM>"
```

- Slot FaktaCuil **08.00 dan 12.00 WIB**, maksimal 2 video per hari (Akmal 2026-11-12: ikut jendela upload FaktaBor 07.00-09.00). Upload nggak tentu tiap hari, jadi pakai slot kosong berikutnya tanpa nanya Akmal, terus kabarin jam tayangnya setelah upload (D-037). Slot FaktaCuil dan MayzFact (01.00/04.00) saling terpisah.
- `upload` baca `narration_mode` dari `script.json` dan otomatis pakai token + channel FaktaCuil. Jangan tambah flag.
- Sebelum `videos().insert`, kode ngecek akun yang login beneran channel FaktaCuil. Upload nggak bisa ditarik, jadi cek ini wajib.
- Error "Belum login channel FaktaCuil" atau "Token YouTube ditolak": minta Akmal jalanin `uv run mayzfact login youtube --channel faktacuil` (browser kebuka), terus ulang.
- Error "faktacuil_youtube_channel_id masih kosong": minta Akmal isi `Settings.faktacuil_youtube_channel_id` pakai ID channel yang diprint pas login.
- Error "Token FaktaCuil login ke channel …": akun yang kepilih salah. Minta Akmal login ulang pakai akun channel FaktaCuil. Jangan akalin.
- Error "udah pernah di-upload": jangan hapus `youtube.json`, tanya Akmal.
- Sukses: `youtube.json` punya `"channel": "faktacuil"`. Commit hasil upload dan push ke origin sesuai aturan `bikin-short` langkah 11 dan `AGENTS.md` (Git).

## 10. TikTok

Dilewat. FaktaCuil belum punya metadata TikTok; jangan bikin `tiktok.json` kecuali Akmal minta.
