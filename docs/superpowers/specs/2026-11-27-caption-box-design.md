# Caption FaktaCuil style "box" (neobrutalism)

Tanggal: 2026-11-27. Status: disetujui Akmal ("oke" ke usulan di chat).

## Tujuan

Style caption kedua buat FaktaCuil, buat dites di beberapa video lalu dibandingin retensinya sama style sekarang. Style sekarang (1 kata Fredoka besar di 75% tinggi frame) tetap jadi default dan nggak berubah.

Referensi: screenshot TikTok dari Akmal. Tiap kata punya kotak gelap sendiri dengan border terang. Satu potong kalimat tampil sekaligus, maksimal 2 baris. Kata yang lagi diucapin jadi kotak hijau lime yang agak miring dan glowing.

## Keputusan

- **Pemilih style:** field opsional `caption_style` di `script.json`. Nilainya `"word"` (default) atau `"box"`. `"box"` cuma boleh buat `narration_mode: "faktacuil"`. Field ini nggak ikut hash suara, jadi run lama bisa diganti style-nya cukup pakai `--from timeline`.
- **Pengelompokan:** satu tampilan = satu beat. Beat yang kepanjangan dibagi rata jadi beberapa tampilan, maksimal 8 kata dan 36 huruf per tampilan (kotak ±31 px per huruf + 50 px padding, jadi ±1.500 px, muat 2 baris 900 px; diukur dari still).
- **Teks:** pakai huruf asli naskah, bukan kapital, sama kayak referensi. Tanda baca di ujung kata dibuang, kecuali `?` (sama kayak style sekarang). Keyword beat tetap teks kuning `#FFC53D`.
- **Timeline:** `captionStyle: "faktacuil-box"`. Tiap item `captions` dapet field `group` (nomor tampilan). Timing per kata nggak berubah.
- **Render:** satu tampilan muncul dari kata pertama sampai kata terakhir group-nya selesai. Kata aktif adalah kata terakhir di group yang udah mulai diucapin, jadi highlight-nya nggak kedip pas ada jeda kecil.

## Visual (call gue, bisa direvisi Akmal setelah lihat still)

- Kotak kata: background `#27272a`, border 3 px `#d4d4d8`, radius 12, padding 4×16 px. Teks Fredoka 700, 64 px, putih, stroke hitam 6 px. Bayangan keras `5px 6px 0 #000` (ciri neobrutalism).
- Kata aktif: background lime `#a3e635`, border `#ecfccb`, teks `#14290a` tanpa stroke, miring −4°, scale 1,12, ditambah glow lime. Masuknya 3 frame.
- Tampilan: tengah horizontal, titik tengahnya di 75% tinggi frame (sama kayak style sekarang), lebar maks 900 px, flex-wrap. Masuk: opacity 0→1 dan scale 0,9→1 dalam 3 frame.

## Di luar scope

- Pilihan style lewat halaman brief.
- Animasi yang ditiru frame per frame. Belum ada video sumbernya, baru screenshot.
- MayzFact Top 3.

## Langkah

1. Test merah: model nolak `caption_style` yang nggak dikenal dan `"box"` di top3. Timeline `box` ngasih `captionStyle: "faktacuil-box"` + `group` per beat dengan batas 8 kata / 36 huruf. Default nggak berubah.
2. `models.py` + `timeline.py`.
3. `types.ts` + `Captions.tsx`, terus `tsc`.
4. Cek visual pakai `npx remotion still` di satu run FaktaCuil.
5. Docs: skill `bikin-faktacuil`, `DECISIONS.md` (D-069), `HANDOFF.md`.
