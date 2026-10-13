"""HTML halaman brief: 1 kartu per kelompok konteks, keyword yang bisa di-copy, textarea link, upload, status fetch."""

from __future__ import annotations

import json
from html import escape

from mayzfact.manual.links import lines_of

_CSS = """
body{font-family:system-ui,sans-serif;margin:0;background:#f4f4f5;color:#18181b}
header{position:sticky;top:0;background:#18181b;color:#fff;padding:12px 16px;display:flex;gap:16px;align-items:center;z-index:2}
header button{padding:8px 16px;font-size:15px;cursor:pointer}
main{max-width:980px;margin:0 auto;padding:16px;display:grid;gap:12px}
.card{background:#fff;border-radius:10px;padding:14px;display:grid;gap:8px;box-shadow:0 1px 3px #0002}
.tag{font-size:12px;font-weight:700;padding:2px 8px;border-radius:99px;background:#e4e4e7}
.tag.hook{background:#fde68a}
.shots{margin:0;padding-left:18px;font-size:14px}.shots li{margin:4px 0}
.refs{display:flex;gap:6px;margin-top:4px}.refs img{height:120px;border-radius:6px}
.kw{display:flex;flex-wrap:wrap;gap:6px}.kw button{border:1px solid #d4d4d8;background:#fafafa;border-radius:6px;padding:3px 8px;cursor:pointer}
textarea{width:100%;min-height:72px;padding:8px;font-size:14px;box-sizing:border-box;font-family:inherit}
#progress{background:#fff;border-radius:10px;padding:12px 14px;box-shadow:0 1px 3px #0002;display:none;gap:6px}
#progress .bar{height:10px;background:#e4e4e7;border-radius:99px;overflow:hidden}#progress .bar div{height:100%;background:#2563eb;transition:width .4s}
#progress pre{margin:0;max-height:160px;overflow:auto;font-size:12px;background:#f4f4f5;padding:8px;border-radius:6px;white-space:pre-wrap}
.state{font-size:13px}.state.ok{color:#15803d}.state.error,.state.missing{color:#b91c1c}.state.warn{color:#b45309}
"""

_JS = """
async function save(){
  const groups = {};
  document.querySelectorAll('[data-group]').forEach(card => { groups[card.dataset.group] = card.querySelector('textarea').value; });
  const res = await fetch('/api/links', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({groups})});
  const data = await res.json();
  document.getElementById('msg').textContent = res.ok ? `Tersimpan. Kosong: ${data.missing.join(', ') || '-'}` : data.error;
  if (res.ok) setTimeout(() => location.reload(), 600);
}
async function upload(group, input){
  const file = input.files[0]; if (!file) return;
  document.getElementById('msg').textContent = `Upload ${file.name}...`;
  // Simpan isi textarea dulu, biar upload (yang nambah baris file:) nggak nimpa link yang belum di-Simpan.
  const groups = {};
  document.querySelectorAll('[data-group]').forEach(card => { groups[card.dataset.group] = card.querySelector('textarea').value; });
  const saved = await fetch('/api/links', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({groups})});
  if (!saved.ok) { document.getElementById('msg').textContent = (await saved.json()).error; return; }
  const res = await fetch(`/api/upload?group=${encodeURIComponent(group)}`, {method:'POST', headers:{'X-Filename': encodeURIComponent(file.name)}, body:file});
  const data = await res.json();
  if (!res.ok) { document.getElementById('msg').textContent = data.error; return; }
  location.reload();
}
const STATE_LABEL = {running: 'Lagi jalan', done: 'Selesai, siap review di Studio', awaiting: 'Berhenti: ada kelompok yang perlu diisi/diganti', failed: 'Berhenti karena error, cek terminal'};
let lastState = null;
function line(box, tag, text){ const el = document.createElement(tag); el.textContent = text; box.appendChild(el); return el; }
function bar(box, done, total){
  const outer = line(box, 'div', ''); outer.className = 'bar';
  line(outer, 'div', '').style.width = `${total ? Math.round(100 * (Number(done) || 0) / total) : 0}%`;
}
async function pollProgress(){
  try {
    const p = await (await fetch('/api/progress')).json();
    const box = document.getElementById('progress');
    if (p.state) {
      // Semua isi lewat textContent: label kelompok asalnya dari Gemini, jangan pernah jadi HTML.
      box.style.display = 'grid';
      box.replaceChildren();
      line(box, 'b', `Fetch: ${STATE_LABEL[p.state] || p.state}`);
      line(box, 'div', `Link ${p.links_done}/${p.links_total}`); bar(box, p.links_done, p.links_total);
      line(box, 'div', `Shot ${p.shots_done}/${p.shots_total}`); bar(box, p.shots_done, p.shots_total);
      if (p.current) line(box, 'div', `Sekarang: ${p.current}`);
      line(box, 'pre', (p.log || []).slice(-10).join('\\n'));
      if (lastState === 'running' && p.state !== 'running') location.reload();
      lastState = p.state;
    }
  } catch (e) {}
}
pollProgress(); setInterval(pollProgress, 2000);
function copyText(t){ navigator.clipboard.writeText(t); document.getElementById('msg').textContent = `Ke-copy: ${t}`; }
"""


def _shot_item(shot: dict) -> str:
    refs = "".join(f'<img src="/files/{escape(f)}" loading="lazy">' for f in shot["ref_frames"])
    return (
        f"<li><b>Shot {shot['index'] + 1}</b> · {shot['start_s']:.1f}–{shot['end_s']:.1f}s · {escape(shot['media'])} · "
        + (f"<span class=tag>CARD #{int(shot['countdown'])}</span> " if shot.get("countdown") else "")
        + f"{escape(shot['text'])}{f'<div class=refs>{refs}</div>' if refs else ''}</li>"
    )


def _card(group: dict, shots: list[dict], entries: list[dict], state: dict) -> str:
    is_hook = group["id"] == "hook"
    keywords = "".join(
        f'<button type="button" onclick=\'copyText({escape(json.dumps(k), quote=True)})\'>{escape(k)}</button>'
        for lang in ("en", "zh") for k in group["keywords"].get(lang, [])
    )
    css = state.get("state", "") if entries else "missing"
    if css == "missing" and entries:
        css = ""  # status lama dari fetch sebelumnya, sekarang udah diisi
    if css == "ok" and state.get("message"):
        css = "warn"
    label = {"ok": "OK", "warn": "OK", "error": "GAGAL", "missing": "KOSONG"}.get(css, "TERSIMPAN")
    message = escape(state.get("message", "") if css else "")
    refs = "".join(f'<img src="/files/{escape(f)}" loading="lazy">' for f in group.get("ref_frames", []))
    return f"""
<section class="card" data-group="{escape(group['id'], quote=True)}">
  <div><span class="tag {'hook' if is_hook else ''}">{escape(group['label'])}</span> · {len(shots)} shot</div>
  {f'<div>Frame dari source:</div><div class="refs">{refs}</div>' if refs else ''}
  <ul class="shots">{''.join(_shot_item(s) for s in shots)}</ul>
  <div class="kw">{keywords or '<i>tanpa keyword</i>'}</div>
  <textarea placeholder="1 baris = 1 link Douyin/TikTok/Pinterest/URL langsung (RedNote: upload file). Boleh lebih dari 1. Tambah ' #3' buat foto ke-3.">{escape(lines_of(entries))}</textarea>
  <div>Upload file: <input type="file" accept="video/*,image/*" onchange="upload({escape(json.dumps(group['id']), quote=True)}, this)"></div>
  <div class="state {css}">{label} {message}</div>
</section>"""


def render_page(run_id: str, plan: dict, links: dict, status: dict) -> str:
    entries = links.get("groups", {})
    states = status.get("groups", {})
    shots = {shot["index"]: shot for shot in plan["shots"]}
    groups = plan["groups"]
    filled = sum(1 for group in groups if entries.get(group["id"]))
    cards = "".join(
        _card(group, [shots[i] for i in group["shots"]], entries.get(group["id"], []), states.get(group["id"], {}))
        for group in groups
    )
    return f"""<!doctype html>
<html lang="id"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Brief {escape(run_id)}</title><style>{_CSS}</style></head>
<body><header><b>Brief {escape(run_id)}</b><span>{filled}/{len(groups)} kelompok terisi ({len(plan['shots'])} shot)</span>
<button onclick="save()">Simpan</button><span id="msg"></span></header>
<main><section id="progress"></section>{cards}</main>
<script>{_JS}</script></body></html>"""
