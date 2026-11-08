# Gen expressiveness + native lossless — scope yang disetujui

Akmal menyetujui lima poin hasil pembacaan dokumentasi: aktifkan delivery direction Gen; pertahankan reference Gen; gunakan WAV lossless sebelum render; jangan menambahkan knob OmniVoice yang diabaikan CosyVoice; uji A/B sekitar 15 detik, 1.0x. Default repo tetap ElevenLabs. Tidak mengubah model, reference/profile GUI, naskah, voice/video run lama; tidak render ulang video penuh atau upload.

## Perubahan terbatas
1. `Settings` menambah `voicestudio_instruct` (default kosong) dan `voicestudio_audio_format` (default mp3). Override lokal PC memilih WAV + instruksi narator fakta antusias namun natural, penekanan dan jeda terukur, tidak berteriak. Format hanya mp3/wav; instruksi kosong valid untuk kontrol A/B.
2. Adapter mengirim format dan instruct secara eksplisit, cache identity mengandung keduanya. Profil Gen tetap di-resolve unik. WAV native dipakai untuk alignment; tidak ada fallback berbayar atau klaim high/ultra dari parameter yang tidak didukung.
3. `run_tts` menyimpan byte WAV native ke voice.wav dan membuat voice.mp3 hanya untuk brief/marker kompatibilitas. Native incoming aman untuk retry jika konversi gagal; tidak boleh tertukar dengan pending mp3. Metadata audio_file menentukan file master.
4. Timeline render membaca WAV ketika dipilih metadata dan menolak file native yang hilang; metadata lama tetap MP3. Tidak menaikkan sample rate atau memalsukan phoneme timings.
5. A/B naskah identik dari short terakhir, Gen/seed/language sama, keduanya WAV dan speed 1.0; bedanya hanya instruct kosong vs arahan ekspresif. Sampel dan verifikasi di cache/quality-ab, bukan run produksi.

## Plan + acceptance
TDD settings/HTTP/cache identity; TDD native preservation/compatibility/retry/timeline; aktifkan override lokal; generate dua sampel nyata + ffprobe + byte/cache checks; regression dan lint, independent review; update decision/handoff dan commit tanpa push. Kirim dua WAV ke Telegram untuk penilaian subjektif intonasi. Keberhasilan API tidak dianggap bukti bahwa ekspresinya sudah lebih bagus.
