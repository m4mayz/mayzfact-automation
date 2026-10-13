# Fase 3B: BGM sesuai konteks + SFX

- **Tanggal:** 2026-10-13
- **Status:** design disetujui lewat chat. Akmal minta langsung dikerjain, review lewat Studio.
- **Referensi:** [spec 3A](2026-10-13-fase3a-countdown-captions-design.md), D-001.

## 1. Tujuan

Video dapat musik latar yang sesuai mood naskah, plus SFX di 4 momen:

- awal hook
- number card
- subject card
- pergantian shot

## 2. Aset

**BGM:** `assets/bgm/<mood>.mp3`, disiapin Akmal.

- Mood yang disaranin: mystery, suspense, dark, epic, space, tech, nature, playful, funny, inspiring, sad, energetic.
- Variasi per mood boleh pakai nomor, misalnya `mystery-2.mp3`.
- Ekstensi yang diterima: `.mp3 .m4a .wav .ogg`.

**SFX:**

- `assets/sfx/sfx.json` berisi mapping momen → nama file di `https://www.myinstants.com/media/sounds/`.
- Default-nya: `{"hook": "cinematicboom.mp3", "number": "vine-boom.mp3", "subject": "transition-whoosh.mp3", "cut": "fast-whoosh.mp3"}`.
- File di-download sekali ke `assets/sfx/` pakai `net.download` (ada retry).
- Kalau download gagal, momen itu dilewat dan ada log.

**Git:** file audio nggak di-commit (`.gitignore`). Yang di-commit cuma `sfx.json`.

## 3. Pemilihan BGM

- Modul baru `mayzfact/audio.py`.
- Kalau `runs/<id>/audio.json` (`{"bgm": "<nama file>"}`) udah ada dan file-nya masih ada di `assets/bgm/`, file itu yang dipakai. Akmal bisa ganti BGM dengan ngedit file ini.
- Kalau belum ada, Gemini milih 1 nama file dari daftar di `assets/bgm/`:
  - inputnya teks naskah
  - schema `BgmChoice{file}`, prompt `prompts/pick_bgm.md`
- Kalau cuma ada 1 file, langsung dipakai tanpa nanya Gemini.
- Kalau folder kosong, Gemini gagal, atau jawaban Gemini bukan salah satu file di folder, BGM jadi `null` plus log.
- File BGM dan SFX yang kepakai di-copy ke `runs/<id>/audio/bgm/` dan `runs/<id>/audio/sfx/`, karena public dir Remotion = folder run.

## 4. `timeline.json`

```json
"bgm": {"src": "audio/bgm/mystery.mp3", "volume": 0.12, "fadeOutFrames": 30},
"sfx": [{"src": "audio/sfx/vine-boom.mp3", "from": 292, "volume": 0.9}]
```

Penempatan SFX:

| Momen | Kapan | Volume |
|---|---|---|
| `hook` | frame 0 | 0.8 |
| `number` | tiap `numberFrom` | 0.9 |
| `subject` | tiap `cardFrom - 3` | 0.7 |
| `cut` | tiap awal shot ke-2 dst. dikurangi 3 frame | 0.35 |

Shot yang ketutup card nggak dapat SFX `cut`, begitu juga shot yang awalnya pas `numberFrom`.

Semua `from` dibatasi minimal 0. Kalau `audio` nggak ada, `bgm` = `null` dan `sfx` = `[]`.

## 5. Pipeline & Remotion

- `Deps.audio: Callable[[RunPaths, log], dict] | None`. `real_deps` nyiapin `prepare_audio` pakai client http + Gemini writer.
- Step `timeline` manggil `deps.audio` dulu, terus hasilnya dikirim ke `run_timeline(..., audio=...)`.
- **`SoundLayer` (Remotion):**
  - Tiap SFX jadi 1 `Sequence` berisi `Audio`.
  - BGM diputer loop sepanjang video, dengan volume yang turun ke 0 di `fadeOutFrames` terakhir.

## 6. Testing & DoD

- **Pytest** (network di-mock):
  - `ensure_sfx`: download, file yang udah ada nggak di-download ulang, kalau gagal momennya dilewat
  - `list_bgm`
  - `pick_bgm`: 1 file, pilihan valid, pilihan nggak valid, error
  - `prepare_audio`: `audio.json` dipakai ulang, file ke-copy
  - posisi SFX di timeline
  - pipeline manggil `deps.audio`
- `tsc` + test render marker, fixture-nya ditambah 1 SFX + BGM.
- **DoD:**
  1. Di Studio, run i2xag kedengeran BGM mystery + SFX di 4 momen.
  2. Semua test lolos.
  3. Render cuma setelah Akmal oke.
