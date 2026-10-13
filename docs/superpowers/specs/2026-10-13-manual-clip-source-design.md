# Metode manual: klip dicari Akmal, harness yang proses

- **Tanggal:** 2026-10-13
- **Status:** disetujui lewat chat (4 bagian design). Akmal minta langsung lanjut ke plan + eksekusi.
- **Referensi:** [spec Fase 2](2026-10-03-fase2-hook-matching-design.md), `docs/DECISIONS.md` D-018 (risiko ToS) dan D-019 (keputusan ini).

## 1. Tujuan

Search otomatis Douyin/RedNote nggak bisa dipakai:

- Douyin: login web ditolak terus, termasuk lewat QR yang udah dikonfirmasi.
- RedNote: IP diblok (error 300012, "IP at risk").

Bilibili di-skip.

Jadi buat **semua shot**, klip dicari Akmal sendiri di app HP. Harness nyiapin brief, nerima link atau file, terus ngerjain sisanya: download, pilih bagian terbaik, normalisasi, timeline, review Studio, dan render.

## 2. Mode

Config `CLIP_SOURCE`:

- `manual` (default): alur di bawah.
- `auto`: alur Fase 2 (`hook → clips`), nggak diubah dan nggak dihapus.

```text
manual: source → script → tts → plan → fetch → timeline → (review Studio) → render
auto:   source → script → tts → hook → clips → timeline → (review Studio) → render
```

- `plan` dan `fetch` masuk grup step setelah suara, jadi aturan kunci suara (D-007) tetap berlaku.
- `--from` cuma nerima step yang ada di mode aktif.

## 3. Step `plan`

- Daftar shot dihitung dari timing TTS pakai aturan `MAX_SHOT_SECONDS` yang udah ada (`split_shots`), dan subjeknya dari `beat_subjects`.
- Segmen hook diambil dari video source (logic Fase 2: download, scene detect, 3 frame per segmen) ke `runs/<id>/plan/`.
- Shot hook ditentuin pakai `hook_slot_map`: shot yang selesai paling lambat di `HOOK_SECONDS + 0.5`.
- Keyword per shot:
  - Shot hook: `describe_segments`, yaitu Gemini vision yang ngasih query en + zh.
  - Shot isi: query beat (en), plus terjemahan zh dari 1 panggilan Gemini buat semua query. Kalau Gemini gagal atau key-nya kosong, zh dikosongin.
- Output `shots_plan.json`:

```json
{
  "hook_seconds": 10.0,
  "segments": [{"index": 0, "start_s": 0.07, "end_s": 1.98, "frames": ["plan/seg_01_0.jpg", "plan/seg_01_1.jpg", "plan/seg_01_2.jpg"]}],
  "shots": [
    {"index": 0, "beat": 0, "start_s": 0.0, "end_s": 3.41, "media": "video", "text": "…", "subject": null,
     "hook_segment": 0, "ref_frames": ["plan/seg_01_0.jpg", "…"], "keywords": {"en": ["…"], "zh": ["…"]}}
  ]
}
```

## 4. Brief (`mayzfact brief <id>`)

- Server lokal `127.0.0.1:BRIEF_PORT` (default 3100, kalau kepakai coba port berikutnya) yang nampilin halaman brief.
- Halaman dibikin ulang tiap kali dibuka dari `shots_plan.json`, `links.json`, dan `links_status.json`.
- **Per shot:**
  - nomor, waktu, label HOOK/ISI
  - narasi + subjek
  - frame referensi (cuma shot hook)
  - keyword en/zh dengan tombol copy
  - input link (boleh ditambah ` #n` buat maksa foto ke-n)
  - upload file
  - status: kosong / tersimpan / gagal + pesan / peringatan skor rendah
- **Atas halaman:** progres "x/N terisi" dan tombol Simpan.
- **API:**
  - `GET /api/state`
  - `POST /api/links`: nulis `links.json`
  - `POST /api/upload?shot=N`: body = isi file, header `X-Filename`. Disimpan di `runs/<id>/manual/shot_XX.<ext>`. Maksimal 500 MB, ekstensi cuma video/gambar.
  - `GET /files/<rel>`: cuma file di dalam folder run.
- `links.json`: `{"shots": {"1": {"url": "https://…", "pick": 3}, "2": {"file": "manual/shot_02.mp4"}}}`. Key-nya nomor shot mulai dari 1.

## 5. Step `fetch`

- **Wajib semua:** kalau ada shot yang belum diisi, `fetch` nulis status, terus berhenti dengan `AwaitingInput`. Pesannya nyebut nomor shot + `mayzfact brief <id>`, dan exit code 3 (bukan error).
- **Dapetin media per link:**
  - `file`: langsung dipakai.
  - URL langsung (`.mp4`, `.mov`, `.webm`, `.jpg`, `.jpeg`, `.png`, `.webp`): download biasa.
  - Douyin / RedNote: `yt-dlp` dulu, terus resolver Python port dari scrapr (Douyin: ttwid + data SSR + WAF proof-of-work + API `iteminfo`; RedNote: `__INITIAL_STATE__`), terus fallback meta `og:video`/`og:image`.
  - TikTok / Pinterest / lainnya: `yt-dlp`, terus fallback meta `og:`.
  - Cache di `cache/manual/<sha1 url>`. Link yang sama nggak di-download ulang.
- **Pilih bagian:**
  - Video: frame tiap 0.5 detik dari 60 detik pertama, dinilai SigLIP. Shot hook dibandingin sama rata-rata embedding frame referensi. Shot isi dibandingin sama embedding teks (subjek, atau keyword en pertama, atau narasi). Start = `offset − durasi/2`, dibatasi `[0, durasi_file − durasi_shot − 0.2]`. Kalau video lebih pendek dari `durasi_shot + 0.2`, shot itu error.
  - Foto: kalau ada `#n`, pakai foto ke-n. Kalau nggak, foto dengan skor tertinggi.
- **Skor rendah cuma jadi peringatan** di status (teks < 0.10, gambar < 0.60). Nggak bikin gagal.
- **Kalau semua shot oke:** tulis `clips.json` (format Fase 1–2, plus `provider` = jenis link, `page_url` = link/file, `query` = `manual`, `match` = skor, `hook_segment`) dan `links_status.json`.
- **Kalau ada yang gagal:** cuma tulis status, terus `AwaitingInput`. Hasil download yang udah berhasil tetap di cache.

## 6. Error handling

- Resolver gagal: pesan status nyaranin upload file.
- Server brief nolak nomor shot yang nggak ada di plan, path di luar folder run, ekstensi yang nggak didukung, dan file yang kegedean.
- Gemini gagal: keyword zh kosong, run tetap jalan.

## 7. Testing

Unit test (tanpa network beneran, browser, atau model):

- plan (mapping hook, keyword)
- deteksi jenis link dan parse `#n`
- resolver Douyin/RedNote pakai HTML/JSON buatan
- WAF solver pakai soal kecil
- pemilihan potongan/foto pakai encoder palsu
- aturan "wajib semua"
- endpoint server brief pakai server lokal di port acak
- pipeline mode manual/auto

## 8. Definition of Done

1. `uv run mayzfact run i2xag_1OJfM --from plan --no-render` berhenti dengan exit code 3 + pesan brief, dan `shots_plan.json` punya ±16 shot.
2. `uv run mayzfact brief i2xag_1OJfM` nampilin semua shot di `localhost:3100`.
3. Akmal ngisi semua shot, termasuk minimal 1 link Douyin, 1 RedNote (link atau upload), dan 1 post foto ganda. Abis itu `--from fetch --no-render` sukses dan `voice.mp3` nggak disentuh.
4. Link yang gagal kelihatan di brief, dan setelah diganti `fetch` sukses.
5. Akmal review di Studio dan oke, baru render.
6. Semua test lolos, termasuk mode `auto`.

## 9. Risiko

- Download RedNote kemungkinan ketahan blok IP, jadi upload file yang bakal kepakai.
- Resolver hasil port bisa rusak kalau Douyin/RedNote ngubah halamannya.
- Kalau `MAX_SHOT_SECONDS` atau naskah berubah setelah link diisi, nomor shot bisa geser. Cek ulang brief.

## 10. Revisi 2026-10-13: link per konteks (D-020)

Bagian ini menggantikan aturan "1 link per shot" di bagian 3–5.

**Kelompok (`plan`):**

- Semua shot hook masuk kelompok `hook`.
- Shot lain dikelompokin per subjek beat. Id kelompok = slug subjek (`horseshoe-crab`). Kalau subjeknya kosong, pakai `beat-N`.
- `shots_plan.json` dapat field `group` di tiap shot, plus daftar:

```json
"groups": [{"id": "hook", "label": "HOOK", "shots": [0, 1, 2], "keywords": {"en": [], "zh": []}}]
```

- Keyword kelompok = gabungan keyword shot-shotnya, tanpa duplikat.

**`links.json`:**

```json
{"groups": {"hook": [{"url": "https://…"}], "horseshoe-crab": [{"url": "https://…", "pick": 2}, {"file": "manual/horseshoe-crab_1.mp4"}]}}
```

**Brief:**

- 1 card per kelompok, isinya:
  - daftar shot + narasi
  - frame referensi per shot hook
  - keyword
  - 1 textarea, 1 baris = 1 link. Boleh pakai ` #n`. File upload muncul sebagai baris `file:manual/<id>_<k>.<ext>`, dan kalau baris itu dihapus, file-nya nggak dipakai.
- Upload: `POST /api/upload?group=<id>`.
- Progres yang ditampilin: "x/N kelompok terisi".

**`fetch`:**

- Semua link di satu kelompok di-download (cache tetap per URL). Kalau ada 1 link yang gagal, kelompok itu error, dan pesannya nyebut baris yang gagal.
- Shot diproses berurutan. Tiap shot milih opsi dengan skor tertinggi yang belum kepakai:
  - video: potongan yang nggak overlap sama potongan yang udah dipakai dari video yang sama
  - foto: foto yang belum dipakai
- Kalau semua opsi udah kepakai, opsi terbaik dipakai ulang dan muncul peringatan "tambah link lagi".
- `#n` = cuma foto ke-n dari post itu.
- Target pembandingnya tetap sama: shot hook pakai frame referensinya sendiri, shot isi pakai teks subjek.
- Status ditulis per kelompok: `missing` / `error` / `ok` + peringatan.
- `AwaitingInput` nyebut label kelompok.

**Frame source buat kelompok isi (revisi Akmal 2026-10-13):**

- Tiap kelompok non-hook juga dapat 3 frame dari video source: `plan/<id>_0..2.jpg`, diambil di posisi 25/50/75% dari rentang waktu subjeknya.
- Rentang dihitung dari transcript: mulai pas subjek pertama kali disebut (nama lengkap, atau kalau nggak ketemu, kata terakhirnya), sampai subjek berikutnya disebut. Kalau subjeknya nggak ketemu di transcript, kelompok itu tanpa frame.
- Field: `groups[].ref_frames`. Frame ini cuma referensi di brief. Target pencocokan `fetch` buat shot isi tetap teks subjek.
