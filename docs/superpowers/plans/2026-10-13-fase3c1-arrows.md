# Fase 3C-1 Arrows + Circles Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans.

**Goal:** Panah dan lingkaran yang ngikutin subjek, posisinya dari deteksi OWLv2.
**Spec:** [`docs/superpowers/specs/2026-10-13-fase3c1-arrows-design.md`](../specs/2026-10-13-fase3c1-arrows-design.md)

> **Ruling (eksekutor):** Plan ini sengaja ringan, cuma interface sama test kunci, karena Akmal minta langsung dikerjain. Kodenya ditulis pakai TDD.

## Global Constraints

- Branch `fase3c-overlay`.
- Commit pakai `caveman-commit`, 1 baris, tanpa atribusi.
- Test biasa nggak boleh nge-load model asli. Test yang butuh model asli pakai marker `clip`.
- `voice.mp3` nggak boleh disentuh.
- Jangan render final sebelum Akmal review di Studio.

## Review Focus

1. Klip yang kependekan, misalnya 1 detik.
2. Subjek nggak kedeteksi sama sekali: shot nggak dapat overlay, dan nggak crash.
3. Klip landscape (`blur`): koordinat harus pas di kotak foreground.
4. Klip hook yang nyambung panjang: harus banyak titik deteksi.
5. Cache tetap valid setelah `--from fetch` ganti klip, karena `key` ikut size/mtime file.

### Task 1: `detect.py` + `overlay.py`

Isinya: `Owlv2Detector`, `screen_box`, `fill_points`, `shot_query`, `prepare_overlays`. Test-nya di `tests/test_overlay.py`.

### Task 2: Timeline + pipeline

Isinya:
- `build_timeline(overlays=)` milih jenis dan warna overlay.
- `Deps.overlay` dipanggil di step timeline.

Test-nya di `tests/test_timeline.py` dan `tests/test_pipeline.py`.

### Task 3: Remotion

Isinya: `Overlays.tsx` (`Arrow`, `Circle`), update types, `ShortVideo`, sama fixture test render.

### Task 4: E2E i2xag + Studio + review + HANDOFF
