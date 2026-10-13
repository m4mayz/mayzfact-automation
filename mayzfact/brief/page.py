"""HTML halaman brief: kartu per shot, keyword yang bisa di-copy, input link/upload, status fetch."""

from __future__ import annotations

import json
from html import escape

_CSS = """
body{font-family:system-ui,sans-serif;margin:0;background:#f4f4f5;color:#18181b}
header{position:sticky;top:0;background:#18181b;color:#fff;padding:12px 16px;display:flex;gap:16px;align-items:center;z-index:2}
header button{padding:8px 16px;font-size:15px;cursor:pointer}
main{max-width:980px;margin:0 auto;padding:16px;display:grid;gap:12px}
.card{background:#fff;border-radius:10px;padding:14px;display:grid;gap:8px;box-shadow:0 1px 3px #0002}
.tag{font-size:12px;font-weight:700;padding:2px 8px;border-radius:99px;background:#e4e4e7}
.tag.hook{background:#fde68a}
.refs{display:flex;gap:6px}.refs img{height:160px;border-radius:6px}
.kw{display:flex;flex-wrap:wrap;gap:6px}.kw button{border:1px solid #d4d4d8;background:#fafafa;border-radius:6px;padding:3px 8px;cursor:pointer}
input[type=text]{width:100%;padding:8px;font-size:14px;box-sizing:border-box}
.state{font-size:13px}.state.ok{color:#15803d}.state.error,.state.missing{color:#b91c1c}.state.warn{color:#b45309}
"""

_JS = """
const plan = PLAN;
async function save(){
  const shots = {};
  document.querySelectorAll('[data-shot]').forEach(card => {
    const n = card.dataset.shot, url = card.querySelector('.url').value.trim(), file = card.querySelector('.file').value;
    if (url) shots[n] = {url}; else if (file) shots[n] = {file};
  });
  const res = await fetch('/api/links', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({shots})});
  const data = await res.json();
  document.getElementById('msg').textContent = res.ok ? `Tersimpan. Kosong: ${data.missing.join(', ') || '-'}` : data.error;
  if (res.ok) setTimeout(() => location.reload(), 600);
}
async function upload(n, input){
  const file = input.files[0]; if (!file) return;
  const res = await fetch(`/api/upload?shot=${n}`, {method:'POST', headers:{'X-Filename': encodeURIComponent(file.name)}, body:file});
  const data = await res.json();
  document.getElementById('msg').textContent = res.ok ? `Shot ${n}: ${data.file} ke-upload` : data.error;
  if (res.ok) setTimeout(() => location.reload(), 600);
}
function copyText(t){ navigator.clipboard.writeText(t); document.getElementById('msg').textContent = `Ke-copy: ${t}`; }
"""


def _card(shot: dict, entry: dict, state: dict) -> str:
    number = shot["index"] + 1
    is_hook = shot["hook_segment"] is not None
    refs = "".join(f'<img src="/files/{escape(f)}" loading="lazy">' for f in shot["ref_frames"])
    keywords = "".join(
        f'<button type="button" onclick=\'copyText({escape(json.dumps(k), quote=True)})\'>{escape(k)}</button>'
        for lang in ("en", "zh") for k in shot["keywords"].get(lang, [])
    )
    url_value = escape(entry.get("url", "") + (f" #{entry['pick']}" if entry.get("pick") else ""), quote=True)
    file_value = escape(entry.get("file", ""), quote=True)
    css = state.get("state", "missing" if not entry else "")
    if css == "ok" and state.get("message"):
        css = "warn"
    label = {"ok": "OK", "warn": "OK", "error": "GAGAL", "missing": "KOSONG"}.get(css, "TERSIMPAN")
    message = escape(state.get("message", "") or ("file: " + entry["file"] if entry.get("file") else ""))
    return f"""
<section class="card" data-shot="{number}">
  <div><b>Shot {number}</b> · {shot['start_s']:.1f}–{shot['end_s']:.1f}s ·
    <span class="tag {'hook' if is_hook else ''}">{'HOOK' if is_hook else 'ISI'}</span>
    · {escape(shot['media'])} · subjek: <b>{escape(shot.get('subject') or '-')}</b></div>
  <div>{escape(shot['text'])}</div>
  {f'<div class="refs">{refs}</div>' if refs else ''}
  <div class="kw">{keywords or '<i>tanpa keyword</i>'}</div>
  <input class="url" type="text" placeholder="Link Douyin/RedNote/TikTok/Pinterest/URL langsung (opsional: #3 buat foto ke-3)" value="{url_value}">
  <input class="file" type="hidden" value="{file_value}">
  <div>Atau upload: <input type="file" accept="video/*,image/*" onchange="upload({number}, this)"></div>
  <div class="state {css}">{label} {message}</div>
</section>"""


def render_page(run_id: str, plan: dict, links: dict, status: dict) -> str:
    entries = links.get("shots", {})
    states = status.get("shots", {})
    filled = sum(1 for shot in plan["shots"] if entries.get(str(shot["index"] + 1)))
    cards = "".join(
        _card(shot, entries.get(str(shot["index"] + 1), {}), states.get(str(shot["index"] + 1), {})) for shot in plan["shots"]
    )
    return f"""<!doctype html>
<html lang="id"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Brief {escape(run_id)}</title><style>{_CSS}</style></head>
<body><header><b>Brief {escape(run_id)}</b><span>{filled}/{len(plan['shots'])} terisi</span>
<button onclick="save()">Simpan</button><span id="msg"></span></header>
<main>{cards}</main>
<script>const PLAN = {json.dumps({'count': len(plan['shots'])})};{_JS}</script></body></html>"""
