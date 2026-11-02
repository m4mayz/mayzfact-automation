# CTA scene opt-in (D-048)

Desain bounded sudah disetujui di chat: revisi blok CTA yang ada setelah item dua, bukan segmen/footage baru. Naskah Top 3 baru memilih `cta_scene` secara eksplisit; metadata tidak ada berarti perilaku legacy persis tetap. Audio, wording, voice/provider, ASR dan speed tidak berubah.

## Kontrak

- `cta_scene`: theme `volcano` atau `word`, `transform_word` (kata ucapan pemicu), `comment_text` (teks kartu), dan `label` untuk theme word. Nested fields divalidasi ketat; source mode tidak menerima opt-in.
- Plan mempertahankan seluruh shot/durasi CTA dari detektor bersama `cta_beat_indices`, menandainya otomatis dalam satu kelompok. Brief menampilkan AUTO CTA tanpa kontrol link/upload/trim/SFX; preflight/manual completeness tidak memintanya.
- Fetch meminjam hanya video lokal non-CTA yang sudah tampil sebelum CTA. Pilihan pseudo-random seeded deterministik; offset berlanjut per sumber, loop jika pendek. Metadata reused eksplisit, tanpa download/ML/penilaian relevansi dekorasi. Tidak pernah mengambil footage item satu. Jika tidak ada video sebelumnya, background warna bergerak frame-based menggantikan footage, tanpa meminta link baru.
- Scene mengisi seluruh rentang CTA sampai sebelum kartu satu. Like besar sejak transisi, transformasi pada kata tema, subscribe pada ajakan, comment pada kata comment. Cues hanya timestamp kata alignment asli; jika kata hilang, batas beat struktural boleh dipakai tanpa klaim timestamp ucapan. Stage tidak tumpang tindih. Caption di bawah, tanpa emoji/panah/overlay CTA legacy ganda.
- Volcano SVG eruption dan semua animasi berbasis frame Remotion. Theme word menyediakan transformasi kartu teks untuk topik lain, tidak hardcode volcano untuk semua video. Tidak menambah pilihan SFX/BGM.

## Verifikasi

TDD per slice schema/plan/manual/brief/fetch/timing/render markup, regression source + metadata absent. Full offline pytest, TypeScript, Ruff/diff. Fixture lokal nyata di `out/cta-scene-fixture`, render 1080x1920 + ffprobe + contact sheet berlabel untuk review visual. Tidak menyentuh run produksi/server/settings atau membuat voice.
