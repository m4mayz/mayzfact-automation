"""HTML halaman brief: 1 kartu per kelompok konteks, dipecah per-shot dengan keyword, single-line textbox link, upload, status fetch."""

from __future__ import annotations

import json
from html import escape

from mayzfact.manual.links import lines_of

_CSS = """
body{font-family:system-ui,sans-serif;margin:0;background:#f4f4f5;color:#18181b}
header{position:sticky;top:0;background:#18181b;color:#fff;padding:12px 16px;display:flex;gap:16px;align-items:center;z-index:2}
header button{padding:8px 16px;font-size:15px;cursor:pointer}
.layout{max-width:1320px;margin:0 auto;padding:16px;display:grid;grid-template-columns:320px 1fr;gap:16px;align-items:start}
.layout.nosource{max-width:980px;grid-template-columns:1fr}
main{display:grid;gap:16px;min-width:0}
.source{position:sticky;top:64px;display:grid;gap:6px}.source video{width:100%;max-height:calc(100vh - 110px);border-radius:10px;background:#000}
@media (max-width:900px){.layout{grid-template-columns:1fr}.source{position:static}.source video{max-height:60vh}}
.card{background:#fff;border-radius:10px;padding:16px;display:grid;gap:12px;box-shadow:0 1px 3px #0002}
.card-header{display:flex;align-items:center;gap:8px;font-size:15px;font-weight:600}
.tag{font-size:12px;font-weight:700;padding:2px 8px;border-radius:99px;background:#e4e4e7}
.tag.hook{background:#fde68a}
.shots{display:grid;gap:12px;margin:0;padding:0;list-style:none}
.shot-box{background:#fafafa;border:1px solid #e4e4e7;border-radius:8px;padding:12px;display:grid;gap:8px}
.shot-header{display:flex;flex-wrap:wrap;align-items:center;gap:8px;font-size:14px}
.badge{font-size:11px;font-weight:700;text-transform:uppercase;padding:2px 6px;border-radius:4px}
.badge.video{background:#dbeafe;color:#1e40af}
.badge.photo{background:#fef3c7;color:#92400e}
.badge.card{background:#ede9fe;color:#5b21b6}
.shot-text{color:#27272a;font-size:13px;line-height:1.4}
.refs{display:flex;gap:6px;margin-top:2px}.refs img{height:100px;border-radius:6px}
.kw{display:flex;flex-wrap:wrap;gap:6px}.kw button{border:1px solid #d4d4d8;background:#fff;border-radius:6px;padding:3px 8px;cursor:pointer;font-size:12px}
.kw button:hover{background:#f4f4f5}
.shot-input-row{display:flex;gap:8px;align-items:center}
.shot-input-row input[type=text]{flex:1;height:36px;padding:0 10px;font-size:13px;border:1px solid #d4d4d8;border-radius:6px;box-sizing:border-box;font-family:inherit}
.shot-input-row input[type=text]:focus{outline:none;border-color:#2563eb}
.btn-upload{position:relative;overflow:hidden;display:inline-flex;align-items:center;justify-content:center;height:36px;padding:0 12px;font-size:13px;font-weight:500;background:#f4f4f5;border:1px solid #d4d4d8;border-radius:6px;cursor:pointer;white-space:nowrap}
.btn-upload:hover{background:#e4e4e7}
.btn-upload input[type=file]{position:absolute;left:0;top:0;opacity:0;width:100%;height:100%;cursor:pointer}
#progress{background:#fff;border-radius:10px;padding:12px 14px;box-shadow:0 1px 3px #0002;display:none;gap:6px}
#progress .bar{height:10px;background:#e4e4e7;border-radius:99px;overflow:hidden}#progress .bar div{height:100%;background:#2563eb;transition:width .4s}
#progress pre{margin:0;max-height:160px;overflow:auto;font-size:12px;background:#f4f4f5;padding:8px;border-radius:6px;white-space:pre-wrap}
.state{font-size:13px}.state.ok{color:#15803d}.state.error,.state.missing{color:#b91c1c}.state.warn{color:#b45309}
"""

_JS = """
async function save(){
  const shots = {};
  document.querySelectorAll('input[data-shot]').forEach(inp => {
    const v = inp.value.trim();
    if (v) shots[inp.dataset.shot] = v;
  });
  const res = await fetch('/api/links', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({shots})});
  const data = await res.json();
  const missingText = (data.missing || []).map(m => typeof m === 'number' ? `shot ${m + 1}` : m).join(', ') || '-';
  document.getElementById('msg').textContent = res.ok ? `Tersimpan. Kosong: ${missingText}` : data.error;
  if (res.ok) setTimeout(() => location.reload(), 600);
}
async function uploadShot(shotIndex, input){
  const file = input.files[0]; if (!file) return;
  document.getElementById('msg').textContent = `Upload shot ${shotIndex + 1} (${file.name})...`;
  const shots = {};
  document.querySelectorAll('input[data-shot]').forEach(inp => {
    const v = inp.value.trim();
    if (v) shots[inp.dataset.shot] = v;
  });
  const saved = await fetch('/api/links', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({shots})});
  if (!saved.ok) { document.getElementById('msg').textContent = (await saved.json()).error; return; }
  const res = await fetch(`/api/upload?shot=${encodeURIComponent(shotIndex)}`, {
    method: 'POST',
    headers: {'X-Filename': encodeURIComponent(file.name)},
    body: file
  });
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
function copyText(t, btn){
  function done(){
    document.getElementById('msg').textContent = `Ke-copy: ${t}`;
    if (btn) {
      const orig = btn.textContent;
      btn.textContent = '✓ ' + orig;
      btn.style.background = '#dcfce7';
      btn.style.borderColor = '#86efac';
      setTimeout(() => {
        btn.textContent = orig;
        btn.style.background = '';
        btn.style.borderColor = '';
      }, 1200);
    }
  }
  if (navigator.clipboard && window.isSecureContext) {
    navigator.clipboard.writeText(t).then(done).catch(() => fallbackCopy(t, done));
  } else {
    fallbackCopy(t, done);
  }
}
function fallbackCopy(t, cb){
  const ta = document.createElement('textarea');
  ta.value = t;
  ta.style.position = 'fixed';
  ta.style.left = '-9999px';
  ta.style.top = '0';
  document.body.appendChild(ta);
  ta.focus();
  ta.select();
  try {
    document.execCommand('copy');
    if (cb) cb();
  } catch (e) {
    document.getElementById('msg').textContent = `Gagal copy: ${t}`;
  }
  document.body.removeChild(ta);
}
"""


def _shot_row(shot: dict, group: dict, val: str, state: dict) -> str:
    s_idx = shot["index"]
    refs = "".join(f'<img src="/files/{escape(f)}" loading="lazy">' for f in shot.get("ref_frames", []))

    kw_list = []
    for lang in ("en", "zh"):
        for k in shot.get("keywords", {}).get(lang, []):
            kw_list.append(k)
    if not kw_list:
        for lang in ("en", "zh"):
            for k in group.get("keywords", {}).get(lang, []):
                kw_list.append(k)
    keywords = "".join(
        f'<button type="button" onclick=\'copyText({escape(json.dumps(k), quote=True)}, this)\'>{escape(k)}</button>'
        for k in kw_list
    )

    countdown_badge = (f'<span class="badge card">CARD #{int(shot["countdown"])}</span> '
                       if shot.get("countdown") else "")
    media_badge = f'<span class="badge {escape(shot.get("media", "video"))}">{escape(shot.get("media", "video"))}</span>'

    css = state.get("state", "") if val else "missing"
    if css == "missing" and val:
        css = ""
    if css == "ok" and state.get("message"):
        css = "warn"
    label = {"ok": "OK", "warn": "OK", "error": "GAGAL", "missing": "KOSONG"}.get(css, "TERSIMPAN" if val else "KOSONG")
    message = escape(state.get("message", "") if css else "")

    return f"""
    <div class="shot-box" data-shot-box="{s_idx}">
      <div class="shot-header">
        <b>Shot {s_idx + 1}</b> · {shot['start_s']:.1f}–{shot['end_s']:.1f}s · {media_badge} · {countdown_badge}
        <span class="shot-text">{escape(shot.get('text', ''))}</span>
      </div>
      {f'<div class="refs">{refs}</div>' if refs else ''}
      <div class="kw">{keywords or '<i>tanpa keyword</i>'}</div>
      <div class="shot-input-row">
        <input type="text" data-shot="{s_idx}" value="{escape(val)}" placeholder="1 link (opsional: tambah @6 atau @6-10 buat detik) atau upload">
        <label class="btn-upload"><input type="file" accept="video/*,image/*" onchange="uploadShot({s_idx}, this)">Upload</label>
      </div>
      <div class="state {css}">{label} {message}</div>
    </div>"""


def _card(group: dict, shots: list[dict], links: dict, status: dict) -> str:
    is_hook = group["id"] == "hook"
    refs = "".join(f'<img src="/files/{escape(f)}" loading="lazy">' for f in group.get("ref_frames", []))

    shot_rows = []
    for shot in shots:
        s_idx = shot["index"]
        val = ""
        if "shots" in links:
            entry = links["shots"].get(str(s_idx))
            if isinstance(entry, dict):
                val = lines_of([entry])
            elif isinstance(entry, str):
                val = entry
        elif "groups" in links:
            pos = group["shots"].index(s_idx) if s_idx in group["shots"] else -1
            group_entries = links["groups"].get(group["id"], [])
            if 0 <= pos < len(group_entries):
                val = lines_of([group_entries[pos]])

        st = {}
        if "shots" in status and str(s_idx) in status["shots"]:
            st = status["shots"][str(s_idx)]
        elif "groups" in status and group["id"] in status["groups"]:
            st = status["groups"][group["id"]]

        shot_rows.append(_shot_row(shot, group, val, st))

    return f"""
<section class="card" data-group="{escape(group['id'], quote=True)}">
  <div class="card-header">
    <span class="tag {'hook' if is_hook else ''}">{escape(group['label'])}</span> · {len(shots)} shot
  </div>
  {f'<div>Frame dari source:</div><div class="refs">{refs}</div>' if refs else ''}
  <div class="shots">{''.join(shot_rows)}</div>
</section>"""


def render_page(run_id: str, plan: dict, links: dict, status: dict, source: str | None = None) -> str:
    shots = {shot["index"]: shot for shot in plan["shots"]}
    groups = plan["groups"]

    if "shots" in links:
        filled_shots = sum(1 for shot in plan["shots"] if str(shot["index"]) in links["shots"] and links["shots"][str(shot["index"])])
        filled_groups = sum(1 for g in groups if all(str(i) in links["shots"] and links["shots"][str(i)] for i in g["shots"]))
    else:
        entries = links.get("groups", {})
        filled_groups = sum(1 for group in groups if entries.get(group["id"]))
        filled_shots = sum(min(len(g["shots"]), len(entries.get(g["id"], []))) for g in groups)

    cards = "".join(
        _card(group, [shots[i] for i in group["shots"]], links, status)
        for group in groups
    )
    aside = (f'<aside class="source"><b>Video source</b><video src="/files/{escape(source, quote=True)}" controls preload="metadata">'
             "</video></aside>") if source else ""
    return f"""<!doctype html>
<html lang="id"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Brief {escape(run_id)}</title><style>{_CSS}</style></head>
<body><header><b>Brief {escape(run_id)}</b><span>{filled_shots}/{len(plan['shots'])} shot ({filled_groups}/{len(groups)} kelompok)</span>
<button onclick="save()">Simpan</button><span id="msg"></span></header>
<div class="layout{'' if source else ' nosource'}">{aside}<main><section id="progress"></section>{cards}</main></div>
<script>{_JS}</script></body></html>"""
