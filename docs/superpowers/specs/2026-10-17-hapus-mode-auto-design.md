# Spec — Hapus mode auto, sisa mode manual aja

- **Tanggal:** 2026-10-17
- **Status:** diminta Akmal di chat, nunggu review spec ini.
- **Keputusan baru:** D-031 (ditulis pas implementasi, lihat bagian 7).

## 1. Kenapa

Mode auto (`CLIP_SOURCE=auto`: step `hook` + `clips`, cari klip otomatis lewat Pexels/Pixabay dan scraping TikTok/Douyin/Pinterest pakai Playwright) udah nggak kepake. Semua video sekarang lewat jalur manual: agent nulis naskah → suara → plan → Akmal isi link di brief → fetch → timeline → render → upload. Kode auto cuma bikin project lebih susah dibaca harness lain dan nambah ±51 test yang nggak ngetes jalur yang dipakai.

**Rencana nanti (bukan bagian spec ini):** kalau auto balik, bentuknya beda: yang otomatis cuma nyari klip, pakai browser Akmal sendiri yang udah login TikTok. Kode Playwright yang sekarang (profil browser terpisah di `browser-profiles/`) nggak dipakai ulang, nanti ditulis dari nol. Ide ini dicatat di D-031 aja.

## 2. Tujuan, non-tujuan, anti-tujuan

**Tujuan**
- Cuma ada 1 urutan step: `source → tts → plan → fetch → timeline → render`.
- Semua kode, setting, env var, dependency, test, dan docs yang cuma buat auto hilang.
- `.env` dan `.env.example` cuma berisi variabel yang beneran dibaca kode.

**Non-tujuan**
- Nggak ada perubahan perilaku di jalur manual. Run yang udah ada (`runs/<id>/`) tetap bisa dilanjutin pakai perintah yang sama.
- Nggak bikin fitur auto versi baru.

**Anti-tujuan (gagal walaupun "jalan")**
- Fungsi yang dipakai manual ikut kehapus, terus brief/plan/fetch/timeline rusak.
- `voice.mp3`, `script.json`, `youtube.json`, atau `final.mp4` di run lama kehapus atau jadi nggak kebaca.
- Isi `.env` (API key, token) ke-print, ke-log, atau ke-commit selama bersih-bersih.
- `flow.svg` atau `sources/` diubah.

## 3. Yang dihapus

### Step dan pipeline (`mayzfact/pipeline.py`)
- `STEPS` auto dan `ALL_STEPS` digabung jadi satu daftar: `source, tts, plan, fetch, timeline, render`. `--from hook` / `--from clips` hilang dari pilihan CLI.
- `settings.clip_source` dan cabang `MANUAL_STEPS if ... else STEPS` hilang.
- `STEP_ENV["clips"]`, `CLIP_MAX_SEARCHES`, `step_outputs` buat hook/clips, `AFTER_VOICE` yang nyebut hook/clips, guard "butuh mode manual", branch `hook`/`clips` di `_run_step`, dan pesan error/log yang nyebut mode auto atau `--from hook/clips`.
- Field `Deps` yang cuma buat auto: `search`, `media_cache`, `hook`, `scorer`, `clip_search`, plus pembuatnya di `real_deps` (`search()`, `fetch_thumb`, `hook()`, `clip_search()`). `http` dan `encoder` tetap.

### Modul yang dihapus utuh
- `mayzfact/providers/pexels.py`, `pixabay.py`, `stock.py`, `types.py`
- `mayzfact/platforms/` (semua: `base.py`, `parsers.py`, `browser.py`, `__init__.py`)
- `mayzfact/thumbs.py`, `mayzfact/scoring.py`, `mayzfact/cache.py`
- `mayzfact/steps/hook.py` dan `mayzfact/steps/clips.py`, **setelah** bagian yang dipakai manual dipindah (bagian 4).
- `providers/elevenlabs.py` tetap. Kalau folder `providers/` tinggal elevenlabs, biarin di situ.

### Bagian auto di file campuran
- `matching.py`: `top_k`, `match_label`, `rerank_key`.
- `media.py`: `best_rendition`, `tier`, `pick_rendition`, dan import `providers.types`.
- `ytdlp.py`: parameter `cookies` dan `max_seconds` (cuma dipakai Playwright), default `step="hook"`, docstring "klip platform login".
- `store.py`: `hook_dir`, `hook_json`.
- `config.py`: `BROWSER_PROFILES_DIR`, `_clip_source`, `_flag` (cuma dipakai `BROWSER_HEADLESS`).
- `steps/timeline.py`: pesan log "atau --from clips (auto)".
- Deskripsi CLI dan `pyproject.toml` yang bilang "klip stock".

### Setting dan env var
Dihapus dari `Settings`, `ENV_FIELDS`, `.env.example`, dan `.env`:
`CLIP_SOURCE`, `PEXELS_API_KEY`, `PIXABAY_API_KEY`, `HOOK_PLATFORMS`, `CLIP_PLATFORMS`, `BROWSER_HEADLESS`, `HOOK_EXACT_THRESHOLD`, `PHOTO_RATIO` (udah nggak dibaca kode sama sekali).

Tambahan dari Akmal: `GEMINI_API_KEYS` dan `GEMINI_MODEL` di `.env` (sisa sebelum D-028, udah nggak dibaca kode).

Yang tetap: `ELEVENLABS_*`, `TARGET_DURATION_RATIO`, `MIN_DURATION_SECONDS`, `MAX_SHOT_SECONDS`, `FG_MIN_HEIGHT_RATIO`, `HOOK_SECONDS`, `BRIEF_PORT`, `YOUTUBE_CLIENT_SECRET_JSON`, `YOUTUBE_TOKEN_JSON`, `NGROK_BASIC_AUTH`.

**Cara bersihin `.env`:** hapus baris variabelnya pakai script yang cuma nyocokin nama variabel di awal baris. Isi nilainya nggak pernah di-print. Nilai API key Pexels/Pixabay/Gemini ikut hilang (nggak bisa dibalikin dari repo); Akmal udah setuju hapus semua.

### CLI (`mayzfact/cli.py`)
- `login` cuma `youtube`: `mayzfact login youtube`. `login <platform>` dan `login --check` hilang.
- Import `platforms.*` di atas file hilang (CLI nggak lagi narik kode Playwright).

### Dependency
- `playwright` dari `pyproject.toml`, terus `uv lock` ulang.

### Field naskah `fallback_query`
- Cuma dipakai `run_clips`. Dihapus dari model `Script`, `check-script`, contoh JSON di skill `bikin-short`, dan factory test.
- `script.json` lama yang masih punya `fallback_query` tetap harus kebaca (field ekstra diabaikan, bukan error).

### Test
- Hapus file yang cuma ngetes auto: `test_hook.py`, `test_clips_hook.py`, `test_clips_step.py`, `test_browser_platform.py`, `test_platform_base.py`, `test_platform_parsers.py`, `test_stock_providers.py`, `test_scoring.py`, `test_cache.py`.
- Rapihin file campuran: `test_clip_selection.py` (sisa test `split_shots` + `beat_subjects`), `test_media.py`, `test_matching.py`, `test_pipeline.py`, `test_cli.py`, `test_config.py`, `test_ytdlp.py`, `test_store.py`, `tests/factories.py` (`cand()`).
- `test_pipeline.py` paling berat: `SETTINGS` sekarang auto + `FakeSearch`. Ganti jadi world manual (plan + fetch palsu) supaya test timeline/naskah yang ada tetap ngetes hal yang sama lewat jalur manual.

### Docs
- `README.md`: contoh `--from clips`, "Mode lama: `CLIP_SOURCE=auto`", seluruh bagian "Hook (Fase 2)" (login platform, `browser-profiles/`).
- `AGENTS.md`: aturan "minta Akmal jalanin `mayzfact login <platform>`" diganti versi manual (link yang minta captcha/login = minta link lain). Larangan print/log/commit isi `browser-profiles/` **tetap** selama foldernya masih ada di disk (isinya cookie session yang masih hidup) *(keputusan agent)*. Aturan nggak solve captcha, nggak rotasi proxy, nggak spoof fingerprint tetap.
- `docs/HANDOFF.md`: tambah handoff fase ini; bagian Fase 2 lama ditandai "dihapus di D-031", nggak dihapus (riwayat).
- `docs/DECISIONS.md`: keputusan lama nggak diedit, cuma ditambah D-031.
- Spec/plan lama di `docs/superpowers/` nggak diubah (riwayat).
- `.gitignore` baris `browser-profiles/` tetap (folder lama masih ada di disk).
- `flow.svg` nggak disentuh walaupun masih nyebut Pexels/Pixabay.

## 4. Yang dipindah (dipakai manual, tinggal di file auto)

| Fungsi | Sekarang di | Dipakai | Pindah ke |
| --- | --- | --- | --- |
| `prepare_source_segments`, `transcript_near`, `FRAME_POSITIONS` | `steps/hook.py` | `steps/source.py`, `steps/plan.py` | modul baru `mayzfact/source_frames.py` |
| `normalize_local` | `steps/clips.py` | `steps/fetch.py` | `steps/fetch.py` (atau modul kecil kalau impor muter) |
| `split_shots`, `ShotSlot`, `beat_subjects` | `steps/clips.py` | `steps/plan.py`, `overlay.py` | modul baru `mayzfact/shots.py` |

Nama dan perilaku fungsinya nggak berubah, cuma lokasinya. Nama modul tujuan itu usulan; builder boleh milih lain asal satu tanggung jawab per file dan nggak ada impor muter.

## 5. Yang nggak berubah

- Download link manual (`manual/obtain.py`, resolver Douyin/TikTok/og, yt-dlp) nggak pakai cookie browser dan nggak nyentuh `browser-profiles/`. WAF proof-of-work Douyin (D-018) tetap.
- SigLIP (`embed.py`), deteksi cut (`scenes.py`), OWLv2, `net.py`, upload YouTube, ngrok, brief, prefetch.
- `clips.json` tetap nulis `provider`/`page_url`/`author` (ditulis fetch).

## 6. Data di disk

- `browser-profiles/`, `cache/search/`, `cache/thumbs/`, `cache/media/`, `runs/*/hook/`, `runs/*/hook.json` nggak dipakai lagi. Spec ini **nggak** ngehapus folder itu otomatis; agent nyebutin ukurannya di akhir dan Akmal yang mutusin hapus atau nggak. `cache/manual/` tetap dipakai.
- Run yang sekarang ada di disk (`4735ZE89GXQ`, `NSua7RPoFJg`, `i2xag_1OJfM`, `piD9Fjp-mG8`, `ydA5gOdKvfc`) semuanya punya `shots_plan.json`, jadi tetap bisa di-`--from timeline` / `--from render`. Run auto murni (tanpa `shots_plan.json`) nggak perlu didukung; nggak ada lagi di disk *(keputusan agent)*.

## 7. D-031 (isi yang ditulis)

Mode auto dihapus; pipeline cuma mode manual. Alasan: nggak kepake sejak D-019/D-028. Kalau auto balik, bentuknya: cari klip otomatis pakai browser Akmal yang udah login TikTok, kode ditulis dari nol. Authority: Akmal (chat 2026-10-17).

## 8. Cara ngecek beres

- `uv run pytest` lolos semua.
- `uvx ruff check --select F,I` lolos di file yang diubah.
- `rg -i "clip_source|pexels|pixabay|playwright|hook_platforms|clip_platforms|browser_headless|fallback_query|GEMINI" mayzfact tests .env.example README.md AGENTS.md .agents` nggak nemu apa-apa (kecuali D-031/HANDOFF yang sengaja nyebut).
- `uv run mayzfact run <id> --help` nggak nawarin `hook`/`clips`. `uv run mayzfact login youtube --help` jalan.
- Run lama dicek tanpa kredit, **di salinan**: copy `runs/ydA5gOdKvfc` ke folder sementara (scratchpad), jalanin timeline di salinan itu (`run_pipeline(..., runs_dir=<sementara>, from_step="timeline", no_render=True)`), terus bandingin `timeline.json`-nya sama yang asli (kecuali urutan key). Jangan jalanin langsung di `runs/ydA5gOdKvfc`: `--from timeline` ngehapus `final.mp4`, dan video ini udah ke-upload *(keputusan agent)*.
- Nama variabel di `.env` dicek (tanpa nilai): cuma yang ada di daftar "tetap".

## 9. Diserahin ke builder

- Urutan pengerjaan dan pembagian commit.
- Nama modul tujuan di bagian 4.
- Cara bikin world manual di `test_pipeline.py`.
- Apakah `providers/` diganti nama atau dibiarin dengan isi cuma `elevenlabs.py` (default: dibiarin).
