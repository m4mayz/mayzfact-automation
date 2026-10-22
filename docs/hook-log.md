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
