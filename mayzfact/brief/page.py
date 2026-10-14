"""HTML halaman brief: 1 kartu per kelompok konteks, dipecah per-shot dengan keyword, single-line textbox link, upload, status fetch."""

from __future__ import annotations

import json
from html import escape

_CSS = """
:root {
  --bg: #f8fafc;
  --card-bg: #ffffff;
  --border: #e2e8f0;
  --text-main: #0f172a;
  --text-muted: #64748b;
  --accent: #2563eb;
  --accent-hover: #1d4ed8;
  --badge-video-bg: #dbeafe;
  --badge-video-text: #1e40af;
  --badge-photo-bg: #fef3c7;
  --badge-photo-text: #92400e;
  --badge-card-bg: #ede9fe;
  --badge-card-text: #5b21b6;
}

* { box-sizing: border-box; }
body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  margin: 0;
  background: var(--bg);
  color: var(--text-main);
  -webkit-font-smoothing: antialiased;
}

header {
  position: sticky;
  top: 0;
  background: #0f172a;
  color: #fff;
  padding: 12px 20px;
  display: flex;
  flex-wrap: wrap;
  gap: 12px 20px;
  align-items: center;
  justify-content: space-between;
  z-index: 20;
  box-shadow: 0 2px 8px rgba(0,0,0,0.15);
}
.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}
.header-left b {
  font-size: 16px;
  letter-spacing: -0.01em;
}
.header-left span {
  font-size: 13px;
  color: #94a3b8;
  background: rgba(255,255,255,0.08);
  padding: 3px 10px;
  border-radius: 99px;
}
.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}
header button.btn-save {
  padding: 8px 18px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  background: var(--accent);
  color: #fff;
  border: none;
  border-radius: 8px;
  transition: background 0.15s, transform 0.05s;
}
header button.btn-save:hover { background: var(--accent-hover); }
header button.btn-save:active { transform: scale(0.97); }
#msg {
  font-size: 13px;
  color: #cbd5e1;
  max-width: 320px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.layout {
  max-width: 1360px;
  margin: 0 auto;
  padding: 20px;
  display: grid;
  grid-template-columns: 340px 1fr;
  gap: 20px;
  align-items: start;
}
.layout.nosource {
  max-width: 1000px;
  grid-template-columns: 1fr;
}
main {
  display: grid;
  gap: 20px;
  min-width: 0;
}

.source {
  position: sticky;
  top: 76px;
  display: grid;
  gap: 8px;
}
.source-details {
  background: var(--card-bg);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 12px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.05);
}
.source-summary {
  cursor: pointer;
  list-style: none;
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 14px;
  font-weight: 600;
  color: var(--text-main);
  padding-bottom: 8px;
  user-select: none;
}
.source-summary::-webkit-details-marker { display: none; }
.source-summary::after {
  content: '▾';
  font-size: 16px;
  color: var(--text-muted);
  transition: transform 0.2s;
}
details[open] .source-summary::after {
  transform: rotate(180deg);
}
.source video {
  width: 100%;
  max-height: calc(100vh - 160px);
  border-radius: 8px;
  background: #000;
  display: block;
}

.card {
  background: var(--card-bg);
  border: 1px solid var(--border);
  border-radius: 14px;
  padding: 18px;
  display: grid;
  gap: 14px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.05);
}
.card-header {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 15px;
  font-weight: 600;
}
.tag {
  font-size: 12px;
  font-weight: 700;
  padding: 3px 10px;
  border-radius: 99px;
  background: #e2e8f0;
  color: #334155;
  letter-spacing: 0.02em;
}
.tag.hook {
  background: #fef08a;
  color: #854d0e;
}
.shots {
  display: grid;
  gap: 12px;
  margin: 0;
  padding: 0;
  list-style: none;
}
.shot-box {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 14px;
  display: grid;
  gap: 10px;
  transition: border-color 0.15s, box-shadow 0.15s;
}
.shot-box:focus-within {
  border-color: #93c5fd;
  box-shadow: 0 0 0 1px #93c5fd;
  background: #fff;
}
.shot-header {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  font-size: 13.5px;
}
.badge {
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  padding: 2.5px 7px;
  border-radius: 5px;
  letter-spacing: 0.02em;
}
.badge.video { background: var(--badge-video-bg); color: var(--badge-video-text); }
.badge.photo { background: var(--badge-photo-bg); color: var(--badge-photo-text); }
.badge.card { background: var(--badge-card-bg); color: var(--badge-card-text); }
.shot-time-span {
  font-weight: 600;
  color: var(--text-muted);
  font-size: 12.5px;
}
.shot-text {
  color: #334155;
  font-size: 13.5px;
  line-height: 1.5;
  background: #f1f5f9;
  padding: 6px 10px;
  border-radius: 6px;
  width: 100%;
  box-sizing: border-box;
}

.refs {
  display: flex;
  gap: 8px;
  overflow-x: auto;
  padding-bottom: 4px;
  scrollbar-width: thin;
  -webkit-overflow-scrolling: touch;
}
.refs img {
  height: 105px;
  border-radius: 8px;
  object-fit: cover;
  flex-shrink: 0;
  border: 1px solid #e2e8f0;
  background: #000;
}
.group-refs-label {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-muted);
}

.kw {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.kw button {
  border: 1px solid #cbd5e1;
  background: #fff;
  border-radius: 6px;
  padding: 5px 10px;
  cursor: pointer;
  font-size: 12.5px;
  font-family: inherit;
  color: #334155;
  min-height: 32px;
  display: inline-flex;
  align-items: center;
  transition: all 0.15s;
}
.kw button:hover { background: #f1f5f9; border-color: #94a3b8; }
.kw button:active { transform: scale(0.97); }

.shot-input-row {
  display: flex;
  gap: 8px;
  align-items: center;
}
.shot-input-row input[type=text] {
  flex: 1;
  min-width: 0;
  height: 40px;
  padding: 0 12px;
  font-size: 14px;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  box-sizing: border-box;
  font-family: inherit;
  background: #fff;
  color: var(--text-main);
  transition: border-color 0.15s;
}
.shot-input-row input[type=text]:focus {
  outline: none;
  border-color: var(--accent);
}

.btn-upload {
  position: relative;
  overflow: hidden;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  height: 40px;
  padding: 0 14px;
  font-size: 13px;
  font-weight: 600;
  background: #fff;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  cursor: pointer;
  white-space: nowrap;
  color: #334155;
  flex-shrink: 0;
  transition: all 0.15s;
}
.btn-upload:hover { background: #f1f5f9; border-color: #94a3b8; }
.btn-upload:active { transform: scale(0.97); }
.btn-upload input[type=file] {
  position: absolute;
  left: 0;
  top: 0;
  opacity: 0;
  width: 100%;
  height: 100%;
  cursor: pointer;
}

.shot-time-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 8px 14px;
  font-size: 12.5px;
  color: var(--text-muted);
  background: #f1f5f9;
  padding: 8px 12px;
  border-radius: 8px;
}
.time-label { font-weight: 600; color: #475569; }
.time-inputs { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
.time-inputs label {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 12.5px;
  font-weight: 500;
  color: #334155;
}
.time-inputs input[type=number] {
  width: 76px;
  height: 32px;
  padding: 0 6px;
  font-size: 13px;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  box-sizing: border-box;
  background: #fff;
  font-family: inherit;
  text-align: center;
  transition: border-color 0.15s;
}
.time-inputs input[type=number]:focus { outline: none; border-color: var(--accent); }

.state {
  font-size: 12px;
  font-weight: 600;
  padding: 4px 8px;
  border-radius: 6px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  width: fit-content;
}
.state.ok { background: #dcfce7; color: #15803d; }
.state.warn { background: #fef3c7; color: #b45309; }
.state.error { background: #fee2e2; color: #b91c1c; }
.state.missing { background: #f1f5f9; color: #64748b; }

#progress {
  background: var(--card-bg);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 14px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.05);
  display: none;
  gap: 8px;
}
#progress .bar { height: 8px; background: #e2e8f0; border-radius: 99px; overflow: hidden; }
#progress .bar div { height: 100%; background: var(--accent); transition: width .4s; }
#progress pre {
  margin: 0;
  max-height: 160px;
  overflow: auto;
  font-size: 12px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  padding: 8px 10px;
  border-radius: 6px;
  white-space: pre-wrap;
  color: #334155;
}

/* Mobile Action Bar */
.mobile-save-bar {
  display: none;
}

@media (max-width: 900px) {
  .layout {
    grid-template-columns: 1fr;
    padding: 12px;
    gap: 14px;
  }
  .source {
    position: static;
  }
  .source video {
    max-height: 45vh;
  }
}

@media (max-width: 600px) {
  header {
    padding: 10px 14px;
  }
  .header-right button.btn-save {
    display: none;
  }
  .mobile-save-bar {
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    background: rgba(15, 23, 42, 0.95);
    backdrop-filter: blur(8px);
    -webkit-backdrop-filter: blur(8px);
    padding: 10px 16px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    z-index: 50;
    box-shadow: 0 -4px 16px rgba(0,0,0,0.2);
    border-top: 1px solid rgba(255,255,255,0.1);
  }
  .mobile-save-bar .btn-save {
    flex: 1;
    min-height: 44px;
    font-size: 15px;
    font-weight: 700;
    border-radius: 8px;
    background: var(--accent);
    color: #fff;
    border: none;
    cursor: pointer;
  }
  .mobile-save-bar .mobile-msg {
    font-size: 12.5px;
    color: #cbd5e1;
    max-width: 140px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  body {
    padding-bottom: 75px;
  }
  .card {
    padding: 14px;
    border-radius: 12px;
  }
  .shot-box {
    padding: 12px;
  }
  .shot-input-row {
    flex-direction: column;
    align-items: stretch;
  }
  .shot-input-row input[type=text] {
    height: 44px;
    font-size: 15px;
  }
  .btn-upload {
    height: 40px;
    width: 100%;
  }
  .time-inputs {
    width: 100%;
    justify-content: space-between;
  }
  .time-inputs label {
    flex: 1;
    justify-content: center;
  }
  .time-inputs input[type=number] {
    flex: 1;
    max-width: 80px;
    height: 36px;
    font-size: 14px;
  }
}
"""

_JS = r"""
function setMsg(text) {
  const m1 = document.getElementById('msg');
  if (m1) m1.textContent = text;
  const m2 = document.getElementById('mobile-msg');
  if (m2) m2.textContent = text;
}

function collectShots(){
  const shots = {};
  document.querySelectorAll('input[data-shot]').forEach(inp => {
    let v = inp.value.trim();
    if (!v) return;
    const idx = inp.dataset.shot;
    const startInp = document.querySelector(`input[data-time-start="${idx}"]`);
    const endInp = document.querySelector(`input[data-time-end="${idx}"]`);
    const startVal = startInp ? startInp.value.trim() : '';
    const endVal = endInp ? endInp.value.trim() : '';
    if (startVal || endVal) {
      v = v.replace(/\s+(@\S+|#\S+)\s*$/, '');
      if (startVal && endVal) {
        v += ` @${startVal}-${endVal}`;
      } else if (startVal) {
        v += ` @${startVal}`;
      }
    }
    shots[idx] = v;
  });
  return shots;
}

let autoSaveTimer = null;
function scheduleAutoSave() {
  setMsg('Menyimpan otomatis...');
  clearTimeout(autoSaveTimer);
  autoSaveTimer = setTimeout(async () => {
    const shots = collectShots();
    try {
      const res = await fetch('/api/links', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({shots})
      });
      if (res.ok) {
        setMsg('Tersimpan otomatis ✓');
        setTimeout(() => setMsg(''), 2500);
      } else {
        const data = await res.json();
        setMsg(data.error || 'Gagal simpan');
      }
    } catch (e) {
      setMsg('Gagal koneksi');
    }
  }, 1000);
}

document.addEventListener('input', (e) => {
  if (e.target.matches('input[data-shot], input[data-time-start], input[data-time-end]')) {
    scheduleAutoSave();
  }
});

async function save(){
  clearTimeout(autoSaveTimer);
  setMsg('Menyimpan...');
  const shots = collectShots();
  const res = await fetch('/api/links', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({shots})});
  const data = await res.json();
  const missingText = (data.missing || []).map(m => typeof m === 'number' ? `shot ${m + 1}` : m).join(', ') || '-';
  setMsg(res.ok ? `Tersimpan. Kosong: ${missingText}` : data.error);
  if (res.ok) setTimeout(() => location.reload(), 600);
}

async function uploadShot(shotIndex, input){
  const file = input.files[0]; if (!file) return;
  setMsg(`Upload shot ${shotIndex + 1} (${file.name})...`);
  const shots = collectShots();
  const saved = await fetch('/api/links', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({shots})});
  if (!saved.ok) { setMsg((await saved.json()).error); return; }
  const res = await fetch(`/api/upload?shot=${encodeURIComponent(shotIndex)}`, {
    method: 'POST',
    headers: {'X-Filename': encodeURIComponent(file.name)},
    body: file
  });
  const data = await res.json();
  if (!res.ok) { setMsg(data.error); return; }
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
    setMsg(`Ke-copy: ${t}`);
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
    setMsg(`Gagal copy: ${t}`);
  }
  document.body.removeChild(ta);
}
"""


def _shot_row(shot: dict, group: dict, entry: dict | str | None, state: dict) -> str:
    s_idx = shot["index"]
    refs = "".join(f'<img src="/files/{escape(f)}" loading="lazy">' for f in shot.get("ref_frames", []))

    kw_list = []
    for lang in ("en", "zh"):
        kw_list.extend(shot.get("keywords", {}).get(lang, []))
    if not kw_list:
        for lang in ("en", "zh"):
            kw_list.extend(group.get("keywords", {}).get(lang, []))
    keywords = "".join(
        f'<button type="button" onclick=\'copyText({escape(json.dumps(k), quote=True)}, this)\'>{escape(k)}</button>'
        for k in kw_list
    )

    countdown_badge = (f'<span class="badge card">CARD #{int(shot["countdown"])}</span>'
                       if shot.get("countdown") else "")
    media_badge = f'<span class="badge {escape(shot.get("media", "video"))}">{escape(shot.get("media", "video"))}</span>'

    url_val = ""
    start_val = ""
    end_val = ""
    if isinstance(entry, dict):
        if entry.get("file"):
            url_val = f"file:{entry['file']}"
        elif entry.get("url"):
            url_val = entry["url"] + (f" #{entry['pick']}" if entry.get("pick") else "")
        if entry.get("start_s") is not None:
            start_val = f"{entry['start_s']:g}"
        if entry.get("end_s") is not None:
            end_val = f"{entry['end_s']:g}"
    elif isinstance(entry, str) and entry.strip():
        from mayzfact.manual.links import parse_time_range
        clean, s_s, e_s = parse_time_range(entry)
        url_val = clean
        if s_s is not None:
            start_val = f"{s_s:g}"
        if e_s is not None:
            end_val = f"{e_s:g}"

    has_val = bool(url_val)
    css = state.get("state", "") if has_val else "missing"
    if css == "missing" and has_val:
        css = ""
    if css == "ok" and state.get("message"):
        css = "warn"
    label = {"ok": "OK", "warn": "OK", "error": "GAGAL", "missing": "KOSONG"}.get(css, "TERSIMPAN" if has_val else "KOSONG")
    message = escape(state.get("message", "") if css else "")

    return f"""
    <div class="shot-box" data-shot-box="{s_idx}">
      <div class="shot-header">
        <b>Shot {s_idx + 1}</b>
        <span class="shot-time-span">· {shot['start_s']:.1f}–{shot['end_s']:.1f}s</span>
        {media_badge}
        {countdown_badge}
      </div>
      <div class="shot-text">{escape(shot.get('text', ''))}</div>
      {f'<div class="refs">{refs}</div>' if refs else ''}
      <div class="kw">{keywords or '<i>tanpa keyword</i>'}</div>
      <div class="shot-input-row">
        <input type="text" data-shot="{s_idx}" value="{escape(url_val)}" placeholder="1 link Douyin/TikTok/Pinterest/URL atau upload file">
        <label class="btn-upload"><input type="file" accept="video/*,image/*" onchange="uploadShot({s_idx}, this)">Upload</label>
      </div>
      <div class="shot-time-row">
        <span class="time-label">Detik klip (opsional):</span>
        <div class="time-inputs">
          <label>Mulai: <input type="number" step="0.1" min="0" data-time-start="{s_idx}" value="{escape(start_val)}" placeholder="0.0">s</label>
          <label>Selesai: <input type="number" step="0.1" min="0" data-time-end="{s_idx}" value="{escape(end_val)}" placeholder="otomatis">s</label>
        </div>
      </div>
      <div class="state {css}">{label} {message}</div>
    </div>"""


def _card(group: dict, shots: list[dict], links: dict, status: dict) -> str:
    is_hook = group["id"] == "hook"
    refs = "".join(f'<img src="/files/{escape(f)}" loading="lazy">' for f in group.get("ref_frames", []))

    shot_rows = []
    for shot in shots:
        s_idx = shot["index"]
        entry = None
        if "shots" in links:
            entry = links["shots"].get(str(s_idx))
        elif "groups" in links:
            pos = group["shots"].index(s_idx) if s_idx in group["shots"] else -1
            group_entries = links["groups"].get(group["id"], [])
            if 0 <= pos < len(group_entries):
                entry = group_entries[pos]

        st = {}
        if "shots" in status and str(s_idx) in status["shots"]:
            st = status["shots"][str(s_idx)]
        elif "groups" in status and group["id"] in status["groups"]:
            st = status["groups"][group["id"]]

        shot_rows.append(_shot_row(shot, group, entry, st))

    return f"""
<section class="card" data-group="{escape(group['id'], quote=True)}">
  <div class="card-header">
    <span class="tag {'hook' if is_hook else ''}">{escape(group['label'])}</span> · {len(shots)} shot
  </div>
  {f'<div class="group-refs-label">Frame dari source:</div><div class="refs">{refs}</div>' if refs else ''}
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
    aside = (
        f'<aside class="source"><details class="source-details" open>'
        f'<summary class="source-summary"><span>🎬 <b>Video source</b></span></summary>'
        f'<video src="/files/{escape(source, quote=True)}" controls preload="metadata"></video>'
        f'</details></aside>'
    ) if source else ""

    return f"""<!doctype html>
<html lang="id"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Brief {escape(run_id)}</title><style>{_CSS}</style></head>
<body>
<header>
  <div class="header-left">
    <b>Brief {escape(run_id)}</b>
    <span>{filled_shots}/{len(plan['shots'])} shot ({filled_groups}/{len(groups)} kelompok)</span>
  </div>
  <div class="header-right">
    <button type="button" class="btn-save" onclick="save()">Simpan</button>
    <span id="msg"></span>
  </div>
</header>
<div class="layout{'' if source else ' nosource'}">
  {aside}
  <main>
    <section id="progress"></section>
    {cards}
  </main>
</div>
<div class="mobile-save-bar">
  <button type="button" class="btn-save" onclick="save()">Simpan Semua</button>
  <span id="mobile-msg" class="mobile-msg"></span>
</div>
<script>{_JS}</script>
</body></html>"""
