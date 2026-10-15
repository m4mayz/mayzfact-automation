# Spec — Upload terjadwal ke YouTube

- **Tanggal:** 2026-10-15
- **Status:** disetujui Akmal di chat, nunggu review spec ini.
- **Konteks:** D-025 nunda upload lewat API karena project Google Cloud yang belum diaudit bakal ngunci video jadi private. Akmal bilang project-nya udah lolos audit, jadi upload + jadwal lewat API sekarang dikerjain. Ini ngegantiin D-025 poin 4.

## 1. Tujuan

Setelah Akmal oke `final.mp4`, agent:

1. nulis metadata YouTube lengkap ke `runs/<id>/upload.json`,
2. ngusulin jam tayang dan nunggu Akmal konfirmasi,
3. upload video ke YouTube dengan jadwal itu (`publishAt`), terus ngasih link-nya.

Berhasil kalau: video muncul di YouTube Studio sebagai *Scheduled* di jam yang dikonfirmasi, metadata-nya sesuai `upload.json`, dan run yang sama nggak bisa ke-upload 2 kali.

## 2. Keputusan dari chat

| Topik | Keputusan |
| --- | --- |
| Audit project | Udah lolos. `publishAt` langsung dipakai. |
| Simpan token | Ditulis ke baris `YOUTUBE_TOKEN_JSON` di `.env` (JSON inline, sama kayak `YOUTUBE_CLIENT_SECRET_JSON`). |
| Library | `google-auth-oauthlib` (login) + `google-api-python-client` (upload). |
| Judul | Bahasa Inggris, ≤ 100 karakter, ada `#Shorts`. |
| Deskripsi | 1–2 kalimat ringkasan, hashtag, credit klip dari `clips.json`. |
| Tag | 5–10 tag topik. |
| Kategori | Dipilih agent per video (mis. 15 Pets & Animals, 27 Education). |
| Bahasa | `en` (judul/deskripsi dan audio). |
| Made for kids | `false`. |
| Jadwal | Agent ngusulin slot kosong berikutnya (21.00 atau 04.00 WIB), Akmal konfirmasi atau ganti. Setelah lewat jadwal, video jadi public. |

## 3. Komponen

### `mayzfact/youtube.py`

- `SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]`
- `login(client_secret_json: str, env_file: Path) -> None`
  - `InstalledAppFlow.from_client_config(json.loads(client_secret_json), SCOPES).run_local_server(port=0)`. Browser kebuka, Akmal pilih akun dan setuju.
  - Hasil `creds.to_json()` ditulis ke `.env` lewat `set_env_value(env_file, "YOUTUBE_TOKEN_JSON", value)`.
- `set_env_value(env_file: Path, name: str, value: str) -> None`
  - Ganti baris `NAME=...` yang ada (atau tambah di akhir kalau belum ada). Value ditulis dalam kutip tunggal biar JSON-nya kebaca `python-dotenv`. Baris lain nggak disentuh. Tulis atomik (file `.tmp` lalu replace).
- `credentials(token_json: str) -> Credentials`
  - `Credentials.from_authorized_user_info(json.loads(token_json), SCOPES)`, refresh kalau expired. Refresh nggak nulis ulang `.env` (refresh token tetap sama).
- `UploadMeta` (pydantic): `title`, `description`, `tags: list[str]`, `category_id: str`, `language: str = "en"`.
  - `title`: 1–100 karakter, nggak boleh ada `<` atau `>`.
  - `description`: ≤ 5000 byte UTF-8, nggak boleh ada `<` atau `>`.
  - `tags`: total panjang (dijumlah + koma) ≤ 500 karakter.
  - `category_id`: string angka.
- `next_slot(taken: list[datetime], now: datetime) -> datetime`
  - Slot = tiap hari jam 21.00 dan 04.00 WIB (`Asia/Jakarta`). Ambil slot pertama yang ≥ `now + 15 menit` dan belum ada di `taken`.
- `taken_slots(runs_dir: Path) -> list[datetime]`: baca `publish_at` dari semua `runs/*/youtube.json`.
- `parse_publish_at(text: str, now: datetime) -> datetime`
  - Format `YYYY-MM-DD HH:MM`, dibaca sebagai WIB. Ditolak kalau kurang dari 15 menit dari `now`.
- `video_body(meta: UploadMeta, publish_at: datetime) -> dict`
  - `snippet`: title, description, tags, categoryId, defaultLanguage, defaultAudioLanguage.
  - `status`: `privacyStatus: "private"`, `publishAt` (UTC ISO 8601, akhiran `Z`), `selfDeclaredMadeForKids: false`.
- `upload_video(paths: RunPaths, meta: UploadMeta, publish_at: datetime, service, log) -> dict`
  - Tolak kalau `runs/<id>/youtube.json` udah ada.
  - `videos().insert(part="snippet,status", body=..., media_body=MediaFileUpload(final.mp4, chunksize=8 MB, resumable=True))`, loop `next_chunk(num_retries=3)` sambil nge-log persen.
  - Sukses: tulis `youtube.json` = `{video_id, url, studio_url, publish_at (WIB ISO), uploaded_at}`.

### Config

`Settings` nambah `youtube_client_secret_json` dan `youtube_token_json` (env `YOUTUBE_CLIENT_SECRET_JSON`, `YOUTUBE_TOKEN_JSON`). `.env.example` nambah dua nama itu (tanpa isi).

### CLI

| Perintah | Isi |
| --- | --- |
| `mayzfact login youtube` | Login sekali, token masuk `.env`. |
| `mayzfact next-slot` | Print slot kosong berikutnya, mis. `2026-10-15 21:00`. |
| `mayzfact upload <id> --at "YYYY-MM-DD HH:MM"` | Cek semuanya, upload, print link video + link YouTube Studio. |

`youtube` masuk sebagai pilihan `login` di samping platform hook. `login --check` nggak ikut ngecek YouTube.

### Skill `bikin-short` dan `AGENTS.md`

Langkah 6–7 lama diganti:

6. **Metadata:** agent nulis `runs/<id>/upload.json` sesuai default di bagian 2.
7. **Checkpoint jadwal:** agent jalanin `mayzfact next-slot`, nunjukin judul + jam usulan ke Akmal, tunggu konfirmasi atau jam lain.
8. **Upload:** `mayzfact upload <id> --at "<jam>"` (background), terus kasih link-nya ke Akmal.

`AGENTS.md`: upload ke YouTube itu aksi keluar. Jangan jalanin `mayzfact upload` sebelum Akmal konfirmasi jamnya. Jangan print isi `YOUTUBE_*`.

## 4. Error

| Kasus | Perilaku |
| --- | --- |
| `YOUTUBE_CLIENT_SECRET_JSON` kosong / bukan JSON | `PipelineError`: isi dulu di `.env`. |
| `YOUTUBE_TOKEN_JSON` kosong | `PipelineError`: jalanin `mayzfact login youtube`. |
| Token dicabut / refresh gagal (`RefreshError`) | `PipelineError`: login ulang. |
| `final.mp4` / `upload.json` nggak ada, atau `upload.json` nggak valid | `PipelineError` dengan pesan field yang salah. Nggak ada request ke YouTube. |
| `youtube.json` udah ada | `PipelineError` + link video lama. Upload ulang = hapus file itu manual. |
| `--at` salah format atau < 15 menit lagi | `PipelineError`. |
| `HttpError` dari YouTube (kuota, 4xx/5xx) | `PipelineError` dengan status + alasan dari API. `youtube.json` nggak ditulis, aman di-retry. |
| Koneksi putus | `next_chunk(num_retries=3)`. Kalau tetap gagal, `PipelineError`. |

Isi secret dan token nggak pernah di-print atau di-log, termasuk di pesan error.

## 5. Test

Tanpa API beneran:

- `UploadMeta`: judul kepanjangan, ada `<`, tag kepanjangan → ditolak; yang valid lolos.
- `next_slot`: urutan 04.00/21.00, slot yang kepake dilewatin, slot < 15 menit lagi dilewatin, nyebrang hari.
- `parse_publish_at`: WIB → UTC benar, format salah dan jam yang udah lewat ditolak.
- `video_body`: private, `publishAt` UTC `Z`, made for kids `false`, kategori, bahasa.
- `upload_video`: pakai fake service: nulis `youtube.json`; nolak kalau `youtube.json` udah ada (fake service nggak dipanggil); `HttpError` → `youtube.json` nggak ada.
- `set_env_value`: cuma baris itu yang berubah, baris lain dan komentar tetap; baris baru ditambah kalau belum ada; `load_settings` bisa baca balik JSON-nya.
- CLI: `upload` tanpa token → exit 1 dengan pesan login; `next-slot` nge-print format yang benar.

Belum dites otomatis: login beneran dan upload beneran. Upload pertama Akmal jadi tes beneran-nya.

## 6. Di luar scope

- Thumbnail custom (Shorts jarang pakai).
- Playlist, komentar, statistik.
- Ngecek jadwal yang kepake langsung dari YouTube (cukup dari `runs/*/youtube.json`).
- Ganti jadwal atau hapus video yang udah ke-upload (lewat YouTube Studio aja).
