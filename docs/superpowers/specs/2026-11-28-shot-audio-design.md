# Audio klip per shot + mode SFX transisi

Tanggal: 2026-11-28. Status: disetujui Akmal ("oke lanjut").

## Tujuan

Akmal mau beberapa shot ngeluarin suara asli klipnya. Volumenya bisa diatur relatif ke BGM, dan bunyi pergantian shot bisa disederhanain per video.

## Keputusan

### Brief, per shot video
- Checkbox "Mute", default dicentang.
- Kalau di-uncheck, muncul:
  - input "Volume" 0–200 % (default 100, step 5);
  - label read-only "BGM: X%", yaitu volume BGM video ini pakai rumus timeline (`faktacuil_bgm_volume`, lagu pilihan + durasi suara). Kalau BGM belum dipilih atau bukan FaktaCuil, pakai volume dasar.
- Shot foto: checkbox disabled.
- Preview klip di brief ikut state mute/volume (volume preview dibatasi 100 %, batas `<video>`).

### Brief, per video
- Radio "SFX transisi":
  - `click_random` (default): klik + SFX random, perilaku sekarang;
  - `click`: klik aja;
  - `none`: tanpa SFX.
- Yang diatur: semua bunyi pergantian shot (`cut` + `extra_*`, `hook_cut` + `hook_extra_*`, `item_reveal`). Klik CTA dan SFX kustom per shot nggak ikut.

### Data (`links.json`)
- Per shot: `"volume": 1.5` (fraksi 0–2). Nggak ada = mute.
- Level atas: `"transition_sfx": "click" | "none"`. Nggak ada = `click_random`.
- Simpan tanpa key `audio`/`transition_sfx` (tab lama, upload) tetap bawa nilai lama.
- `same_clip` nggak ngitung `volume`.

### Fetch
- Shot video dengan `volume` dipotong bareng audionya: `-map 0:a:0?`, AAC 128k, `atempo=<speed>` kalau speed ≠ 1 biar nadanya nggak berubah.
- Shot lain tetap `-an`.
- `clips.json` dapet `"volume"` buat shot itu.
- Fetch motong ulang semua shot tiap jalan, jadi ganti mute cukup lewat `--from fetch`.

### Timeline + Remotion
- `Shot.volume` dari `clips.json`.
- `ShotView`: `<Video>` utama (layout full atau foreground di layout blur) nggak di-mute dan pakai `volume`. Background blur dan shot dekoratif tetap mute.
- Remotion 4.0.538 dukung volume > 1 pas render.
- `transition_sfx` dibaca pipeline dari `links.json`, masuk ke `audio`, lalu dipakai di `_sound`.

### API brief
- `POST /api/links` nerima `audio: {idx: persen | null}` dan `transition_sfx`.
- `GET /api/bgm-volume` → `{"percent": 6.0}`, di-cache per (lagu, durasi).

## Di luar scope
- Ducking otomatis audio klip di bawah narasi.
- Normalisasi loudness audio klip.
- Mode SFX per shot.
