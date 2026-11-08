# Top 3, CTA sebelum nomor satu, target final 30–40 detik

> Riwayat D-045. Bagian style/batas CTA dan anggaran total disupersede oleh [revisi bounded D-046](2026-11-02-top3-playful-cta-design.md): CTA 1–4 beat dan delta kata CTA aktual di atas 10; aturan non-CTA/legacy tetap. Gunakan skill repo terbaru untuk authoring.

## Status dan tujuan

Desain percakapan disetujui Akmal; dokumen ini menunggu review tertulis sebelum plan implementasi.
Branch: `fase-top3-cta`, berangkat dari baseline aktif `6cb523f` tanpa menghapus fitur lokal yang sudah ada.

Ubah pola video baru pada branch ini menjadi Top 3 agar hasil final ditargetkan 30–40 detik. Ini perubahan terbatas pada alur naskah, validasi, pemetaan hook, dan panduan operator; tidak mengganti sistem render atau model suara.

## Keputusan yang sudah disetujui

- Dari source Top 5, ambil peringkat asli 3, 2, 1. Buang seluruh pembahasan item 5 dan 4, bukan mengurutkan ulang lima item atau memilih tiga sesuka agent.
- Urutan: hook → Number three + penjelasan → Number two + penjelasan → CTA → Number one + penjelasan → selesai.
- CTA tepat sebelum pengumuman Number one, bukan di awal, sesudah nomor satu, atau di tengah penjelasan item.
- CTA bergaya tantangan/pilih kubu yang ringan dan berubah mengikuti tema. Gaya acuan:
  - `Subscribe if you'd touch it, like if you'd watch,`
  - `or comment 'nope' if you'd run.`
- Gimmick agama/ancaman, janji palsu, hadiah palsu, atau menyembunyikan nomor satu sampai orang subscribe tidak digunakan.
- Target 30–40 detik berlaku untuk `final.mp4` setelah speed-up yang sudah ada, bukan voice mentah saja.

## Batas perubahan

Tidak mengganti provider ElevenLabs, voice, model, stability, BGM, SFX, caption styling, panah, jadwal, atau alur review. Gaya sampel suara sebelumnya tidak menjadi default. Tidak memotong, membuat ulang, atau meng-upload ulang run produksi lama. Tidak memakai kredit TTS sungguhan untuk test implementasi tanpa permintaan baru. Branch tidak di-push/merge tanpa izin.

Naskah tetap ditulis agent dan direview Akmal sebelum TTS; tidak menambah LLM eksternal atau pemotong source otomatis. Fakta, hedges, dan detail item terpilih tetap bersumber dari source. Detail item 5/4 sengaja dibuang sesuai keputusan, bukan dipindahkan ke item lain. Source yang hanya punya 3, 2, 1 boleh dipakai; source tanpa tiga peringkat yang dapat dikenali ditolak dengan pesan jelas, bukan diisi fakta baru.

## Mode per naskah dan kompatibilitas

Tambahkan `narration_mode` ke schema Script, nilai `source` atau `top3`, default `source` jika field tidak ada. Ini mempertahankan kontrak run lama dan test lama; panduan operator branch mewajibkan `narration_mode: top3` untuk semua naskah baru. Tidak melakukan migrasi massal file runs.

Mode `source` tetap memakai perhitungan lama berbasis durasi source dan aturan CTA sebelumnya. Mode `top3` memakai aturan di dokumen ini, terlepas panjang source. Field mode dipertahankan saat normalisasi dan serialisasi; nilai mode tidak dikenal ditolak, bukan diam-diam fallback.

## Naskah dan struktur yang divalidasi

Pada mode `top3`:

1. Countdown tepat tiga buah dengan urutan 3, 2, 1; subjek masing-masing cocok dengan peringkat asli source setelah normalisasi spasi/kapitalisasi. Angka 5/4, duplikat, subjek tertukar, atau peringkat hilang gagal sebelum TTS.
2. Teks pengumuman tetap `Number N, [subject].`. Hook menyebut tiga item, bukan lima; teaser nomor satu tidak membuka kalimat dengan pola yang terbaca sebagai card countdown.
3. Setiap item memiliki minimal dua beat penjelasan non-CTA. CTA tidak boleh dipakai untuk memenuhi kuota penjelasan item dua.
4. CTA adalah satu blok berurutan, satu atau dua beat, langsung sebelum beat Number one. Blok memuat pemicu like, subscribe, dan comment, walaupun source tidak memiliki ketiganya. Tidak ada CTA di hook, penjelasan item lain, atau sesudah Number one.
5. Tiap beat maksimal 10 kata, foto 15–45%, beat pertama video, keyword/subject/emoji/panah dan batas overlap 4-gram 15% tetap mengikuti aturan yang ada.

Gaya CTA dibuat oleh agent dalam tahap kreatif, bukan dihasilkan validator. Validator memeriksa kontrak struktur dan pemicu, sedangkan review naskah memastikan pilihan tantangannya masuk akal untuk tema dan tidak membuat klaim palsu.

## Pemicu CTA yang perlu dibenahi

Parser sekarang tidak mengenali `like if you'd watch` sebagai ajakan like. Perlu memperluas helper CTA bersama, bukan hanya check-script, sehingga timeline dan validator membaca gaya acuan secara sama.

Dukung `Like if ...` pada awal kalimat/klausa, termasuk sesudah koma seperti contoh disetujui. Pertahankan perilaku lama untuk `like and subscribe`, `hit like`, dan sejenisnya. Jangan menandai `if you like these animals` atau `animals like this` sebagai ajakan like. Comment dan subscribe tetap memakai helper yang sama dengan timeline. Tambahkan regresi untuk trigger positif dan negatif, termasuk posisi event di timeline sebelum Number one.

## Anggaran durasi dan biaya

Pada speed produksi 1.1x, gunakan target 80 kata total, rentang validasi 76–84 kata, termasuk hook, tiga pengumuman, semua penjelasan, dan CTA. Rentang ini bukan batas baru per beat. Perhitungan dari kisaran ElevenLabs terukur 1.92–2.28 kata/detik menunjukkan 80 kata kira-kira 31.9–37.9 detik setelah 1.1x; ini estimasi, bukan jaminan.

Untuk speed berbeda, skala target/rentang kata proporsional terhadap `video_speed / 1.1` dengan pembulatan deterministik (target round; batas bawah ceil; batas atas floor). Validasi speed positif dan finite. Jalur source lama tidak berubah. CLI dan pemeriksaan pra-TTS menggunakan sumber aturan anggaran yang sama, sehingga target yang dicetak cocok dengan yang divalidasi.

Sesudah TTS, laporkan estimasi final dari durasi suara nyata dibagi speed. Jika di luar 30–40 detik, tampilkan peringatan jelas; simpan audio berbayar, jangan regenerate, hapus, time-stretch tambahan, atau mengubah speed otomatis. Ini target editorial, bukan alasan membuang audio yang sudah dibayar. Operator mengabarkan ketidaksesuaian dan meminta persetujuan sebelum perubahan berbiaya.

Sesudah render yang memang diminta user, verifikasi durasi MP4 memakai ffprobe. Jangan menyebut target tercapai hanya karena kata lolos. Test implementasi memakai fixture lokal dan dependency palsu yang jelas sebagai test, bukan mengaku sebagai hasil API produksi.

## Hook, brief, dan timeline

Pemetaan hook saat ini hanya melihat batas 10 detik; dengan naskah lebih singkat, Number three bisa masuk jendela itu dan keliru memakai keyword/frame hook.

Untuk mode `top3`, hanya shot sebelum countdown pertama yang boleh mendapat `hook_segment`; pengumuman Number three dan semua item sesudahnya memakai keyword serta referensi subjeknya sendiri. Tetap gunakan timing nyata/alignment yang sudah ada, bukan timestamp karangan. Hook source tetap dapat dibaca dari segmen yang tersedia; tidak perlu mengubah source.json atau sumber video.

CTA yang dipindahkan memakai keyword visual CTA sendiri, subject kosong, dan tidak mewarisi subjek item dua. Jangan menandai CTA sebagai hook hanya karena waktunya cocok. Card 3/2/1 dan animasi CTA mengikuti naskah/timing, tidak memerlukan perubahan komponen React. Pemetaan mode source lama tetap kompatibel.

## Unit perubahan

- `mayzfact/models.py`: mode naskah dengan default legacy.
- `mayzfact/steps/script.py` dan helper kecil bila perlu: anggaran bersama, aturan Top 3, blok CTA, pencocokan peringkat source.
- `mayzfact/cta.py`: shared trigger untuk CTA kondisional.
- `mayzfact/cli.py`, `mayzfact/pipeline.py`: gunakan validasi/anggaran sama dan laporkan estimasi durasi nyata tanpa menyentuh audio berbayar.
- `mayzfact/steps/plan.py`: pembatasan mapping hook sebelum countdown pertama, khusus Top 3.
- Test schema/script/CTA/plan/timeline/CLI/pipeline; ikuti pola fixture yang sudah ada.
- `.agents/skills/bikin-short/SKILL.md`, `AGENTS.md` bila perlu, `docs/DECISIONS.md`, `docs/HANDOFF.md`: aturan branch dan handoff. Jangan mengubah `flow.svg` atau `sources/`.
- Helper operator di luar repo, terutama `mayzfact_audit.py`, masih mengasumsikan seluruh countdown source; setelah implementasi, sesuaikan dengan mode per-script dan fungsi validator repo agar tidak menolak Top 3 yang benar atau melaporkan target lama. Perubahan ini tetap terpisah dan tidak di-commit seolah file repo.

## Kriteria selesai

- RED nyata terlebih dahulu untuk aturan baru; kemudian GREEN untuk test terarah dan regresi suite tanpa API berbayar.
- Fixture Top 5 → naskah Top 3 dengan item asli 3/2/1 lolos; struktur salah, subjek salah, CTA salah tempat, CTA tidak lengkap, dan kata di luar anggaran ditolak sebelum TTS.
- CTA gaya acuan menyalakan tiga jenis event; event CTA berakhir sebelum countdown satu dan CTA tidak dihitung sebagai penjelasan.
- Plan Top 3 tidak memberi hook_segment pada countdown pertama/isi/CTA; frame dan keyword item tidak berasal dari item yang sengaja dibuang.
- Jalankan check-script/CLI pada fixture lokal, test suite relevan/full, lint file berubah, dan cek diff. Test tidak menulis ke runs produksi atau mengganti setting mesin.
- Run legacy tanpa narration_mode tetap terbaca dan mengikuti aturan lama. Audio, metadata upload, dan video produksi tidak dimodifikasi.
- Dokumentasi menyatakan jelas pola baru, target final, gaya CTA yang bervariasi, dan titik review yang masih berlaku.
- Commit lokal beridentitas m4mayz, satu baris Conventional Commit tanpa trailer; tidak push/merge branch fitur tanpa izin.

## Tahap berikutnya

Setelah Akmal menyetujui spec tertulis ini, buat plan implementasi terarah dengan TDD dan minta review plan serta pilihan metode eksekusi. Tidak mulai mengubah kode produk sebelum gate itu selesai.
