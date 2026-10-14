# Decision Log

Keputusan penting project mayzfact-automation. Detail teknis Fase 1 ada di [`docs/superpowers/specs/2026-09-30-fase1-pipeline-design.md`](superpowers/specs/2026-09-30-fase1-pipeline-design.md).

## D-001 — 2026-09-30 — Project dikerjain bertahap dalam 4 fase

- **Status:** accepted. Urutan Fase 2 dan 3 masih boleh dituker.
- **Konteks:** Goal akhir project ini shorts yang kualitas edit-nya setara source `i2xag_1OJfM`, sesuai `flow.svg`. Kalau dikerjain sekaligus, scope-nya terlalu besar.
- **Keputusan:**
  1. Fase 1: pipeline dasar (naskah ulang + TTS + klip stock).
  2. Fase 2: hook matching (klip 1–10 detik awal sama/mirip source, cari di TikTok/Douyin/RedNote dengan login, visual matching).
  3. Fase 3: edit style ala `i2xag` (caption per kata, BGM, SFX, transisi, title card, CTA, panah/lingkaran/emoji).
  4. Fase 4: pilih source otomatis + upload terjadwal 21.00 & 04.00 WIB.
- **Alasan:** Fase 2 ditaruh sebelum 3 karena itu bagian paling nggak pasti (login, anti-bot, akurasi matching).
- **Konsekuensi:** tiap fase punya spec → plan → implementasi sendiri.
- **Authority:** diusulin agent. Akmal minta Fase 1 berupa "klip gabungan + TTS saja", terus approve design Fase 1 yang scope-nya ngikutin pembagian ini (chat 2026-09-30).

## D-002 — 2026-09-30 — Fase 1 ambil klip dari stock API

- **Status:** accepted
- **Konteks:** Di `flow.svg`, TikTok/Douyin/RedNote jadi sumber utama dan Pexels/Pixabay/Pinterest jadi fallback.
- **Keputusan:** Fase 1 cuma pakai Pexels + Pixabay lewat API resmi. TikTok/Douyin/RedNote/Pinterest masuk Fase 2 bareng hook matching.
- **Alasan:** stabil, legal, nggak perlu login. Scraping platform dengan login itu bagian paling berat dan rawan.
- **Authority:** pilihan Akmal (chat 2026-09-30).

## D-003 — 2026-09-30 — LLM pakai Gemini API

- **Status:** accepted
- **Keputusan:** rewrite naskah + keyword klip pakai Gemini (SDK `google-genai`, structured output). Model diatur lewat `GEMINI_MODEL`.
- **Konsekuensi:** vision buat Fase 2 juga bisa pakai Gemini.
- **Authority:** pilihan Akmal (chat 2026-09-30).

## D-004 — 2026-09-30 — Arsitektur Python orchestrator + Remotion renderer

- **Status:** accepted
- **Keputusan:** Python (uv) jalanin semua step dan nulis `timeline.json`. Remotion (TypeScript) cuma render dari `timeline.json`.
- **Alasan:** Fase 2 butuh CLIP/torch/opencv yang enaknya di Python. Remotion dipakai dari awal biar Fase 3 tinggal nambah komponen di timeline yang sama.
- **Alternatif yang ditolak:** full TypeScript (Fase 2 ribet), dan Python + ffmpeg dulu (render harus ditulis ulang di Fase 3).
- **Authority:** pilihan Akmal (chat 2026-09-30).

## D-005 — 2026-09-30 — Visual campuran video + foto, foto pakai zoom pelan

- **Status:** accepted
- **Keputusan:** sekitar 30% shot pakai foto (`PHOTO_RATIO`). Gemini yang nentuin beat mana jadi foto, dan ada fallback dua arah video ↔ foto. Foto dapat zoom-in pelan 1.00 → 1.08 di Remotion.
- **Authority:** Akmal minta foto ikut dipakai. Zoom pelan dipilih Akmal dari opsi "zoom pelan" vs "diam" (chat 2026-09-30).

## D-006 — 2026-09-30 — Klip landscape pakai layout blur background

- **Status:** accepted
- **Keputusan:** klip/foto landscape atau square nggak di-crop jadi full 9:16. Klipnya tetap tampil di tengah, dengan background versi blur dari media yang sama. Tinggi foreground minimal sekitar 50% frame (`FG_MIN_HEIGHT_RATIO`), dan kalau perlu kiri-kanannya di-crop.
- **Konsekuensi:** klip 16:9 kepotong ±37% di kiri-kanan. Kalau terlalu banyak yang hilang, rasio foreground bisa diturunin lewat config.
- **Authority:** aturan dari Akmal (chat 2026-09-30). Interpretasi angka 50% dan crop kiri-kanan dari agent, dikonfirmasi pas review spec.

## D-007 — 2026-09-30 — Naskah + suara dikunci setelah TTS pertama

- **Status:** accepted
- **Konteks:** test & review bakal jalan berkali-kali. Tiap panggilan ElevenLabs makan kredit.
- **Keputusan:**
  - Begitu `runs/<id>/voice.mp3` ada, `script.json`, `voice.mp3`, dan `tts.json` nggak di-generate ulang.
  - Suara baru cuma lewat flag `--new-voice`.
  - `--from source|script|tts` ditolak kalau suara udah ada.
  - Hash naskah di `tts.json` dicek biar naskah yang diedit manual nggak diam-diam manggil ElevenLabs.
  - Test otomatis selalu pakai response palsu.
- **Konsekuensi:** mau ganti naskah berarti bayar TTS lagi lewat `--new-voice`. `voice.mp3` jangan dihapus.
- **Authority:** permintaan Akmal (chat 2026-09-30). Mekanisme kunci + flag dari agent, dikonfirmasi pas review spec.

## D-008 — 2026-10-01 — ElevenLabs pakai banyak API key

- **Status:** accepted
- **Konteks:** Akmal punya 9 key ElevenLabs. Semua key cuma punya izin TTS: `user_read` dan `voices_read` ditolak, jadi sisa kredit nggak bisa dicek duluan.
- **Keputusan:**
  - Key ditulis di `ELEVENLABS_API_KEYS`, dipisah koma tanpa spasi.
  - Key dicoba berurutan. Kalau HTTP 401/402/403 (kuota habis, key salah, izin kurang), pindah ke key berikutnya. Request yang ditolak nggak makan kredit.
  - Error lain (400, 5xx yang udah di-retry, timeout) langsung stop tanpa ganti key, biar nggak ketagih dobel.
  - Pesan error cuma nyebut nomor key, bukan isinya.
- **Konsekuensi:** key yang kuotanya udah habis tetap dicoba duluan tiap run. Requestnya ditolak cepat dan gratis.
- **Authority:** permintaan Akmal (chat 2026-10-01). Aturan fallback-nya dari agent.

## D-009 — 2026-10-01 — Voice Liam + model eleven_v3

- **Status:** accepted
- **Konteks:** Akmal minta agent milih sendiri voice pria yang cocok buat nada "teacher for kids". Key-nya nggak bisa baca Voice Library, jadi pilihannya dari default voice.
- **Keputusan:**
  - `ELEVENLABS_VOICE_ID=TX3LPaxmHKxFdv7VOQHJ` (Liam: pria muda Amerika, confident, buat social media).
  - `ELEVENLABS_MODEL=eleven_v3`, karena paling ekspresif.
  - Udah dites pakai 1 request pendek: `with-timestamps` jalan, dan alignment-nya cocok persis sama teks.
- **Konsekuensi:** ElevenLabs bakal matiin default voice tanggal 2026-12-31. Pengganti resmi Liam adalah "Lawrence - Bright and Informative". ID-nya belum ketemu karena key nggak punya izin `voices_read`. Sebelum 2026-12-31, ganti `ELEVENLABS_VOICE_ID` ke Lawrence atau voice lain.
- **Authority:** pilihan agent atas permintaan Akmal (chat 2026-10-01).

## D-010 — 2026-10-01 — Gemini juga pakai banyak API key

- **Status:** accepted
- **Konteks:** Akmal ngisi 3 key Gemini dipisah koma. Ketiganya udah dicek valid, dan `gemini-3.8-flash` tersedia di semua key.
- **Keputusan:**
  - Variabelnya `GEMINI_API_KEYS`. Nama variabel di `.env` di-rename dari `GEMINI_API_KEY`, isinya nggak disentuh.
  - Key dicoba berurutan. Kalau 401/403/429 atau 400 `API_KEY_INVALID`, pindah ke key berikutnya.
  - 5xx di-retry di key yang sama. 400 lain langsung stop.
- **Authority:** pola multi key diminta Akmal buat ElevenLabs (D-008). Penerapan ke Gemini disimpulin agent dari isi `.env`.

## D-011 — 2026-10-03 — Fase 2 dikerjain dalam 1 spec

- **Status:** accepted
- **Keputusan:** hook matching, adapter 4 platform login, dan rerank SigLIP masuk 1 spec dan 1 plan ([spec Fase 2](superpowers/specs/2026-10-03-fase2-hook-matching-design.md)).
- **Alternatif yang ditolak:** 2a (tanpa login) dulu, baru 2b (platform login).
- **Konsekuensi:** plan-nya besar, dan bagian platform paling nggak pasti. Kalau satu platform macet, platform itu di-skip, jadi sisa pipeline tetap jalan.
- **Authority:** pilihan Akmal (chat 2026-10-03).

## D-012 — 2026-10-03 — Platform login cuma buat hook, SigLIP rerank buat semua shot

- **Status:** accepted
- **Keputusan:** TikTok/Douyin/RedNote/Pinterest cuma dicari buat klip `HOOK_SECONDS` awal. Shot lain tetap dari Pexels/Pixabay, tapi diurutkan ulang pakai skor SigLIP teks vs thumbnail.
- **Alasan:** request scraping per video tetap sedikit, jadi risiko akun ke-flag lebih rendah.
- **Authority:** Akmal awalnya milih platform buat semua shot, terus direvisi sendiri jadi cuma hook (chat 2026-10-03).

## D-013 — 2026-10-03 — SigLIP ViT-B-16 lewat open_clip, torch CPU

- **Status:** accepted
- **Keputusan:** embedding pakai `open_clip` model `ViT-B-16-SigLIP` (`webli`) di CPU.
- **Alternatif yang ditolak:**
  - CLIP ViT-B-32: lebih kecil tapi kurang akurat.
  - ViT-L / so400m: kegedean buat CPU.
  - Gemini vision buat scoring: kuota dan sering 503.
  - Torch CUDA di RTX 2050: download ±2.5 GB, padahal volume per run kecil.
- **Authority:** rekomendasi agent, disetujui Akmal (chat 2026-10-03).

## D-014 — 2026-10-03 — Playwright + yt-dlp, platform ke-blok di-skip

- **Status:** accepted
- **Keputusan:**
  - Search lewat Chrome Playwright pakai profil login, dengan cara nangkep JSON internal. Download pakai `yt-dlp` + cookies profil.
  - Kalau kena captcha atau login expired, platform itu di-skip buat sisa run, dan run tetap jalan.
  - Video source di-download di step `hook`, bukan `source`, karena step `source` dikunci begitu suara ada (D-007).
- **Authority:** approach A dan aturan skip dipilih Akmal. Lokasi download source dari agent (chat 2026-10-03).

## D-015 — 2026-10-03 — `HOOK_EXACT_THRESHOLD` tetap 0.85

- **Status:** accepted (sementara)
- **Konteks:** E2E pertama `i2xag_1OJfM`: skor pemenang 0.66–0.78, dan nggak ada pasangan yang klip persis sama. A (skor terendah pasangan "sama persis") nggak ada, jadi threshold nggak bisa dihitung.
- **Keputusan:** default tetap 0.85, dan semua pemenang dilabel `similar`.
- **Konsekuensi:** kalibrasi diulang setelah TikTok/Douyin/RedNote jalan stabil dan ada pasangan klip yang persis sama.
- **Authority:** aturan kalibrasi dari plan Task 14 Step 6, dijalanin agent (2026-10-03).

## D-016 — 2026-10-09 — Revisi setelah review video Fase 2

- **Status:** accepted
- **Konteks:** Review Akmal atas `i2xag_1OJfM` Fase 2:
  - hook udah cocok ±70%
  - layout oke
  - shot non-hook nggak nyambung, kecuali shot yang nyebut nama hewan
  - ganti shot terlalu sering
  - Douyin/RedNote susah login
- **Root cause shot nggak nyambung:** query-nya udah bener, tapi Pexels/Pixabay hampir nggak punya video hewan langka. Foto hewannya ada.
- **Keputusan:**
  - `MAX_SHOT_SECONDS` 2.5 → 4.
  - Rerank pakai query tiap kandidat, bukan kalimat narasi.
  - Batas relevansi 0.10. Kalau skor terbaik di bawah itu, grup media lain (biasanya foto) ikut dinilai, terus yang skornya paling tinggi dipakai.
  - Pinterest ikut jadi sumber shot non-hook (`CLIP_PLATFORMS=pinterest`, maksimal 40 search per run).
  - Default `HOOK_PLATFORMS` jadi `tiktok,pinterest`. Douyin/RedNote tetap ada di code dan bisa diaktifin lagi lewat `.env`.
- **Konsekuensi:** D-012 direvisi, karena platform login (Pinterest) sekarang juga dipakai buat shot non-hook. Run nambah ±16–32 search Pinterest, kira-kira 3–5 menit.
- **Authority:** semua usulan dari agent, disetujui Akmal (chat 2026-10-09). Angka 4 detik dipilih Akmal.

## D-017 — 2026-10-09 — Relevansi klip dinilai pakai nama subjek, hook cuma ke shot yang selesai di area hook

- **Status:** accepted
- **Konteks:** Review Studio Akmal:
  - Shot "Number five, horseshoe crab" (9.74–12.45s) masih kebagian klip hook pterosaurus, karena aturannya `start_s < 10`.
  - Shot aksi masih nampilin pemandangan doang (pasir, air, dasar sungai).
  - Pengukuran: skor SigLIP pakai query lengkap nggak bisa misahin yang meleset (0.145–0.147) dari yang nyambung (0.153). Pakai nama hewan aja, pemisahnya jelas: meleset 0.000–0.088, nyambung ≥0.105.
- **Keputusan:**
  - Klip hook cuma dipasang ke shot dengan `end_s ≤ HOOK_SECONDS + 0.5`.
  - Teks penilaian relevansi = nama subjek beat. Sumbernya field `subject` baru di schema naskah (prompt Gemini diupdate), atau beat countdown "Number X, …" yang dibawa ke beat berikutnya. Kalau nggak ada subjek, fallback ke query.
  - Batas relevansi tetap 0.10.
  - Flag `--no-render`: review di Remotion Studio dulu, render final setelah Akmal oke.
- **Authority:** Akmal minta "naikin batas" (shot aksi meleset diganti foto) dan review via Studio. Mekanisme subjek dari agent, berdasarkan pengukuran di atas (chat 2026-10-09).

## D-018 — 2026-10-11 — Risiko ToS platform diterima Akmal

- **Status:** accepted
- **Konteks:** search otomatis Douyin/RedNote gagal karena captcha (Douyin) dan blok IP "IP at risk" (RedNote, error 300012).
- **Keputusan:** Akmal secara eksplisit nerima risiko pelanggaran ToS platform (scraping, pakai klip creator lain) dan minta dicariin repo open source yang bisa search otomatis. Kutipan: "persetan dengan TOS, catat ini".
- **Batas yang tetap dipegang agent:**
  - Challenge otomatis yang diselesaiin browser biasa tanpa manusia (misalnya WAF proof-of-work Douyin) boleh dipakai.
  - Captcha yang butuh manusia nggak di-solve otomatis.
  - Blok IP nggak diakalin pakai proxy/rotasi IP.
- **Konsekuensi:** akun bisa ke-ban, dan video bisa kena klaim hak cipta atau takedown. Ini tanggung jawab Akmal.
- **Authority:** keputusan Akmal (chat 2026-10-11).

## D-019 — 2026-10-13 — Klip dicari manual oleh Akmal, Bilibili di-skip

- **Status:** accepted
- **Konteks:** Hasil spike 2026-10-11/12:
  - login web Douyin ditolak (QR udah dikonfirmasi, tetap "Please log in using the Douyin App")
  - RedNote diblok IP (300012)
  - MediaCrawler kena tembok yang sama
  - search lewat videosearch.io dianggap nggak akurat
- **Keputusan:**
  - Mode `CLIP_SOURCE=manual` jadi default: semua shot dicari Akmal sendiri, link/file diinput lewat halaman brief lokal, harness yang download + pilih bagian pakai SigLIP. Spec: [manual clip source](superpowers/specs/2026-10-13-manual-clip-source-design.md).
  - Semua shot wajib diisi sebelum `fetch` jalan.
  - Post foto ganda dipilih otomatis pakai SigLIP, atau dipaksa pakai `#n`.
  - Mode `auto` (Fase 2) tetap ada sebagai opsi.
  - Bilibili nggak ditambah.
- **Authority:** keputusan Akmal (chat 2026-10-12/13). Pendekatan A (manual default, auto disimpan) dipilih Akmal.

## D-020 — 2026-10-13 — Link manual diisi per konteks, bukan per shot

- **Status:** accepted (revisi D-019)
- **Konteks:** Di brief pertama, run i2xag minta 16 link. Padahal shot 1–3 itu 1 klip hook yang sama, dan shot 4–6 sama-sama horseshoe crab.
- **Keputusan:**
  - Shot dikelompokin per konteks: semua shot hook jadi 1 kelompok `hook`, sisanya per subjek beat. Kalau subjeknya kosong, per beat.
  - Link/file diisi per kelompok. Boleh lebih dari 1 per kelompok.
  - `fetch` yang ngebagi: tiap shot dapat potongan video yang nggak tumpang tindih, atau foto yang beda. Kalau stok kurang, kelompok error "tambah link". Revisi D-021: awalnya boleh dipakai ulang plus peringatan.
- **Authority:** keputusan Akmal (chat 2026-10-13: "link yang ditambahin itu sesuai konteksnya, bukan sesuai shot").

## D-021 — 2026-10-13 — Klip nggak boleh tampil 2 kali, dan momen "Number X" pakai number card Remotion

- **Status:** accepted. No-reuse udah diimplementasi, number card baru dicatat dan belum dibikin.
- **Konteks:** Review Studio run i2xag (Akmal, 2026-10-13).
- **Keputusan:**
  - **No-reuse:** potongan klip yang udah tampil nggak dipakai lagi di shot setelahnya, termasuk lintas kelompok kalau link-nya sama. Urutan pilihan `fetch`:
    1. video/foto yang belum kepakai
    2. bagian lain (nggak overlap) dari video yang udah kepakai, plus peringatan
    3. kalau dua-duanya nggak ada, kelompok error "tambah link"
  - **Number card:** pas narasi nyebut "Number X" (countdown), yang tampil itu number card buatan Remotion, bukan klip dari link.
    - Gaya di source i2xag: angka besar warna chrome/silver di background gelap berpartikel, abis itu gambar subjek dalam frame menyala plus label nama subjek.
    - Momen ini dideteksi dari teks beat ("Number five, …") + timing alignment TTS.
    - Bagian narasi "Number X" nggak masuk brief.
- **Authority:** Akmal (chat 2026-10-13: "klip yang udah digunakan jangan digunakan lagi setelahnya", "pas audio nyebutin 'number ...' itu harusnya muncul klip number … tolong catat agar buat kustom dengan remotion").

## D-022 — 2026-10-13 — RedNote dihapus dari sumber link klip

- **Status:** accepted (revisi D-019)
- **Konteks:** Tes link beneran `xhslink.com/o/44jNwnYztNq` diarahkan ke `/login`, karena note RedNote minta login. Download tanpa login nggak jalan, dan dari Fase 2 cookie login RedNote juga belum beres.
- **Keputusan:**
  - Link RedNote (`xiaohongshu.com`, `xhslink.com`, `rednote.com`) ditolak di brief dengan pesan "save file-nya dari app, terus upload".
  - Resolver RedNote dihapus.
  - Upload file tetap jalan, jadi video dari app RedNote masih bisa dipakai lewat upload.
  - Mode `auto` nggak diubah. RedNote juga nggak masuk default `HOOK_PLATFORMS`.
- **Authority:** Akmal (chat 2026-10-13: "rednote hapus aja dari source clip").

## D-023 — 2026-10-13 — Timing ikut suara asli; panah/lingkaran sebentar + muter; nanti dipicu script

- **Status:** accepted. Poin 1–3 udah diimplementasi, poin 4 dicatat buat nanti.
- **Konteks:** Akmal review 3C-1 + 3B di Studio.
  - Panah tampil sepanjang shot dan geraknya kelambatan.
  - Angka countdown kerasa "nunggu SFX".
- **Keputusan:**
  1. **Awal kata digeser ke suara beneran.** Alignment ElevenLabs ngitung jeda sebelum kata sebagai bagian dari kata itu, makanya bisa kecepetan 0,1–0,9 detik. Sekarang awal kata ditentuin dari energi `voice.mp3` (`mayzfact/voice_onset.py`). Ini kepakai di caption dan card countdown.
  2. **Number card:**
     - Background tampil dari awal beat.
     - Angkanya melesat masuk pas "Number" kedengeran, barengan puncak SFX `whoosh-clean.mp3`.
     - Subject card mulai pas nama subjek kedengeran.
  3. **Panah/lingkaran:**
     - Muncul 6 frame setelah shot mulai, barengan `quick-ting.mp3`.
     - Tampil sampai fade-nya selesai 0,5 detik (15 frame) sebelum ganti klip. Batas 40 frame awal dihapus atas permintaan Akmal.
     - Panah nyapu 1× setengah putaran (kanan → atas → kiri) sepanjang durasi tampil. Sempat diganti muter terus, tapi Akmal minta balik ke 1 sapuan.
     - Volume quick-ting 0,35.
     - Query dari keyword dipotong 2 kata, karena keyword panjang bikin OWLv2 nangkep benda lain.
     - Panah muter setengah putaran di sekeliling subjek.
     - Lingkaran digambar dalam 6 frame.
  4. **Panah dipicu script (nanti):** nggak semua klip dapat panah. Panah muncul kalau narasinya ngajak lihat, misalnya "look at this". Ini butuh perubahan di logic script dan cuma buat kasus tertentu, jadi dikerjain nanti.
- **Authority:** Akmal (chat 2026-10-13).
