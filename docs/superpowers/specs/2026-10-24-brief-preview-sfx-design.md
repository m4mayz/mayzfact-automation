# Brief: preview klip + SFX kustom per shot

- **Tanggal:** 2026-10-24
- **Branch:** `fase-brief-sfx`
- **Authority:** Akmal (chat 2026-10-24). Akmal minta langsung dikerjain tanpa sesi tanya, jadi keputusan di bawah yang ditandai *(agent)* itu pilihan agent.

## Kenapa

Sebelum fetch jalan, Akmal nggak tau bagian mana dari video yang bakal jadi klip. Dia juga belum bisa nambah SFX sendiri di momen tertentu klip. Selama ini SFX cuma dari aturan otomatis di timeline.

## Yang dibikin

### 1. Preview klip per shot

- Tiap shot yang link-nya udah ke-download (prefetch `siap`) atau file-nya udah di-upload dapat tombol **Preview**. Video baru dimuat pas tombolnya dibuka, biar halaman nggak berat.
- Preview muter **bagian yang bakal dipakai**, diulang terus: `[mulai, mulai + durasi shot]`. `mulai`-nya ditentuin sesuai urutan ini (aturannya sama kayak fetch):
  1. kolom **Mulai** diisi: pakai itu;
  2. link-nya sama kayak shot sebelumnya: lanjut dari ujung bagian shot sebelumnya;
  3. fetch udah pernah jalan dan link-nya masih sama: pakai `source_s` di `clips.json` (termasuk hook yang 1 video nyambung);
  4. selain itu: **otomatis**, baru dipilih pas fetch (SigLIP). Preview muter dari detik 0 dengan label "otomatis".
- Tombol **Pakai detik ini** ngisi kolom Mulai dari posisi preview sekarang. Bagian yang dipakai dipotong biar nggak lewat ujung video, sama kayak fetch.
- Kalau isinya foto: yang tampil fotonya, tanpa bagian waktu.
- File hasil download disajikan lewat endpoint baru, cuma file yang tercatat di `prefetch.json` buat URL shot itu (folder `cache/manual/`), atau file upload di dalam folder run.

### 2. SFX kustom per shot

- Baris pill **SFX** di tiap shot: "Tanpa" + semua file audio di `assets/sfx/` *(agent: diambil dari library SFX yang udah dipilih Akmal; file baru yang ditaruh di situ otomatis muncul)*.
- Bentuknya radio: 1 shot maksimal 1 SFX kustom. Pill "Tanpa" buat ngosongin.
- Klik pill langsung muter SFX-nya.
- Pas SFX dipilih, muncul kolom **Detik**: kapan SFX diputer, dihitung dari awal shot muncul di video (0 sampai durasi shot). Tombol **Dari preview** ngisi detik dari posisi preview.
- Pas preview jalan, SFX yang dipilih ikut bunyi di detiknya, jadi timing-nya bisa langsung dicek.
- Disimpan di `links.json`, di entry shot: `"sfx": {"file": "uy.mp3", "at_s": 0.8}`. Server nolak nama file yang nggak ada di library, detik negatif, atau detik yang lewat durasi shot.

### 3. Masuk ke video

- Step timeline baca SFX kustom dari `links.json` + `shots_plan.json`: waktunya = `start_s` shot + `at_s`. Nggak perlu fetch ulang; cukup `--from timeline`.
- File SFX-nya di-copy ke `runs/<id>/audio/sfx/` kayak SFX lain. Hening di depan file dihitung, jadi bunyinya kedengeran pas di detik yang dipilih.
- Volume 0,5 *(agent)*. SFX kustom nambah di atas SFX otomatis, nggak gantiin.
- Hiasan: kalau gagal, timeline tetap jadi tanpa SFX kustom, terus nulis log.
- Fetch nganggep 2 entry tetap "link sama" walaupun SFX-nya beda. Jadi hook 1 video nyambung dan klip lanjutan nggak putus gara-gara SFX.

## Bukan bagian dari ini

- Upload SFX baru dari brief. SFX baru tetap lewat link myinstants ke agent (aturan AGENTS.md).
- Lebih dari 1 SFX kustom per shot.
- Pilihan bagian otomatis (SigLIP) dijalanin di brief. Butuh model ±1 GB di server brief.
- Ngatur volume SFX kustom per shot.

## Test

- `links.py`: validasi SFX, waktu absolut SFX, aturan `mulai` preview (4 aturan di atas).
- Fetch: hook nyambung + klip lanjutan tetap jalan walaupun entry-nya punya `sfx`.
- `audio.py` + timeline: SFX kustom ke-copy, frame-nya `start_s + at_s` dikurangi hening depan, volume 0,5.
- Server: endpoint SFX + media (termasuk nolak path di luar folder), simpan SFX, upload ulang nggak ngilangin SFX.
- UI: dicek manual di browser (render HTML-nya dites dari Python).
