# Plan — opsi VoiceStudio (desain chat disetujui)

1. TDD default ElevenLabs dan `settings.local.json` tervalidasi; tambahkan contoh tracked dan ignore file PC.
2. TDD factory provider dan validasi key conditional. Tidak ada fallback berbayar.
3. TDD adapter HTTP VoiceStudio: resolve profil, request MP3 eksplisit, cache audio atomik, minta word timestamps, mapping exact script dan reject mismatch/timing invalid.
4. Netralisasi log TTS dan identitas metadata/resume tanpa mengubah kontrak downstream atau audio lama.
5. Aktifkan override PC untuk Gen. Uji nyata ke folder cache terpisah (bukan run produksi), ffprobe + `beat_timings`/`word_timings`; cek cache retry.
6. Review diff, regression tests, lint, catat D-043 dan HANDOFF, commit branch `fase-voicestudio-tts`. Tidak push tanpa izin karena bukan alur upload.
