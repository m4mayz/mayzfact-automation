"""HTML halaman brief: layout rapi, clean container, responsif mobile dan desktop."""

from __future__ import annotations

import json
from html import escape

_CSS = """
:root {
  --bg-page: #f4f4f5;
  --bg-card: #ffffff;
  --bg-subtle: #f8fafc;
  --bg-well: #eff6ff;
  --border-card: #d4d4d8;
  --border-subtle: #cbd5e1;
  --border-well: #93c5fd;

  --text-primary: #09090b;
  --text-secondary: #334155;
  --text-muted: #52525b;

  --brand-orange: #ff7a00;
  --brand-orange-soft: #fff0db;
  --brand-orange-border: #fdba74;
  --brand-orange-text: #c2410c;

  --blue-main: #2563eb;
  --blue-hover: #1d4ed8;
  --blue-soft: #eff6ff;

  --green-main: #16a34a;
  --green-soft: #dcfce7;
  --green-border: #bbf7d0;

  --red-main: #dc2626;
  --red-soft: #fee2e2;
  --red-border: #fecaca;

  --amber-main: #d97706;
  --amber-soft: #fef3c7;
  --amber-border: #fde68a;

  --purple-soft: #f5f3ff;
  --purple-text: #6d28d9;
  --purple-border: #ddd6fe;

  --radius-card: 16px;
  --radius-box: 12px;
  --radius-pill: 999px;

  --shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.05);
  --shadow-md: 0 4px 12px rgba(0, 0, 0, 0.05);

  --stripe-blue: repeating-linear-gradient(
    -45deg,
    #2563eb 0px,
    #2563eb 4px,
    #60a5fa 4px,
    #60a5fa 8px
  );
  --stripe-green: repeating-linear-gradient(
    -45deg,
    #16a34a 0px,
    #16a34a 4px,
    #4ade80 4px,
    #4ade80 8px
  );
  --stripe-pink: repeating-linear-gradient(
    -45deg,
    #db2777 0px,
    #db2777 4px,
    #f472b6 4px,
    #f472b6 8px
  );
}

* {
  box-sizing: border-box;
  -webkit-tap-highlight-color: transparent;
}

body {
  margin: 0;
  padding: 0 0 60px;
  background-color: var(--bg-page);
  color: var(--text-primary);
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  -webkit-font-smoothing: antialiased;
  line-height: 1.5;
}

/* Fixed Top Nav Bar */
.top-nav {
  position: sticky;
  top: 0;
  z-index: 40;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  border-bottom: 1px solid var(--border-card);
  padding: 10px 20px;
}

.top-nav-inner {
  max-width: 1360px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
}

.brand {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  text-decoration: none;
  color: var(--text-primary);
  font-weight: 700;
  font-size: 18px;
  letter-spacing: -0.02em;
}

.brand-mark {
  width: 26px;
  height: 26px;
  border-radius: 7px;
  background: linear-gradient(135deg, #ff9900 0%, #ff6200 100%);
  display: grid;
  place-items: center;
  color: #fff;
}

.brand-mark svg {
  width: 14px;
  height: 14px;
  stroke: #fff;
  stroke-width: 2.2;
  fill: none;
}

.nav-pills {
  display: flex;
  align-items: center;
  gap: 6px;
  background: #f1f5f9;
  padding: 4px;
  border-radius: 12px;
  overflow-x: auto;
}

.nav-pill {
  border: none;
  background: transparent;
  color: var(--text-secondary);
  font-family: inherit;
  font-size: 13px;
  font-weight: 500;
  padding: 6px 14px;
  border-radius: 8px;
  cursor: pointer;
  white-space: nowrap;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  transition: all 0.15s ease;
}

.nav-pill:hover {
  color: var(--text-primary);
  background: rgba(255, 255, 255, 0.6);
}

.nav-pill.active {
  background: #09090b;
  color: #ffffff;
}

.nav-count {
  font-size: 11px;
  font-weight: 600;
  padding: 1px 6px;
  border-radius: 99px;
  background: rgba(0, 0, 0, 0.08);
}

.nav-pill.active .nav-count {
  background: rgba(255, 255, 255, 0.2);
}

.nav-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.sync-status {
  font-size: 12px;
  color: var(--text-muted);
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: #f8fafc;
  padding: 6px 12px;
  border-radius: var(--radius-pill);
  border: 1px solid var(--border-subtle);
  max-width: 260px;
}

.sync-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--green-main);
  flex-shrink: 0;
}

#msg {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.btn-primary-dark {
  background: #09090b;
  color: #fff;
  border: none;
  border-radius: 8px;
  padding: 8px 18px;
  font-family: inherit;
  font-size: 13.5px;
  font-weight: 600;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  transition: opacity 0.15s, transform 0.05s;
}

.btn-primary-dark:hover { opacity: 0.9; }
.btn-primary-dark:active { transform: scale(0.98); }

/* Main App Container */
.app-container {
  max-width: 1360px;
  margin: 16px auto 0;
  padding: 0 20px;
}

/* Page Header & Stats */
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 14px;
  margin-bottom: 16px;
}

.page-title {
  font-size: 26px;
  font-weight: 700;
  letter-spacing: -0.025em;
  margin: 0;
  display: flex;
  align-items: center;
  gap: 10px;
}

.header-badges {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.header-badge {
  background: #fff;
  border: 1px solid var(--border-card);
  border-radius: var(--radius-pill);
  padding: 5px 12px;
  font-size: 12px;
  font-weight: 500;
  color: var(--text-secondary);
  display: inline-flex;
  align-items: center;
  gap: 6px;
  box-shadow: var(--shadow-sm);
}

/* Timeline & Pacing Card */
.timeline-card {
  background: #fff;
  border: 1px solid var(--border-card);
  border-radius: var(--radius-card);
  padding: 16px 20px;
  box-shadow: var(--shadow-sm);
  margin-bottom: 20px;
  min-width: 0;
}

.timeline-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.timeline-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
}

.timeline-summary {
  font-size: 12px;
  color: var(--text-muted);
}

.timeline-track {
  display: flex;
  gap: 8px;
  overflow-x: auto;
  padding-bottom: 6px;
  scrollbar-width: thin;
}

.timeline-shot-chip {
  flex: 0 0 auto;
  min-width: 76px;
  padding: 8px 10px;
  background: #f8fafc;
  border: 1px solid var(--border-subtle);
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.15s ease;
  display: flex;
  flex-direction: column;
  gap: 4px;
  text-align: center;
}

.timeline-shot-chip:hover {
  background: #eff6ff;
  border-color: #93c5fd;
}

.timeline-shot-chip.is-active {
  background: #eff6ff;
  border-color: var(--blue-main);
  box-shadow: 0 0 0 1px var(--blue-main);
}

.timeline-shot-num {
  font-size: 11px;
  color: var(--text-muted);
  font-weight: 500;
}

.timeline-shot-dur {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}

.timeline-shot-bar {
  height: 5px;
  border-radius: 99px;
  background: #e2e8f0;
  width: 100%;
  overflow: hidden;
}

.timeline-shot-chip.is-filled .timeline-shot-bar {
  background: var(--blue-main);
}

/* Two-column Workspace Layout */
.workspace-layout {
  display: grid;
  grid-template-columns: 340px minmax(0, 1fr);
  gap: 20px;
  align-items: start;
  min-width: 0;
}

.workspace-layout.nosource {
  grid-template-columns: minmax(0, 1fr);
  max-width: 960px;
  margin: 0 auto;
}

/* Sidebar Sticky */
.sidebar-sticky {
  position: sticky;
  top: 76px;
  display: grid;
  gap: 16px;
  min-width: 0;
}

.z-card {
  background: var(--bg-card);
  border: 1px solid var(--border-card);
  border-radius: var(--radius-card);
  padding: 18px 20px;
  box-shadow: var(--shadow-sm);
  min-width: 0;
}

.z-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 14px;
}

.z-card-title {
  font-size: 15px;
  font-weight: 600;
  margin: 0;
  color: var(--text-primary);
}

.video-frame {
  border-radius: 12px;
  overflow: hidden;
  background: #000;
  border: 1px solid var(--border-card);
}

.video-frame video {
  width: 100%;
  display: block;
  max-height: 240px;
  object-fit: contain;
  background: #000;
}

/* Readiness Striped Bars */
.readiness-pct {
  font-size: 32px;
  font-weight: 700;
  letter-spacing: -0.03em;
  color: var(--text-primary);
  display: flex;
  align-items: baseline;
  gap: 8px;
  margin: 2px 0 14px;
}

.readiness-pct small {
  font-size: 13px;
  font-weight: 500;
  color: var(--green-main);
}

.striped-metric-list {
  display: grid;
  gap: 10px;
}

.striped-metric-item {
  display: grid;
  gap: 4px;
}

.striped-metric-top {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: var(--text-secondary);
}

.striped-metric-top b {
  color: var(--text-primary);
}

.striped-track {
  height: 8px;
  background: #f1f5f9;
  border-radius: 99px;
  overflow: hidden;
}

.striped-fill {
  height: 100%;
  border-radius: 99px;
  transition: width 0.3s ease;
}

.striped-fill.green { background: var(--stripe-green); }
.striped-fill.blue { background: var(--stripe-blue); }
.striped-fill.pink { background: var(--stripe-pink); }

/* Main Cards Stack */
.cards-stack {
  display: grid;
  gap: 20px;
  min-width: 0;
}

.card-group {
  background: #fff;
  border: 1px solid var(--border-card);
  border-radius: var(--radius-card);
  padding: 20px;
  box-shadow: var(--shadow-sm);
  min-width: 0;
}

.group-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
  flex-wrap: wrap;
}

.group-title-wrap {
  display: flex;
  align-items: center;
  gap: 10px;
}

.group-title {
  font-size: 17px;
  font-weight: 600;
  margin: 0;
}

.group-tag {
  font-size: 11px;
  font-weight: 700;
  padding: 3px 8px;
  border-radius: 99px;
  background: #e2e8f0;
  color: #334155;
  text-transform: uppercase;
}

.group-tag.hook {
  background: var(--brand-orange-soft);
  color: var(--brand-orange-text);
  border: 1px solid var(--brand-orange-border);
}

/* Reference Strip */
.refs-strip-wrap {
  background: #f8fafc;
  border: 1px solid var(--border-subtle);
  border-radius: 12px;
  padding: 10px 14px;
  margin-bottom: 16px;
}

.refs-strip-header {
  display: flex;
  justify-content: space-between;
  font-size: 11.5px;
  color: var(--text-muted);
  margin-bottom: 6px;
}

.refs {
  display: flex;
  gap: 8px;
  overflow-x: auto;
  scrollbar-width: thin;
  padding-bottom: 4px;
}

.refs img {
  height: 80px;
  min-width: 110px;
  object-fit: cover;
  border-radius: 8px;
  border: 1px solid rgba(0,0,0,0.08);
  cursor: zoom-in;
  background: #000;
  flex-shrink: 0;
}

/* Shots List */
.shots {
  display: grid;
  gap: 14px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.shot-box {
  background: #fcfcfb;
  border: 1px solid var(--border-card);
  border-radius: var(--radius-box);
  padding: 16px;
  display: grid;
  gap: 12px;
  transition: border-color 0.15s, box-shadow 0.15s;
}

.shot-box:focus-within {
  border-color: #93c5fd;
  box-shadow: 0 0 0 1px #93c5fd;
  background: #fff;
}

.shot-top-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  flex-wrap: wrap;
}

.shot-meta-left {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.shot-num {
  font-size: 15px;
  font-weight: 700;
  color: var(--text-primary);
}

.time-seek-pill {
  background: #fff;
  border: 1px solid var(--border-card);
  border-radius: var(--radius-pill);
  padding: 3px 9px;
  font-size: 11.5px;
  font-weight: 500;
  font-family: 'JetBrains Mono', monospace;
  color: var(--text-secondary);
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.time-seek-pill:hover {
  background: var(--blue-soft);
  border-color: #93c5fd;
  color: var(--blue-main);
}

.time-seek-pill.is-playing {
  background: var(--blue-main);
  border-color: var(--blue-main);
  color: #fff;
}

.time-seek-pill:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.prefetch {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: var(--radius-pill);
  background: var(--border-subtle);
  color: var(--text-secondary);
  max-width: 100%;
  overflow-wrap: anywhere;
}
.prefetch:empty { display: none; }
.pf-download { background: #dbeafe; color: #1e40af; }
.pf-siap { background: #dcfce7; color: #166534; }
.pf-gagal { background: #fee2e2; color: #991b1b; }

.z-badge {
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  padding: 2.5px 7px;
  border-radius: 5px;
}

.z-badge.video { background: #dbeafe; color: #1e40af; }
.z-badge.photo { background: #fef3c7; color: #92400e; }
.z-badge.card { background: var(--purple-soft); color: var(--purple-text); border: 1px solid var(--purple-border); }

.state {
  font-size: 11.5px;
  font-weight: 600;
  padding: 3px 9px;
  border-radius: var(--radius-pill);
  display: inline-flex;
  align-items: center;
  gap: 5px;
  width: fit-content;
}

.state::before {
  content: '';
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #9ca3af;
}

.state.ok { background: var(--green-soft); color: var(--green-main); border: 1px solid var(--green-border); }
.state.ok::before { background: var(--green-main); }

.state.warn { background: var(--amber-soft); color: var(--amber-main); border: 1px solid var(--amber-border); }
.state.warn::before { background: var(--amber-main); }

.state.error { background: var(--red-soft); color: var(--red-main); border: 1px solid var(--red-border); }
.state.error::before { background: var(--red-main); }

.state.saved { background: var(--blue-soft); color: var(--blue-main); border: 1px solid #bfdbfe; }
.state.saved::before { background: var(--blue-main); }

.state.missing { background: #f4f4f5; color: #71717a; border: 1px solid #e4e4e7; }
.state.missing::before { background: #a1a1aa; }

.shot-script {
  font-size: 13.5px;
  line-height: 1.5;
  color: #334155;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 10px 12px;
}

.kw-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
}

.kw-row-label {
  font-size: 11px;
  font-weight: 600;
  color: var(--text-muted);
}

.kw-chip {
  border: 1px solid var(--border-card);
  background: #fff;
  color: var(--text-secondary);
  border-radius: 6px;
  padding: 4px 9px;
  font-size: 12px;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-family: inherit;
  transition: all 0.15s;
}

.kw-chip:hover {
  background: #f1f5f9;
  border-color: #cbd5e1;
}

.kw-chip.copied {
  background: var(--green-soft);
  border-color: var(--green-border);
  color: var(--green-main);
}

/* Zentra Prompt Well */
.zentra-prompt-well {
  background: var(--bg-well);
  border: 1px solid var(--border-well);
  border-radius: 12px;
  padding: 10px 12px;
  display: grid;
  gap: 8px;
}

.well-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  flex-wrap: wrap;
}

.well-title {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  font-weight: 600;
  color: #334155;
}

.well-trim-group {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.trim-pill {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  background: rgba(255, 255, 255, 0.85);
  border: 1px solid rgba(148, 163, 184, 0.4);
  border-radius: 6px;
  padding: 2px 7px;
  font-size: 11px;
  font-weight: 500;
  color: var(--text-secondary);
}

.trim-pill input[type="number"] {
  width: 50px;
  border: none;
  background: transparent;
  font-family: 'JetBrains Mono', monospace;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-primary);
  text-align: right;
  padding: 1px 0;
}

.trim-pill input[type="number"]:focus { outline: none; }

.well-input-bar {
  background: #ffffff;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  padding: 4px 6px 4px 10px;
  display: flex;
  align-items: center;
  gap: 8px;
  box-shadow: 0 1px 2px rgba(0,0,0,0.03);
}

.well-input-bar:focus-within {
  border-color: var(--blue-main);
}

.source-token {
  display: inline-flex;
  align-items: center;
  background: var(--brand-orange-soft);
  border: 1px solid var(--brand-orange-border);
  color: var(--brand-orange-text);
  font-size: 11px;
  font-weight: 600;
  padding: 2px 6px;
  border-radius: 4px;
  white-space: nowrap;
  flex-shrink: 0;
  user-select: none;
}

.source-token.empty {
  background: #f1f5f9;
  border-color: #cbd5e1;
  color: #94a3b8;
}

.well-input-bar input[type="text"] {
  flex: 1;
  min-width: 0;
  border: none;
  background: transparent;
  font-family: inherit;
  font-size: 13.5px;
  color: var(--text-primary);
  height: 32px;
}

.well-input-bar input[type="text"]:focus { outline: none; }

.well-actions {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  flex-shrink: 0;
}

.btn-well-ghost {
  border: 1px solid #cbd5e1;
  background: #f8fafc;
  color: var(--text-secondary);
  border-radius: 6px;
  height: 30px;
  padding: 0 8px;
  font-size: 11.5px;
  font-weight: 500;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  font-family: inherit;
}

.btn-well-ghost:hover {
  background: #e2e8f0;
}

.btn-well-upload {
  position: relative;
  overflow: hidden;
  background: #09090b;
  color: #fff;
  border-radius: 6px;
  height: 30px;
  padding: 0 10px;
  font-size: 11.5px;
  font-weight: 600;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  white-space: nowrap;
}

.btn-well-upload input[type="file"] {
  position: absolute;
  inset: 0;
  opacity: 0;
  cursor: pointer;
}

/* Progress Panel */
#progress {
  display: none;
  background: linear-gradient(135deg, #fff5eb 0%, #eff6ff 100%);
  border: 1px solid #bfdbfe;
  border-radius: var(--radius-card);
  padding: 18px 20px;
  gap: 10px;
  margin-bottom: 16px;
}

#progress pre {
  margin: 4px 0 0;
  padding: 10px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.9);
  border: 1px solid #bfdbfe;
  font-family: 'JetBrains Mono', monospace;
  font-size: 11.5px;
  max-height: 120px;
  overflow: auto;
  white-space: pre-wrap;
}

/* Lightbox & Toast */
.lightbox {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.85);
  backdrop-filter: blur(6px);
  z-index: 100;
  display: none;
  place-items: center;
  padding: 20px;
  cursor: zoom-out;
}
.lightbox.open { display: grid; }
.lightbox img {
  max-width: 90%;
  max-height: 85vh;
  border-radius: 12px;
}

.toast-pill {
  position: fixed;
  bottom: 80px;
  left: 50%;
  transform: translateX(-50%) translateY(16px);
  background: #09090b;
  color: #fff;
  padding: 9px 18px;
  border-radius: var(--radius-pill);
  font-size: 13px;
  font-weight: 500;
  box-shadow: 0 4px 16px rgba(0,0,0,0.2);
  z-index: 95;
  opacity: 0;
  pointer-events: none;
  transition: all 0.2s ease;
  white-space: nowrap;
}
.toast-pill.show {
  opacity: 1;
  transform: translateX(-50%) translateY(0);
}

.mobile-dock { display: none; }

@media (max-width: 960px) {
  .workspace-layout {
    grid-template-columns: 1fr;
  }
  .sidebar-sticky {
    position: static;
  }
  .app-container {
    padding: 0 12px;
  }
}

@media (max-width: 640px) {
  body {
    padding-bottom: calc(80px + env(safe-area-inset-bottom));
  }
  html {
    scroll-padding-top: 112px;
    scroll-padding-bottom: calc(80px + env(safe-area-inset-bottom));
  }
  .top-nav {
    padding: 6px 10px;
  }
  .top-nav-inner {
    gap: 4px;
  }
  .nav-pills {
    order: 3;
    width: 100%;
    min-width: 0;
    gap: 2px;
    padding: 2px;
  }
  .nav-pill {
    flex: 1 0 auto;
    justify-content: center;
    min-height: 44px;
    padding: 4px 6px;
    gap: 4px;
    font-size: 12px;
  }
  .sync-status {
    max-width: 170px;
    padding: 4px 8px;
  }
  .nav-right .btn-primary-dark {
    display: none;
  }
  .app-container {
    margin-top: 10px;
    padding: 0 10px;
  }
  .page-header {
    gap: 6px;
    margin-bottom: 10px;
  }
  .page-title {
    font-size: 20px;
    overflow-wrap: anywhere;
  }
  .header-badges {
    gap: 4px;
  }
  .header-badge {
    padding: 3px 8px;
    font-size: 11px;
  }
  .timeline-card, .z-card, .card-group, #progress {
    padding: 10px;
    border-radius: 12px;
  }
  .timeline-card {
    margin-bottom: 10px;
  }
  .timeline-header {
    flex-wrap: wrap;
    gap: 2px 8px;
    margin-bottom: 6px;
  }
  .timeline-track {
    gap: 6px;
    padding-bottom: 2px;
  }
  .timeline-shot-chip {
    min-width: 64px;
    padding: 5px 8px;
    gap: 2px;
  }
  .workspace-layout, .sidebar-sticky, .cards-stack {
    gap: 10px;
  }
  .z-card-header, .group-header {
    margin-bottom: 8px;
  }
  .video-frame video {
    max-height: 140px;
  }
  .readiness-pct {
    font-size: 24px;
    margin: 0 0 6px;
    flex-wrap: wrap;
  }
  .striped-metric-list {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 6px 10px;
  }
  .striped-metric-top {
    gap: 4px;
  }
  .striped-metric-top span {
    min-width: 0;
    overflow-wrap: anywhere;
  }
  .group-title-wrap {
    flex-wrap: wrap;
    gap: 4px 8px;
    min-width: 0;
  }
  .group-title, .state, .shot-script, .kw-chip {
    overflow-wrap: anywhere;
    max-width: 100%;
  }
  .group-title {
    font-size: 15px;
  }
  .refs-strip-wrap {
    padding: 8px;
    margin-bottom: 8px;
  }
  .refs-strip-header {
    flex-wrap: wrap;
    gap: 2px 8px;
  }
  .refs img {
    height: 56px;
    min-width: 78px;
  }
  .shots {
    gap: 8px;
  }
  .shot-box {
    min-width: 0;
    padding: 10px;
    gap: 8px;
  }
  .shot-top-bar, .shot-meta-left {
    gap: 4px 6px;
  }
  .shot-script {
    padding: 6px 8px;
  }
  .kw-chip, .time-seek-pill {
    min-height: 44px;
  }
  .kw-row {
    min-width: 0;
    flex-wrap: nowrap;
    overflow-x: auto;
    padding: 2px 0;
  }
  .kw-row-label, .kw-chip {
    flex-shrink: 0;
  }
  .zentra-prompt-well {
    min-width: 0;
    padding: 8px;
    gap: 6px;
  }
  .well-header {
    flex-direction: column;
    align-items: flex-start;
  }
  .well-trim-group {
    width: 100%;
  }
  .trim-pill {
    flex: 1;
    min-width: 0;
    min-height: 44px;
  }
  .trim-pill input[type="number"] {
    width: 100%;
    min-width: 0;
    min-height: 40px;
    font-size: 16px;
  }
  .trim-pill:focus-within {
    outline: 2px solid var(--blue-main);
    outline-offset: 2px;
  }
  .well-input-bar {
    display: grid;
    grid-template-columns: auto minmax(0, 1fr);
    gap: 4px 6px;
    padding: 4px 6px;
  }
  .well-input-bar input[type="text"] {
    width: 100%;
    height: 44px;
    font-size: 16px;
  }
  .well-actions {
    grid-column: 1 / -1;
    width: 100%;
    gap: 6px;
    border-top: 1px solid #f1f5f9;
    padding-top: 4px;
  }
  .btn-well-ghost, .btn-well-upload {
    flex: 1;
    height: 44px;
    justify-content: center;
  }
  .btn-well-upload:focus-within {
    outline: 2px solid var(--blue-main);
    outline-offset: 2px;
  }
  .toast-pill {
    max-width: calc(100% - 20px);
    white-space: normal;
    overflow-wrap: anywhere;
    bottom: calc(80px + env(safe-area-inset-bottom));
  }
  .mobile-dock {
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    background: rgba(9, 9, 11, 0.95);
    backdrop-filter: blur(10px);
    padding: 8px 10px calc(8px + env(safe-area-inset-bottom));
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    z-index: 90;
    border-top: 1px solid rgba(255,255,255,0.1);
  }
  .mobile-dock-btn {
    flex: 0 0 auto;
    min-height: 44px;
    background: #fff;
    color: #09090b;
    border: none;
    border-radius: var(--radius-pill);
    padding: 11px;
    font-size: 14px;
    font-weight: 700;
    cursor: pointer;
  }
}
"""

_JS = r"""
let toastTimer = null;
function showToast(text) {
  const t = document.getElementById('toast');
  if (!t) return;
  t.textContent = text;
  t.classList.add('show');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => t.classList.remove('show'), 2200);
}

function setMsg(text, withToast = false) {
  const m1 = document.getElementById('msg');
  if (m1) m1.textContent = text || 'Tersimpan otomatis';
  const m2 = document.getElementById('mobile-msg');
  if (m2) m2.textContent = text || 'Tersimpan otomatis';
  if (withToast && text) showToast(text);
}

function detectSourceToken(rawUrl) {
  const v = (rawUrl || '').trim().toLowerCase();
  if (!v) return { label: '/empty', empty: true };
  if (v.startsWith('file:')) return { label: '/local-file', empty: false };
  if (v.includes('douyin.com')) return { label: '/douyin', empty: false };
  if (v.includes('tiktok.com')) return { label: '/tiktok', empty: false };
  if (v.includes('pinterest.com') || v.includes('pin.it')) return { label: '/pinterest', empty: false };
  if (v.includes('youtube.com') || v.includes('youtu.be')) return { label: '/youtube', empty: false };
  if (v.includes('instagram.com')) return { label: '/instagram', empty: false };
  return { label: '/web-url', empty: false };
}

function updateLiveCounts() {
  const boxes = document.querySelectorAll('.shot-box[data-shot-box]');
  const total = boxes.length;
  let filled = 0;
  let missing = 0;
  let issue = 0;

  boxes.forEach(box => {
    const idx = box.dataset.shotBox;
    const inp = box.querySelector(`input[data-shot="${idx}"]`);
    const badge = box.querySelector(`[data-state-badge="${idx}"]`);
    const tokenEl = box.querySelector(`[data-token-badge="${idx}"]`);
    const chip = document.getElementById(`timeline-chip-${idx}`);
    const val = inp ? inp.value.trim() : '';
    const hasVal = val.length > 0;
    const rawStatus = box.dataset.status || '';

    if (tokenEl) {
      const tk = detectSourceToken(val);
      tokenEl.textContent = tk.label;
      tokenEl.classList.toggle('empty', tk.empty);
    }

    if (hasVal) {
      filled++;
      box.classList.add('is-filled');
      if (chip) chip.classList.add('is-filled');
      if ((rawStatus === 'missing' || !rawStatus) && badge) {
        badge.className = 'state saved';
        badge.textContent = 'TERSIMPAN';
      }
    } else {
      missing++;
      box.classList.remove('is-filled');
      if (chip) chip.classList.remove('is-filled');
      if (badge) {
        badge.className = 'state missing';
        badge.textContent = 'KOSONG';
      }
    }

    if (rawStatus === 'error' || rawStatus === 'warn') {
      issue++;
    }
  });

  const pct = total ? Math.round((filled / total) * 100) : 0;
  const setTxt = (id, v) => {
    const el = document.getElementById(id);
    if (el) el.textContent = v;
  };

  setTxt('count-all', total);
  setTxt('count-missing', missing);
  setTxt('count-filled', filled);
  setTxt('count-issue', issue);
  setTxt('big-pct-text', `${pct}.0%`);
  setTxt('big-delta-text', `+${filled} klip terisi`);
  setTxt('timeline-summary-text', `${filled}/${total} shot terhubung (${pct}%)`);
}

function scrollToShot(idx) {
  document.querySelectorAll('.timeline-shot-chip').forEach(c => c.classList.remove('is-active'));
  const chip = document.getElementById(`timeline-chip-${idx}`);
  if (chip) chip.classList.add('is-active');

  const box = document.querySelector(`.shot-box[data-shot-box="${idx}"]`);
  if (box) {
    box.scrollIntoView({ behavior: 'smooth', block: 'center' });
    const inp = box.querySelector(`input[data-shot="${idx}"]`);
    if (inp) setTimeout(() => inp.focus(), 300);
  }
}

function filterShots(mode, btn) {
  document.querySelectorAll('.nav-pill').forEach(b => b.classList.remove('active'));
  if (btn) btn.classList.add('active');

  document.querySelectorAll('.card-group[data-group]').forEach(card => {
    let visibleInCard = 0;
    card.querySelectorAll('.shot-box[data-shot-box]').forEach(box => {
      const idx = box.dataset.shotBox;
      const inp = box.querySelector(`input[data-shot="${idx}"]`);
      const hasVal = inp && inp.value.trim().length > 0;
      const st = box.dataset.status || '';

      let show = true;
      if (mode === 'missing') show = !hasVal;
      else if (mode === 'filled') show = hasVal;
      else if (mode === 'issue') show = (st === 'error' || st === 'warn');

      box.style.display = show ? 'grid' : 'none';
      if (show) visibleInCard++;
    });
    card.style.display = visibleInCard > 0 ? 'block' : 'none';
  });
}

// Tombol waktu di tiap shot muter suara naskah beat itu (start_s/end_s itu waktu di voice.mp3, bukan di source).
let beatStop = null;
function clearPlaying() {
  document.querySelectorAll('.time-seek-pill.is-playing').forEach(b => b.classList.remove('is-playing'));
}
function playBeat(btn, start, end) {
  const a = document.getElementById('voice');
  if (!a) return;
  const active = document.querySelector('.time-seek-pill.is-playing');
  clearPlaying();
  if (active === btn) { a.pause(); beatStop = null; return; }
  a.currentTime = start;
  beatStop = end;
  btn.classList.add('is-playing');
  a.play().catch(() => {});
}
const voiceEl = document.getElementById('voice');
if (voiceEl) {
  voiceEl.addEventListener('timeupdate', () => {
    if (beatStop !== null && voiceEl.currentTime >= beatStop) { voiceEl.pause(); beatStop = null; clearPlaying(); }
  });
  voiceEl.addEventListener('ended', clearPlaying);
}

const sourceVideoEl = document.getElementById('source-video');
if (sourceVideoEl) {
  sourceVideoEl.addEventListener('timeupdate', () => {
    const ind = document.getElementById('video-time-indicator');
    if (ind) {
      const t = sourceVideoEl.currentTime;
      const m = String(Math.floor(t / 60)).padStart(2, '0');
      const s = (t % 60).toFixed(1).padStart(4, '0');
      ind.textContent = `${m}:${s}`;
    }
  });
}

function openLightbox(src) {
  const lb = document.getElementById('lightbox');
  const img = document.getElementById('lightbox-img');
  if (lb && img) {
    img.src = src;
    lb.classList.add('open');
  }
}

async function pasteToShot(idx) {
  const inp = document.querySelector(`input[data-shot="${idx}"]`);
  if (!inp) return;
  try {
    const text = await navigator.clipboard.readText();
    if (text) {
      inp.value = text.trim();
      inp.dispatchEvent(new Event('input', { bubbles: true }));
      showToast(`Link ter-paste di Shot ${idx + 1}`);
    } else {
      inp.focus();
      showToast('Clipboard kosong');
    }
  } catch (e) {
    inp.focus();
    showToast('Tekan & tahan untuk paste');
  }
}

function clearShot(idx) {
  const inp = document.querySelector(`input[data-shot="${idx}"]`);
  if (!inp) return;
  inp.value = '';
  inp.dispatchEvent(new Event('input', { bubbles: true }));
  showToast(`Shot ${idx + 1} dibersihkan`);
}

function collectShots() {
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
  updateLiveCounts();
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
        const data = await res.json();
        if (data.urls) setPrefetchUrls(data.urls);
        pollProgress();
      } else {
        setMsg('Gagal simpan');
      }
    } catch (e) {
      setMsg('Gagal simpan');
    }
  }, 750);
}

// Habis autosave, badge prefetch nempel ke URL yang baru disimpan; label lama dihapus sampai poll berikutnya.
function setPrefetchUrls(urls) {
  document.querySelectorAll('.prefetch[data-shot-badge]').forEach(el => {
    const url = urls[el.dataset.shotBadge] || '';
    if (el.dataset.prefetchUrl === url) return;
    el.dataset.prefetchUrl = url;
    el.textContent = '';
    el.className = 'prefetch pf-';
  });
}

document.addEventListener('input', (e) => {
  if (e.target.matches('input[data-shot], input[data-time-start], input[data-time-end]')) {
    scheduleAutoSave();
  }
});

async function save() {
  clearTimeout(autoSaveTimer);
  setMsg('Menyimpan...');
  const shots = collectShots();
  try {
    const res = await fetch('/api/links', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({shots, retry: true})  // klik Simpan = link yang gagal dicoba lagi
    });
    if (res.ok) {
      const data = await res.json();
      const missingText = (data.missing || []).map(m => typeof m === 'number' ? `shot ${m + 1}` : m).join(', ') || '-';
      setMsg(`Tersimpan · Kosong: ${missingText}`, true);
      setTimeout(() => location.reload(), 600);
      return;
    }
  } catch (e) {}
  updateLiveCounts();
  setMsg('Tersimpan', true);
}

async function uploadShot(shotIndex, input) {
  const file = input.files[0];
  if (!file) return;
  setMsg(`Upload shot ${shotIndex + 1} (${file.name})...`, true);
  const shots = collectShots();
  try {
    const saved = await fetch('/api/links', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({shots})
    });
    if (saved.ok) {
      const res = await fetch(`/api/upload?shot=${encodeURIComponent(shotIndex)}`, {
        method: 'POST',
        headers: {'X-Filename': encodeURIComponent(file.name)},
        body: file
      });
      if (res.ok) {
        location.reload();
        return;
      }
    }
  } catch (e) {}

  const inp = document.querySelector(`input[data-shot="${shotIndex}"]`);
  if (inp) {
    inp.value = `file:${file.name}`;
    updateLiveCounts();
    setMsg(`File: ${file.name}`, true);
  }
}

const STATE_LABEL = {
  running: 'Lagi download & potong klip...',
  done: 'Selesai · Siap review di Remotion Studio',
  awaiting: 'Menunggu input link klip',
  failed: 'Berhenti karena error'
};

function renderProgressUI(p) {
  const box = document.getElementById('progress');
  if (!box || !p.state) return;
  box.style.display = 'grid';
  box.replaceChildren();

  const header = document.createElement('div');
  header.style.display = 'flex';
  header.style.justifyContent = 'space-between';
  header.style.alignItems = 'center';
  header.innerHTML = `<b style="font-size:14px;letter-spacing:-0.02em;">Pipeline: ${STATE_LABEL[p.state] || p.state}</b><span class="source-token">/fetch-worker</span>`;
  box.appendChild(header);

  function addStripedBar(label, done, total, colorClass) {
    const pct = total ? Math.round(100 * (Number(done) || 0) / total) : 0;
    const item = document.createElement('div');
    item.className = 'striped-metric-item';
    item.innerHTML = `
      <div class="striped-metric-top"><span>${label}</span><b>${done}/${total} (${pct}%)</b></div>
      <div class="striped-track"><div class="striped-fill ${colorClass}" style="width:${pct}%"></div></div>
    `;
    box.appendChild(item);
  }

  addStripedBar('Links Downloaded', p.links_done, p.links_total, 'blue');
  addStripedBar('Shots Processed', p.shots_done, p.shots_total, 'green');

  if (p.log && p.log.length) {
    const pre = document.createElement('pre');
    pre.textContent = p.log.slice(-8).join('\n');
    box.appendChild(pre);
  }
}

let lastState = null;
const PREFETCH_LABEL = {antre: 'antre', download: 'download…', siap: 'siap', gagal: 'gagal'};
function renderPrefetch(states) {
  for (const [url, st] of Object.entries(states)) {
    document.querySelectorAll('.prefetch').forEach(el => {
      if (el.dataset.prefetchUrl !== url) return;
      let label = PREFETCH_LABEL[st.state] || '';
      if (st.state === 'gagal' && st.message) label += ': ' + st.message;
      el.textContent = label;
      el.className = 'prefetch pf-' + st.state;
    });
  }
}
async function pollProgress() {
  try {
    const p = await (await fetch('/api/progress')).json();
    if (p.prefetch) renderPrefetch(p.prefetch);
    if (p.state) {
      renderProgressUI(p);
      if (lastState === 'running' && p.state !== 'running') location.reload();
      lastState = p.state;
    }
  } catch (e) {}
}
pollProgress(); setInterval(pollProgress, 2000);

function copyText(t, btn) {
  function done() {
    setMsg(`Ke-copy: ${t}`, true);
    if (btn) {
      btn.classList.add('copied');
      setTimeout(() => btn.classList.remove('copied'), 1200);
    }
  }
  if (navigator.clipboard && window.isSecureContext) {
    navigator.clipboard.writeText(t).then(done).catch(() => fallbackCopy(t, done));
  } else {
    fallbackCopy(t, done);
  }
}

function fallbackCopy(t, cb) {
  const ta = document.createElement('textarea');
  ta.value = t;
  ta.style.position = 'fixed';
  ta.style.left = '-9999px';
  document.body.appendChild(ta);
  ta.focus();
  ta.select();
  try {
    document.execCommand('copy');
    if (cb) cb();
  } catch (e) {
    setMsg(`Gagal copy`, true);
  }
  document.body.removeChild(ta);
}

updateLiveCounts();
"""


def _detect_token(url: str) -> tuple[str, str]:
    v = url.strip().lower()
    if not v:
        return "/empty", "empty"
    if v.startswith("file:"):
        return "/local-file", ""
    if "douyin.com" in v:
        return "/douyin", ""
    if "tiktok.com" in v:
        return "/tiktok", ""
    if "pinterest.com" in v or "pin.it" in v:
        return "/pinterest", ""
    if "youtube.com" in v or "youtu.be" in v:
        return "/youtube", ""
    if "instagram.com" in v:
        return "/instagram", ""
    return "/web-url", ""


PREFETCH_LABEL = {"antre": "antre", "download": "download…", "siap": "siap", "gagal": "gagal"}


def _prefetch_badge(idx: int, url: str, state: dict | None) -> str:
    """Selalu ada (kosong kalau belum ada link), biar JS bisa nempelin URL baru habis autosave tanpa reload."""
    st = (state or {}).get("state", "") if url else ""
    label = PREFETCH_LABEL.get(st, "")
    if st == "gagal" and (state or {}).get("message"):
        label += f": {state['message']}"
    return (f'<span class="prefetch pf-{escape(st)}" data-shot-badge="{idx}" data-prefetch-url="{escape(url, quote=True)}">'
            f'{escape(label)}</span>')


def _shot_row(shot: dict, group: dict, entry: dict | str | None, state: dict, voice_ok: bool = False,
              prefetch: dict | None = None) -> str:
    s_idx = shot["index"]
    pill_attr = (f'onclick="playBeat(this, {shot["start_s"]:.1f}, {shot["end_s"]:.1f})"' if voice_ok
                 else 'disabled title="suara belum ada"')
    refs = "".join(f'<img src="/files/{escape(f)}" onclick="openLightbox(this.src)" loading="lazy">' for f in shot.get("ref_frames", []))

    kw_list = []
    for lang in ("en", "zh"):
        kw_list.extend(shot.get("keywords", {}).get(lang, []))
    if not kw_list:
        for lang in ("en", "zh"):
            kw_list.extend(group.get("keywords", {}).get(lang, []))

    keywords = "".join(
        f'<button type="button" class="kw-chip" onclick=\'copyText({escape(json.dumps(k), quote=True)}, this)\'>'
        f'<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>'
        f'{escape(k)}</button>'
        for k in kw_list
    )

    countdown_badge = (f'<span class="z-badge card">CARD #{int(shot["countdown"])}</span>'
                       if shot.get("countdown") else "")
    media_badge = f'<span class="z-badge {escape(shot.get("media", "video"))}">{escape(shot.get("media", "video"))}</span>'

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

    token_label, token_empty = _detect_token(url_val)
    token_empty_cls = "empty" if token_empty else ""

    return f"""
    <div class="shot-box {'is-filled' if has_val else ''}" data-shot-box="{s_idx}" data-status="{css}">
      <div class="shot-top-bar">
        <div class="shot-meta-left">
          <span class="shot-num">Shot {s_idx + 1:02d}</span>
          <button type="button" class="time-seek-pill" {pill_attr}>
            <svg width="10" height="10" viewBox="0 0 24 24" fill="currentColor"><polygon points="5 3 19 12 5 21 5 3"/></svg>
            {shot['start_s']:.1f}s – {shot['end_s']:.1f}s
          </button>
          {media_badge}
          {countdown_badge}
        </div>
        <div class="state {css}" data-state-badge="{s_idx}">{label} {message}</div>
        {_prefetch_badge(s_idx, entry.get("url", "") if isinstance(entry, dict) else "", (prefetch or {}).get(entry.get("url", "")) if isinstance(entry, dict) else None)}
      </div>

      <div class="shot-script">
        {escape(shot.get('text', ''))}
      </div>

      {f'<div class="refs">{refs}</div>' if refs else ''}

      <div class="kw-row">
        <span class="kw-row-label">Keywords:</span>
        {keywords or '<i style="color:var(--text-muted);font-size:12px;">tanpa keyword</i>'}
      </div>

      <div class="zentra-prompt-well">
        <div class="well-header">
          <span class="well-title">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="#64748b"><path d="M12 2L14.8 9.2L22 12L14.8 14.8L12 22L9.2 14.8L2 12L9.2 9.2L12 2Z"/></svg>
            Klip video / gambar
          </span>
          <div class="well-trim-group">
            <label class="trim-pill">Mulai <input type="number" step="0.1" min="0" data-time-start="{s_idx}" value="{escape(start_val)}" placeholder="0.0">s</label>
            <label class="trim-pill">Selesai <input type="number" step="0.1" min="0" data-time-end="{s_idx}" value="{escape(end_val)}" placeholder="auto">s</label>
          </div>
        </div>
        <div class="well-input-bar">
          <span class="source-token {token_empty_cls}" data-token-badge="{s_idx}">{token_label}</span>
          <input type="text" data-shot="{s_idx}" value="{escape(url_val)}" placeholder="Paste link Douyin/TikTok/Pinterest atau upload file...">
          <div class="well-actions">
            <button type="button" class="btn-well-ghost" onclick="pasteToShot({s_idx})">Paste</button>
            <button type="button" class="btn-well-ghost" onclick="clearShot({s_idx})">Clear</button>
            <label class="btn-well-upload">
              <span>Upload</span>
              <input type="file" accept="video/*,image/*" onchange="uploadShot({s_idx}, this)">
            </label>
          </div>
        </div>
      </div>
    </div>"""


def _card(group: dict, shots: list[dict], links: dict, status: dict, voice_ok: bool = False,
          prefetch: dict | None = None) -> str:
    is_hook = group["id"] == "hook"

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

        shot_rows.append(_shot_row(shot, group, entry, st, voice_ok, prefetch))

    return f"""
<section class="card-group card" data-group="{escape(group['id'], quote=True)}">
  <div class="group-header">
    <div class="group-title-wrap">
      <h2 class="group-title">{escape(group['label'])}</h2>
      <span class="group-tag {'hook' if is_hook else ''}">Kelompok · {len(shots)} Shot</span>
    </div>
  </div>
  <div class="shots">{''.join(shot_rows)}</div>
</section>"""


def render_page(run_id: str, plan: dict, links: dict, status: dict, source: str | None = None,
                voice: str | None = None, prefetch: dict | None = None) -> str:
    shots = {shot["index"]: shot for shot in plan["shots"]}
    groups = plan["groups"]

    if "shots" in links:
        filled_shots = sum(1 for shot in plan["shots"] if str(shot["index"]) in links["shots"] and links["shots"][str(shot["index"])])
        filled_groups = sum(1 for g in groups if all(str(i) in links["shots"] and links["shots"][str(i)] for i in g["shots"]))
    else:
        entries = links.get("groups", {})
        filled_groups = sum(1 for group in groups if entries.get(group["id"]))
        filled_shots = sum(min(len(g["shots"]), len(entries.get(g["id"], []))) for g in groups)

    total_shots = len(plan["shots"])
    total_duration = plan["shots"][-1]["end_s"] if plan["shots"] else 0.0
    pct = round(100 * filled_shots / total_shots) if total_shots else 0

    # Compact timeline chips
    timeline_chips = []
    for shot in plan["shots"]:
        s_idx = shot["index"]
        dur = max(0.5, shot["end_s"] - shot["start_s"])

        has_val = False
        if "shots" in links:
            has_val = bool(links["shots"].get(str(s_idx)))
        elif "groups" in links:
            g_id = shot.get("group")
            if g_id and g_id in links["groups"]:
                g_shots = next((g["shots"] for g in groups if g["id"] == g_id), [])
                if s_idx in g_shots and len(links["groups"][g_id]) > g_shots.index(s_idx):
                    has_val = bool(links["groups"][g_id][g_shots.index(s_idx)])

        filled_cls = "is-filled" if has_val else ""
        timeline_chips.append(f"""
        <div class="timeline-shot-chip {filled_cls}" id="timeline-chip-{s_idx}" onclick="scrollToShot({s_idx})">
          <span class="timeline-shot-num">Shot {s_idx + 1:02d}</span>
          <span class="timeline-shot-dur">{dur:.1f}s</span>
          <div class="timeline-shot-bar"></div>
        </div>""")

    # Group striped metric bars
    colors = ["green", "blue", "pink"]
    group_metrics_html = []
    for idx, g in enumerate(groups):
        g_shots = g["shots"]
        g_filled = sum(1 for i in g_shots if (str(i) in links.get("shots", {}) and links["shots"][str(i)]))
        g_pct = round(100 * g_filled / len(g_shots)) if g_shots else 0
        color = colors[idx % len(colors)]
        group_metrics_html.append(f"""
        <div class="striped-metric-item">
          <div class="striped-metric-top">
            <span>{escape(g['label'])} ({len(g_shots)} shots)</span>
            <b id="bar-group-{idx}-label">{g_pct}%</b>
          </div>
          <div class="striped-track">
            <div class="striped-fill {color}" id="bar-group-{idx}-fill" style="width: {g_pct}%"></div>
          </div>
        </div>""")

    cards = "".join(
        _card(group, [shots[i] for i in group["shots"]], links, status, voice is not None, prefetch)
        for group in groups
    )

    if source:
        aside = f"""
        <aside class="sidebar-sticky">
          <div class="z-card">
            <div class="z-card-header">
              <h2 class="z-card-title">Video Source</h2>
              <span class="z-badge video" id="video-time-indicator">00:00.0</span>
            </div>
            <div class="video-frame">
              <video src="/files/{escape(source, quote=True)}" id="source-video" controls preload="metadata"></video>
            </div>
          </div>

          <div class="z-card">
            <div class="z-card-header">
              <h2 class="z-card-title">Kesiapan Klip</h2>
              <span class="state ok">{filled_shots}/{total_shots} Terisi</span>
            </div>
            <div class="readiness-pct">
              <span id="big-pct-text">{pct}.0%</span>
              <small id="big-delta-text">+{filled_shots} klip terisi</small>
            </div>
            <div class="striped-metric-list">
              {''.join(group_metrics_html)}
            </div>
          </div>
        </aside>"""
    else:
        aside = ""

    return f"""<!doctype html>
<html lang="id">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=5, viewport-fit=cover">
  <title>Brief #{escape(run_id)} — Zentra Studio</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@500&display=swap" rel="stylesheet">
  <style>{_CSS}</style>
</head>
<body>
{f'<audio id="voice" src="/files/{escape(voice, quote=True)}" preload="metadata"></audio>' if voice else ''}
<header class="top-nav">
  <div class="top-nav-inner">
    <a href="#" class="brand" onclick="return false;">
      <span class="brand-mark">
        <svg viewBox="0 0 24 24"><path d="M7 17L17 7M7 7h10v10"/></svg>
      </span>
      <span>zentra</span>
    </a>

    <nav class="nav-pills" role="tablist">
      <button type="button" class="nav-pill active" onclick="filterShots('all', this)">
        Semua <span class="nav-count" id="count-all">{total_shots}</span>
      </button>
      <button type="button" class="nav-pill" onclick="filterShots('missing', this)">
        Kosong <span class="nav-count" id="count-missing">{total_shots - filled_shots}</span>
      </button>
      <button type="button" class="nav-pill" onclick="filterShots('filled', this)">
        Terisi <span class="nav-count" id="count-filled">{filled_shots}</span>
      </button>
      <button type="button" class="nav-pill" onclick="filterShots('issue', this)">
        Flagged <span class="nav-count" id="count-issue">0</span>
      </button>
    </nav>

    <div class="nav-right">
      <div class="sync-status">
        <span class="sync-dot"></span>
        <span id="msg">Tersimpan otomatis</span>
      </div>
      <button type="button" class="btn-primary-dark" onclick="save()">Simpan Brief</button>
    </div>
  </div>
</header>

<div class="app-container">
  <div class="page-header">
    <h1 class="page-title">Brief #{escape(run_id)}</h1>
    <div class="header-badges">
      <div class="header-badge">
        <span>⏱ 0.0s – {total_duration:.1f}s Source</span>
      </div>
      <div class="header-badge" id="stats-capsule">
        <span id="stats-text">{filled_shots}/{total_shots} shot ({filled_groups}/{len(groups)} kelompok)</span>
      </div>
    </div>
  </div>

  <div class="timeline-card">
    <div class="timeline-header">
      <h2 class="timeline-title">Pacing & Timeline Shot</h2>
      <span class="timeline-summary" id="timeline-summary-text">{filled_shots}/{total_shots} shot terhubung ({pct}%)</span>
    </div>
    <div class="timeline-track">
      {''.join(timeline_chips)}
    </div>
  </div>

  <div class="workspace-layout{'' if source else ' nosource'}">
    {aside}
    <main class="cards-stack">
      <section id="progress"></section>
      {cards}
    </main>
  </div>
</div>

<div class="mobile-dock">
  <div style="display:flex;flex-direction:column;min-width:0;">
    <small style="font-size:10px;text-transform:uppercase;color:#a1a1aa;">Brief Sync</small>
    <span id="mobile-msg" style="font-size:12px;color:#fff;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">Tersimpan otomatis</span>
  </div>
  <button type="button" class="mobile-dock-btn" onclick="save()">Simpan Brief</button>
</div>

<div id="toast" class="toast-pill"></div>
<div id="lightbox" class="lightbox" onclick="this.classList.remove('open')">
  <img id="lightbox-img" src="" alt="Preview Frame">
</div>

<script>{_JS}</script>
</body>
</html>"""
