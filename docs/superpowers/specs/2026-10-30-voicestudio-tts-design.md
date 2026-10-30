# Opsi TTS VoiceStudio

Desain integrasi di chat disetujui Akmal: tambahkan provider VoiceStudio, default repo tetap ElevenLabs, aktifkan VoiceStudio + profil `Gen` hanya di PC ini. Perubahan terbatas pada seam TTSProvider yang sudah ada; output downstream tetap sama.

## Kontrak
- `Settings().tts_provider` tetap `elevenlabs`. Override nonrahasia per-PC ada di `settings.local.json` (gitignored), bukan `.env`. Nilai lokal divalidasi dan hanya setting TTS yang didukung boleh diisi.
- VoiceStudio di `http://127.0.0.1:3900`, engine `cosyvoice`, profil `Gen` (`49a69f8b` saat discovery). Resolusi profil harus unik dan gagal jika tidak ditemukan; jangan substitusi suara default.
- TTS dipanggil dengan engine/voice/language/output eksplisit lewat API lokal. Tidak mengubah engine GUI, tidak memasang paket ke environment mayzfact, tidak melakukan fallback ke layanan berbayar.
- Audio ditranskrip dengan word timestamps VoiceStudio lalu dipetakan ke teks asli: pertahankan seluruh karakter/punctuation naskah. Hanya perbedaan case/punctuation dan representasi angka ekuivalen 0–10 (`five`/`5`) yang boleh dinormalisasi. Kata hilang/berubah atau timing tidak valid harus menghentikan step, bukan menghasilkan timestamp rekaan.
- Simpan audio hasil generasi ke cache sebelum alignment. Gagal alignment tidak boleh membuang audio atau memaksa generate ulang; cache dikunci oleh provider/engine/voice/teks dan opsi sintesis.
- Keluaran tetap `voice.mp3` + `tts.json` dengan alignment kompatibel `beat_timings` dan `word_timings`. Audio run lama tidak disentuh. Log menyebut provider yang benar.
- Validasi key ElevenLabs hanya saat provider ElevenLabs digunakan.

## Verifikasi
TDD unit: default + override lokal, provider routing, tanpa API key ElevenLabs untuk VoiceStudio, resolusi Gen, HTTP errors tanpa fallback, cache + retry alignment, exact script mapping dan timing invalid. Uji nyata Gen lewat adapter sampai `run_tts`, ffprobe, beat/word timings. Jalankan regression tests tanpa render/ML sesuai konfigurasi repo. Tidak membuat atau mengupload video baru.
