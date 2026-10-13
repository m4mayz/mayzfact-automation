# Fase 3C-1: panah + lingkaran yang ngikutin subjek

- **Tanggal:** 2026-10-13
- **Status:** design disetujui lewat chat. Akmal minta langsung dikerjain, review lewat Studio.
- **Referensi:** spec [3A](2026-10-13-fase3a-countdown-captions-design.md) dan [3B](2026-10-13-fase3b-audio-design.md).
- **Model:** OWLv2 `google/owlv2-base-patch16-ensemble`, revisi `cfd3195ba4ea9592eec887ded089f4c08eff231d`. Ukurannya 621 MB, disimpen di `models/`. Kecepatan di CPU Akmal ±3,8 detik per frame.

## 1. Tujuan

Kayak di source `i2xag`: panah merah/kuning nunjuk subjek dan ngikutin gerakannya, dan sesekali lingkaran ngelilingin subjek.

## 2. Deteksi (`mayzfact/detect.py`)

- `Owlv2Detector(cache_dir=MODELS_DIR)` di-load lazy.
- `best_box(image_path, query) -> (score, (x0, y0, x1, y1)) | None` ngebalikin kotak dengan skor tertinggi, dalam koordinat piksel gambar.

## 3. Overlay per shot (`mayzfact/overlay.py`)

**Query:**
- Subjek beat dari `beat_subjects`.
- Kalau subjeknya kosong (biasanya shot hook): keyword `en` pertama di `shots_plan.json` (mode manual) atau `queries[0]` beat-nya (mode auto).
- Kalau semuanya kosong, shot itu dilewat.

**Titik deteksi:**
- Video: detik 0,5, 1,5, 2,5, … selama masih `< durasi klip`. Kalau klipnya lebih pendek dari itu, cukup 1 titik di tengah.
- Foto: 1 titik di detik 0.
- Frame diambil pakai `extract_frame`.

**Filter:**
- Skor `< 0.12` dianggap titik hilang.
- Kalau titik valid kurang dari 50%, shot itu nggak dapat overlay.
- Titik yang hilang diisi pakai titik valid terdekat.

**Konversi ke layar 1080×1920:**
- `full`: `s = max(1080/w, 1920/h)`, dengan offset `(1080 - w·s)/2` dan `(1920 - h·s)/2`.
- `blur`: kotak foreground setinggi `fgHeight` di tengah layar. Di dalamnya `s = max(1080/w, fgH/h)`, offset dihitung relatif ke kotak itu.

**Cache:**
- Disimpen di `runs/<id>/overlays.json` dengan format `{"<file>": {"key": "<size>-<mtime>-<query>", "points": [{"t", "x", "y", "w", "h"}] | null}}`.
- Kalau `key` masih sama, deteksi nggak diulang.

**Shot yang dilewat:** shot yang ketutup card countdown (aturannya sama kayak di ShortVideo).

## 4. Timeline

- `build_timeline(..., overlays=None)` → `overlays: [{type, color, from, durationInFrames, keyframes: [{frame, x, y, w, h}]}]`.
  - `frame` relatif ke awal shot.
  - `from` dan `durationInFrames` sama kayak shot-nya.
- **Jenis:** shot yang lolos ke-1, 2, 3, 4 dapat `arrow`, shot ke-5 dapat `circle`, dan seterusnya.
- **Warna:** `#ff2a2a` dan `#ffd400` gantian per overlay.
- Kalau `overlays` nggak ada, hasilnya `[]`.

## 5. Remotion (`Overlays.tsx`)

- Posisi tiap frame = interpolasi linear dari keyframes.

**Arrow:**
- SVG panah tebal dengan isi warna dan outline hitam 8px, panjang ±230px.
- Ujungnya di `(cx, top + 0.08h)`.
- Sudutnya berubah dari -35° (datang dari kanan atas) ke 0° (tegak dari atas) sepanjang shot.
- Kalau `top < 260`, panah datang dari kanan dengan sudut -90°, ujungnya di `(right - 0.08w, cy)`.
- Masuk pakai spring scale 0 → 1 (±5 frame).

**Circle:**
- Elips dengan pusat di tengah kotak, radius `0.55w × 0.55h`, stroke 14px warna + outline hitam.
- Digambar pakai `stroke-dashoffset` dalam 8 frame.

**Urutan layer:** shots → card → overlays → captions.

## 6. Pipeline

- `Deps.overlay: Callable[[RunPaths, log], dict] | None` dipanggil di step timeline.
- Kalau error, cuma muncul log dan timeline tetap jadi tanpa overlay (sama kayak audio).

## 7. Testing & DoD

- **Pytest** (detektor palsu):
  - konversi koordinat `full` / `blur`
  - pengisian titik + aturan 50%
  - query per shot
  - cache
  - jenis + warna
  - shot yang ketutup card
  - wiring pipeline
  - test model asli pakai marker `clip`
- `tsc` + test render.
- **DoD:** di Studio, run i2xag nampilin panah/lingkaran yang nempel di subjek. Render cuma setelah Akmal oke.
