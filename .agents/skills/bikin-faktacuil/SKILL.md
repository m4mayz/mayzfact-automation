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
- CTA cuma like (gimmick "coba tekan like, like-mu berubah jadi X?") di tengah, bukan di akhir. Tanpa subscribe dan comment.
- BGM 1 lagu sepanjang video, dari folder lokal.
- Suara, jadwal, dan channel upload sendiri.

## 1. Source

Sama kayak `bikin-short` langkah 1:

```bash
uv run mayzfact run <url atau id> --no-render
```

Source boleh video Inggris atau Indonesia. Step source juga nyimpen transkrip asli Indonesia (bukan terjemahan) di `source.json` field `transcript_id`; kosong kalau videonya nggak punya (D-052).

Kalau source-nya Top N, boleh ambil **1 item** aja; semua fakta di naskah harus dari item itu. Step source jalan sebelum naskah ada, jadi dia tetap download `source.mp4` dan bikin frame `plan/seg_XX_K.jpg` walau format FaktaCuil. File itu nggak dipakai, abaikan.

## 2. Tulis naskah

Agent nulis `runs/<id>/script.json`. Kalau `transcript_id` nggak kosong, tulis dari teks Indonesia itu dan `check-script` ngebandingin overlap 4-gram ke teks itu (tulis ulang, jangan nyalin kalimat asli); kalau kosong, pakai `transcript` Inggris kayak biasa. Aturan **Isi** dari `bikin-short` langkah 2 tetap berlaku: tiap beat harus punya dasar kalimat di source, jangan nambah fakta, angka, atau perbandingan, jangan ngerasin klaim ("can/may/some" tetap "bisa/mungkin/sebagian"), dan pertahankan kata pembatas source. Terjemahan nggak boleh nambah apa pun.

**Bahasa.** Indonesia santai: `nggak`, `udah`, `banget` boleh. Jangan maksa slang. Kata teknis yang biasa dipakai orang Indonesia tetap dipakai.

**Struktur.** Urutannya:

1. **Hook** pertanyaan "Kenapa…?" (beat 1–2).
2. **Salah kaprah** ("Padahal…", "Kamu mungkin mengira…"), minimal 1 beat.
3. **CTA** like gimmick, 1–3 beat.
4. **Jawaban** ("Ternyata…", "Karena itu…", "Jadi…"), minimal 2 beat.
5. Penutup singkat (boleh bagian dari jawaban).

Kata pembuka "Padahal…"/"Ternyata…" cuma pola; kode nggak ngecek, jadi boleh divariasi.

**Aturan yang dicek `check-script`** (pesannya English):

| Aturan | Isi |
| --- | --- |
| F1 | Beat 1 dibuka kata `Kenapa`; tanda `?` paling lambat di beat 2. |
| F2 | Nggak ada beat "Number N,". |
| F3 | Blok CTA tepat 1, 1–3 beat. |
| F4 | Minimal 1 beat salah kaprah antara hook dan CTA. |
| F5 | Minimal 2 beat jawaban setelah CTA. |
| F6 | Blok CTA punya tepat 1 ajakan like Indonesia ("tekan/pencet/klik/kasih like", "tekan tombol like"). Nol `subscribe`, nol `komen`/`komentar`/`comment`. |
| F7 | Ada 1 beat CTA yang ngandung `transform_word`, diakhiri `?`, dan ada frasa `jadi [seekor/sebuah] <objek tema>`. |
| F8 | Beat CTA: `subject` kosong, `point` false. |
| F9 | Semua beat: `point` false, `emoji` dan `emoji_word` kosong. |
| F10 | `keyword` (kalau diisi) 1 kata yang ada di teks beat itu, bukan di beat CTA. |
| F11 | Jumlah kata total di rentang (lihat bawah). |
| umum | ≤10 kata per beat, foto 15–45% beat, tiap beat punya `queries`, overlap 4-gram dengan source ≤15%. |

**CTA.** Contoh (dua beat):

```
Tapi coba tekan like dulu,
apakah like-mu berubah jadi madu?
```

Kata "like" cuma muncul di CTA. Pertanyaan gimmick nggak punya ajakan sendiri tapi tetap bagian blok CTA. `cta_scene` wajib:

```json
"cta_scene": {"theme": "honey", "transform_word": "berubah", "comment_text": "MADU"}
```

- `transform_word` kata tunggal yang ada di pertanyaan; morph mulai di kata itu.
- `comment_text` wajib ada di schema tapi nggak ditampilin di FaktaCuil. Isi kata objek huruf kapital (maks 24 karakter).
- Objek harus salah satu dari 6 ilustrasi. Objek lain = **STOP**, bikin ilustrasinya dulu (sama kayak top3).

| theme | frasa setelah `jadi` |
| --- | --- |
| `volcano` | `gunung berapi`, `gunung meletus`, `gunung api` |
| `unicorn` | `unicorn` |
| `honey` | `madu` |
| `puppy` | `anak anjing`, `anjing` |
| `lion` | `singa` |
| `shark` | `hiu`, `ikan hiu` |

**Per beat.**

- `keyword`: 1 kata yang ditekankan (caption-nya kuning), isi di ±1 dari 3 beat, bukan beat CTA. Kata yang dipilih sering bukan subjek ("ternyata", "aman"). Tanda hubung boleh (`kupu-kupu`).
- `point` selalu false, `emoji` dan `emoji_word` selalu kosong.
- `subject`: hewan/objek yang dibahas, kosong di beat CTA.
- `queries` bahasa Inggris dan `queries_zh` Mandarin, sama kayak top3. Beat CTA juga wajib punya `queries`: shot CTA minta link di brief kayak shot lain (D-053), jadi isi keyword klip yang cocok buat background pill like.
- `hook_queries` selalu `{}`: FaktaCuil nggak punya segmen hook dari source.
- Beat pertama otomatis jadi video.

**Panjang.** Kata CTA ikut dihitung. Rumusnya `kata = detik_final × video_speed × FAKTACUIL_RAW_WPS` (2.27, dari sampel Eric). Di ElevenLabs speed 1.1 targetnya **62 kata, rentang 50–74**. Kalau FaktaCuil dijalanin lewat VoiceStudio (speed 1.15) targetnya 65, rentang 53–78. Pakai angka yang diprint `check-script` ("target T") kalau beda.

Selesai nulis:

```bash
uv run mayzfact check-script <id>
```

`OK` cuma berarti format dan jumlah kata lolos. Cek sendiri tiap beat terhadap aturan **Isi** sebelum nunjukin ke Akmal.

## 3. Checkpoint: Akmal review naskah

Tunjukin di chat, per beat: **teks Indonesia | kalimat source Inggris yang jadi dasarnya | keyword visual (`queries`)**. Tambahin kolom `keyword` caption. Beat CTA dasarnya "CTA gimmick". Tunggu "oke" atau koreksi. **Jangan lanjut sebelum Akmal oke** (langkah 4 bikin suara, pakai kredit ElevenLabs).

## 4. Suara dan plan

Perintahnya sama kayak `bikin-short` langkah 4:

```bash
uv run mayzfact run <id> --no-render
```

Bedanya:

- Voice default ElevenLabs **Eric** (`Settings.faktacuil_elevenlabs_voice_id`), model `eleven_v3`, stability 0.5, tanpa delivery tag. Setting MayzFact (voice Liam, tag `calm`, provider global) nggak kebawa ke FaktaCuil.
- VoiceStudio bisa dipakai kalau Akmal isi di `settings.local.json`: `faktacuil_tts_provider` (`"voicestudio"`), `faktacuil_voicestudio_voice` (profil bahasa Indonesia), `faktacuil_voicestudio_instruct`. Kalau provider voicestudio tapi voice kosong, pipeline berhenti sebelum TTS. Belum ada profil bahasa Indonesia, jadi default-nya tetap ElevenLabs.
- Jangan generate ulang suara, dan jangan hapus `voice.mp3`/`script.json` tanpa izin Akmal.
- Log `[tts] FaktaCuil estimasi final …` ngasih peringatan kalau estimasi di luar 20–30 detik. Audio tetap disimpan; jangan regenerate atau ubah speed otomatis.
- Plan nggak bikin segmen hook. Shot maksimal 3 detik (`faktacuil_max_shot_seconds`, D-053), jadi biasanya 1 beat = 1 shot. Kalau beberapa shot pakai link yang sama, isi Mulai beda-beda biar dapet adegan lain dan SFX transisinya bunyi.

Exit 3 "Nunggu input" = plan udah jadi, lanjut ke brief.

## 5–7. Brief, fetch, timeline, render

Sama kayak `bikin-short` langkah 5, 6, 8 (langkah 7 Studio cuma kalau Akmal minta). Bedanya:

- Brief nggak punya grup HOOK dan badge CARD. Shot CTA masuk grup **CTA** dan minta link kayak shot lain (bukan AUTO CTA, D-053).
- Timeline nggak punya `countdown`, `emojis`, dan `overlays`. `intro` + SFX hook di detik 0 sama kayak MayzFact. `timeline.json` punya `captionStyle: "faktacuil"` dan `ctaScene.style: "faktacuil"`: pill like gelap → kursor klik → "LIKED" biru → stiker flat objek tema (`FaktaCuilCta.tsx`, ditiru dari FaktaBor `pJe_Qok8qDA`). Klip CTA tampil normal, nggak di-blur.
- Caption: kalimat tanya kebawa "?", caption ngilang pas jeda ≥0,25 detik, lebar maksimal 60% frame.
- BGM: file audio pertama (urut nama) di `assets/channels/faktacuil/bgm/`. Folder itu **lokal dan di-gitignore** (lagu berhak cipta, repo public). Jangan download atau copy lagu sendiri, dan jangan commit; Akmal yang naruh file. Kalau folder kosong, sementara pakai `assets/bgm/main.mp3` dan log bilang begitu; sebutin ke Akmal.
- Kirim preview dan jam penting dari `timeline.json` (`ctaScene`, klik like di `sfx`), plus apa yang dilewat.

## 8. Metadata YouTube

Tulis `runs/<id>/upload.json`. Formatnya disamain sama FaktaBor (D-053, dicek dari `info.json` 3 video FaktaBor):

```json
{"title": "Rumah Jepang Dibangun Tanpa Paku😱", "description": "...", "tags": [], "category_id": "22", "language": "id"}
```

- **language** wajib `"id"`. Upload ditolak kalau bukan.
- **title:** bahasa Indonesia, Title Case, klaim yang bikin penasaran, diakhiri 😱 tanpa spasi. Pola FaktaBor: "Rumah Jepang Ini Tanpa Paku😱", "Alasan Koboi Membuat Jeans Sekaku Ini😱", "Pantas Banyak Orang Gagal Pakai Topi Renang😱". Maksimal 100 karakter, tanpa `<` `>`. Klaimnya harus kejawab di video. Jangan copy judul source; tulis sendiri.
- **description:** 2–4 kalimat bahasa Indonesia: ulang hook, kasih jawaban singkat, tutup pakai kalimat seru atau pertanyaan + 1 emoji yang nyambung (misal 🇯🇵). Terus baris baru, hashtag: `#faktaunik #faktamenarik`, 3–8 hashtag topik huruf kecil (`#jepang #rumahjepang #arsitektur`), terus `#shorts #shortvideo #youtubeshorts #fyp #viral #viralshorts`. Maksimal 5000 byte, tanpa `<` `>`.
- **tags:** `[]`, sama kayak FaktaBor.
- **category_id:** `"22"` (People & Blogs), sama kayak FaktaBor.

## 9. Jadwal dan upload

```bash
uv run mayzfact next-slot --channel faktacuil
uv run mayzfact upload <id> --at "<YYYY-MM-DD HH:MM>"
```

- Slot FaktaCuil **12.00 dan 18.00 WIB**, maksimal 2 video per hari. Upload nggak tentu tiap hari, jadi pakai slot kosong berikutnya tanpa nanya Akmal, terus kabarin jam tayangnya setelah upload (D-037). Slot FaktaCuil dan MayzFact (01.00/04.00) saling terpisah.
- `upload` baca `narration_mode` dari `script.json` dan otomatis pakai token + channel FaktaCuil. Jangan tambah flag.
- Sebelum `videos().insert`, kode ngecek akun yang login beneran channel FaktaCuil. Upload nggak bisa ditarik, jadi cek ini wajib.
- Error "Belum login channel FaktaCuil" atau "Token YouTube ditolak": minta Akmal jalanin `uv run mayzfact login youtube --channel faktacuil` (browser kebuka), terus ulang.
- Error "faktacuil_youtube_channel_id masih kosong": minta Akmal isi `Settings.faktacuil_youtube_channel_id` pakai ID channel yang diprint pas login.
- Error "Token FaktaCuil login ke channel …": akun yang kepilih salah. Minta Akmal login ulang pakai akun channel FaktaCuil. Jangan akalin.
- Error "udah pernah di-upload": jangan hapus `youtube.json`, tanya Akmal.
- Sukses: `youtube.json` punya `"channel": "faktacuil"`. Commit hasil upload dan push ke origin sesuai aturan `bikin-short` langkah 11 dan `AGENTS.md` (Git).

## 10. TikTok

Dilewat. FaktaCuil belum punya metadata TikTok; jangan bikin `tiktok.json` kecuali Akmal minta.
