# Spec — Revisi brief: audio naskah, download duluan, frame referensi wajib

- **Tanggal:** 2026-10-15
- **Status:** diminta Akmal di chat, nunggu review spec ini.
- **Konteks:** 3 revisi halaman brief + fetch. Poin "keyword harus sesuai shot" masuk spec naskah (`2026-10-15-agent-script-design.md`, bagian 6), karena keyword-nya ditulis bareng naskah.

## 1. Tombol waktu di tiap shot muter suara naskah

**Sekarang:** tombol `12.3s – 14.1s` di tiap shot nge-seek video source. Salah, soalnya `start_s`/`end_s` itu waktu di `voice.mp3` (suara kita), bukan di source.

**Jadi:**
- Halaman nyediain satu `<audio id="voice" src="/files/voice.mp3" preload="metadata">` tersembunyi.
- Klik tombol: `voice.currentTime = start_s`, play, berhenti otomatis di `end_s` (lewat event `timeupdate`). Klik lagi pas lagi main = stop.
- Tombol yang lagi main dikasih state visual (ikon jadi stop), biar jelas yang bunyi yang mana.
- Video source tetap ada di samping, dengan kontrol bawaan, nggak di-seek dari tombol shot lagi.
- Server `/files/` udah dukung Range, jadi seek audio langsung jalan.

## 2. Download klip langsung pas link disimpan

**Sekarang:** klik Simpan cuma nulis `links.json`. Download baru jalan pas agent jalanin `run --from fetch`, jadi Akmal nunggu 2 kali.

**Jadi:**
- Server brief punya worker download (1 thread, antrean). Tiap `POST /api/links` sukses, semua URL yang belum ada di cache dimasukin antrean. Upload file (`manual/`) nggak perlu di-download.
- Download pakai `Obtainer.obtain` yang sama kayak fetch, jadi hasilnya masuk `cache/manual/` dengan `cache_key(url)` yang sama. Pas `run --from fetch` jalan, semua link udah kena cache dan fetch tinggal motong + nilai klip.
- Status per shot di halaman: `antre` → `download…` → `siap` / `gagal: <pesan>`. Disimpan di `runs/<id>/prefetch.json` (`{url: {"state", "message", "files"}}`), di-poll bareng `/api/progress` yang udah ada.
- Link yang gagal download ditandain merah di shot-nya, jadi Akmal bisa ganti link sebelum nyuruh agent lanjut.
- Ganti link di shot yang sama = URL lama dibiarin di cache (nggak dihapus), URL baru masuk antrean.
- Worker berhenti rapi pas server di-stop (Ctrl+C). Download yang lagi jalan diselesaiin dulu kalau < 30 detik, kalau nggak, dibatalin dan file `.part`-nya dihapus.
- `run_fetch` nggak berubah: dia tetap manggil `obtain`, yang sekarang langsung kena cache.

Batasan: download cuma buat URL. Kalau Obtainer butuh captcha/login, state-nya `gagal` dengan pesan yang sama kayak fetch, dan Akmal yang nanganin.

## 3. Semua shot wajib punya frame referensi

**Sekarang:** shot hook dapat frame dari segmen hook. Shot lain dapat frame kelompok cuma kalau subjeknya ketemu di transcript source (`subject_ranges`). Shot CTA / intro / subjek yang nggak ketemu: kosong.

**Jadi:**
- Step `plan` ngisi `ref_frames` buat **tiap shot**, bukan per kelompok:
  1. Shot hook: 3 frame segmen hook (kayak sekarang).
  2. Shot lain: 3 frame dari rentang waktu subjeknya di source (`subject_ranges`), kayak sekarang tapi ditaruh di tiap shot.
  3. Shot yang subjeknya nggak ketemu di transcript (CTA, intro, beat tanpa subjek): 3 frame dari rentang waktu **proporsional**. Posisi beat di naskah kita (`start_s / durasi suara`) dipetain ke durasi source. Jadi beat CTA di awal dapat frame awal source, dst.
- Kalau source lebih pendek dari posisi yang dihitung, pakai frame terakhir source.
- `mayzfact brief <id>` nolak jalan (exit 1) kalau ada shot di `shots_plan.json` yang `ref_frames`-nya kosong atau file-nya nggak ada: "Shot X belum punya frame referensi. Jalanin: `mayzfact run <id> --from plan`".
- `group.ref_frames` dihapus dari plan dan halaman; halaman nampilin frame per shot (sekarang udah ada tempatnya di tiap shot-box).

## 4. Error

| Kasus | Perilaku |
| --- | --- |
| `voice.mp3` nggak ada pas brief dibuka | Tombol waktu disabled + tooltip "suara belum ada". (Normal: brief jalan setelah tts, jadi jarang.) |
| Download gagal (link mati, captcha, timeout) | State `gagal` + pesan di shot. Autosave nggak ngulang yang gagal. Klik Simpan (atau start `brief` lagi) = coba lagi. |
| Server brief ditutup pas antrean masih ada | Sisanya di-download pas `run --from fetch` (jalur lama tetap jalan). |
| `ffmpeg` gagal ambil frame | Shot itu `ref_frames` kosong, `plan` log error-nya, dan `brief` nolak jalan sampai dibenerin. |

## 5. Test

- Page: tombol shot nunjuk ke `voice.mp3` + `start_s`/`end_s` (ada di HTML), nggak ada lagi `seekSourceVideo`.
- Server: `POST /api/links` masukin URL ke antrean, worker manggil `obtain` (fake) sekali per URL, `prefetch.json` berubah `antre → siap`; URL gagal → `gagal` + pesan; URL yang sama disimpan 2 kali cuma di-download sekali.
- Plan: shot CTA dapat 3 frame proporsional; shot subjek dapat frame rentang subjek; semua shot `ref_frames` terisi (fixture video pendek).
- CLI: `brief` exit 1 kalau ada shot tanpa frame, pesannya nyebut shot dan `--from plan`.

## 6. Di luar scope

- Potong/nilai klip di brief (tetap di `fetch`).
- Edit naskah dari brief.
