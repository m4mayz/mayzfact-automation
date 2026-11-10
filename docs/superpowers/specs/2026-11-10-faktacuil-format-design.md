# Spec: format FaktaCuil (`narration_mode: "faktacuil"`)

- **Tanggal:** 2026-11-10
- **Status:** diimplementasi di branch `fase-faktacuil-format` (Task 1–12 ter-commit, docs Task 13–14). Spec ini diupdate 2026-11-10 biar sesuai yang dibangun: jawaban Akmal atas Q1–Q8 (voice Eric, VoiceStudio, slot 12.00/18.00, shot 2,0 detik, BGM Bully), kalibrasi tempo 2,27, dan deviasi implementasi (bagian 13). Keputusan Akmal (1)–(8) di bagian 2 disetujui 2026-11-10.
- **Keputusan baru:** D-051 (`docs/DECISIONS.md`).
- **Branch:** `fase-faktacuil-format`
- **Bahan:** laporan riset T8 `E:\APROJECT\mayzfact-refs\faktacuil\LAPORAN-T8-format-faktabor-zonag2v.md` (di luar repo), spec D-050 `docs/superpowers/specs/2026-11-10-top3-only-design.md`, branding `assets/channels/faktacuil/`.

## 1. Kenapa

Akmal mau channel kedua, FaktaCuil: Shorts fakta unik bahasa Indonesia, satu video satu fakta. Formatnya niru konsep @FaktaBor dan @zona-g2v (T8), bukan kontennya: hook "Kenapa…?", salah kaprah, jawaban, CTA like gimmick di tengah, caption 1 kata, footage reupload ganti tiap 1–2,5 detik, durasi 20–30 detik.

Pipeline sekarang cuma kenal format top3 (D-050). Field `narration_mode` sengaja disisain buat format channel lain. Spec ini nambah nilai kedua tanpa ngubah perilaku top3.

## 2. Keputusan yang udah disepakati Akmal (2026-11-10)

1. **Sumber naskah:** video Inggris, sama kayak alur MayzFact. Agent nerjemahin + nulis ulang ke bahasa Indonesia santai. Aturan "jangan nambah fakta dari luar source" tetap.
2. **Durasi final** 20–30 detik (setelah speed-up).
3. **CTA:** gimmick "coba tekan like, like-mu berubah jadi X?" pakai `CtaScene` yang udah ada, di tengah sebelum jawaban, cuma like (tanpa subscribe). Detektor pemicu bahasa Indonesia terpisah dari aturan Inggris.
4. **Dimatiin:** panah/lingkaran, card countdown, emoji, intro whip, flash. **Tetap:** SFX transisi, blur teks klip.
5. **Caption:** 1 kata, Fredoka putih outline hitam, animasi pop, kata kunci kuning brand.
6. **Voice:** ElevenLabs bahasa Indonesia. Task pertama: 3 sampel pendek buat dipilih Akmal. Kredit 3 sampel pendek udah disetujui, generate-nya lewat lead. **Jawaban 2026-11-10:** voice cowok, akun ElevenLabs free jadi cuma voice premade yang bisa lewat API. Dipilih **Eric** `cjVigY5qzO86Huf0OWal`. FaktaCuil juga bisa VoiceStudio (`faktacuil_tts_provider` dkk di `settings.local.json`); profil bahasa Indonesia belum ada.
7. **BGM:** 1 lagu sepanjang video, dipilih Akmal (referensi gaya: Bully main theme, D minor, ±98 BPM feel). File nyusul. Repo public, jadi lagu berhak cipta nggak boleh di-commit; lokasinya lokal + gitignore. Sementara pakai `main.mp3`. **Jawaban 2026-11-10:** dipilih Bully "Welcome to Bullworth" (117,5 BPM). File-nya lokal di `assets/channels/faktacuil/bgm/` (gitignored); Akmal/lead yang naruh, agent nggak download atau copy.
8. **Upload:** channel FaktaCuil lewat OAuth token kedua, slot jadwal sendiri terpisah dari MayzFact. Jam final belum diputusin (kandidat 12.00 dan 18.00 WIB), jadi configurable di `Settings`. Metadata bahasa Indonesia, hashtag pola `#faktaunik #faktamenarik` + topik + generik. **Jawaban 2026-11-10:** slot 12.00 dan 18.00 WIB, maksimal 2 video per hari; upload nggak tentu tiap hari, jadi `next-slot` ambil slot kosong berikutnya.

Footage tetap lewat brief + `links.json` manual dari Akmal.

## 3. Tujuan, non-tujuan, anti-tujuan

**Tujuan**
- `script.json` dengan `narration_mode: "faktacuil"` bisa jalan dari naskah sampai upload di channel FaktaCuil.
- `check-script` nge-cek aturan naskah FaktaCuil (bagian 5), pesannya English kayak sekarang.
- Timeline + Remotion ngeluarin video dengan caption Fredoka, CTA like + scene transformasi di tengah, tanpa dekorasi yang dimatiin (bagian 6).
- Upload ke channel yang benar, slot jadwal nggak bentrok sama MayzFact.

**Non-tujuan**
- Perilaku top3 nggak berubah: anggaran kata, validasi, plan, timeline, Remotion, upload MayzFact, slot 01.00/04.00.
- Nggak bikin registry format, strategy class, atau config per channel. Dua format cukup pakai cabang `if mode == "faktacuil"` di tempat yang emang beda.
- Nggak ngubah step source (tetap transcript English), brief, dan fetch.
- Nggak bikin watermark di dalam video. `assets/channels/faktacuil/watermark.png` itu watermark branding YouTube Studio yang dipasang Akmal manual (commit `cbf145e`).
- Nggak bikin CTA akhir-loop gaya FaktaBor terbaru (T8). Akmal milih CTA tengah.
- Nggak bikin metadata TikTok buat FaktaCuil (lihat Q5).

**Anti-tujuan (gagal walaupun test hijau)**
- Video top3 hasil render beda dari sebelumnya, atau `timeline.json` top3 berubah.
- Video FaktaCuil ke-upload ke channel MayzFact (atau sebaliknya).
- Slot FaktaCuil ngisi atau ngeblok slot MayzFact.
- File lagu berhak cipta ke-commit ke repo public.
- `voice.mp3` run mana pun ditimpa, atau sampel voice ke-generate ulang tanpa izin.

## 4. Nama nilai `narration_mode`: `"faktacuil"`

Nilai baru `"faktacuil"` di `Script.narration_mode` (`mayzfact/models.py:34`).

Alasannya: nilai ini bukan cuma nentuin struktur naskah. Dia juga nentuin bahasa, voice, style caption, BGM, dekorasi yang mati, akun YouTube, dan slot. Nama struktur kayak `"why"` atau `"single"` bakal nyesatin kalau nanti MayzFact bikin format 1 fakta bahasa Inggris, karena channel dan bahasanya beda. Pola `top3` (nama format) dan `faktacuil` (nama channel) emang nggak seragam, tapi sekarang format dan channel masih 1:1. Kalau nanti satu channel punya 2 format, baru dipecah.

Ditolak:
- `"id_single"`, `"kenapa"`, `"why"`: nama struktur, padahal cabangnya ngatur channel juga.
- Field baru `channel` terpisah dari `narration_mode`: 2 field yang selalu berpasangan cuma nambah kombinasi invalid. D-050 udah nyebut `narration_mode` sebagai pemilih format channel.

## 5. Kontrak `script.json` FaktaCuil

### Schema (`mayzfact/models.py`)

```python
class Beat(BaseModel):
    ...                      # field lama nggak berubah
    keyword: str = ""        # FaktaCuil: 1 kata di beat ini yang caption-nya kuning brand


class Script(BaseModel):
    narration_mode: Literal["top3", "faktacuil"]
    approved_word_count: int | None = ...   # tetap, berlaku buat dua format
    cta_scene: CtaScene                     # tetap wajib, schema CtaScene nggak berubah
    beats: list[Beat]
    bgm: str = ""
    hook_queries: dict[str, HookQuery] = {}
```

- `CtaScene` (`mayzfact/models.py:8-14`) nggak berubah. Tema tetap 6 ilustrasi. `comment_text` tetap wajib di schema, tapi di FaktaCuil nggak ditampilin (nggak ada stage comment). Isinya kata objek transformasi huruf kapital, misal `"MADU"`. Lihat bagian 12.
- `keyword` baru, default `""`. Hash suara (`script_text`) cuma dari teks beat, jadi field ini nggak ngubah hash.
- `load_script` (`mayzfact/steps/script.py:136-141`) nerima `"top3"` dan `"faktacuil"`. Pesan error format lama tetap ngandung `narration_mode` dan nyebut dua nilai yang didukung.

Contoh:

```json
{
  "narration_mode": "faktacuil",
  "cta_scene": {"theme": "honey", "transform_word": "berubah", "comment_text": "MADU"},
  "beats": [
    {"text": "Kenapa kucing suka banget masuk ke kardus?", "media": "video",
     "queries": ["cat sitting in cardboard box"], "queries_zh": ["猫 纸箱"],
     "subject": "cat", "keyword": "kardus"},
    {"text": "Padahal kardus itu sempit dan nggak empuk,", "media": "photo", "queries": ["cat squeezed in small box"],
     "subject": "cat", "keyword": "sempit"},
    {"text": "Tapi coba tekan like dulu,", "media": "video", "queries": ["finger tapping like button phone"]},
    {"text": "apakah like-mu berubah jadi madu?", "media": "video", "queries": ["honey dripping jar"]},
    {"text": "Ternyata ruang sempit bikin kucing merasa aman,", "media": "video", "queries": ["cat hiding relaxed"],
     "subject": "cat", "keyword": "aman"}
  ],
  "hook_queries": {}
}
```

(Contoh ini cuma bentuk. Fakta di video beneran wajib dari source.)

### Aturan naskah FaktaCuil (`check-script` + sebelum TTS)

Dicek di modul baru `mayzfact/faktacuil.py` (fungsi murni), dipanggil dari `check_script` (`mayzfact/steps/script.py:46`) lewat 1 cabang di awal fungsi.

| # | Aturan | Pesan (English) |
|---|---|---|
| F1 | Hook: teks beat 1 dibuka kata `Kenapa` (case-insensitive). Kalimat pertama selesai pakai `?` paling lambat di beat 2. | `FaktaCuil hook must open with "Kenapa" and end the question with "?" within the first two beats.` |
| F2 | Nggak ada beat yang kebaca countdown (`parse_countdown(...).number is not None`). | `FaktaCuil beats must not use "Number N," countdown announcements.` |
| F3 | Blok CTA (definisi di bawah) ada tepat 1, kontigu, 1–3 beat. | `FaktaCuil CTA must be one contiguous block of 1-3 beats.` |
| F4 | Salah kaprah sebelum CTA: minimal 1 beat non-CTA antara akhir hook (beat yang ada `?` pertama) dan awal blok CTA. | `FaktaCuil needs at least one misconception beat between the hook question and the CTA.` |
| F5 | Jawaban setelah CTA: minimal 2 beat non-CTA setelah blok CTA. | `FaktaCuil needs at least two answer beats after the CTA.` |
| F6 | Blok CTA punya tepat 1 pemicu like Indonesia (`id_like_positions`), nol `subscribe`, nol comment (`komen`, `komentar`, `comment`). | `FaktaCuil CTA must invite exactly one like ("tekan like") and must not ask to subscribe or comment.` |
| F7 | Ada 1 beat di blok CTA yang ngandung `cta_scene.transform_word` (kata utuh), diakhiri `?`, dan ada frasa `jadi [seekor/sebuah] <objek tema>` (tabel objek di bawah). | `CTA illustration {theme!r} does not match the narrated transformation object. ...` (pesan sama kayak top3 biar agent kenal) |
| F8 | Beat CTA: `subject` kosong, `point` false. | sama kayak top3: `CTA beat {n} must have an empty subject.` / `point=false` |
| F9 | Semua beat: `point` false, `emoji` dan `emoji_word` kosong. | `FaktaCuil does not use arrows or emoji; beat {n} must have point=false and empty emoji fields.` |
| F10 | `keyword` (kalau diisi) harus 1 token yang ada di teks beat itu: teks dipisah spasi, tanda baca tepi dibuang (`_EDGE_PUNCT`), case-insensitive, sama kayak token caption. Jadi `kupu-kupu` boleh. Nggak boleh di beat CTA. | `Beat {n} keyword {kw!r} must be one word that appears in the beat text (and not in CTA beats).` |
| F11 | Jumlah kata total masuk rentang FaktaCuil (bawah). | `The narration has {count} words; it must have between {low} and {high}.` (pesan sama) |
| — | Aturan umum yang tetap: ≤10 kata per beat, foto 15–45%, tiap beat punya `queries`, overlap 4-gram ≤15%, teks nggak kosong. | pesan yang udah ada |

Aturan top3 yang **nggak** berlaku di FaktaCuil: `top3_problems`, wajib like+subscribe+comment, `missing_cta` dari source (source Inggris yang ngajak subscribe nggak maksa naskah ngajak subscribe, karena keputusan 3), `explanation_count` per item countdown.

Overlap 4-gram tetap dicek walaupun naskahnya terjemahan (hampir pasti 0%). Murah, dan nangkep kalau agent lupa nerjemahin.

**Blok CTA FaktaCuil** (`faktacuil_cta_indices(beats)`, pengganti `cta_beat_indices` buat mode ini):
- Anchor = beat yang punya token berawalan `like` (`like`, `like-mu`, `likenya`), atau token `subscribe`/`komen`/`komentar`/`comment`. Token dibersihin pakai `mayzfact.cta.clean`.
- Blok = `range(anchor pertama, anchor terakhir + 1)`. Nggak ada anchor = blok kosong.
- Kenapa token berawalan `like`: di naskah bahasa Indonesia, kata "like" cuma muncul di CTA. Pertanyaan gimmick "apakah like-mu berubah jadi madu?" nggak punya pemicu klik, tapi harus ikut blok (sama kayak beat gimmick di top3).

**Pemicu like Indonesia** (`id_like_positions(tokens)` di `mayzfact/faktacuil.py`, terpisah dari `LIKE_BEFORE` Inggris di `mayzfact/cta.py:8`):
- Token `like` (persis, setelah `clean`) yang didahului `tekan`, `pencet`, `klik`, `kasih`, `tekanlah`, atau didahului `tombol` yang didahului salah satu kata itu ("tekan tombol like").
- `like-mu`, "aku like", "like video ini" tanpa kata kerja ajakan **bukan** pemicu.
- Kata awal frasa (buat stage like mulai pas ajakan kedengeran): mundur dari kata kerja ke `coba` kalau ada ("coba tekan like"), sama kayak `try tapping like` di top3 (`mayzfact/cta_scene.py:43-46`).

**Objek tema → kata Indonesia** (F7):

| theme | frasa yang diterima setelah `jadi` |
|---|---|
| `volcano` | `gunung berapi`, `gunung meletus`, `gunung api` |
| `unicorn` | `unicorn` |
| `honey` | `madu` |
| `puppy` | `anak anjing`, `anjing` |
| `lion` | `singa` |
| `shark` | `hiu`, `ikan hiu` |

Objek di luar tabel = STOP, bikin ilustrasi baru dulu (aturan yang sama kayak top3 di skill `bikin-short`).

### Panjang naskah

Rumus: `kata = detik_final × video_speed × tempo_mentah`.

- `tempo_mentah` = kata/detik suara ElevenLabs bahasa Indonesia sebelum speed-up. Terukur dari sampel Eric: 40 kata / 17,60 detik (`eleven_v3`, stability 0.5, tanpa delivery tag) = **2,27**. Disimpan sebagai konstanta `FAKTACUIL_RAW_WPS = 2.27` di `mayzfact/faktacuil.py`. (Asumsi awal 2,5 sebelum diukur; referensi T8 final 2,45–3,4 kata/detik, MayzFact Inggris 2,2 mentah.)
- Rentang final **20–30 detik**, target **25 detik**.
- Di speed 1.1 dan tempo 2,27 (k = 1,1 × 2,27 = 2,497): target `round(25 × k)` = **62**, bawah `ceil(20 × k)` = **50**, atas `floor(30 × k)` = **74** (`faktacuil_word_range(1.1)` = `(62, 50, 74)`). Di speed 1.15 (VoiceStudio): **65 / 53 / 78**. Hitungannya dibulatin ke 6 desimal dulu biar noise float nggak geser batas (20 × 1,4 = 28,000000000000004). Referensi T8: 57–77 kata.
- Kata CTA ikut dihitung, tanpa allowance tambahan (CTA FaktaCuil cuma 1–3 beat pendek).
- `approved_word_count` tetap ngunci jumlah kata per run, sama kayak top3.
- `check_voice` (`mayzfact/pipeline.py:73`) buat FaktaCuil ngasih peringatan kalau estimasi final di luar **20–30 detik** (top3 tetap 30–40, `pipeline.py:88`).

## 6. Perubahan per step

### source (`mayzfact/steps/source.py`)
Nggak berubah. Source tetap video Inggris (keputusan 1), transcript tetap `languages=["en"]` (`source.py:35`). Step source jalan sebelum naskah ada, jadi format belum diketahui di sini, dan emang nggak perlu.

### script / check-script (`mayzfact/models.py`, `mayzfact/steps/script.py`, `mayzfact/faktacuil.py` baru, `mayzfact/cli.py`)
- Schema: bagian 5.
- `load_script` (`script.py:129`): nerima dua mode.
- `narration_word_range` (`script.py:33`): cabang FaktaCuil pakai `faktacuil_word_range(video_speed)`; top3 tetap.
- `check_script` (`script.py:46`): kalau mode `faktacuil`, hasilnya `faktacuil_problems(script)` (F1–F10) + cek panjang F11 (`narration_word_range`) + cek umum. Cek foto, beat kosong, ≤10 kata, dan queries diekstrak ke helper `_beat_problems(script)` yang juga dipanggil top3 di posisi yang sama. Cek overlap tetap paling akhir di dua mode. Urutan pesan top3 nggak boleh berubah; golden Task 1 punya case yang gagal di banyak aturan sekaligus buat jagain ini.
- `top3`: tambah 1 cek baru `keyword` harus kosong (`Top 3 beats must not set keyword.`). Naskah top3 yang ada nggak punya field ini, jadi hasil cek mereka nggak berubah.
- CLI `check-script` (`cli.py:82`) nggak berubah selain lewat `check_script_file`. Output `OK: naskah lolos cek (N kata, target T)` tetap.

### tts (`mayzfact/config.py`, `mayzfact/pipeline.py`)
- `mayzfact/steps/tts.py` nggak berubah.
- `Settings` (`config.py`) dapat field baru (bukan rahasia, nggak masuk `.env`):
  - `faktacuil_elevenlabs_voice_id: str = "cjVigY5qzO86Huf0OWal"`: Eric, voice premade yang bisa lewat API akun free (jawaban Q1, Akmal 2026-11-10).
  - `faktacuil_elevenlabs_delivery_tag: str = ""`: tag `[calm]` D-047 dipilih buat suara Inggris, belum tentu cocok.
  - `faktacuil_tts_provider: str = "elevenlabs"`, `faktacuil_voicestudio_voice: str = ""`, `faktacuil_voicestudio_instruct: str = ""`: FaktaCuil juga bisa VoiceStudio. Akmal ngisinya di `settings.local.json` (ketiganya ada di daftar field yang diterima `load_settings`; provider divalidasi, voice nggak boleh kosong kalau diisi). Profil bahasa Indonesia belum ada, jadi default-nya ElevenLabs.
  - `faktacuil_max_shot_seconds: float = 2.0` (lihat bagian plan).
  - Model (`eleven_v3`) dan stability (0.5) pakai field yang udah ada.
- Fungsi baru `settings_for_mode(settings, mode)` di `config.py`: top3 balikin `settings` apa adanya (identity). FaktaCuil balikin `replace(settings, tts_provider=faktacuil_tts_provider, voicestudio_voice=..., voicestudio_instruct=..., elevenlabs_voice_id=..., elevenlabs_delivery_tag=..., hook_seconds=0.0, max_shot_seconds=...)` dari field `faktacuil_*`, jadi `tts_provider` global (override MayzFact di `settings.local.json`) nggak kebawa. `video_speed`: `__post_init__` nge-bump 1,1 jadi 1,15 kalau voicestudio, dan `replace()` ikut kena (FaktaCuil voicestudio dapat 1,15). Kebalikannya, 1,15 hasil bump MayzFact voicestudio diturunin ke 1,1 kalau FaktaCuil pakai ElevenLabs.
- Cek VoiceStudio ada di `_require_script`, yang cuma jalan sebelum step tts: FaktaCuil + `tts_provider == "voicestudio"` + `voicestudio_voice` kosong → `PipelineError("config", ...)` yang nyuruh ngisi `faktacuil_voicestudio_voice` di `settings.local.json`. Provider selain `elevenlabs`/`voicestudio` ditolak di `run_pipeline`. PC yang setting lokalnya voicestudio tetap bisa jalanin `--from fetch/timeline/render`.
- `run_pipeline` (`pipeline.py`): `load_script` udah dipanggil di sini. Simpan mode-nya, terus `settings = settings_for_mode(settings, mode)` sebelum cek provider, `_require_script`, `check_voice`, dan `real_deps(settings)`. Run pertama (naskah belum ada) nggak sampai TTS, jadi aman.
- `real_deps.tts()` (`pipeline.py:118`): kalau `settings.elevenlabs_voice_id` kosong (misal `faktacuil_elevenlabs_voice_id` di-override kosong) → `PipelineError("config", "Voice ElevenLabs kosong. Isi elevenlabs_voice_id (FaktaCuil: faktacuil_elevenlabs_voice_id) di Settings.")` sebelum provider dibikin. Default Eric nggak kosong, jadi nggak kena.
- Cache pending TTS (`tts.py:62-65`) udah pakai identity voice/model/tag, jadi pending top3 nggak bakal kepakai buat FaktaCuil.
- Sampel voice: CLI kecil `mayzfact voice-sample` (bagian 8, plan Task 2).

### plan (`mayzfact/steps/plan.py`)
- `cta_beat_indices(beats)` di `plan.py:181-184` dan `plan.py:196` diganti `cta_indices(script)`: dispatcher di `mayzfact/narration.py` yang balikin `cta_beat_indices` buat top3 dan `faktacuil_cta_indices` buat FaktaCuil.
- `settings_for_mode` maksa `hook_seconds=0` buat FaktaCuil, jadi `run_plan` nggak bikin segmen hook (`plan.py:185`). Semua shot pakai `queries`/`queries_zh` beat-nya sendiri, dan `hook_queries` FaktaCuil selalu `{}`. Alasannya: hook FaktaCuil cuma 1 kalimat tanya (±3 detik). Kalau `hook_seconds` tetap 10, ±40% video ngambil keyword dari transcript source dan `queries` beat-nya nggak kepake.
- `settings_for_mode` juga nurunin `max_shot_seconds` ke `faktacuil_max_shot_seconds` = 2,0 (MayzFact 4,0). `real_deps.plan` baca `settings.max_shot_seconds`, jadi cukup ganti Settings-nya. Alasannya: referensi ganti klip tiap 1–2,5 detik (jawaban Q8, Akmal 2026-11-10). Akibatnya link per video lebih banyak dari top3.
- Frame referensi tiap shot pakai `subject_ranges` atau posisi proporsional (`plan.py:132-134`). `source_rank` selalu `None`. Step source tetap bikin frame `seg_*` karena mode belum ketahuan di sana; frame itu nggak dipakai.
- Shot CTA tetap `auto_cta: true` (`plan.py:220-223`), jadi brief/fetch otomatis nanganinnya.

### brief (`mayzfact/brief/`)
Nggak berubah. Brief cuma baca `shots_plan.json` (grup `HOOK`, `AUTO CTA`, per subjek). Badge `CARD #` (`mayzfact/brief/page.py:2063`) nggak muncul karena `countdown` selalu `None`.

### fetch (`mayzfact/steps/fetch.py`)
Nggak berubah. Shot `auto_cta` pakai ulang video sebelumnya (`mayzfact/cta_background.py`).

### timeline (`mayzfact/steps/timeline.py`, `mayzfact/cta_scene.py`, `mayzfact/audio.py`, `mayzfact/pipeline.py`)
Mode dibaca dari `script["narration_mode"]` di `build_timeline` (`timeline.py:416`). Cabang FaktaCuil:

| Bagian | top3 (tetap) | FaktaCuil |
|---|---|---|
| Card countdown (`_countdown`, `timeline.py:107`) | jalan | otomatis kosong (F2 nolak beat countdown) |
| Caption (`_captions`, `timeline.py:156`) | putih, kata panjang/subjek diwarnai cyan/hijau/kuning (`timeline.py:31-32,169-172`) | putih `#ffffff` (`CAPTION_WHITE`), kata `keyword` per beat kuning brand `#FFC53D`, kata lain nggak diwarnai. Teks tetap kapital. |
| Prop style | nggak ada | `"captionStyle": "faktacuil"` di root `timeline.json` |
| CTA click (`_top3_cta`, `timeline.py:347`) | like + subscribe Inggris | fungsi baru `_faktacuil_cta`: cuma like, pemicu `id_like_positions`, berhenti di `stop` scene. Dipakai buat click SFX. |
| Scene CTA (`build_scene`, `mayzfact/cta_scene.py:12`) | blok `cta_beat_indices`, berhenti di Number one (`cta_scene.py:23-26`) | blok `faktacuil_cta_indices`, berhenti di shot pertama beat setelah blok. Cue like pakai `id_like_positions`, mundur ke `tekan/pencet/klik` lalu `coba`. Cue transform tetap dari `transform_word`. |
| Emoji (`_emojis`) | dari marks | `marks` nggak dibikin, jadi kosong |
| Panah (`_overlays`) | dari OWLv2 | `overlays` nggak dibikin, jadi kosong |
| Intro whip (`timeline.py:497`) + SFX `hook` (`timeline.py:214`) | jalan | mati: `intro: None`, SFX `hook` nggak ditambah |
| Flash + SFX `hook_cut`/`hook_extra_*` (`timeline.py:241-247`) | di dalam hook | mati: `hook_end` dipaksa 0, jadi semua pergantian klip dapat `cut` + 1 SFX `extra_*` acak (SFX transisi tetap) |
| Magic reveal + `item_reveal` | setelah card | otomatis nggak ada (nggak ada card) |
| BGM | `mystery.mp3` hook + `main.mp3` dari Number pertama + riser | 1 lagu dari awal sampai akhir (bawah) |
| Blur teks klip (`_add_blurs`) | jalan | jalan (keputusan 4) |

**Pipeline** (`pipeline.py:321-333`): kalau mode FaktaCuil, `deps.marks` dan `deps.overlay` nggak dipanggil. Selain ngikutin keputusan 4, ini ngelewatin deteksi OWLv2 ±3 menit.

**BGM** (`mayzfact/audio.py:109`): `prepare_audio` baca `script["narration_mode"]`. Buat FaktaCuil:
- Folder lokal `assets/channels/faktacuil/bgm/`, di-gitignore (`.gitignore` tambah `assets/channels/faktacuil/bgm/`).
- Ambil file audio pertama (urut nama, ekstensi lewat `list_bgm`) di folder itu. Folder kosong, nggak ada, atau cuma berisi non-audio → pakai `assets/bgm/main.mp3` + log `[timeline] BGM FaktaCuil belum ada di assets/channels/faktacuil/bgm/, sementara pakai main.mp3`. `main.mp3` juga nggak ada → tanpa BGM + log. Lebih dari 1 file → pakai yang pertama + log semua nama. Lagu yang dipilih Akmal: Bully "Welcome to Bullworth" (117,5 BPM); Akmal/lead yang naruh file-nya, agent nggak download atau copy.
- Hasilnya `{"bgm": None, "bgm_main": <file>}`, jadi `_sound` masuk cabang 1 BGM sepanjang video (`timeline.py:210-212`) tanpa riser. Nggak ada kode `_sound` baru buat BGM.
- `audio.json` FaktaCuil: `{"bgm": null, "bgm_main": "<nama file yang dipakai>"}`. Top3 tetap `{"bgm": ...}` kayak sekarang.

### Remotion (`remotion/src/`)
- `fonts.ts`: tambah `FREDOKA` dari `@remotion/google-fonts/Fredoka` weight `700` (package udah ada, versi 4.0.538, `Fredoka.mjs` ada di checkout utama). Nggak nambah dependency.
- `types.ts` (`TimelineProps`, `types.ts:107`): tambah `captionStyle?: 'faktacuil'`.
- `ShortVideo.tsx:15,45`: terusin `captionStyle` ke `<Captions>`.
- `Captions.tsx`: kalau `style === 'faktacuil'`:
  - font `FREDOKA` 700, isi `caption.color`, outline hitam (`WebkitTextStroke` + `paintOrder`), drop shadow kanan bawah,
  - animasi pop tanpa blur: scale 0.6 → 1.12 → 1 dalam 5 frame, opacity 0 → 1 dalam 2 frame,
  - posisi tetap `top: 75%`,
  - font size turun otomatis biar kata panjang Indonesia ("membersihkannya") muat di lebar 960 px, tetap 1 baris. Rumusnya ditentuin implementer, dicek pakai `npx remotion still`.
  - Tanpa `captionStyle`, komponen persis kayak sekarang (Anton, motion blur).
- `CtaScene.tsx`: nggak berubah. Stage-nya cuma `like` + `transform` karena timeline nggak bikin cue subscribe/comment. Tulisan "LIKE" tetap English (kata "like" emang dipakai di naskah Indonesia).
- `Intro.tsx`, `Emojis.tsx`, `Overlays.tsx`, `NumberCard.tsx`: nggak berubah; prop-nya kosong.

### render (`mayzfact/steps/render.py`)
Nggak berubah. `video_speed` 1.1 dipakai dua format. Kalau sampel nunjukin tempo Indonesia kecepetan di 1.1, itu jadi keputusan Akmal (Q2), bukan ganti otomatis.

### upload, login, next-slot (`mayzfact/youtube.py`, `mayzfact/cli.py`, `mayzfact/config.py`)
- **Secret baru:** `YOUTUBE_TOKEN_JSON_FAKTACUIL` → `Settings.youtube_token_json_faktacuil` (`ENV_FIELDS`, `config.py:61-66`), `repr=False`. Client secret OAuth tetap `YOUTUBE_CLIENT_SECRET_JSON` yang sama.
- **Setting biasa baru:**
  - `faktacuil_slot_hours: tuple[int, ...] = (12, 18)` (final, Akmal 2026-11-10: 12.00 dan 18.00 WIB, maksimal 2 video per hari; `next_slot` ngurutin jam dulu),
  - `faktacuil_youtube_channel_id: str = ""` (ID channel FaktaCuil, `UC...`, bukan rahasia; diisi Akmal lewat kode `Settings` setelah login).
- **Login:** `mayzfact login youtube --channel faktacuil` nyimpen token ke `YOUTUBE_TOKEN_JSON_FAKTACUIL` (`youtube.login(..., token_env=...)`, yang sekarang balikin token-nya, jangan di-print). Setelah token kesimpen, CLI nge-print judul + ID channel dari `youtube.channel_info` (`channels().list(part="id,snippet", mine=True)`), biar Akmal bisa ngecek akunnya bener dan ngisi `faktacuil_youtube_channel_id`. Tanpa `--channel` perilakunya sama kayak sekarang.
- **Upload** (`cli.py`, `youtube.upload_video`): mode dibaca dari `runs/<id>/script.json` mentah lewat `youtube.run_mode` (tanpa file = top3, file rusak atau mode tak dikenal = error). Buat FaktaCuil, urutannya:
  1. `faktacuil_youtube_channel_id` nggak kosong (cek sebelum service dibikin), token `youtube_token_json_faktacuil` kebaca,
  2. `upload.json` wajib `language: "id"`,
  3. service dibikin, lalu sebelum `videos().insert`, `channel_info(service)` harus balikin ID yang sama dengan `faktacuil_youtube_channel_id`. ID kosong atau beda → `PipelineError`, nggak upload. Upload nggak bisa ditarik, jadi cek akun ini wajib,
  4. `youtube.json` dapat field `"channel": "faktacuil"`.
  
  Top3: token, body, dan isi `youtube.json` sama persis kayak sekarang (tanpa field `channel`).
- **Slot:** `next_slot(taken, now, hours=SLOT_HOURS)` (`youtube.py:155`) dapat parameter jam. `taken_slots(runs_dir, channel)` (`youtube.py:144`) nyaring `youtube.json`: channel `faktacuil` cuma ngitung file dengan `"channel": "faktacuil"`, channel `mayzfact` ngitung file tanpa field `channel` (semua upload lama). CLI `next-slot --channel faktacuil` pakai `settings.faktacuil_slot_hours`; tanpa flag tetap 01.00/04.00.
- **Metadata:** aturan nulis `upload.json` FaktaCuil ada di skill (plan Task 13). Kode cuma maksa `language: "id"`.

## 7. Cara top3 dijaga nggak berubah

1. **Cabang di satu tempat per step.** Semua kode FaktaCuil masuk `mayzfact/faktacuil.py` atau cabang `if mode == "faktacuil"`. Kode top3 yang ada nggak di-refactor selain ekstraksi `_beat_problems` (script.py) dan dispatcher `cta_indices`.
2. **Test golden sebelum ngubah apa pun** (plan Task 1): simpan output top3 dari kode sekarang ke `tests/golden/`:
   - `build_timeline` dari `timeline_fixture` (`tests/test_cta_scene.py`) dan dari `top3_script()` + `fake_alignment`,
   - `check_script` (daftar pesan) buat `top3_script()` valid dan beberapa varian invalid yang udah ada di test,
   - `run_plan` dari fixture `tests/test_top3_plan.py` (tanpa path absolut).
   
   Test-nya bandingin JSON persis. Golden nggak boleh di-regenerate di task lain; kalau beda, berarti top3 berubah.
3. **Upload/slot top3:** test yang ada (`tests/test_youtube.py:91-101`, `tests/test_cli.py:191`) tetap hijau tanpa diubah. Tambah test: `youtube.json` top3 nggak punya key `channel`; slot MayzFact nggak keblok `youtube.json` FaktaCuil.
4. **Remotion:** tanpa `captionStyle`, `Captions` render persis sama. Dicek pakai `npx remotion still` frame caption top3 sebelum/sesudah (butuh `npm ci` di worktree, Node 22).
5. **Full suite** `uv run pytest -q` di akhir tiap task. Baseline worktree ini: 688 lolos, 1 gagal (`test_cta_visual_markup_cases_run_in_node`, `remotion/node_modules` belum ada, sama kayak R7 spec D-050), 3 skip, 4 deselect. Setelah Task 12: 794 lolos, 3 skip, 4 deselect, 0 gagal (`npm ci` udah jalan di Task 11, jadi test node ikut lolos).

## 8. Sampel voice (keputusan 6)

- CLI baru `mayzfact voice-sample <voice_id> --name <slug>`: 1 request ElevenLabs (`eleven_v3`, stability 0.5, tanpa tag) dengan teks sampel tetap `VOICE_SAMPLE_TEXT_ID`, simpan ke `cache/voice-samples/<slug>.mp3` (cache di-gitignore). Kalau file udah ada → error, nggak request ulang. Print jumlah karakter, durasi, dan kata/detik mentah.
- Teks sampel (±40 kata, nyampur hook, salah kaprah, CTA, jawaban), ditulis di `mayzfact/faktacuil.py`:

  > Kenapa kucing suka banget masuk ke kardus? Padahal kardus itu sempit dan nggak empuk. Tapi coba tekan like dulu, apakah like-mu berubah jadi madu? Ternyata ruang sempit bikin kucing merasa lebih aman, jadi dia bisa santai tanpa takut diganggu.

  Ini teks uji suara, bukan naskah video.
- **Implementer cuma bikin CLI + test pakai fake provider.** Generate 3 sampel beneran dijalanin lead, setelah ada 3 voice ID (Q1).
- Setelah Akmal milih: Eric (`cjVigY5qzO86Huf0OWal`) dan `FAKTACUIL_RAW_WPS = 2.27` (sampel 40 kata, 17,60 detik, `eleven_v3`, stability 0.5, tanpa tag) udah masuk kode dan dicatat di D-051.

## 9. Risiko

- **R1. Detektor CTA kebawa ke top3.** `mayzfact/cta.py` dipakai top3 di 4 tempat. Detektor Indonesia ditaruh di `mayzfact/faktacuil.py`, bukan di `cta.py`, biar `LIKE_BEFORE` nggak kesentuh.
- **R2. `build_scene` dapat cabang.** `cta_scene.py` file top3 yang sensitif (timing cue, label `word`/`structure`). Cabang cuma di 4 titik: `allowed`, `stop`, deteksi cue like + lookback, dan loop `bounds` (`cta_scene.py:49-58`) yang sekarang pakai `cta_kinds` Inggris. Di FaktaCuil, loop itu pakai `id_like_positions` + regex `transform_word`. Golden `timeline_fixture` jagain top3.
- **R3. `keyword` di top3.** Field baru di `Beat` default kosong. Top3 nolak kalau diisi. Run top3 yang ada nggak punya field ini.
- **R4. Tempo Indonesia baru dari 1 sampel.** `FAKTACUIL_RAW_WPS` 2,27 dari sampel Eric (40 kata, 17,60 detik). Kalau naskah beneran jauh beda tempo, rentang 50–74 kata geser; `check_voice` ngasih peringatan kalau estimasi di luar 20–30 detik.
- **R5. Salah akun YouTube.** Google OAuth gampang kepilih akun/brand account yang salah. Cek `channels().list(mine=True)` vs `faktacuil_youtube_channel_id` sebelum upload. Login cuma bisa dijalanin Akmal (browser).
- **R6. Font render butuh internet.** `@remotion/google-fonts` ambil font pas render, sama kayak Anton sekarang. Bukan risiko baru.
- **R7. Kata panjang Indonesia di caption.** 1 kata per tampilan + font auto-kecil. Kalau masih kepotong, baru pertimbangin wrap.
- **R8. Remotion test butuh `node_modules`.** Worktree belum punya. Task Remotion jalanin `npm ci` dulu (Node 22).
- **R9. Rawan conflict merge:** `mayzfact/config.py` (plan Task 6, 12), `mayzfact/cli.py` (Task 2, 12), `mayzfact/pipeline.py` (Task 6, 9), `mayzfact/steps/script.py`, `mayzfact/steps/timeline.py`, `AGENTS.md`, `docs/DECISIONS.md`, `docs/HANDOFF.md`. Rekomendasi: satu branch, task berurutan (plan).

**Belum dicek:** render FaktaCuil beneran, suara ElevenLabs Indonesia dalam naskah panjang (baru sampel 40 kata), cara ElevenLabs baca "like" dan "like-mu" di kalimat Indonesia, `login`/`upload` ke YouTube beneran (baru fake), VoiceStudio bahasa Indonesia (profil belum ada), caption Fredoka di atas klip beneran (still cuma di latar hitam, outline hitam nggak kelihatan).

## 10. Pertanyaan dan jawabannya

Status per 2026-11-10 (jawaban Akmal lewat lead; yang nggak ada jawabannya pakai default spec):

1. **Q1. Voice:** cowok. Akun ElevenLabs free, jadi cuma voice premade yang bisa lewat API. Dipilih **Eric** `cjVigY5qzO86Huf0OWal`. VoiceStudio juga didukung (profil bahasa Indonesia belum ada).
2. **Q2. Tempo:** `video_speed` tetap 1,1; panjang naskah yang ngikutin (`FAKTACUIL_RAW_WPS` 2,27, rentang 50–74 kata). Belum ada keputusan ganti speed khusus FaktaCuil.
3. **Q3. Source listicle:** pakai default spec (boleh ambil 1 item, semua fakta dari item itu). Belum ditegasin Akmal.
4. **Q4. Jam slot:** **12.00 dan 18.00 WIB, maksimal 2 video per hari.** Upload nggak tentu tiap hari, jadi `next-slot` cukup ambil slot kosong berikutnya.
5. **Q5. TikTok:** pakai default spec (nggak ada `tiktok.json` FaktaCuil). Belum ada jawaban Akmal.
6. **Q6. ID channel:** Akmal isi `Settings.faktacuil_youtube_channel_id` setelah `login youtube --channel faktacuil` nge-print ID-nya. Belum diisi.
7. **Q7. SFX CTA:** pakai default spec (`click` yang sama kayak MayzFact).
8. **Q8. Panjang shot:** ikut referensi, ±2 detik per klip: `faktacuil_max_shot_seconds = 2.0` (MayzFact tetap 4,0).

## 11. Yang diputusin architect (cek pas baca)

- Nama nilai `faktacuil` (bagian 4).
- `keyword` sebagai field baru di `Beat`, bukan diturunin dari `subject`. Alasannya: kata yang perlu ditekankan sering bukan subjek ("TERNYATA", "AMAN").
- Teks caption tetap kapital (referensi FaktaBor juga kapital).
- SFX `hook` (boom di frame 0) ikut mati bareng intro whip, karena bunyinya pasangan efek intro.
- Di dalam hook, pergantian klip pakai SFX `cut` biasa (bukan `hook_cut` kamera), karena `hook_cut` pasangan flash yang dimatiin.
- `hook_seconds=0` buat FaktaCuil (bagian 6 plan).
- Cek VoiceStudio cuma sebelum step tts, bukan di awal run.
- Struktur dicek posisinya aja (F4, F5). Kata pembuka "Padahal…"/"Ternyata…" cuma aturan di skill, nggak dicek kode, biar agent bebas variasi.
- Foto 15–45% tetap berlaku.
- Watermark nggak di dalam video.

## 12. Pilihan yang ditolak

- **Registry format / class `Format` dengan method per step.** Cuma 2 format. Cabang `if` di ±8 titik lebih gampang dibaca dan nggak nambah layer (sesuai D-050 poin c).
- **Detektor like Indonesia digabung ke `LIKE_BEFORE` di `cta.py`.** Bisa bikin kalimat Inggris kebaca CTA ("press" vs "tekan" aman, tapi daftar campur susah dites dua arah). Keputusan 3 juga minta terpisah.
- **`comment_text` dibikin opsional di `CtaScene` + validator per mode.** Ngubah schema top3 dan pesan error-nya. Field yang nggak kepakai di FaktaCuil lebih murah dari risiko itu.
- **CTA ditandain manual pakai field `cta: true` per beat.** Lebih gampang dideteksi, tapi tetap butuh detektor kata buat timing klik, jadi dua sumber kebenaran.
- **Ngecek kata pembuka struktur ("Padahal", "Ternyata") di kode.** Terlalu kaku buat bahasa santai.
- **Caption style per kata (`Caption.style`).** Style berlaku satu video, cukup 1 prop di root.
- **Channel disimpan di `youtube.json` semua run (termasuk MayzFact).** Bikin isi `youtube.json` top3 berubah. Tanpa field = MayzFact udah cukup.
- **Dua BGM (mystery + main) kayak top3.** Keputusan 7: 1 lagu sepanjang video.
- **CLI sampel voice dilewat, lead jalanin skrip sekali pakai.** Skrip tanpa test gampang ke-run dua kali dan bayar dua kali. CLI-nya kecil, nolak nimpa file, dan bakal kepake lagi kalau voice diganti.


## 13. Deviasi implementasi dari draft awal (2026-11-10)

Hal yang dibangun beda dari draft architect. Yang bagian lain di spec ini udah diupdate; daftar ini buat yang nggak kelihatan dari satu bagian aja.

- **Voice dan TTS:** default `faktacuil_elevenlabs_voice_id` Eric (bukan string kosong). FaktaCuil juga bisa VoiceStudio lewat `faktacuil_tts_provider` / `faktacuil_voicestudio_voice` / `faktacuil_voicestudio_instruct` (draft: FaktaCuil cuma ElevenLabs). `_require_script` nolak FaktaCuil + VoiceStudio kalau `faktacuil_voicestudio_voice` kosong, bukan nolak VoiceStudio sama sekali.
- **`settings_for_mode` ganti lebih banyak field:** `tts_provider`, `voicestudio_voice`, `voicestudio_instruct`, `max_shot_seconds` (2,0), selain voice id, delivery tag, dan `hook_seconds`. `tts_provider` global MayzFact nggak kebawa ke FaktaCuil.
- **`video_speed`:** `__post_init__` `Settings` nge-bump 1,1 jadi 1,15 kalau provider voicestudio, dan `replace()` ikut kena. `settings_for_mode` nurunin balik ke 1,1 kalau 1,15 itu hasil bump MayzFact voicestudio sementara FaktaCuil pakai ElevenLabs. 1,15 yang di-set eksplisit nggak bisa dibedain dari hasil bump, jadi ikut turun; override lain (misal 1,2) kebawa.
- **Tempo:** `FAKTACUIL_RAW_WPS` 2,27 (draft 2,5); rentang kata 50–74 (draft 55–82). `faktacuil_word_range` ngebulatin ke 6 desimal sebelum `ceil`/`floor`.
- **`cta_indices`:** baca `narration_mode` pakai `.get` (script dict tanpa field itu dianggap top3), karena ada test plan top3 tanpa `narration_mode`.
- **Timeline:** `build_timeline` ngabaikan `marks`/`overlays` yang dikirim dari luar untuk FaktaCuil (draft: cuma pipeline yang nggak manggil). `hook_end` dipaksa 0 walau `clips.json` punya `hook_segment`.
- **BGM:** folder lokal ada tapi isinya non-audio = fallback `main.mp3`. `main.mp3` juga nggak ada = tanpa BGM + log, `audio.json` `{"bgm": null, "bgm_main": null}`.
- **Login/upload:** `youtube.login` balikin token (draft: `None`) biar CLI bisa nge-print channel tanpa baca `.env`. `channel_info` pakai `part="id,snippet"`. `youtube.run_mode(paths)` baca `script.json` mentah dan melempar error kalau file rusak atau mode di luar `top3`/`faktacuil` (nebak top3 dari file rusak bisa nge-upload video FaktaCuil ke channel MayzFact). Tanpa `script.json` = top3, jadi run lama tetap bisa upload.
- **Test lama yang berubah:** `tests/test_config.py::test_env_holds_only_secrets` (set `ENV_FIELDS` nambah `YOUTUBE_TOKEN_JSON_FAKTACUIL`). Sisanya nggak diubah, golden top3 nggak di-regenerate.
- **Masih kebuka:** `service()` (token ditolak/kosong) pakai `LOGIN_HINT` MayzFact ("login youtube" tanpa `--channel`). Buat token FaktaCuil, pesan yang bener ada di cek token kosong di CLI; pesan "Token YouTube ditolak" masih nyebut perintah tanpa `--channel`.
- **Run baru FaktaCuil** jalanin step `source` pakai `hook_seconds` 10 (naskah belum ada, mode belum ketahuan), jadi `source.mp4` ke-download walau nggak dipakai.
