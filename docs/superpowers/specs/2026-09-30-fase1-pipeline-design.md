# Fase 1 — Pipeline dasar: naskah ulang + TTS + klip stock

- **Tanggal:** 2026-09-30
- **Status:** draft, nunggu review Akmal
- **Referensi:** [`flow.svg`](../../../flow.svg), [`docs/DECISIONS.md`](../../DECISIONS.md) (pembagian fase dan keputusan utama)

## 1. Tujuan

Dari 1 YouTube Shorts source, pipeline bikin 1 video shorts baru dengan:

- naskah yang ditulis ulang dari transcript source,
- suara TTS ElevenLabs,
- visual dari gabungan klip video + foto stock (Pexels + Pixabay).

Selain itu belum ada edit lain. Fase 1 ini fondasi buat Fase 2–4 (lihat `docs/DECISIONS.md` D-001).

## 2. Scope

**Masuk Fase 1:**

- Input 1 video ID/URL YouTube, diketik manual lewat CLI.
- Transcript → naskah baru (Gemini) → TTS dengan timestamp → cari & download klip video/foto → susun timeline → render Remotion.
- Output `runs/<video_id>/final.mp4`, 1080x1920, 30fps.
- Audio cuma TTS. Audio bawaan klip dibuang.
- Satu-satunya efek: zoom pelan di foto (lihat 4.6).
- Klip landscape/square pakai layout blur background (lihat 4.6).

**Nggak masuk (fase berikutnya):**

- Download video source, deteksi klip 1–10 detik awal, hook matching → Fase 2.
- Cari klip di TikTok/Douyin/RedNote/Pinterest (login akun) → Fase 2.
- Caption, musik, SFX, overlay, transisi, panah/lingkaran/emoji, title card, CTA visual → Fase 3.
- Pilih source otomatis, upload & schedule YouTube → Fase 4.

## 3. Arsitektur

Python jadi orchestrator yang jalanin step-step pipeline. Remotion (TypeScript) cuma jadi renderer: nerima `timeline.json` sebagai props, lalu render MP4.

```text
source → script → tts → clips → timeline → render
```

### 3.1 Struktur folder

```text
mayzfact-automation/
├─ pyproject.toml          # uv, Python 3.14 (pin 3.12/3.13 kalau ada dependency yang belum support)
├─ .env.example            # nama-nama variabel config, isinya di .env
├─ .gitignore              # .env, .venv/, runs/, cache/, sources/, remotion/node_modules/
├─ mayzfact/
│  ├─ cli.py               # entry point CLI
│  ├─ config.py            # baca .env + default
│  ├─ prompts/
│  │  └─ rewrite.md        # prompt rewrite naskah, gampang diedit tanpa nyentuh code
│  ├─ steps/               # source.py, script.py, tts.py, clips.py, timeline.py, render.py
│  └─ providers/           # client tipis: gemini.py, elevenlabs.py, pexels.py, pixabay.py
├─ remotion/               # project Remotion, composition "ShortVideo"
├─ tests/
├─ runs/<video_id>/        # hasil tiap step
├─ cache/                  # search/ = hasil search API (24 jam), media/ = file mentah hasil download
├─ sources/                # video source yang udah ada (nggak dipakai di Fase 1)
└─ transcript.py           # file lama; logic-nya pindah ke steps/source.py, file ini dibiarin
```

### 3.2 CLI

```text
uv run mayzfact run <video_id_or_url> [--from STEP] [--new-voice]
uv run mayzfact voices    # list voice ElevenLabs di akun, buat milih ELEVENLABS_VOICE_ID
```

- Tanpa flag: jalanin step yang file hasilnya belum ada. Step yang udah punya file hasil di-skip.
- `--from STEP`: ulang dari STEP itu dan semua step setelahnya. Step sebelumnya harus udah punya file hasil. Kalau belum ada, stop dengan error. Kalau `voice.mp3` udah ada, STEP cuma boleh `clips`, `timeline`, atau `render` (lihat 3.4).
- `--new-voice`: satu-satunya cara bikin naskah + suara baru setelah `voice.mp3` ada. Flag ini ngulang `script`, `tts`, dan semua step setelahnya. Karena manggil Gemini + ElevenLabs lagi (pakai kredit), jumlah karakter yang bakal dikirim ke ElevenLabs ditampilin dulu sebelum request. Flag ini nggak bisa digabung sama `--from`.

### 3.3 File hasil per step

| Step | Baca | Tulis ke `runs/<id>/` |
| --- | --- | --- |
| source | input CLI | `source.json` |
| script | `source.json` | `script.json` |
| tts | `script.json` | `voice.mp3`, `tts.json` |
| clips | `script.json`, `tts.json` | `clips/shot_XX.mp4` / `.jpg`, `clips.json` |
| timeline | `tts.json`, `clips.json` | `timeline.json` |
| render | `timeline.json`, `voice.mp3`, `clips/` | `final.mp4` |

Tiap file ditulis ke file sementara dulu, baru di-rename. Jadi file setengah jadi nggak pernah dianggap step-nya udah selesai.

### 3.4 Hemat kredit ElevenLabs: naskah + suara dikunci

Tujuannya biar test & review berkali-kali cukup bayar TTS 1x per video.

- Begitu `runs/<id>/voice.mp3` ada, `script.json`, `voice.mp3`, dan `tts.json` **dikunci**. Ketiganya nggak di-generate ulang, baik lewat run biasa maupun `--from`.
- Naskah ikut dikunci karena suara dibuat dari naskah itu. Kalau naskah berubah tapi suaranya nggak, timing beat bakal salah.
- `--from source|script|tts` ditolak kalau `voice.mp3` udah ada. Pesan error-nya nyaranin `--from clips`, atau `--new-voice` kalau emang mau naskah + suara baru.
- `tts.json` nyimpen hash teks naskah yang dipakai buat generate suara. Kalau `script.json` diedit manual sampai nggak cocok sama hash itu, pipeline stop. ElevenLabs nggak dipanggil diam-diam.
- Test otomatis nggak pernah manggil ElevenLabs (lihat section 7).
- `runs/<id>/voice.mp3` jangan dihapus. Kalau kehapus, suara harus dibuat ulang dan kredit kepakai lagi.

## 4. Detail step

### 4.1 source

- Nerima ID mentah (`i2xag_1OJfM`) atau URL `youtube.com/shorts/<id>`, `youtu.be/<id>`, `youtube.com/watch?v=<id>`.
- Ambil transcript English pakai `youtube-transcript-api` (auto-generated juga boleh).
- `source.json`:

```json
{
  "video_id": "i2xag_1OJfM",
  "duration_s": 70.8,
  "transcript": [{"text": "These are the top five ...", "start": 0.0, "duration": 2.5}]
}
```

`duration_s` = `start + duration` snippet terakhir. Kalau transcript nggak ada, stop dengan error.

### 4.2 script (Gemini)

- Step ini dikunci begitu `voice.mp3` ada (lihat 3.4).
- Pakai SDK `google-genai`, structured output lewat Pydantic schema.
- Input ke model: transcript lengkap **dengan timestamp**, biar model bisa ngikutin tempo tiap bagian (hook, isi, ending).
- Aturan di prompt (diambil dari `flow.svg`):
  - Naskah lebih pendek dari source, tapi alur dan pesan utamanya sama.
  - Tempo dan ritme mirip, termasuk hook, pengembangan, dan ending.
  - Kalimat ditulis ulang dari nol, bukan cuma motong bagian source.
  - Pilihan kata, struktur kalimat, dan transisinya beda, biar nggak kelihatan copy-paste.
  - Poin yang kurang penting dibuang, inti informasinya tetap.
  - Enak didengar buat voice over Shorts/TikTok/Reels.
  - Hook boleh dibikin lebih kuat, asal inti pesannya nggak berubah.
  - CTA source (like/subscribe, comment) tetap ada, tapi kalimatnya baru.
  - Kalau source pakai countdown ("Number five … number one"), penomoran dan urutannya sama persis, dan nggak dicampur "first/next/finally".
- **Target durasi:** `max(MIN_DURATION_SECONDS, TARGET_DURATION_RATIO × source.duration_s)`. Default-nya `max(32, 0.6 × durasi source)`. Target jumlah kata = target durasi × 2.6 kata/detik (estimasi, konstanta di code). Kalau source pendek, target tetap minimal 32 detik walaupun jadinya lebih panjang dari source.
- **Output schema:**

```python
class Beat(BaseModel):
    text: str                          # 1 kalimat pendek, English, 1 ide visual
    media: Literal["video", "photo"]   # jenis visual yang cocok buat beat ini
    queries: list[str]                 # 2–3 keyword stock English, paling spesifik duluan

class Script(BaseModel):
    beats: list[Beat]
    fallback_query: str                # keyword umum topik video, buat fallback
```

- Teks tiap beat dibersihin sebelum disimpan: tanda kutip dan dash "fancy" diganti ASCII, spasi dirapihin. Tujuannya biar teks yang dikirim ke TTS sama persis dengan karakter di alignment.
- `media` ditentukan model: `photo` buat subject diam (close-up hewan tertentu, fosil, dll), `video` buat aksi. Target sekitar `PHOTO_RATIO` (default 30%) beat pakai foto. Beat pertama selalu dipaksa `video` di code.
- **Cek otomatis setelah model jawab:**
  1. Jumlah kata masuk range ±15% dari target.
  2. Porsi beat foto antara 15%–45%.
  3. Tiap beat maksimal 10 kata (±3.5 detik). Beat yang lebih panjang disuruh dipecah.
  4. Overlap frasa rendah: dari semua word 4-gram di naskah baru (lowercase, tanpa tanda baca), maksimal 15% yang juga muncul di transcript source.
- Kalau ada cek yang gagal, retry 1x dengan pesan kenapa gagal. Kalau masih gagal, stop dengan error. Nilai overlap disimpan di `script.json` biar bisa dicek manual.

### 4.3 tts (ElevenLabs)

- Step ini dikunci begitu `voice.mp3` ada (lihat 3.4). ElevenLabs cuma dipanggil kalau `voice.mp3` belum ada, atau kalau pakai `--new-voice`.
- Seluruh naskah (teks beat digabung pakai spasi) dikirim dalam **1 request** `text_to_speech.convert_with_timestamps`, biar intonasinya nyambung.
- Voice dari `ELEVENLABS_VOICE_ID`, model dari `ELEVENLABS_MODEL`.
- Key dari `ELEVENLABS_API_KEYS` dicoba berurutan. Kalau satu key ditolak (401/402/403: kuota habis, key salah, izin kurang), pindah ke key berikutnya. Error lain langsung stop.
- Simpan `voice.mp3` dan `tts.json`. Isi `tts.json`: alignment per karakter, durasi audio (diukur pakai ffprobe), hash teks naskah, voice id, dan model.
- **Timing beat** dihitung dari alignment di `tts.json`, dan dipakai step clips. Posisi karakter tiap beat dicocokin ke alignment:
  - Beat pertama mulai di 0.0.
  - Beat `i` mulai di waktu karakter pertamanya.
  - Beat `i` selesai pas beat `i+1` mulai. Beat terakhir selesai di akhir audio.
  - Jadi visual nggak pernah punya jeda.
- Karakter di alignment harus sama persis dengan teks yang dikirim. Kalau beda, pipeline stop dengan error di step clips, jangan ditebak. `voice.mp3` tetap aman, jadi yang dibenerin code-nya, bukan suaranya.
- Kalau durasi audio kurang dari 30 detik:
  - `voice.mp3` tetap disimpan, karena kreditnya udah kepakai dan audionya masih bisa didengerin.
  - Pipeline stop sebelum `clips`, dengan pesan buat pakai `--new-voice`.
  - Cek ini jalan di tiap run, jadi run biasa nggak bakal lanjut pakai suara yang kependekan.

### 4.4 clips (Pexels + Pixabay)

**Pacing:**

- Tiap beat dipecah jadi `n = ceil(durasi_beat / MAX_SHOT_SECONDS)` shot yang durasinya sama.
- Default `MAX_SHOT_SECONDS` = 2.5. Contoh: beat 4 detik jadi 2 shot @2 detik.
- Tiap shot dapat klip yang beda.

**Jenis media per shot:** ikut `media` beat-nya. Shot pertama di video selalu video, kecuali video buat beat itu bener-bener nggak ketemu (fallback di bawah).

**Layout & ukuran yang dibutuhin:** layout tiap media ditentukan dari rasionya, pakai fungsi yang sama dengan step timeline (4.5):

- `full`: harus bisa nutupin 1080x1920.
- `blur`: foreground-nya harus selebar ≥ 1080 dan setinggi ≥ 960.

Ukuran yang dibutuhin itu dipakai buat tier, pemilihan rendition, dan normalisasi. Buat foto, ukurannya dikali `photoZoom` sebagai cadangan zoom.

**Cari kandidat** (per shot, coba `queries` beat satu per satu dari yang paling spesifik). Kalau 1 beat kepecah jadi beberapa shot, shot ke-2 mulai dari query ke-2, dan seterusnya, biar visualnya nggak seragam:

| Jenis | Sumber |
| --- | --- |
| video | Pexels Videos (`orientation=portrait`), Pexels Videos (tanpa filter orientasi), Pixabay Videos |
| foto | Pexels Photos (`orientation=portrait`), Pexels Photos (tanpa filter), Pixabay Images (`image_type=photo`) |

Semua kandidat dari query itu digabung, lalu:

1. Buang duplikat (provider + id yang sama bisa muncul dari 2 query Pexels).
2. Buang yang udah dipakai di video ini (cek provider + id).
3. Buang video yang durasinya kurang dari `durasi shot + 0.5 detik`.
4. Urutin pakai tier kualitas, lalu posisi relevansinya di hasil search provider masing-masing. Kalau posisinya sama, Pexels duluan.

| Tier | Syarat (video & foto) |
| --- | --- |
| 1 | layout `full` dan resolusinya cukup buat ukuran yang dibutuhin |
| 2 | layout `blur` dan resolusinya cukup buat ukuran yang dibutuhin |
| 3 | sisanya (resolusinya kurang, jadi bakal di-upscale) |

Contoh: video 1080x1920 masuk tier 1, dan video 1920x1080 masuk tier 2. Foto Pixabay maksimal 1280px (`largeImageURL`), jadi biasanya masuk tier 2–3.

Ambil kandidat teratas. Kalau semua query beat nggak ngasih kandidat:

1. Coba jenis media satunya (video ↔ foto).
2. Kalau masih kosong, coba `fallback_query`.
3. Kalau masih kosong juga, stop dengan error yang nyebut beat mana.

**Download:**

- Video: rendition paling kecil yang masih ≥ ukuran yang dibutuhin layout-nya. Kalau nggak ada, ambil yang terbesar.
- Foto: Pexels `src.original`, Pixabay `largeImageURL`.
- File mentah disimpan di `cache/media/`. Folder ini di luar folder run, jadi nggak ikut ke-copy Remotion waktu render, dan file yang sama bisa dipakai ulang antar run.

**Normalisasi (ffmpeg):**

- Video:
  - Mulai dari detik 0.5 kalau durasi klip ≥ durasi shot + 1 detik. Kalau nggak, mulai dari 0.
  - Dipotong sepanjang durasi shot + 0.2 detik (cadangan buat pembulatan frame).
  - Diubah jadi 30fps, H.264 yuv420p, tanpa audio.
- Foto: diubah ke JPG.
- Ukuran: media cuma di-downscale sampai ukuran terkecil yang masih ≥ ukuran yang dibutuhin layout-nya. Rasio tetap, dan ffmpeg nggak pernah upscale. Kalau media-nya lebih kecil, Remotion yang nge-scale.
- Crop dan layout **nggak** dikerjain di ffmpeg. Itu tugas Remotion (4.6).

**Cache & credit:**

- Response search disimpan di `cache/search/<provider>/<hash query+params>.json` selama 24 jam. Ini aturan Pixabay, sekalian hemat kuota Pexels.
- `clips.json` nyimpen tiap shot: index, beat, `start_s`, `end_s`, `kind`, file, `width`, `height`, provider, id, page URL, author, dan query yang dipakai. Data ini dipakai buat credit di deskripsi video (Fase 4).

### 4.5 timeline

- Detik diubah ke frame (30fps): `from = round(start_s × 30)`. Durasi tiap shot = `from` shot berikutnya − `from` shot ini.
- Shot terakhir selesai di `ceil(durasi_audio × 30)`, jadi nggak ada gap dan total video = durasi TTS.
- **Layout per shot** ditentukan dari rasio media hasil normalisasi. Fungsinya sama dengan yang dipakai di step clips:
  - `lebar / tinggi ≤ 0.75` → `full`
  - selain itu → `blur`
- Shot `blur` dapat `fgHeight`, yaitu tinggi kotak foreground (dihitung di Python biar bisa dites):
  - Nilainya tinggi natural media kalau ditampilin selebar 1080.
  - Minimal `FG_MIN_HEIGHT_RATIO × 1920` (default 960).
  - Maksimal 1920.
- `timeline.json` (dipakai sebagai input props Remotion):

```json
{
  "fps": 30,
  "width": 1080,
  "height": 1920,
  "durationInFrames": 1263,
  "audio": "voice.mp3",
  "photoZoom": 1.08,
  "shots": [
    {"src": "clips/shot_01.mp4", "kind": "video", "layout": "full", "from": 0, "durationInFrames": 66},
    {"src": "clips/shot_02.jpg", "kind": "photo", "layout": "blur", "from": 66, "durationInFrames": 60, "fgHeight": 960}
  ]
}
```

### 4.6 render (Remotion)

- Composition `ShortVideo`. `calculateMetadata` ngambil `fps`, `width`, `height`, `durationInFrames` dari props.
- `<Audio>` buat `voice.mp3`, lalu 1 `<Sequence>` per shot. Video selalu muted.
- **Layout `full`:** media nutupin seluruh frame 1080x1920 (object-fit cover, crop tengah).
- **Layout `blur`:**
  - Background: media yang sama nutupin seluruh frame, di-blur kuat, agak digelapin, dan di-scale sedikit biar pinggiran blur-nya nggak kelihatan.
  - Foreground: kotak selebar 1080 dan setinggi `fgHeight` dari timeline, posisinya di tengah vertikal. Media ngisi kotak itu pakai object-fit cover.
  - Kalau `fgHeight` lebih tinggi dari tinggi natural media, kiri-kanan media otomatis ke-crop.
  - Contoh: 16:9 jadi kotak 1080x960, kiri-kanan kepotong ±37%. 4:3 kepotong ±16%.

```text
┌────────────┐
│░░░ blur ░░░│  ← media yang sama, full frame, di-blur
│┌──────────┐│
││  klip    ││  ← foreground, tinggi min 50% frame (960px)
││ landscape││
│└──────────┘│
│░░░ blur ░░░│
└────────────┘
```

- **Foto:** zoom-in linear dari 1.00 ke `photoZoom` (default 1.08) selama durasi shot.
  - Di layout `full`, seluruh foto yang di-zoom.
  - Di layout `blur`, kotak foreground-nya tetap (ukuran & posisi nggak berubah). Yang zoom cuma isi foto di dalam kotak itu, dan background blur-nya diam.
- Command render (dijalanin dari folder `remotion/`):

```text
npx remotion render src/index.ts ShortVideo ../runs/<id>/final.mp4 --props=../runs/<id>/timeline.json --public-dir=../runs/<id>
```

- Output H.264 + AAC.

## 5. Config (`.env`)

| Variabel | Default | Keterangan |
| --- | --- | --- |
| `GEMINI_API_KEYS` | – | wajib. Beberapa key dipisah koma tanpa spasi; pindah ke key berikutnya kalau kena limit atau ditolak (401/403/429, API_KEY_INVALID) |
| `GEMINI_MODEL` | `gemini-3.8-flash` | nama persisnya dicek lagi pas implementasi |
| `ELEVENLABS_API_KEYS` | – | wajib. Beberapa key dipisah koma tanpa spasi; dicoba berurutan, pindah ke key berikutnya kalau ditolak (401/402/403) |
| `ELEVENLABS_VOICE_ID` | `TX3LPaxmHKxFdv7VOQHJ` | Liam (default voice, pria muda Amerika). Lihat D-009 |
| `ELEVENLABS_MODEL` | `eleven_v3` | udah dites: alignment cocok persis |
| `PEXELS_API_KEY` | – | wajib |
| `PIXABAY_API_KEY` | – | wajib |
| `TARGET_DURATION_RATIO` | `0.6` | target durasi relatif ke source |
| `MIN_DURATION_SECONDS` | `32` | target minimal (batas keras hasil TTS tetap 30 detik) |
| `MAX_SHOT_SECONDS` | `2.5` | durasi maksimal 1 shot |
| `PHOTO_RATIO` | `0.3` | porsi beat foto |
| `FG_MIN_HEIGHT_RATIO` | `0.5` | tinggi minimal foreground di layout blur |

Angka lain (2.6 kata/detik, batas overlap 15%, zoom 1.08, batas rasio 0.75) jadi konstanta di code.

## 6. Error handling

- Sebelum ada API call, semua variabel wajib dicek. Yang kosong disebut namanya, lalu pipeline stop.
- HTTP 429/5xx di-retry 3x dengan backoff (Gemini 5xx pakai jeda lebih panjang: 5s, 10s, 20s, karena overload "high demand" sering kejadian). Error lain langsung stop dengan pesan yang nyebut step + provider.
- ffmpeg/Remotion gagal: tampilin bagian akhir stderr-nya, terus stop.
- `--from source|script|tts` pas `voice.mp3` udah ada, atau hash naskah nggak cocok sama `tts.json`: stop dengan pesan yang jelas, tanpa manggil ElevenLabs (lihat 3.4).
- Semua kondisi stop di section 4 (transcript kosong, naskah gagal dicek, alignment beda, TTS < 30 detik, beat tanpa klip) pakai pesan yang jelas dan nyebut step mana yang perlu diulang.

## 7. Testing

- **Unit test (pytest)** buat logic murni:
  - parse ID/URL
  - target durasi & jumlah kata
  - cek overlap 4-gram
  - timing beat dari alignment
  - pecah beat jadi shot
  - ranking/tier kandidat
  - pemilihan rendition
  - konversi detik → frame (nggak ada gap, total = durasi audio)
  - keputusan layout `full`/`blur` dan ukuran yang dibutuhin
  - aturan kunci naskah + suara (`--from` ditolak, hash nggak cocok, `--new-voice`)
- **Provider** (Gemini, ElevenLabs, Pexels, Pixabay) dites pakai response palsu. Nggak ada API call beneran di test.
- **Remotion:**
  - typecheck
  - render fixture kecil buatan ffmpeg: 1 video portrait, 1 video landscape, 1 foto landscape, audio sine
  - cek hasilnya pakai ffprobe, dan ambil beberapa frame PNG buat dilihat (layout blur + zoom)
- **E2E manual:** run beneran `i2xag_1OJfM` pakai key asli. ElevenLabs cuma dipanggil 1x di run pertama. Run-run berikutnya buat test & review pakai `voice.mp3` yang sama.

## 8. Definition of Done

1. `uv run mayzfact run i2xag_1OJfM` ngasilin `runs/i2xag_1OJfM/final.mp4`.
2. Hasil ffprobe: 1080x1920, 30fps, H.264 + AAC, durasi ≥ 30 detik dan lebih pendek dari source (70.8 detik).
3. Audio cuma TTS. Nggak ada caption, musik, SFX, overlay, atau transisi. Efek satu-satunya zoom pelan di foto.
4. Visual-nya campuran video + foto dari Pexels/Pixabay:
   - tiap shot ≤ `MAX_SHOT_SECONDS`
   - nggak ada klip dobel
   - cut pas di batas beat
   - klip landscape pakai layout blur dengan foreground ≥ 50% tinggi frame
5. Naskah lolos cek otomatis 4.2. Credit tiap klip ada di `clips.json`.
6. Run ulang (`uv run mayzfact run i2xag_1OJfM --from clips`) jalan tanpa manggil ElevenLabs.
7. Semua test lolos.
8. Akmal udah nonton hasilnya dan oke.

## 9. Prasyarat (disiapin Akmal)

- `GEMINI_API_KEYS` dari Google AI Studio (boleh lebih dari 1, dipisah koma).
- `ELEVENLABS_API_KEYS` (boleh lebih dari 1, dipisah koma). Voice udah dipilih: Liam (D-009).
- `PEXELS_API_KEY` dan `PIXABAY_API_KEY` (gratis).
- Node 22: udah terinstall di nvm, tinggal `nvm use 22.23.1`.

## 10. Catatan & risiko

- **Relevansi klip:** di Fase 1 relevansi klip cuma ngandelin urutan hasil search provider. Belum ada scoring visual (CLIP). Itu masuk Fase 2.
- **Crop:** crop tengah (layout `full`) dan crop kiri-kanan (layout `blur`) bisa motong subject. Smart crop bisa nyusul.
- **Aturan provider:**
  - Pexels minta credit ke creator kalau memungkinkan.
  - Pixabay minta sumber ditunjukin, hasil search di-cache 24 jam, dan nggak boleh mass download sistematis.
  - Credit disimpan di `clips.json`.
- **Kuota:** Pexels 200 request/jam dan 20.000/bulan. Pixabay 100 request/menit. 1 run kira-kira butuh 40–60 request sebelum kena cache.
- **Lisensi Remotion:** gratis buat individu dan perusahaan sampai 3 orang.
