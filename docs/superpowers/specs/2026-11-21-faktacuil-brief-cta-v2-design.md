# FaktaCuil brief v2 + CTA v2

Tanggal: 2026-11-21. Disetujui Akmal di chat (approach A+A).

## Kenapa

Akmal sekarang fokus ke satu channel: FaktaCuil. Ada dua hal yang bikin kerjanya lambat:

1. Halaman brief (`mayzfact brief`). Urutan shot loncat-loncat, preview baru muncul setelah refresh, keyword klip kurang nyambung sama narasi shot, dan frame referensi ditempel di tiap shot padahal posisinya cuma tebakan proporsional.
2. CTA FaktaCuil. Sekarang tiap video wajib punya CTA like gimmick dengan 4 format (`question`/`reveal`/`escape`/`escalate`). Akmal mau CTA opsional dan formatnya diganti 4 format baru.

## Goals

- Brief lebih cepat diisi dari HP: shot urut, preview langsung jalan, bisa ngatur speed klip.
- Keyword bantu nyari klip nyambung ke kalimat narasi shot itu, English only.
- Frame referensi diambil dari shot asli di video source, ditampilin di satu kartu terpisah.
- CTA FaktaCuil opsional, dengan 4 format baru plus CTA-2 (kuis di akhir).

## Non-goals

- Mode MayzFact (`top3`) nggak dihapus. Dibiarin jalan. Perubahan di bagian bersama (brief, fetch, schema `Beat`) nggak boleh bikin test top3 gagal.
- Pindah ke HyperFrames. Tetap Remotion.
- Redesain visual pill LIKE/LIKED dan stiker yang udah ada. Gerak pill dan kursor tetap.

## Anti-goals

- Jangan bikin run yang `voice.mp3`-nya udah ada jadi wajib dibikin ulang. Naskah lama tetap harus bisa lanjut fetch/timeline/render, atau ditolak dengan pesan jelas (lihat "Kompatibilitas").
- Speed nggak boleh bikin timing cache blur teks (`textblur.json`) dan overlay (`overlays.json`) melenceng.
- Jumlah kuis CTA-2 nggak boleh salah. Angkanya dihitung code, bukan agent.

## Constraint

- Brief nggak punya login. Endpoint baru ikut aturan host check yang udah ada di `mayzfact/brief/server.py`.
- Langkah hiasan (stiker, emoji, SFX) nggak boleh bikin run gagal. Bungkus try/except + log.
- Fitur baru: TDD (test merah dulu).
- Komentar kode bahasa Indonesia santai, istilah teknis English.
- Model agent: jangan ada yang pakai Fable.

## Approaches yang dipertimbangkan

**Speed per shot**
- A (dipilih): speed dipasang di fetch waktu motong klip. Ambil `durasi_shot × speed` detik dari source, terus ffmpeg `setpts` ke durasi shot. `clip.mp4` hasilnya udah cepat/lambat, Remotion nggak berubah. Blur teks dan overlay dideteksi dari file klip, jadi timing-nya otomatis pas.
- B (ditolak): klip dipotong biasa, speed diatur lewat `playbackRate` di Remotion. Diff fetch kecil, tapi cache blur teks/overlay ngitung dari klip yang belum dipercepat, jadi harus ditambal di dua tempat.

**Pembagian kerja**
- A (dipilih): 2 branch paralel lewat herdr-team, file-nya hampir nggak tabrakan.
- B (ditolak): 1 branch berurutan. Lebih lambat.

## Branch 1: `fase-brief-v2`

### T1. Speed per shot

- Brief: tiap shot punya pilihan speed. Pilihannya `0.5, 0.75, 1, 1.25, 1.5, 2`, default `1`. Disimpan di entry shot `links.json` sebagai `speed` (float). Entry tanpa `speed` = 1.
- Fetch: shot dengan speed ≠ 1 butuh `durasi_shot × speed` detik source. Semua logika pilih potongan (`start_s` manual, lanjut dari shot sebelumnya, `_first_free`, `_best`, `source.used`) pakai durasi source itu. Hasil akhir dipotong ke durasi shot pakai `setpts=PTS/speed`. Klip tetap tanpa suara.
- Foto: speed diabaikan. Pilihannya disembunyiin atau disabled di UI.
- `clips.json` nyimpen `speed` per shot buat audit.
- `start_s` tetap detik mulai di video source. `end_s` sekarang nggak dibaca fetch, dan spec ini nggak ngubah itu: durasi source selalu `durasi_shot × speed` dari `start_s` (*call* lead).
- Hook top3 yang lewat `_continuous`: speed boleh diabaikan (tetap 1). Builder yang nentuin.

### T2. Preview langsung muncul tanpa refresh

- Sekarang `_clip_tools` cuma nge-render `preview-box` kalau link udah ada waktu halaman dibuka.
- Ubah: `preview-box` selalu di-render. Tombolnya disabled sampai shot punya link dan badge prefetch-nya `siap` (atau shot punya file upload). Polling `/api/progress` (tiap 2 detik) yang ngaktifin tombol.
- Kalau preview lagi kebuka dan link shot-nya diganti, preview nutup sendiri atau reload ke klip baru.
- Semua setting shot langsung kepakai di preview tanpa simpan/refresh: start, end, SFX + detik SFX, dan speed (`video.playbackRate = speed`, loop bagian yang dipakai ngikutin durasi source = durasi shot × speed).

### T3. Urutan shot

- Bug: kartu brief dirender per grup (`render_page` → `_card` per `plan["groups"]`). Grup subject ngumpulin shot dengan subject sama dari seluruh video, jadi urutannya loncat (contoh: shot 1, 3, terus 2).
- Ubah tampilan brief jadi urut index shot 1..N. Label grup/subject cuma jadi info di tiap shot.
- `plan["groups"]` di `plan.json` tetap ada karena dipakai fetch (`_continuous`, `_run_group`). Jangan ubah perilaku fetch.
- Metric bar per grup di header boleh tetap ada.

### T5. Frame referensi di kartu terpisah

- Cuma buat `narration_mode` `faktacuil` (*call* lead). Top3 tetap pakai `ref_frames` per shot, `_shot_frames`, dan `missing_frames` kayak sekarang, jadi test top3 nggak berubah. T3 (urutan shot) berlaku buat dua mode karena cuma ngubah tampilan.
- FaktaCuil: hapus `ref_frames` per shot dari tampilan brief, dan jangan generate lagi di `_shot_frames`.
- Bikin satu kartu "Frame referensi source" di brief.
- Isinya: cut detection di seluruh `source.mp4` (pakai `detect_cuts` + `merge_cuts` + `segments` dari `mayzfact/scenes.py`). Tiap shot source diambil 2 frame di posisi acak dalam shot itu. Random-nya pakai seed `video_id`, jadi plan ulang ngasih frame yang sama.
- Frame disimpan di `plan/ref_XX_K.jpg`, dicatat di `plan.json` sebagai `source_shots: [{index, start_s, end_s, frames}]`.
- Tiap frame nampilin detik-nya di source, klik = lightbox (pakai `openLightbox` yang udah ada).
- FaktaCuil: `missing_frames` (brief nolak jalan kalau ada shot tanpa frame) nggak berlaku. Brief jalan walau kartu frame kosong, cukup kasih pesan.
- Batas: kalau source punya shot banyak banget (lebih dari ±60), *builder yang nentuin* mau dibatasi atau nggak. Catat pilihannya.
- Kalau `source.mp4` nggak ada, kartu frame nampilin pesan, plan nggak gagal.

## Branch 2: `fase-cta-v2`

### T4. Keyword English only + lebih nyambung

- Hapus `queries_zh` dari skill FaktaCuil, `check-script` FaktaCuil, dan tampilan brief. Field di schema `Beat` tetap ada dengan default `[]` (top3 masih pakai). Naskah FaktaCuil yang ngisi `queries_zh` nggak ditolak, cuma diabaikan.
- Aturan nulis `queries` di skill `bikin-faktacuil`:
  - 2–4 query per beat, English.
  - Tiap query nyebut hal yang beneran keliatan di kalimat beat itu (subjek + aksi/objek), bukan topik umum video. Contoh beat "Padahal kardus itu sempit dan nggak empuk": jangan `cat`, tapi `cat squeezing into small cardboard box`.
  - Beat CTA: query buat background yang cocok sama kalimat CTA-nya.
- `check-script` nambah cek ringan: query FaktaCuil harus ASCII (nolak huruf Mandarin), minimal 2 per beat.

### T6. CTA opsional

- `cta_scene` di schema jadi opsional buat FaktaCuil. Top3 tetap wajib.
- Naskah FaktaCuil tanpa CTA: nggak ada scene LIKE/stiker, semua shot jadi shot biasa.
- `check-script` ngecek kecocokan: kalau naskah punya beat CTA tapi `cta_scene` kosong, atau sebaliknya, ditolak.
- Agent milih mau pakai CTA atau nggak. Akmal lihat waktu review naskah.

### T7. Format CTA baru

4 format lama (`question`/`reveal`/`escape`/`escalate`) dihapus, ganti 4 format ini. Kalimat contoh dari Akmal; boleh divariasi dikit asal kata kuncinya ada.

| Format | Posisi | Contoh kalimat | Kata kunci wajib | Visual |
| --- | --- | --- | --- | --- |
| `lucky` (F-a) | tengah | "tapi sebelum lanjut coba tekan like, jika beruntung bisa muncul [objek]" | ajakan like + `muncul` + nama objek | pill LIKE → klik → LIKED → stiker objek |
| `subscribe` (F-b) | tengah | "tapi sebelum lanjut coba tekan like, nanti muncul [objek], subscribe jika berhasil" | ajakan like + `muncul` + nama objek + `subscribe` | pill LIKE → klik → LIKED → stiker → pill SUBSCRIBE → klik → SUBSCRIBED |
| `emoji` (F-c) | akhir, satu-satunya CTA | "tapi mengapa ada emoji [X] saat tekan like?" | `emoji` + `tekan like` + diakhiri `?` | pill LIKE → klik → LIKED → emoji animasi X |
| CTA-2 (`quiz`) | akhir | "nah coba tebak berapa kali aku bilang [kata]" | `berapa kali aku bilang` + kata target | caption biasa, tanpa visual tambahan |

Nama format (`lucky`/`subscribe`/`emoji`) *usulan spec ini*. Builder boleh ganti namanya, asal konsisten.

Aturan kombinasi:
- CTA-1 = salah satu dari `lucky`, `subscribe`, `emoji`. Maksimal 1.
- CTA-2 boleh sendiri atau bareng `lucky`/`subscribe`.
- `emoji` nggak boleh bareng CTA lain, termasuk CTA-2.
- Kombinasi valid: tanpa CTA; `lucky`; `subscribe`; `emoji`; CTA-2; `lucky` + CTA-2; `subscribe` + CTA-2.

Aturan per format:
- **`lucky` / `subscribe`:** blok 1–3 beat di tengah. Tepat 1 ajakan like Indonesia (deteksi `id_like_positions` yang udah ada). Nama objek di blok CTA harus cocok sama `theme`. `subscribe` cuma boleh di format `subscribe`; komen tetap dilarang.
- **`emoji`:** blok CTA = beat terakhir video (1–2 beat terakhir). Wajib ada field emoji (karakter emoji apa aja, misal `"📦"`), nggak terbatas ke whitelist `EMOJI` di `mayzfact/emoji.py`. Codepoint diturunin dari karakternya. Nggak ada tabel nama Indonesia ke emoji: kecocokan "emoji kardus" ↔ 📦 dicek Akmal waktu review naskah, bukan code (*call* lead). Ditampilin pakai Lottie Noto (`ensure_emoji`). Kalau Lottie-nya nggak ada di Noto, kasih peringatan dan fallback ke emoji statis (langkah hiasan, nggak bikin run gagal).
- **CTA-2:** beat terakhir video. Agent ngisi `cta_quiz.word` dan `cta_quiz.answer`. Kata itu harus diucapin minimal 2 kali di narasi sebelum CTA-2. `check-script` tetap read-only: dia ngitung sendiri (case-insensitive, per kata utuh, kalimat CTA-2 nggak dihitung) dan nolak kalau `answer` beda (*call* lead). Karena `check-script` wajib dijalanin tiap naskah diedit, angkanya nggak bisa basi. `answer` dipakai buat metadata/komen pin nanti.
- Beat CTA (semua format): `subject` kosong, `point` false, tanpa `keyword`, tetap wajib `queries`.
- Kata "like" di luar blok CTA tetap ditolak. Pengecualian: kata "like" di beat CTA-2 nggak dihitung sebagai ajakan.

Bentuk `cta_scene` baru (*usulan*, builder boleh ubah asal schema strict `extra="forbid"`):

```json
"cta_scene": {"format": "lucky", "theme": "honey"},
"cta_scene": {"format": "subscribe", "theme": "honey"},
"cta_scene": {"format": "emoji", "emoji": "📦"},
"cta_quiz": {"word": "kardus", "answer": 3}
```

`transform_word` dan `comment_text` nggak dipakai lagi di FaktaCuil.

Objek stiker (`lucky`/`subscribe`):
- Objeknya ikut konteks video. Kalau udah ada stiker yang mirip, pakai itu.
- Kalau belum ada, agent **wajib bikin stiker baru** sebelum render: komponen SVG di `remotion/src/FaktaCuilStickers.tsx` + daftar nama Indonesia di `THEME_NOUNS_ID` + literal `theme` di schema + `types.ts`. Skill nulis langkahnya. Jangan render dengan objek yang nggak cocok.
- Theme yang ada: `volcano`, `unicorn`, `honey`, `puppy`, `lion`, `shark`, `toilet`, `cat`, `zebra`.

Visual:
- Pill LIKE/LIKED, kursor, dan gerak stiker gaya `question` yang sekarang dipakai buat `lucky` dan `subscribe`. Gerak `reveal`/`escape`/`escalate` dihapus.
- Pill SUBSCRIBE di `subscribe` muncul pas kata "subscribe" diucapin (cue dari alignment). Gaya pill-nya ikut pill LIKE FaktaCuil (warna merah YouTube, teks SUBSCRIBE → SUBSCRIBED, klik kursor). *Builder yang nentuin detail motion-nya*, asal konsisten sama pill LIKE.
- `emoji`: pill LIKE muncul pas "tekan like", klik di kata "like", terus emoji Lottie muncul gede di posisi stiker dan tahan sampai video selesai.
- Scene CTA tengah berhenti pas shot jawaban pertama mulai (perilaku sekarang). Scene CTA akhir berhenti di akhir video.

### T8. Aturan struktur ikut posisi CTA

- CTA tengah (`lucky`/`subscribe`): aturan lama tetap. Minimal 1 beat salah kaprah antara hook dan CTA, minimal 2 beat jawaban setelah CTA (F4/F5).
- CTA akhir (`emoji`, CTA-2) atau tanpa CTA: nggak ada cek salah kaprah/jawaban. Yang tetap dicek: ≤10 kata per beat, jumlah kata total (F11), overlap 4-gram, `queries`.
- `lucky`/`subscribe` + CTA-2: cek tengah berlaku buat CTA-1. Beat CTA-2 nggak dihitung sebagai beat jawaban.

## Kompatibilitas run lama

- Naskah FaktaCuil lama dengan `cta_scene.format` `question`/`reveal`/`escape`/`escalate`: `check-script` dan pipeline nolak dengan pesan jelas (format lama udah dihapus), file dibiarin. Run yang udah di-upload nggak perlu dirender ulang.
- Naskah top3 nggak kena perubahan apa pun.
- `links.json` tanpa `speed` = speed 1. `plan.json` lama yang masih punya `ref_frames` per shot tetap kebaca brief (diabaikan).

## Dokumen yang ikut diupdate

- `.agents/skills/bikin-faktacuil/SKILL.md`: format CTA baru, CTA opsional, CTA-2, keyword English, cara bikin stiker baru, kartu frame referensi.
- `docs/DECISIONS.md`: keputusan baru (D-0xx) buat brief v2 dan CTA v2.
- `docs/HANDOFF.md`: status fase.

## Yang diserahkan ke builder

- Nama field/format persis, selama schema strict dan konsisten di Python + `types.ts`.
- Detail motion pill SUBSCRIBE dan emoji di format `emoji`.
- Batas jumlah frame referensi buat source panjang.
- Cara UI speed (dropdown atau pill).
- Pembagian task di dalam tiap branch.

## Tim

herdr-team, 2 tab/worktree paralel:
- `fase-brief-v2`: T1, T2, T3, T5.
- `fase-cta-v2`: T4, T6, T7, T8.

Tiap branch: claude (Opus/Sonnet, bukan Fable) jadi architect + reviewer, opencode model deepseek flash jadi implementer. Lead merge ke `master` setelah test lolos (`uv run pytest`, `uv run pytest -m render`, `npx tsc --noEmit -p .`).

Verifikasi akhir: render 1 short FaktaCuil per format CTA (tanpa CTA, `lucky`, `subscribe`, `emoji`, CTA-2) pakai `npx remotion still`/render frame pendek, dan buka brief di HP buat cek T1–T5.
