# Fase 2 — Hook matching + rerank klip pakai SigLIP

- **Tanggal:** 2026-10-03
- **Status:** disetujui lewat chat (4 bagian design). Akmal minta spec langsung lanjut ke plan tanpa review spec terpisah.
- **Referensi:** [`flow.svg`](../../../flow.svg), [spec Fase 1](2026-09-30-fase1-pipeline-design.md), [`docs/DECISIONS.md`](../../DECISIONS.md) D-011 sampai D-014.

## 1. Tujuan

Sesuai `flow.svg`: klip di 1–10 detik awal video harus sama persis, atau setidaknya mirip, dengan klip yang dipakai source. Sisa video tetap bebas, asal ngikutin naskah. Di Fase 1 klip buat hewan langka sering meleset (horseshoe crab dapat ghost crab, tardigrade dapat preparat mikroskop), jadi Fase 2 juga naikin relevansi semua shot.

Fase 2 nambah 3 hal ke pipeline Fase 1:

1. Step baru `hook`: deteksi klip di `HOOK_SECONDS` awal source, cari klip yang sama di TikTok/Douyin/RedNote/Pinterest + Pexels/Pixabay, terus pilih yang paling mirip pakai SigLIP.
2. Shot kita yang mulai sebelum `HOOK_SECONDS` dipasang klip hasil hook.
3. Shot lain tetap dari Pexels/Pixabay, tapi diurutkan ulang pakai skor SigLIP (teks beat vs thumbnail).

## 2. Scope

**Masuk:**

- Download video source pakai `yt-dlp`.
- Scene detection di `HOOK_SECONDS` awal, plus frame per segmen.
- Query per segmen dari Gemini vision. Kalau Gemini gagal, query diambil dari transcript.
- Adapter search + download buat TikTok, Douyin, RedNote, Pinterest, pakai browser yang udah login.
- Command `mayzfact login <platform>` dan `mayzfact login --check`.
- Embedding SigLIP ViT-B-16 (`open_clip`, torch CPU) buat hook (gambar vs gambar) dan rerank (teks vs gambar).
- `hook.json` + integrasi ke step `clips`.

**Nggak masuk:**

- Platform login buat shot di luar hook (D-012).
- Reverse image search (Google Lens/Yandex).
- Hapus watermark.
- Caption, musik, SFX, overlay (Fase 3). Upload (Fase 4).

## 3. Alur

```text
source → script → tts → hook → clips → timeline → render
```

- `hook` ditaruh setelah `tts` dan masuk grup step setelah suara. Jadi `--from hook` boleh walaupun `voice.mp3` udah ada, dan aturan kunci suara Fase 1 (spec Fase 1 3.4) nggak berubah.
- `hook` cuma butuh `source.json`, nggak butuh naskah.
- Video source di-download di step `hook`, **bukan** di step `source`. Step `source` dikunci begitu suara ada, jadi run lama (misalnya `i2xag_1OJfM`) nggak akan pernah download source kalau taruh di sana.
- Run lama yang belum punya `hook.json` otomatis jalan mulai dari `hook` di run biasa berikutnya. ElevenLabs nggak dipanggil.

File baru di `runs/<id>/`:

| File | Isi |
| --- | --- |
| `source.mp4` | video source ≤1080p |
| `hook/` | frame segmen, frame verifikasi, file pemenang `winner_XX.*` |
| `hook.json` | hasil matching per segmen |

## 4. Step hook

### 4.1 Segmen

1. Download source: `yt-dlp` format mp4 ≤1080p ke `runs/<id>/source.mp4`. Kalau file udah ada, skip.
2. Cut dideteksi di `min(HOOK_SECONDS, durasi source)` awal pakai filter `select='gt(scene,0.25)'` ffmpeg.
3. Cut yang jaraknya < 0.4 detik dari cut sebelumnya digabung jadi 1 grup. Grup diwakili cut terakhirnya, karena transisi whip-blur bikin rentetan cut rapat dan shot baru baru kelihatan penuh di ujung rentetan.
4. Segmen = jarak antar cut. Segmen < 0.5 detik dibuang.
5. Contoh `i2xag_1OJfM` dengan `HOOK_SECONDS=10`: 6 segmen (0.07–1.98, 1.98–2.48, 2.48–3.67, 3.67–6.12, 6.12–8.50, 8.50–10.00).

### 4.2 Embedding segmen

- 3 frame per segmen, di posisi 25%, 50%, dan 75%, lebar 448px.
- Embedding SigLIP ketiga frame dirata-rata, terus dinormalisasi. Caption di source ganti kata tiap frame, jadi rata-rata ini ngurangin pengaruh caption, panah, dan emoji.

### 4.3 Query

- 1 panggilan Gemini (model `GEMINI_MODEL`, key fallback sama kayak Fase 1) buat semua segmen. Input: frame tengah tiap segmen + potongan transcript di rentang waktu segmen itu.
- Output per segmen: `en` (2 query English) dan `zh` (2 query Mandarin).
- Kalau Gemini gagal (semua key ditolak, 5xx setelah retry, output nggak sesuai schema), atau `GEMINI_API_KEYS` kosong: query `en` = potongan transcript segmen (maksimal 8 kata), dan `zh` kosong. Douyin/RedNote kelewat buat segmen itu, tapi run tetap jalan.

### 4.4 Sumber kandidat

| Sumber | Bahasa query | Cara |
| --- | --- | --- |
| TikTok | en | browser login, tangkep JSON search |
| Douyin | zh | browser login, tangkep JSON search |
| RedNote | zh | browser login, tangkep JSON search |
| Pinterest | en | browser login, tangkep JSON search |
| Stock (Pexels + Pixabay) | en | API Fase 1, video + foto |

- Per sumber per segmen: pakai query pertama. Query kedua cuma dipakai kalau query pertama dapat < 3 hasil.
- Maksimal 8 kandidat teratas per sumber per segmen.
- Kandidat yang udah menang di segmen sebelumnya nggak boleh dipakai lagi.
- `HOOK_PLATFORMS` nentuin platform mana yang aktif (default keempatnya).

### 4.5 Seleksi

1. **Tahap 1 (thumbnail):** thumbnail tiap kandidat di-download ke `cache/thumbs/`. Thumbnail yang gagal di-download atau nggak bisa dibuka di-skip. Skor = cosine embedding thumbnail vs embedding segmen. Ambil 3 teratas.
2. **Tahap 2 (verifikasi):** 3 kandidat itu di-download ke `cache/media/`.
   - Video: frame diambil tiap 0.5 detik dari 30 detik pertama. Skor = cosine maksimal frame vs segmen. `offset_s` = waktu frame dengan skor maksimal itu.
   - Foto: skor = cosine foto vs segmen, `offset_s` = 0.
   - Kandidat yang gagal di-download atau rusak di-skip.
3. **Pemenang** = skor tahap 2 paling tinggi. File-nya di-copy ke `runs/<id>/hook/winner_XX.<ext>`.
4. **Label:** skor ≥ `HOOK_EXACT_THRESHOLD` jadi `exact`, selain itu `similar`. Pemenang tetap dipakai walaupun `similar`, sesuai `flow.svg`.
5. Kalau segmen nggak punya kandidat yang lolos: `winner` = null.

### 4.6 `hook.json`

```json
{
  "hook_seconds": 10.0,
  "skipped_platforms": [{"platform": "douyin", "reason": "captcha/login"}],
  "segments": [
    {
      "index": 0, "start_s": 0.067, "end_s": 1.983,
      "queries": {"en": ["horseshoe crab held up"], "zh": ["鲎"]},
      "candidates": [{"source": "tiktok", "provider_id": "7412", "thumb_score": 0.81}],
      "winner": {
        "source": "tiktok", "provider": "tiktok", "provider_id": "7412", "kind": "video",
        "file": "hook/winner_01.mp4", "offset_s": 3.5, "score": 0.91, "label": "exact",
        "page_url": "https://www.tiktok.com/@x/video/7412", "author": "x"
      }
    }
  ]
}
```

`candidates` nyimpen maksimal 5 kandidat teratas tahap 1, buat debugging.

## 5. Platform

### 5.1 Login

- `mayzfact login <tiktok|douyin|rednote|pinterest>`: buka Chrome (Playwright `channel="chrome"`) pakai profil `browser-profiles/<platform>/`, terus lu login manual dan tekan Enter di terminal.
- `mayzfact login --check`: baca cookies tiap profil, terus print `login` / `belum login` per platform. Penandanya cookie login: TikTok/Douyin `sessionid`, RedNote `web_session`, Pinterest `_auth=1`. Nama cookie ini dicek ulang pas E2E.
- `browser-profiles/` masuk `.gitignore`.

### 5.2 Search & download

- Search: buka URL search platform, tangkep response JSON internal yang URL-nya cocok pola per platform, terus di-parse jadi `Candidate`. Field yang hilang bikin item itu di-skip, nggak crash.
- Halaman di-scroll sambil nunggu. Maksimal nunggu 20 detik.
- Download:
  - video: `yt-dlp` pakai cookies profil (format Netscape), mp4 ≤1080p
  - foto: download langsung URL gambar
- Anti-ban:
  - jeda acak 2–5 detik antar search per platform
  - maksimal 12 search per platform per run
  - browser headed secara default (`BROWSER_HEADLESS=false`)

### 5.3 Ke-blok

- Tandanya: URL kebelokin ke halaman login/captcha, JSON nggak datang dalam 20 detik, atau batas 12 search kepakai.
- Platform itu ditandai ke-blok buat sisa run, dicatat di `skipped_platforms`, dan log-nya nyuruh `mayzfact login <platform>`.
- Run tetap jalan pakai sumber lain.

## 6. Rerank SigLIP buat shot non-hook

- `Candidate` dapat field `thumbnail_url`: Pexels video `image`, Pexels foto `src.medium`, Pixabay video `videos.*.thumbnail`, Pixabay foto `webformatURL`.
- Per grup percobaan Fase 1 (media beat, media lain, `fallback_query`), kandidat dikumpulin dari **semua** query grup itu.
- Skor = cosine embedding **nama subjek beat** (misalnya "sturgeon") vs embedding thumbnail. Subjek diambil dari field `subject` di naskah, atau dari beat countdown ("Number five, horseshoe crab") yang dibawa ke beat berikutnya. Kalau subjek nggak ada, pakai query yang nemuin kandidat itu. Query lengkap kayak "sturgeon river underwater" bikin SigLIP nyocokin pemandangannya, bukan hewannya (D-017). Thumbnail yang gagal dapat skor -1.
- Batas relevansi 0.10 (dari data run `i2xag`: foto yang nyambung 0.094–0.163, video yang meleset 0.003–0.093). Kalau kandidat terbaik di satu grup skornya di bawah batas, grup berikutnya (biasanya foto hewan yang sama) ikut dinilai, terus yang skornya paling tinggi yang dipakai.
- Sumber kandidat shot non-hook: Pexels + Pixabay + platform di `CLIP_PLATFORMS` (default Pinterest). 1 search platform per query, hasilnya dipakai buat video dan foto. Maksimal 40 search per run (D-016).
- Urutan: kandidat tier 3 di belakang. Sisanya skor paling tinggi duluan, terus tier, terus urutan provider.
- Aturan Fase 1 tetap jalan: klip nggak boleh dobel, durasi video minimal shot + 0.5 detik, link mati diganti kandidat berikutnya.

## 7. Integrasi ke clips

- Shot yang selesai paling lambat di `HOOK_SECONDS + 0.5` dipasang ke segmen hook yang punya pemenang, sesuai urutan: shot ke-1 dapat pemenang ke-1, dan seterusnya. Kalau pemenangnya habis, sisa shot pakai cara biasa.
- Video hook dinormalisasi mulai dari `offset_s − durasi_shot/2`, dibatasi antara 0 dan `durasi_file − durasi_shot − 0.2`.
- Entry di `clips.json` dapat field tambahan `hook_segment` dan `match`. `query` diisi `hook:<index>`.
- Kalau file pemenang gagal diproses, shot itu balik ke cara biasa dan dicatat di log.

## 8. Config baru

| Variabel | Default | Keterangan |
| --- | --- | --- |
| `HOOK_SECONDS` | `10` | panjang area hook di source dan di video kita |
| `HOOK_EXACT_THRESHOLD` | `0.85` | batas label `exact`. Dikalibrasi pas E2E |
| `HOOK_PLATFORMS` | `tiktok,pinterest` | platform aktif buat hook, dipisah koma. Douyin/RedNote bisa diaktifin lagi (D-016) |
| `CLIP_PLATFORMS` | `pinterest` | platform login tambahan buat shot non-hook. Kosongin = cuma stock |
| `MAX_SHOT_SECONDS` | `4` | sebelumnya 2.5 (Fase 1). Shot sekarang hampir selalu 1 per beat |
| `BROWSER_HEADLESS` | `false` | `true` buat jalan tanpa jendela browser |

Dependency baru: `numpy`, `torch` (wheel CPU dari PyPI di Windows), `open-clip-torch`, `playwright`, `yt-dlp`. Model `ViT-B-16-SigLIP` / `webli` di-download otomatis sekali (±800 MB).

## 9. Error handling

- Download source atau scene detect gagal: step `hook` stop dengan pesan yang nyebut `--from hook`.
- Gemini gagal: pakai query dari transcript (4.3).
- Platform ke-blok: di-skip (5.3).
- Thumbnail/media rusak atau gagal di-download: kandidat itu di-skip.
- Segmen tanpa pemenang: shot-nya pakai cara biasa.
- Model SigLIP gagal di-load: `PipelineError` yang nyebut nama model dan nyuruh cek koneksi buat download pertama.

## 10. Testing

- Unit test (tanpa model, browser, maupun network):
  - gabung cut dan bikin segmen
  - deteksi cut dari video fixture merah → biru
  - ambil frame
  - ranking dan label
  - mapping shot ke segmen
  - parser JSON keempat platform (termasuk item rusak)
  - deteksi ke-blok, konversi cookie, throttle
  - orkestrasi `run_hook` pakai encoder/sumber palsu
  - rerank di `clips`
  - wiring pipeline
- Marker `clip`: SigLIP asli harus ngasih skor lebih tinggi ke gambar yang mirip, dan ke teks yang cocok.
- Platform beneran cuma dites manual pas E2E. Payload asli direkam jadi fixture test.

## 11. Definition of Done

1. `mayzfact login --check` nunjukin keempat platform `login`.
2. `uv run mayzfact run i2xag_1OJfM --from hook` sukses, dan `voice.mp3` nggak berubah (mtime sama).
3. `hook.json` punya 6 segmen ±1, tiap segmen punya pemenang, skor, dan label.
4. Contact sheet segmen source vs pemenang berdampingan: minimal setengah segmen nunjukin hewan/objek yang sama.
5. Shot non-hook lebih relevan dari Fase 1 menurut Akmal, terutama horseshoe crab dan tardigrade.
6. `uv run pytest` dan `uv run pytest -m clip` lolos, dan Akmal udah nonton hasilnya.

## 12. Risiko

- **Hak cipta & ToS:** klip dari TikTok/Douyin/RedNote/Pinterest milik creator-nya, dan scraping pakai akun asli melanggar ToS platform. Akun bisa ke-flag dan video bisa kena klaim. Ini keputusan Akmal dari `flow.svg`.
- **Watermark:** klip TikTok/Douyin bisa ada watermark. Fase 2 belum menghapusnya.
- **Endpoint berubah:** pola URL dan bentuk JSON platform sering berubah, jadi parser perlu dirawat. Fixture rekaman bikin perubahan cepat ketahuan.
- **Waktu run:** ±250 thumbnail, ±18 download verifikasi, dan embedding ±1000 frame di CPU. Perkiraan nambah 3–6 menit per video.
