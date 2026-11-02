# ElevenLabs calm delivery — D-047

## Scope yang disetujui

Akmal memilih sample 2 (`2-kalem-natural`): prefix `[calm] `, stability `0.5`, voice `TX3LPaxmHKxFdv7VOQHJ`, model `eleven_v3`. Berlaku untuk revoice penuh video saat ini dan default short berikutnya. Implementasi ini hanya kode/test/dokumen; parent mengurus setting lokal, backup, revoice, plan/brief dan commit. Tidak memanggil TTS, mengubah run/audio historis, naskah, speed atau wording.

## Kontrak

- `Settings.elevenlabs_delivery_tag` default `calm`; string kosong mematikan prefix. Default stability menjadi `0.5`; voice/model tetap. Override lokal tervalidasi, bukan `.env`.
- Provider menambahkan satu prefix hanya pada request. `script.json`, hash teks, hitungan karakter, beat dan caption tetap berdasarkan teks asli.
- Provider mengembalikan audio + alignment mentah; `run_tts` menyimpan keduanya sebelum memanggil normalisasi alignment. Kegagalan mapping tidak kehilangan audio berbayar dan retry memakai pending yang sama.
- Alignment boleh memuat prefix persis `[tag] ` (sampel nyata), `[tag]` tanpa spasi, atau langsung teks asli. Hanya jika suffix identik dengan teks asli dan panjang ketiga array cocok, potong jumlah entri prefix yang sama dari characters/start/end. Jangan menggeser, menginterpolasi atau menebak timestamp.
- Mismatch pada delivery bertag gagal setelah penyimpanan pending; jangan menghasilkan caption tag atau menyamarkan kata berbeda. Simpan raw alignment dan delivery tag pada metadata sukses untuk provenance. Provider tanpa tag mempertahankan perilaku lama.
- Cache identity menambah `delivery_tag` hanya saat nonkosong. Pending tanpa tag/identity legacy tidak boleh digunakan untuk request bertag; pending berbeda tidak ditimpa. Voice yang sudah selesai tetap dilindungi.

## Verifikasi

Strict RED→GREEN per perilaku: default/config, prefix request, included/omitted/no-space alignment, mismatch/array lengths, unchanged timestamps, identity/pending isolation, failure-after-save/resume, wiring produksi dan timeline tanpa tag. Focused + full offline suite dan Ruff F/I; tidak menjalankan render/ML/API asli. Parent menilai diff sebelum commit dan mengukur audio nyata saat revoice terpisah.
