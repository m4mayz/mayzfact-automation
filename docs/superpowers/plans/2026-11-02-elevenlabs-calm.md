# Plan — ElevenLabs calm delivery

Desain bounded sudah disetujui pada delegasi; kontrak di [spec](../specs/2026-11-02-elevenlabs-calm-design.md). Semua perubahan dibiarkan uncommitted.

1. RED→GREEN: default `calm`/`0.5`, override lokal aman, voice/model tetap.
2. RED→GREEN: provider prefix request dan identity bersyarat tanpa mengubah hasil audio/raw alignment.
3. RED→GREEN: normalisasi exact character/start/end slicing setelah pending tersimpan; metadata provenance dan penolakan cache legacy/incompatible.
4. RED→GREEN: wiring Settings ke provider, caption/timing memakai original text; coverage included/omitted/no-tag/mismatch dan retry tanpa sintesis ulang.
5. Jalankan focused/full offline tests, Ruff F/I dan diff check; review inline. Update skill authoring, D-047 dan HANDOFF dengan bukti aktual. Tidak memanggil API, menulis setting lokal, mengubah runs, render, brief, commit atau push.
