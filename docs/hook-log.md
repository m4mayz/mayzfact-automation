# Hook log — hook vs retensi

Tujuan: tiap video, catat 3 beat pertama + retensi, biar hook bisa dibandingin. Data dari `yt_retention.py` (YouTube Analytics, dicek 2026-10-21). Retensi = % penonton yang masih nonton di detik itu.

## Retensi (pembacaan terdekat dari kurva)

| run | video | durasi | ~10 dtk | ~25 dtk | akhir | avg view |
|---|---|---|---|---|---|---|
| piD9Fjp-mG8 | Two Heads | 63s | 100% | 75% | 46% | 75% |
| ydA5gOdKvfc | Unexpected Moments | 34s | 71% | 50% | 32% | 66% |
| XUxt7H7b01I | White Animals | 70s | 73% | 46% | 26% | 48% |
| WHM6ID-p5iQ | Ocean Predators | 76s | 85% | 67% | 15% | 54% |
| 4735ZE89GXQ | Unreal Features | 59s | 76% | 43% | 18% | 44% |
| i2xag_1OJfM | Ancient Creatures | 50s | 65% | 35% | 19% | 45% |
| NSua7RPoFJg | Birds | 52s | 62% | 30% | 20% | 43% |

Belum ada data: PPZhbe711qg (Cat Breeds), WrEQDprW_cc (Disappear), xc_xDyPY01U (Sci-Fi). Ocean Predators baru 90 views di window analytics, jadi angkanya rapuh.

## Hook, 3 beat pertama

### Two Heads (retensi tertinggi)
1. "Every animal here was born with two heads." — klaim konkret, klip langsung terlihat aneh
2. "And wait till you see number one." — open loop
3. "Its two heads can react on their own." — teaser spesifik + emoji
4. CTA di beat 4-5, retensi tetap 100% di dtk 9.

### Birds (retensi terendah)
1. "Five crazy birds have real superpowers!" — abstrak, klip stok burung biasa
2. "Number one looks totally impossible." — open loop kosong (apa yang impossible?)
3. "Drop a comment, then hit subscribe!" — CTA nongol sebelum ada alasan bertahan
4. Item #5 dibuka foto potret diam.

## Hipotesis (dari 2 naskah, belum terbukti)
1. Beat 1 sebut hal konkret yang aneh, bisa langsung divisualkan.
2. Beat 2 open loop yang spesifik.
3. Beat 3 teaser visual item #1.
4. CTA sesudah beat 3/4, bukan sebelum. Posisi CTA bukan penyebab utama: Two Heads aman dengan CTA di awal.
5. Klip beat 1-3 video bergerak, bukan foto potret.

Birds ditulis ulang pakai rumus ini (contoh, belum dipakai):
1. "These birds walk underwater, drop bones from the sky, and freeze in midair."
2. "Number one doesn't flap its wings at all."
3. "Hold on, because number five is a bird diving like a scuba diver."
4. "Comment which one is wildest, then hit subscribe!"

## Cara pakai
Tiap video baru: tambah baris di tabel + 3 beat pertama. Kalau 2-3 video berikutnya pakai rumus ini dan retensi ~10 dtk tidak naik di atas ~75%, buang hipotesisnya. Kalau drop 5-10 dtk masih >25 poin, pertimbangkan pindah CTA (lihat D-035).

## FaktaCuil: retensi vs CTA (dicek 2026-11-24)

Data YouTube Analytics API: `audienceWatchRatio` + `relativeRetentionPerformance` per `elapsedVideoTimeRatio` (filter `video==<id>`), dicocokin ke detik kata di `runs/<id>/timeline.json`. Detik di bawah = detik timeline (final dirender 1,1×, posisi relatifnya sama). Analytics telat ±2 hari.

| run | video | CTA | CTA mulai | drop terbesar | rel. retensi 3 dtk | avg view | meledak hari pertama |
|---|---|---|---|---|---|---|---|
| LVp0vwcAYl0 | Kucing masuk celah | v1 cat | 5,8 | 7-8 dtk, -18 | 0,82 | 103% | hari ke-2 |
| Dssgofzoom8 | Lomba peluk ikan | v1 shark | 8,5 | 10-11 dtk, -17 | 0,79 | 107% | nggak |
| gu2M14rfRlU | Rumah Jepang | v1 volcano | 12,2 | 13-14 dtk, -13 | 0,51 | 90% | nggak |
| gNA8gTQriOQ | Lidah kucing | v1 lion | 9,5 | 11-12 dtk, -12 | 0,60 | 91% | nggak |
| k4q6JQCQxSs | Kucing manis | v1 honey | 6,3 | 7-8 dtk, -11 | 0,56 | 93% | nggak |
| q3QsqNQxqUc | Kucing & anjing minum | v1 puppy | 9,2 | 11-12 dtk, -8 | 0,73 | 112% | ya (31k/7 jam) |
| pJe_Qok8qDA | Topi renang | escalate | 11,1 | 12-13 dtk, -7 | 0,81 | 105% | ya (30k/3 jam) |
| 6y6YTamrghQ | Snack Jepang | escape | 8,2 | 6-7 dtk, -8 | 0,60 | 94% | nggak |
| xRdCrossVN1 | Nyebrang Vietnam | escape | 5,4 | 6-7 dtk, -9 | 0,70 | 103% | ya (31k/7 jam) |
| nuVqCHEpzG0 | Pagar ayam | tanpa | - | 5-6 dtk, -6 | 0,86 | 112% | 8,7k/7 jam |

Temuan:
1. CTA v1 ("apakah like-mu berubah jadi X?"): drop terbesar video jatuh 1-2 dtk setelah ajakan like, -11 sampai -18 poin dalam sedetik. `escape`/`escalate`/tanpa CTA cuma -6 sampai -9.
2. Video yang langsung meledak: rel. retensi 3 dtk >= 0,70 dan avg view > 100%. Yang lambat kebanyakan 0,51-0,60 dan < 95%.
3. Demografi (umur, gender, negara) sama di semua video, views dari subscriber < 0,5%. Yang nentuin cuma reaksi di batch tes awal.

Belum terbukti: format v2 `lucky`/`subscribe` ("siapa tahu muncul cabai ini") polanya mirip v1. Cek ulang 2026-11-27 pas data BMW (`IeeRKhqFYzI`, subscribe) dan Pedas (`gv6ZaNv9CH4`, lucky) masuk. Kalau drop-nya juga >= -11 sesudah ajakan like, pertimbangkan CTA `emoji` di akhir atau tanpa CTA.

### Cek ulang 2026-11-27

CTA tengah v2 kena pola yang sama kayak v1, lebih parah:

| run | video | CTA | "LIKE" mulai | drop terbesar | rel. retensi 3 dtk | avg view | views |
|---|---|---|---|---|---|---|---|
| IeeRKhqFYzI | Logo BMW | subscribe | 6,2 | 6-7 dtk, -24 | 0,43 | 77% | 8,5k |
| gv6ZaNv9CH4 | Pedas | lucky | 6,8 | 7-8 dtk, -14 | 0,46 | 74% | 2,6k |

Video tanpa CTA di periode yang sama: Geta 36,5k (109%), Anjing julurin lidah 31,7k (±10 jam), Madu 31,3k (92%), Atap resin 28,2k (93%), Pagar ayam 20,2k (111%), Sourdough 3,9k (106%).

Catatan:
1. Hook BMW dan Pedas juga lemah (rel. 3 dtk < 0,5, diukur sebelum CTA), jadi efek hook dan CTA belum kepisah.
2. Drop tajam bisa muncul tanpa CTA (Madu -11 di 6-7 dtk), tapi di BMW/Pedas jatuh tepat 1 dtk setelah "LIKE".
3. Sourdough: retensi bagus, engaged ±50%, "Viewed vs swiped away" di Studio 77,7%, tapi berhenti di batch tes (1.992 → 770 → 423 views/hari). Nggak ada metrik yang jelasin; dugaan topik niche atau faktor acak.
4. Video lambat bisa meledak telat: Geta dan Madu masih 2k / 0,6k di hari pertama, 3 hari kemudian di atas 30k. Jangan nilai video sebelum umur 3 hari.

Saran: stop CTA tengah (`lucky`/`subscribe`) dulu. Pakai tanpa CTA atau CTA di akhir (`emoji_question`, mulai `gjan1G-i2sI`), terus bandingin retensinya.
