# Decision Log

Keputusan penting project mayzfact-automation. Detail teknis Fase 1 ada di [`docs/superpowers/specs/2026-09-30-fase1-pipeline-design.md`](superpowers/specs/2026-09-30-fase1-pipeline-design.md).

## D-001 — 2026-09-30 — Project dikerjain bertahap dalam 4 fase

- **Status:** accepted. Urutan Fase 2 dan 3 masih boleh dituker. Poin 4 diganti D-025.
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

- **Status:** diganti D-028 (Gemini dicabut)
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

- **Status:** diganti D-028 (Gemini dicabut)
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

- **Status:** accepted. Poin 1–3 diimplementasi di 3C-1, poin 4 di 3C-2 (lihat D-024).
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

## D-024 — 2026-10-14 — Emoji animasi + CTA like/subscribe; panah cuma di beat yang ngajak lihat

- **Status:** accepted, diimplementasi di 3C-2.
- **Konteks:** Fase 3C-2. Akmal mau emoji yang ada animasinya kayak di source i2xag, dan SFX-nya dia yang milih.
- **Keputusan:**
  1. **Tanda beat "Gabungan".** Naskah baru dapat `point`/`emoji`/`emoji_word` dari prompt rewrite. Naskah lama ditandain Gemini tanpa ganti suara, hasilnya di-cache di `annotations.json`.
  2. **Emoji:** Noto Emoji Animation (Lottie, CC BY 4.0). Pilihannya dibatasi 28 emoji yang udah dicek ada animasinya. Muncul barengan `pop_7e9Is8L.mp3`.
  3. **Timing emoji:**
     - Mulai di `emoji_word`. Kalau jatuh di tengah CTA, mulainya digeser ke akhir CTA.
     - Boleh nyambung lewat akhir beat-nya, maksimal 2,5 detik.
     - Berhenti sebelum card countdown, emoji, atau CTA berikutnya, atau pas video habis.
     - Kalau kata pemicunya kurang dari 1 detik sebelum card/CTA, mulainya dimajuin ke kata sebelumnya.
     - Kalau tetap kurang dari 20 frame, emojinya nggak dipasang.
  4. **CTA like/subscribe:**
     - Animasinya ngikutin source frame per frame. Bunyi klik pakai `mouse-click-by-ek6_VR0O6PL.mp3`.
     - "like" cuma dihitung kalau ngajak (misalnya "hit like" atau "like and subscribe"), bukan yang artinya "mirip".
     - Subscribe nunggu like selesai, dan dua-duanya harus muat sebelum video habis.
  5. **Panah/lingkaran** cuma di shot yang beat-nya `point`. Beat tanpa tanda nggak dapat panah. Ini nutup D-023 #4.
- **Authority:** Akmal (chat 2026-10-14).

## D-025 — 2026-10-14 — Fase 4 jadi versi harness: project dijalanin lewat AI agent

- **Status:** accepted. Ngegantiin D-001 poin 4. Poin 4 di bawah diganti D-027.
- **Konteks:** Alur sekarang tetap butuh Akmal di tiap video: isi link klip, review di Studio, oke-in render. Jadi pipeline yang jalan sendiri pakai cron udah nggak relevan. Akmal mau project ini dipakai lewat harness AI agent: Claude Code, Codex, OpenCode, Antigravity.
- **Keputusan:**
  1. Aturan main agent ada di `AGENTS.md`. `CLAUDE.md` cukup import `AGENTS.md`, karena Claude Code bacanya `CLAUDE.md`.
  2. Alur bikin 1 video ada di skill `.agents/skills/bikin-short/SKILL.md`. Codex, OpenCode, dan Antigravity nemu skill ini otomatis, sedangkan Claude Code diarahin lewat `CLAUDE.md`.
  3. Metadata upload (judul, deskripsi, credit klip, jadwal) ditulis agent ke `runs/<id>/upload.md`. Nggak perlu kode baru.
  4. Akmal upload sendiri di YouTube Studio. Upload lewat YouTube Data API ditunda: project Google Cloud yang belum lolos audit bakal ngunci video upload-annya jadi private.
  5. Milih source otomatis jadi opsional. Akmal tetap ngasih URL, atau agent nyariin kandidat.
- **Authority:** Akmal (chat 2026-10-14).

## D-026 — 2026-10-14 — Link klip diisi per shot, brief kebuka ke LAN

- **Status:** accepted. Ngubah cara isi link di D-020 (kelompok konteks tetap ada buat ngelompokin tampilan dan frame source).
- **Konteks:** Akmal ngisi link dari HP, dan pengen milih klip yang pas buat tiap shot, termasuk bagian detik tertentu.
- **Keputusan:**
  1. Link diisi per shot: 1 shot = 1 link atau 1 file upload, plus Mulai/Selesai (detik) opsional. Disimpan di `links.json` bagian `shots`.
  2. Shot berurutan yang pakai link sama, videonya nyambung (nggak loncat ke awal klip).
  3. Server brief selalu bind `0.0.0.0` biar bisa dibuka dari HP. Host cuma boleh localhost atau IP privat, POST tetap dicek Origin. Nggak ada login, jadi jangan dijalanin di WiFi publik.
  4. Naskah: tiap item countdown minimal punya 2 beat penjelasan.
- **Authority:** Akmal (chat dengan harness lain, 2026-10-14).

## D-027 — 2026-10-15 — Upload terjadwal lewat YouTube Data API

- **Status:** accepted. Ngegantiin D-025 poin 4.
- **Konteks:** Akmal mau agent sekalian upload dan jadwalin video setelah `final.mp4` oke. Project Google Cloud-nya udah lolos audit YouTube API, jadi video yang di-upload lewat API nggak kekunci private.
- **Keputusan:**
  1. Login OAuth sekali lewat `mayzfact login youtube` (scope `youtube.upload`). Token ditulis ke baris `YOUTUBE_TOKEN_JSON` di `.env`, sama kayak `YOUTUBE_CLIENT_SECRET_JSON`.
  2. Agent nulis metadata ke `runs/<id>/upload.json`: judul bahasa Inggris ≤ 100 karakter + `#Shorts`, deskripsi (ringkasan + hashtag, tanpa daftar credit klip: Akmal minta dihapus setelah upload pertama), 5–10 tag, kategori sesuai isi, bahasa `en`, made for kids `false`.
  3. Agent ngusulin slot kosong berikutnya (04.00/21.00 WIB) lewat `mayzfact next-slot`. Upload cuma jalan setelah Akmal konfirmasi jamnya.
  4. Video di-upload sebagai private + `publishAt`, jadi YouTube yang bikin public di jamnya. Hasilnya di `runs/<id>/youtube.json`, dan run yang sama nggak bisa ke-upload 2 kali.
  5. Kalau Akmal minta langsung tayang, `mayzfact upload <id> --now` upload sebagai public tanpa `publishAt`.
- **Authority:** Akmal (chat 2026-10-15).

## D-028 — 2026-10-15 — Naskah ditulis agent, Gemini dicabut

- **Status:** accepted. Ngegantiin D-003 dan D-010.
- **Konteks:** Naskah dari Gemini kaku dan humornya hilang (run `4735ZE89GXQ`). Akmal mau naskah jadi tanggung jawab harness agent dan dia review dulu sebelum suara dibikin.
- **Keputusan (dari interview):**
  1. Naskah = nulis ulang source: fakta, urutan, dan momen tetap, kata-katanya baru. Nggak nambah fakta dari luar source.
  2. Nada persis source, termasuk "bro" dan celetukan penutup tiap item.
  3. Panjang ±80% durasi source, intro dipadetin.
  4. CTA dipadetin ke comment + like + subscribe (1–2 beat), harus pakai kata "like"/"subscribe" beneran. `check-script` nolak kalau kata CTA source hilang.
  5. Panah/ajakan lihat: agent yang nentuin, nggak ada kuota.
  6. Review di chat per beat (teks baru | sumber | keyword). Suara setelah Akmal oke.
  7. Gemini dicabut total: naskah, keyword klip (EN + ZH), tanda emoji/panah, BGM, keyword hook semua ditulis agent di `script.json`. `run` berhenti exit 3 sampai naskah ada; frame hook dibikin di step `source` biar agent bisa lihat.
- **Authority:** Akmal (chat 2026-10-15).

## D-029 — 2026-10-15 — Brief: audio naskah, download duluan, frame per shot wajib

- **Status:** accepted, diimplementasi.
- **Konteks:** Revisi brief dari Akmal setelah ngisi link video pertama lewat harness.
- **Keputusan:**
  1. Tombol waktu di tiap shot muter `voice.mp3` dari `start_s` sampai `end_s` (waktu itu milik suara kita, bukan source). Video source tetap ada dengan kontrol bawaan.
  2. Link yang disimpan langsung di-download worker di server brief, pakai `Obtainer` + cache yang sama dengan fetch. Status per URL di `runs/<id>/prefetch.json`, kelihatan di halaman. Link gagal nggak diulang sama autosave (biar link captcha nggak dihajar tiap ketik); klik Simpan atau start server lagi = coba lagi. Link `siap` nggak diulang sama sekali.
  3. Tiap shot punya 3 frame referensi dari source: hook dari segmen hook, shot subjek dari rentang subjeknya di transcript, sisanya (CTA/intro) dari posisi proporsional. `mayzfact brief` nolak jalan kalau ada shot tanpa frame. Frame per kelompok dihapus.
- **Authority:** Akmal (chat 2026-10-15).

## D-030 — 2026-10-16 — ngrok default buat brief dan Studio

- **Status:** accepted, diimplementasi.
- **Konteks:** WiFi yang dipakai Akmal ngeblok akses HP ke laptop (client isolation), jadi alamat LAN brief nggak kepake.
- **Keputusan:** `mayzfact brief` otomatis buka `ngrok http <port>` dengan `--basic-auth` dari `NGROK_BASIC_AUTH` (`.env`), dan ngrok ikut mati bareng brief (`taskkill /T`, karena ngrok scoop jalan lewat shim). `--no-ngrok` buat skip. `mayzfact tunnel <port>` buat Studio (3000). Tanpa `NGROK_BASIC_AUTH` yang valid (password ≥ 8 karakter), ngrok nggak dinyalain sama sekali. Server brief nerima Host `*.ngrok-free.app`/`.dev`/`.io` (commit `8ee0f39`).
- **Authority:** Akmal (chat 2026-10-16).

## D-031 — 2026-10-17 — Mode auto dihapus, `.env` cuma rahasia

- **Status:** accepted, diimplementasi.
- **Konteks:** Semua video lewat jalur manual sejak D-019/D-028. Mode auto (`CLIP_SOURCE=auto`: step `hook` + `clips`, Pexels/Pixabay, scraping TikTok/Douyin/Pinterest pakai Playwright) nggak kepake.
- **Keputusan:**
  1. Pipeline cuma `source → tts → plan → fetch → timeline → render`. Kode, test, env, dan dependency `playwright` khusus auto dihapus. `mayzfact login` tinggal `youtube`. Field naskah `fallback_query` dicabut (naskah lama yang masih punya field ini tetap kebaca).
  2. `.env` cuma 4 rahasia: `ELEVENLABS_API_KEYS`, `YOUTUBE_CLIENT_SECRET_JSON`, `YOUTUBE_TOKEN_JSON`, `NGROK_BASIC_AUTH`. Setting lain jadi default di `Settings` (`mayzfact/config.py`), biar harness bisa langsung ngubah di kode.
  3. Keputusan lama (D-002, D-011–D-017, D-019) nggak diedit, cuma digantiin di sini.
- **Voice ID pindah ke kode:** tugas D-009 (ganti voice Liam sebelum 2026-12-31) sekarang dikerjain di `Settings.elevenlabs_voice_id` (`mayzfact/config.py`), bukan `ELEVENLABS_VOICE_ID` di `.env` (variabel itu udah diabaikan).
- **Nanti, kalau auto balik:** yang otomatis cuma nyari klip, pakai browser Akmal sendiri yang udah login TikTok. Kode Playwright lama nggak dipakai ulang, ditulis dari nol.
- **Authority:** Akmal (chat 2026-10-17).

## D-032 — 2026-10-18 — Slot tayang jadi 01.00 dan 04.00 WIB

- **Status:** accepted, diimplementasi.
- **Keputusan:** `SLOT_HOURS` di `mayzfact/youtube.py` jadi `(1, 4)`. Slot 21.00 diganti 01.00 WIB, slot 04.00 tetap. Keduanya jatuh pas jam siang-sore US (01.00 WIB = 14.00 EDT, 04.00 WIB = 17.00 EDT; mulai 1 November jadi 13.00 dan 16.00 EST).
- **Revisi:** D-027 dan angka 21.00 di Fase 4 (yang lama nggak diedit).
- **Authority:** Akmal (chat 2026-10-18).

## D-033 — 2026-10-20 — Hook naskah dipoles, target kata pakai 2.2 kata/detik

- **Status:** accepted, diimplementasi.
- **Konteks:** Data YouTube Studio Akmal: ±40% penonton swipe di awal, retensi turun di detik 20–40. 4 video terakhir dibuka label tanpa kata kerja ("Five most beautiful white animals."), celetukan nyontek source, dan durasinya 81–98% source (target 80%) karena `check-script` ngitung 2.6 kata/detik, padahal ElevenLabs v3 cuma 2.07–2.28.
- **Keputusan:**
  - `WORDS_PER_SECOND` di `mayzfact/steps/script.py` jadi 2.2.
  - Skill `bikin-short` langkah 2 dapat bagian Hook: beat 1 kalimat "These…" lengkap dengan kata kerja + pembatas source, beat 2 teaser nomor 1 yang nggak dilemahin, teaser nggak dibuka "Number one,".
  - Celetukan pakai gambaran sendiri, bukan salinan source.
  - Fakta, urutan item, bagian tengah, dan posisi CTA nggak diubah.
- **Ukuran:** "Viewed vs swiped away" 2–3 video berikutnya. Kalau nggak turun dari 40%, coba pamerin nomor 1 di detik 0.
- **Authority:** Akmal (chat 2026-10-20).

## D-034 — 2026-10-20 — Token YouTube bisa baca Analytics

- **Status:** accepted, diimplementasi.
- **Keputusan:** `SCOPES` di `mayzfact/youtube.py` nambah `yt-analytics.readonly` dan `youtube.readonly` (cuma baca), buat ngambil kurva retensi per video lewat YouTube Analytics API. Butuh login ulang sekali (`mayzfact login youtube`). "Viewed vs swiped away" belum ada di API, tetap dari YouTube Studio.
- **Authority:** Akmal (chat 2026-10-20).

## D-035 — 2026-10-20 — Review di Studio diganti preview render

- **Status:** accepted.
- **Konteks:** Akmal nggak bisa review di Remotion Studio (chat 2026-10-20).
- **Keputusan:** Checkpoint review di Studio (langkah 7 skill `bikin-short`) dilewat. Habis fetch + timeline langsung render, terus agent ngirim preview 720p (`runs/<id>/preview.mp4`) ke Akmal. Itu checkpoint review-nya: revisi dikerjain setelah Akmal nonton, terus render ulang. Upload tetap nunggu oke video + konfirmasi jam. Studio cuma dibuka kalau Akmal minta.
- **Konsekuensi:** Tiap revisi visual = 1 render ulang (±5–8 menit).
- **Authority:** Akmal (chat 2026-10-20: "untuk sekarang dan seterusnya render aja langsung terus kirim previewnya").
