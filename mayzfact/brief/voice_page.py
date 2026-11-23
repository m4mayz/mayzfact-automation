"""Halaman brief mode suara: teks naskah siap paste ke web ElevenLabs + upload hasilnya."""

from __future__ import annotations

from html import escape

CSS = """
:root { --bg-page:#f4f4f5; --bg-card:#fff; --border-card:#d4d4d8; --text-primary:#09090b; --text-muted:#52525b;
  --blue-main:#2563eb; --blue-hover:#1d4ed8; --green-main:#15803d; --red-main:#b91c1c; }
* { box-sizing:border-box; }
body { margin:0; background:var(--bg-page); color:var(--text-primary);
  font-family:-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; line-height:1.5; }
main { max-width:720px; margin:0 auto; padding:24px 16px 48px; }
h1 { font-size:1.25rem; margin:0 0 4px; }
.sub { color:var(--text-muted); margin:0 0 20px; }
section { background:var(--bg-card); border:1px solid var(--border-card); border-radius:8px; padding:16px; margin-bottom:16px; }
h2 { font-size:1rem; margin:0 0 8px; }
textarea { width:100%; min-height:180px; font:inherit; padding:10px; border:1px solid var(--border-card); border-radius:6px; resize:vertical; }
button, .file { display:inline-block; font:inherit; font-weight:600; padding:10px 16px; border-radius:6px; border:0;
  background:var(--blue-main); color:#fff; cursor:pointer; min-height:44px; }
button:hover, .file:hover { background:var(--blue-hover); }
button:focus-visible, .file:focus-within { outline:3px solid #93c5fd; outline-offset:2px; }
.file input { position:absolute; opacity:0; width:1px; height:1px; }
.hint { color:var(--text-muted); font-size:.9rem; margin:8px 0 0; }
audio { width:100%; margin-top:12px; }
#msg { margin-top:10px; font-weight:600; }
#msg.ok { color:var(--green-main); } #msg.err { color:var(--red-main); }
"""

JS = """
const msg = document.getElementById('msg');
function say(text, ok) { msg.textContent = text; msg.className = ok ? 'ok' : 'err'; }
document.getElementById('copy').addEventListener('click', async () => {
  const box = document.getElementById('text');
  try { await navigator.clipboard.writeText(box.value); say('Teks ke-copy.', true); }
  catch { box.select(); say('Copy otomatis nggak jalan, teksnya udah keblok. Copy manual ya.', false); }
});
document.getElementById('file').addEventListener('change', async (ev) => {
  const file = ev.target.files[0];
  if (!file) return;
  say(`Upload ${file.name}...`, true);
  try {
    const res = await fetch('/api/voice', {method: 'POST', body: file,
      headers: {'X-Filename': encodeURIComponent(file.name)}});
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || res.status);
    location.reload();
  } catch (err) { say(`Upload gagal: ${err.message}`, false); }
});
"""


def render_voice_page(video_id: str, text: str, upload: str | None) -> str:
    current = (f'<p class="hint">Udah ada: <b>{escape(upload)}</b>. Habis dicek, bilang ke agent buat lanjut '
               f'(<code>mayzfact run {escape(video_id)} --no-render</code>). Upload lagi buat ganti.</p>'
               f'<audio controls src="/files/{escape(upload)}"></audio>') if upload else (
        '<p class="hint">Belum ada file. Format: mp3, wav, atau m4a.</p>')
    return f"""<!doctype html>
<html lang="id"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Suara {escape(video_id)}</title><style>{CSS}</style></head>
<body><main>
<h1>Suara {escape(video_id)}</h1>
<p class="sub">Generate di web ElevenLabs pakai teks ini, terus upload hasilnya di sini.</p>
<section>
  <h2><label for="text">1. Teks naskah</label></h2>
  <textarea id="text" readonly>{escape(text)}</textarea>
  <button id="copy" type="button">Copy teks</button>
  <p class="hint">Voice dan model terserah. Stability yang biasa dipakai: 0.5 (Natural).</p>
</section>
<section>
  <h2>2. Upload suara</h2>
  <label class="file">Pilih file suara<input id="file" type="file" accept=".mp3,.wav,.m4a,audio/*"></label>
  {current}
  <p id="msg" role="status"></p>
</section>
</main><script>{JS}</script></body></html>"""
