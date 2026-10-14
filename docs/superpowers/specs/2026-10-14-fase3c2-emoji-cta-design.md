# Fase 3C-2: emoji animasi, CTA like/subscribe, panah dipicu naskah

- **Tanggal:** 2026-10-14
- **Status:** design disetujui lewat chat. Akmal milih SFX-nya sendiri, terus minta langsung dikerjain dan review lewat Studio.
- **Referensi:** spec [3C-1](2026-10-13-fase3c1-arrows-design.md) dan D-023 #4 (panah dipicu naskah).

## 1. Tujuan

Ngikutin source `i2xag`:

- **Panah/lingkaran** cuma muncul di momen naskah yang ngajak lihat. Di source ada 4 momen kayak gitu: "Look at this thing", "look at that shell", "what even is this", sama "Look at this prehistoric-looking fish".
- **Emoji animasi** (🧐 🍀 🤯 dll) muncul di atas caption, nempel ke kata tertentu.
- **CTA:**
  - pas kata "like": tombol like diklik, jadi jempol biru dengan partikel
  - pas kata "subscribe": tombol putih "SUBSCRIBE" diklik, flip jadi merah "SUBSCRIBED", plus confetti

## 2. Penanda beat (gabungan)

Field baru di `Beat`:

- `point: bool` (default `false`): beat ini ngajak lihat sesuatu di layar, jadi panah/lingkaran muncul di shot beat ini.
- `emoji: str` (default `""`): 1 emoji dari daftar yang diizinin.
- `emoji_word: str` (default `""`): kata di beat itu yang jadi titik munculnya emoji.

**Naskah baru:**

- `rewrite.md` diubah biar momen "ngajak lihat" dari source dipertahanin (pakai kata baru), dan tiap beat ngisi 3 field di atas.
- Daftar emoji ditempel ke system prompt dari kode, supaya cuma ada satu sumber daftar.

**Naskah lama** (`script.json` yang beat-nya belum punya key `point`):

- Gemini nandain beat belakangan lewat `prompts/mark_beats.md`, pakai schema `BeatMarks{items: [{index, point, emoji, emoji_word}]}`.
- Teks dan suaranya nggak diubah.
- Hasilnya di-cache di `runs/<id>/annotations.json`, dengan key = hash teks naskah.
- Kalau Gemini gagal atau key-nya kosong, semua beat dianggap tanpa tanda, plus muncul log.

**Normalisasi** (sama buat kedua jalur):

- Emoji yang nggak ada di daftar dibuang.
- Beat countdown nggak dapat emoji.
- Kalau `emoji_word` nggak ketemu di beat itu, emoji muncul di awal beat.

**Daftar emoji** (semua udah dicek ada versi animasinya di Noto): 🧐 🤨 🤯 🫢 🍀 😱 😮 👀 🔥 💀 🤔 😳 😲 🤩 😨 🥶 😂 💯 👍 🦖 🌊 ⚡ 😴 🫣 😬 🤓 😎 🥺.

## 3. Aset emoji

- Pakai Noto Animated Emoji (Lottie, CC BY 4.0) dari `https://fonts.gstatic.com/s/e/notoemoji/latest/<codepoint>/lottie.json`.
- File di-download sekali ke `assets/emoji/<cp>.json` (di-gitignore), terus di-copy ke `runs/<id>/emoji/` buat `staticFile`.
- Kalau download gagal, emoji itu dilewat.

## 4. Timeline

Semua titik waktu pakai kata yang udah di-snap ke suara (`voice_onset`).

**`emojis: [{src, from, durationInFrames}]`**

- `from` = awal `emoji_word` (atau awal beat). Kalau jatuh di tengah CTA, digeser ke akhir CTA.
- Emoji boleh nyambung lewat akhir beat-nya (🍀 di source tampil ±2 detik). Berhentinya di yang paling dulu dari:
  `from + 75`, card countdown berikutnya, emoji berikutnya, CTA berikutnya, atau akhir video.
- Kalau kata pemicunya mepet card/CTA (`< 30` frame), mulainya dimajuin ke kata sebelumnya di beat itu, tapi nggak
  nyebrang CTA (🤯 di source muncul di awal frasa, terus berhenti pas card).
- Kalau hasilnya tetap `< 20` frame, emoji nggak dipasang.

**`cta: [{kind, from, durationInFrames, clickAt}]`**

- `subscribe`: tiap kata yang diawali "subscrib". Durasi 27 frame, `clickAt` 14.
- `like`: kata "like" yang ada di beat yang sama sebelum "subscribe". Durasi 16 frame, `clickAt` 4.
- Kalau "subscribe" mulai sebelum like selesai, subscribe nunggu like selesai (di source juga gitu).

**SFX baru:**

| Momen | File | Kapan | Volume |
|---|---|---|---|
| `emoji` | `pop_7e9Is8L.mp3` | di `from` | 0.6 |
| `click` | `mouse-click-by-ek6_VR0O6PL.mp3` | di `from + clickAt - 3` (puncaknya ±0.1 detik) | 0.8 |

**Panah/lingkaran:**

- Cuma shot yang beat-nya `point`.
- `prepare_overlays(..., point_beats=)` nggak ngedeteksi shot lain, jadi ngirit waktu OWLv2.
- Kalau semua beat tanpa tanda (Gemini gagal), panah nggak muncul sama sekali.

## 5. Remotion

**`Emojis.tsx`**

- Lottie (`@remotion/lottie` 4.0.534 + `lottie-web` 5.13.0), data diambil lewat `fetch(staticFile)` + `delayRender`.
- Box Lottie 370px (emoji yang kelihatan ±300px, kayak di source), tengah horizontal, pusatnya di y = 1180.
- Masuk pakai pop spring, keluar pakai fade 6 frame.

**`Cta.tsx`**, posisi tengah di y ±1190, ngikutin source frame per frame:

- **like** (16 frame):
  1. frame 0–3: tombol bulat biru dengan jempol putih + tulisan "LIKE" di bawahnya, kursor di atas tombol.
  2. frame 4: klik. Tombol hilang, tinggal jempol putih, tulisan LIKE gepeng.
  3. frame 5–6: jempol putih membesar.
  4. frame 7–10: jadi jempol biru gede, jempol mini muncrat cepat.
  5. frame 11–13: jempolnya miring searah jarum jam sampai rebahan.
  6. frame 14: kebalik (jempol ke bawah). Kursor pindah ke kanan bawah.
  7. frame 15: mengecil jadi ikon jempol yang dipakai subscribe.
- **subscribe** (27 frame):
  1. frame 0–3: tombol putih melebar dari tengah, ikon jempol nempel di kirinya.
  2. frame 1–6: huruf merah "SUBSCRIBE" masuk mantul satu-satu.
  3. frame 5–9: kursor naik ke tombol.
  4. frame 14: klik, tombol miring, confetti segitiga merah/putih.
  5. frame 15–17: flip 360° di sumbu X (tulisan sempat kebalik), jadi merah "SUBSCRIBED" 1.42×.
  6. frame 17–22: goyang.
  7. frame 22–26: flip 360° lagi sambil balik ke ukuran normal.
  8. frame 27: hilang (langsung, tanpa fade).
- Font tombol: Montserrat 800 (`@remotion/google-fonts`).

**Urutan layer:** shots → card → overlays → emojis → captions → CTA.

## 6. Testing & DoD

- **Pytest:**
  - field `Beat` + daftar emoji yang ditempel ke prompt rewrite
  - normalisasi tanda beat
  - anotasi naskah lama (Gemini palsu, cache, gagal)
  - download emoji (mock)
  - timing `emojis` / `cta` / SFX
  - filter `point` di `prepare_overlays`
  - wiring pipeline
- `tsc` + test render, fixture-nya ditambah 1 emoji Lottie minimal + 1 CTA.
- **DoD:** run i2xag di Studio nampilin panah cuma di beat `point`, emoji animasi, dan CTA like + subscribe kayak source. Render cuma setelah Akmal oke.
