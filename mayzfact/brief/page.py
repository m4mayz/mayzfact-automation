"""HTML halaman brief gaya Zentra Studio: responsive bento grid, frosted prompt wells, pacer chart, live filters."""

from __future__ import annotations

import json
from html import escape

_CSS = """
:root {
  --bg-canvas: #eeeeec;
  --bg-shell: #f7f7f5;
  --bg-card: #ffffff;
  --bg-subtle: #f4f4f1;
  --border-hairline: #e6e6e2;
  --border-card: #ebebe7;
  --border-strong: #d6d6d0;

  --text-primary: #111110;
  --text-secondary: #4a4a46;
  --text-muted: #8e8e88;
  --text-faint: #b5b5af;

  --ink-pill: #18181b;
  --brand-orange: #ff7a00;
  --brand-orange-soft: #fff0db;
  --brand-orange-border: #fdba74;
  --brand-orange-text: #c2410c;

  --cobalt-deep: #0037d6;
  --cobalt-main: #2563eb;
  --cobalt-light: #dbeafe;

  --emerald-main: #16a34a;
  --emerald-soft: #dcfce7;

  --pink-main: #ec4899;
  --pink-soft: #fce7f3;

  --radius-shell: 28px;
  --radius-card: 22px;
  --radius-well: 16px;
  --radius-input: 12px;
  --radius-pill: 999px;

  --shadow-shell: 0 20px 60px rgba(0, 0, 0, 0.06), 0 1px 3px rgba(0, 0, 0, 0.04);
  --shadow-card: 0 2px 10px rgba(0, 0, 0, 0.025), 0 1px 2px rgba(0, 0, 0, 0.02);
  --shadow-pill: 0 4px 14px rgba(0, 0, 0, 0.07), 0 1px 2px rgba(0, 0, 0, 0.04);
  --shadow-dark-pill: 0 6px 14px rgba(24, 24, 27, 0.22);

  --stripe-blue: repeating-linear-gradient(
    -45deg,
    #1e5eff 0px,
    #1e5eff 4px,
    #4e82ff 4px,
    #4e82ff 8px
  );
  --stripe-green: repeating-linear-gradient(
    -45deg,
    #16a34a 0px,
    #16a34a 3.5px,
    #4ade80 3.5px,
    #4ade80 7px
  );
  --stripe-pink: repeating-linear-gradient(
    -45deg,
    #db2777 0px,
    #db2777 3.5px,
    #f472b6 3.5px,
    #f472b6 7px
  );
  --stripe-amber: repeating-linear-gradient(
    -45deg,
    #d97706 0px,
    #d97706 3.5px,
    #fbbf24 3.5px,
    #fbbf24 7px
  );
}

* {
  box-sizing: border-box;
  -webkit-tap-highlight-color: transparent;
}

body {
  margin: 0;
  background-color: var(--bg-canvas);
  color: var(--text-primary);
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  line-height: 1.45;
  padding: 18px 18px 60px;
}

.app-shell {
  max-width: 1400px;
  margin: 0 auto;
  background: var(--bg-shell);
  border-radius: var(--radius-shell);
  border: 1px solid rgba(255, 255, 255, 0.8);
  box-shadow: var(--shadow-shell);
  padding: 20px 28px 36px;
}

.top-nav {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding-bottom: 24px;
}

.brand {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  text-decoration: none;
  color: var(--text-primary);
  user-select: none;
}

.brand-mark {
  width: 28px;
  height: 28px;
  border-radius: 8px;
  background: linear-gradient(135deg, #ff9900 0%, #ff6200 100%);
  display: grid;
  place-items: center;
  box-shadow: 0 2px 6px rgba(255, 106, 0, 0.3);
  flex-shrink: 0;
}

.brand-mark svg {
  width: 16px;
  height: 16px;
  stroke: #fff;
  stroke-width: 2.2;
  fill: none;
}

.brand-name {
  font-size: 19px;
  font-weight: 600;
  letter-spacing: -0.03em;
  color: #18181b;
}

.nav-pills {
  display: flex;
  align-items: center;
  gap: 6px;
  overflow-x: auto;
  scrollbar-width: none;
  padding: 4px;
}
.nav-pills::-webkit-scrollbar { display: none; }

.nav-pill {
  border: none;
  background: transparent;
  color: var(--text-secondary);
  font-family: inherit;
  font-size: 13.5px;
  font-weight: 500;
  padding: 8px 16px;
  border-radius: 11px;
  cursor: pointer;
  white-space: nowrap;
  display: inline-flex;
  align-items: center;
  gap: 7px;
  transition: all 0.18s cubic-bezier(0.16, 1, 0.3, 1);
}

.nav-pill:hover {
  color: var(--text-primary);
  background: rgba(0, 0, 0, 0.04);
}

.nav-pill.active {
  background: var(--ink-pill);
  color: #ffffff;
  font-weight: 500;
  box-shadow: var(--shadow-dark-pill);
}

.nav-count {
  font-size: 11px;
  font-weight: 600;
  padding: 1px 6px;
  border-radius: 99px;
  background: rgba(0, 0, 0, 0.07);
  color: inherit;
}

.nav-pill.active .nav-count {
  background: rgba(255, 255, 255, 0.2);
  color: #fff;
}

.nav-right {
  display: flex;
  align-items: center;
  gap: 10px;
}

.sync-status {
  font-size: 12.5px;
  font-weight: 500;
  color: var(--text-muted);
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: #fff;
  padding: 6px 12px;
  border-radius: var(--radius-pill);
  border: 1px solid var(--border-hairline);
  max-width: 260px;
}

.sync-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--emerald-main);
  flex-shrink: 0;
}

#msg {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.btn-primary-dark {
  background: var(--ink-pill);
  color: #fff;
  border: none;
  border-radius: 11px;
  padding: 9px 18px;
  font-family: inherit;
  font-size: 13.5px;
  font-weight: 500;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  box-shadow: var(--shadow-dark-pill);
  transition: transform 0.12s ease, opacity 0.15s ease;
}

.btn-primary-dark:hover { opacity: 0.92; }
.btn-primary-dark:active { transform: scale(0.97); }

.overview-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 16px;
  margin-bottom: 22px;
}

.overview-title-group {
  display: flex;
  align-items: center;
  gap: 12px;
}

.overview-title {
  font-size: 34px;
  font-weight: 500;
  letter-spacing: -0.035em;
  margin: 0;
  color: var(--text-primary);
  line-height: 1.05;
}

.circle-icon-btn {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: #ffffff;
  border: 1px solid var(--border-hairline);
  box-shadow: var(--shadow-card);
  display: inline-grid;
  place-items: center;
  cursor: pointer;
  color: var(--text-secondary);
  transition: transform 0.15s ease, border-color 0.15s ease;
  flex-shrink: 0;
}

.circle-icon-btn:hover {
  border-color: var(--border-strong);
  color: var(--text-primary);
  transform: translateY(-1px);
}

.circle-icon-btn svg {
  width: 15px;
  height: 15px;
  stroke: currentColor;
  stroke-width: 1.8;
  fill: none;
}

.connected-capsules {
  display: inline-flex;
  align-items: center;
  background: #ebebe7;
  padding: 3px;
  border-radius: 13px;
  gap: 0;
}

.capsule-white {
  background: #ffffff;
  border: 1px solid rgba(0, 0, 0, 0.05);
  border-radius: 10px;
  padding: 7px 13px;
  font-size: 12.5px;
  font-weight: 500;
  color: var(--text-primary);
  display: inline-flex;
  align-items: center;
  gap: 7px;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.03);
  cursor: pointer;
  font-family: inherit;
}

.capsule-white svg {
  width: 14px;
  height: 14px;
  stroke: var(--text-muted);
  stroke-width: 1.8;
  fill: none;
}

.capsule-bridge {
  font-size: 12px;
  color: var(--text-muted);
  padding: 0 10px;
  font-weight: 400;
  user-select: none;
}

.bento-top {
  display: grid;
  grid-template-columns: 1.65fr 1fr;
  gap: 16px;
  margin-bottom: 20px;
}

.z-card {
  background: var(--bg-card);
  border: 1px solid var(--border-card);
  border-radius: var(--radius-card);
  padding: 22px 24px;
  box-shadow: var(--shadow-card);
  position: relative;
}

.z-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 18px;
}

.z-card-title {
  font-size: 17px;
  font-weight: 500;
  letter-spacing: -0.02em;
  color: var(--text-primary);
  margin: 0;
  display: flex;
  align-items: center;
  gap: 10px;
}

.shot-columns-chart {
  display: grid;
  grid-auto-flow: column;
  grid-auto-columns: minmax(90px, 1fr);
  overflow-x: auto;
  scrollbar-width: thin;
  border-top: 1px solid #f2f2ef;
  position: relative;
  padding-top: 8px;
}

.shot-col {
  padding: 8px 12px 0;
  border-right: 1px solid #f0f0ec;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  min-height: 158px;
  cursor: pointer;
  transition: background 0.2s ease;
  position: relative;
}

.shot-col:last-child { border-right: none; }

.shot-col.is-active {
  background: linear-gradient(180deg, rgba(219, 234, 254, 0.45) 0%, rgba(219, 234, 254, 0.05) 100%);
}

.shot-col-label {
  font-size: 11.5px;
  color: var(--text-muted);
  font-weight: 400;
  margin-bottom: 4px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.shot-col.is-active .shot-col-label {
  color: var(--text-primary);
  font-weight: 500;
}

.shot-col-val {
  font-size: 22px;
  font-weight: 500;
  letter-spacing: -0.03em;
  color: #9ca3af;
  margin-bottom: 14px;
}

.shot-col.is-active .shot-col-val,
.shot-col:hover .shot-col-val {
  color: var(--text-primary);
}

.shot-col-bar-wrap {
  margin-top: auto;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
}

.col-handle {
  width: 18px;
  height: 4px;
  border-radius: 99px;
  background: #93c5fd;
}

.shot-col-bar {
  width: 100%;
  border-radius: 4px 4px 0 0;
  background: var(--stripe-blue);
  transition: height 0.3s ease;
  position: relative;
  overflow: hidden;
}

.shot-col-bar::after {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(180deg, rgba(255,255,255,0) 0%, rgba(255,255,255,0.65) 100%);
}

.shot-col.is-solid .shot-col-bar {
  background: linear-gradient(180deg, #0029b8 0%, #3b82f6 100%);
}
.shot-col.is-solid .shot-col-bar::after { display: none; }

.shot-col.is-empty .shot-col-bar {
  background: repeating-linear-gradient(
    -45deg,
    #e5e5e0 0px,
    #e5e5e0 4px,
    #f2f2ef 4px,
    #f2f2ef 8px
  );
}

.floating-callout {
  position: absolute;
  bottom: 42px;
  left: 50%;
  transform: translateX(-50%);
  background: rgba(255, 255, 255, 0.94);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.9);
  box-shadow: var(--shadow-pill);
  border-radius: var(--radius-pill);
  padding: 6px 14px;
  font-size: 11.5px;
  color: var(--text-secondary);
  white-space: nowrap;
  z-index: 4;
  pointer-events: none;
}

.floating-callout b {
  color: var(--text-primary);
  font-weight: 600;
}

.big-metric-number {
  font-size: 40px;
  font-weight: 500;
  letter-spacing: -0.04em;
  line-height: 1;
  margin: 4px 0 18px;
  color: var(--text-primary);
  display: flex;
  align-items: baseline;
  gap: 10px;
}

.big-metric-sub {
  font-size: 13px;
  font-weight: 500;
  color: var(--emerald-main);
  letter-spacing: -0.01em;
}

.striped-metric-list {
  display: grid;
  gap: 12px;
}

.striped-metric-item {
  display: grid;
  gap: 5px;
}

.striped-metric-top {
  display: flex;
  justify-content: space-between;
  font-size: 12.5px;
  color: var(--text-muted);
  font-weight: 500;
}

.striped-metric-top b {
  color: var(--text-primary);
}

.striped-track {
  height: 10px;
  background: var(--bg-subtle);
  border-radius: 99px;
  overflow: hidden;
  padding: 1px;
}

.striped-fill {
  height: 100%;
  border-radius: 99px;
  transition: width 0.35s cubic-bezier(0.16, 1, 0.3, 1);
}

.striped-fill.green { background: var(--stripe-green); }
.striped-fill.blue { background: var(--stripe-blue); }
.striped-fill.pink { background: var(--stripe-pink); }
.striped-fill.amber { background: var(--stripe-amber); }

.workspace-grid {
  display: grid;
  grid-template-columns: 350px 1fr;
  gap: 16px;
  align-items: start;
}
.workspace-grid.nosource {
  grid-template-columns: 1fr;
}

.source-sticky {
  position: sticky;
  top: 18px;
  display: grid;
  gap: 16px;
}

.video-frame {
  border-radius: 16px;
  overflow: hidden;
  background: #0c0c0e;
  border: 1px solid var(--border-hairline);
  position: relative;
}

.video-frame video {
  width: 100%;
  display: block;
  max-height: 250px;
  object-fit: contain;
  background: #000;
}

.dot-matrix-card {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 12px;
  padding-top: 10px;
}

.dot-matrix {
  display: flex;
  align-items: flex-end;
  gap: 5px;
  height: 46px;
  overflow-x: auto;
  padding-bottom: 2px;
}

.dot-col {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.dot-cell {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #e2e8f0;
  transition: background 0.2s;
}

.dot-cell.active { background: #16a34a; }
.dot-cell.warn { background: #f59e0b; }
.dot-cell.err { background: #ef4444; }

#progress {
  display: none;
  background: linear-gradient(135deg, #fff5eb 0%, #eff6ff 55%, #dbeafe 100%);
  border: 1px solid #bfdbfe;
  border-radius: var(--radius-card);
  padding: 20px 24px;
  gap: 12px;
  margin-bottom: 16px;
  box-shadow: var(--shadow-card);
}

#progress pre {
  margin: 4px 0 0;
  padding: 12px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.85);
  border: 1px solid rgba(147, 197, 253, 0.5);
  font-family: 'JetBrains Mono', monospace;
  font-size: 11.5px;
  color: var(--text-primary);
  max-height: 130px;
  overflow: auto;
  white-space: pre-wrap;
}

.cards-stack {
  display: grid;
  gap: 18px;
  min-width: 0;
}

.group-meta-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 5px 12px;
  border-radius: var(--radius-pill);
  background: var(--bg-subtle);
  border: 1px solid var(--border-hairline);
  font-size: 12px;
  font-weight: 500;
  color: var(--text-secondary);
}

.group-meta-pill.hook {
  background: var(--brand-orange-soft);
  border-color: var(--brand-orange-border);
  color: var(--brand-orange-text);
}

.refs-strip-wrap {
  background: var(--bg-subtle);
  border: 1px solid var(--border-hairline);
  border-radius: 16px;
  padding: 12px 14px;
  margin-bottom: 14px;
}

.refs-strip-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12px;
  color: var(--text-muted);
  font-weight: 500;
  margin-bottom: 8px;
}

.refs {
  display: flex;
  gap: 10px;
  overflow-x: auto;
  scrollbar-width: thin;
  -webkit-overflow-scrolling: touch;
  padding-bottom: 4px;
}

.refs img {
  height: 84px;
  min-width: 120px;
  object-fit: cover;
  border-radius: 10px;
  border: 1px solid rgba(0, 0, 0, 0.08);
  cursor: zoom-in;
  transition: transform 0.18s ease, box-shadow 0.18s ease;
  background: #18181b;
  flex-shrink: 0;
}

.refs img:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 14px rgba(0, 0, 0, 0.1);
}

.shots {
  display: grid;
  gap: 16px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.shot-box {
  background: #fcfcfb;
  border: 1px solid var(--border-hairline);
  border-radius: 20px;
  padding: 18px;
  display: grid;
  gap: 14px;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

.shot-box:focus-within {
  background: #ffffff;
  border-color: #93c5fd;
  box-shadow: 0 8px 28px rgba(37, 99, 235, 0.06);
}

.shot-top-bar {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.shot-meta-left {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}

.shot-index-title {
  font-size: 17px;
  font-weight: 600;
  letter-spacing: -0.025em;
  color: var(--text-primary);
  margin-right: 4px;
}

.time-seek-pill {
  background: #ffffff;
  border: 1px solid var(--border-hairline);
  box-shadow: 0 1px 2px rgba(0,0,0,0.03);
  border-radius: var(--radius-pill);
  padding: 4px 11px;
  font-size: 12px;
  font-weight: 500;
  color: var(--text-primary);
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-family: 'JetBrains Mono', monospace;
  transition: background 0.15s, border-color 0.15s;
}

.time-seek-pill:hover {
  background: var(--cobalt-light);
  border-color: #93c5fd;
  color: var(--cobalt-deep);
}

.z-badge {
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.03em;
  padding: 4px 9px;
  border-radius: 7px;
  background: var(--bg-subtle);
  color: var(--text-secondary);
  border: 1px solid var(--border-hairline);
}

.z-badge.video {
  background: #eff6ff;
  color: #1d4ed8;
  border-color: #bfdbfe;
}

.z-badge.photo {
  background: var(--brand-orange-soft);
  color: var(--brand-orange-text);
  border-color: var(--brand-orange-border);
}

.z-badge.card {
  background: #f5f3ff;
  color: #6d28d9;
  border-color: #ddd6fe;
}

.state {
  font-size: 12px;
  font-weight: 500;
  padding: 5px 12px;
  border-radius: var(--radius-pill);
  background: #ffffff;
  border: 1px solid var(--border-hairline);
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.04);
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: var(--text-secondary);
  width: fit-content;
}

.state::before {
  content: '';
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #9ca3af;
}

.state.ok { color: #15803d; border-color: #bbf7d0; background: #f0fdf4; }
.state.ok::before { background: #16a34a; }

.state.warn { color: #b45309; border-color: #fde68a; background: #fffbeb; }
.state.warn::before { background: #f59e0b; }

.state.error { color: #b91c1c; border-color: #fecaca; background: #fef2f2; }
.state.error::before { background: #ef4444; }

.state.saved { color: #1d4ed8; border-color: #bfdbfe; background: #eff6ff; }
.state.saved::before { background: #2563eb; }

.state.missing { color: #8e8e88; }
.state.missing::before { background: #b5b5af; }

.shot-script {
  font-size: 14.5px;
  line-height: 1.55;
  color: var(--text-primary);
  background: #ffffff;
  border: 1px solid var(--border-hairline);
  border-radius: 12px;
  padding: 12px 14px;
  letter-spacing: -0.01em;
}

.kw-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
}

.kw-row-label {
  font-size: 11.5px;
  font-weight: 500;
  color: var(--text-muted);
  margin-right: 4px;
}

.kw-chip {
  border: 1px solid var(--border-hairline);
  background: #ffffff;
  color: var(--text-secondary);
  border-radius: 8px;
  padding: 5px 10px;
  font-size: 12.5px;
  font-weight: 500;
  font-family: inherit;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  transition: all 0.15s ease;
}

.kw-chip svg {
  width: 12px;
  height: 12px;
  stroke: var(--text-muted);
  stroke-width: 2;
  fill: none;
}

.kw-chip:hover {
  border-color: var(--border-strong);
  color: var(--text-primary);
  background: var(--bg-subtle);
}

.kw-chip.copied {
  background: var(--brand-orange-soft);
  border-color: var(--brand-orange-border);
  color: var(--brand-orange-text);
}

.kw-chip.copied svg {
  stroke: var(--brand-orange-text);
}

.zentra-prompt-well {
  background: linear-gradient(180deg, rgba(206, 226, 255, 0.62) 0%, rgba(232, 242, 255, 0.42) 100%);
  border: 1px solid rgba(147, 197, 253, 0.48);
  border-radius: var(--radius-well);
  padding: 10px 12px 12px;
  display: grid;
  gap: 9px;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.7);
}

.well-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  flex-wrap: wrap;
  padding: 0 4px;
}

.well-title {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12.5px;
  font-weight: 500;
  color: #475569;
}

.well-title svg {
  width: 14px;
  height: 14px;
  fill: #64748b;
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
  background: rgba(255, 255, 255, 0.75);
  border: 1px solid rgba(148, 163, 184, 0.3);
  border-radius: 8px;
  padding: 2px 8px;
  font-size: 11.5px;
  font-weight: 500;
  color: var(--text-secondary);
}

.trim-pill input[type="number"] {
  width: 52px;
  border: none;
  background: transparent;
  font-family: 'JetBrains Mono', monospace;
  font-size: 12px;
  font-weight: 500;
  color: var(--text-primary);
  text-align: right;
  padding: 2px 0;
}

.trim-pill input[type="number"]:focus {
  outline: none;
}

.well-input-bar {
  background: #ffffff;
  border: 1px solid rgba(255, 255, 255, 0.95);
  border-radius: var(--radius-input);
  padding: 6px 8px 6px 12px;
  display: flex;
  align-items: center;
  gap: 8px;
  box-shadow: 0 2px 10px rgba(29, 78, 216, 0.06);
  transition: box-shadow 0.15s ease, border-color 0.15s ease;
}

.well-input-bar:focus-within {
  border-color: #60a5fa;
  box-shadow: 0 4px 16px rgba(37, 99, 235, 0.12);
}

.source-token {
  display: inline-flex;
  align-items: center;
  background: var(--brand-orange-soft);
  border: 1px solid var(--brand-orange-border);
  color: var(--brand-orange-text);
  font-size: 12px;
  font-weight: 500;
  padding: 3px 8px;
  border-radius: 6px;
  white-space: nowrap;
  flex-shrink: 0;
  user-select: none;
}

.source-token.empty {
  background: var(--bg-subtle);
  border-color: var(--border-hairline);
  color: var(--text-muted);
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

.well-input-bar input[type="text"]:focus {
  outline: none;
}

.well-input-bar input[type="text"]::placeholder {
  color: var(--text-faint);
}

.well-actions {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  flex-shrink: 0;
}

.btn-well-ghost {
  border: 1px solid var(--border-hairline);
  background: var(--bg-subtle);
  color: var(--text-secondary);
  border-radius: 8px;
  height: 32px;
  padding: 0 10px;
  font-size: 12px;
  font-weight: 500;
  font-family: inherit;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  transition: all 0.15s;
}

.btn-well-ghost:hover {
  background: #e5e5e0;
  color: var(--text-primary);
}

.btn-well-upload {
  position: relative;
  overflow: hidden;
  background: var(--ink-pill);
  color: #ffffff;
  border-radius: 8px;
  height: 32px;
  padding: 0 12px;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 5px;
  white-space: nowrap;
}

.btn-well-upload input[type="file"] {
  position: absolute;
  inset: 0;
  opacity: 0;
  cursor: pointer;
}

.toast-pill {
  position: fixed;
  bottom: 86px;
  left: 50%;
  transform: translateX(-50%) translateY(16px);
  background: var(--ink-pill);
  color: #fff;
  padding: 10px 18px;
  border-radius: var(--radius-pill);
  font-size: 13px;
  font-weight: 500;
  box-shadow: var(--shadow-dark-pill);
  z-index: 95;
  opacity: 0;
  pointer-events: none;
  transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
  white-space: nowrap;
}

.toast-pill.show {
  opacity: 1;
  transform: translateX(-50%) translateY(0);
}

.lightbox {
  position: fixed;
  inset: 0;
  background: rgba(17, 17, 16, 0.86);
  backdrop-filter: blur(8px);
  z-index: 100;
  display: none;
  place-items: center;
  padding: 20px;
  cursor: zoom-out;
}
.lightbox.open { display: grid; }
.lightbox img {
  max-width: 100%;
  max-height: 86vh;
  border-radius: 16px;
  box-shadow: 0 24px 60px rgba(0, 0, 0, 0.5);
}

.mobile-dock {
  display: none;
}

@media (max-width: 1040px) {
  .bento-top {
    grid-template-columns: 1fr;
  }
  .workspace-grid {
    grid-template-columns: 1fr;
  }
  .source-sticky {
    position: static;
  }
}

@media (max-width: 680px) {
  body {
    padding: 0 0 calc(92px + env(safe-area-inset-bottom, 0px));
    background: var(--bg-shell);
  }

  .app-shell {
    border-radius: 0;
    border: none;
    box-shadow: none;
    padding: 14px 14px 28px;
  }

  .top-nav {
    flex-wrap: wrap;
    gap: 12px;
    padding-bottom: 16px;
  }

  .nav-pills {
    order: 3;
    width: 100%;
    background: #ebebe7;
    border-radius: 13px;
    padding: 4px;
  }

  .nav-pill {
    flex: 1;
    justify-content: center;
    padding: 7px 10px;
    font-size: 12px;
  }

  .nav-right .btn-primary-dark {
    display: none;
  }

  .overview-title {
    font-size: 26px;
  }

  .connected-capsules {
    width: 100%;
    justify-content: space-between;
  }

  .capsule-white {
    flex: 1;
    justify-content: center;
    font-size: 11.5px;
    padding: 7px 8px;
  }

  .shot-columns-chart {
    overflow-x: auto;
    min-width: 100%;
  }

  .shot-col {
    min-width: 86px;
    min-height: 132px;
  }

  .z-card {
    padding: 16px;
    border-radius: 18px;
  }

  .shot-box {
    padding: 14px;
    border-radius: 16px;
  }

  .kw-row {
    flex-wrap: nowrap;
    overflow-x: auto;
    scrollbar-width: none;
    padding-bottom: 2px;
  }
  .kw-row::-webkit-scrollbar { display: none; }
  .kw-chip {
    flex-shrink: 0;
  }

  .well-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
  }

  .well-trim-group {
    width: 100%;
    display: grid;
    grid-template-columns: 1fr 1fr;
  }

  .trim-pill {
    justify-content: space-between;
    padding: 5px 10px;
  }

  .trim-pill input[type="number"] {
    font-size: 15px;
    width: 58px;
  }

  .well-input-bar {
    flex-wrap: wrap;
    padding: 8px 10px;
  }

  .well-input-bar input[type="text"] {
    font-size: 15px;
    width: 100%;
    flex: 1 1 60%;
  }

  .well-actions {
    width: 100%;
    justify-content: flex-end;
    padding-top: 6px;
    border-top: 1px solid #f1f1ee;
  }

  .btn-well-ghost,
  .btn-well-upload {
    height: 36px;
    font-size: 13px;
    flex: 1;
    justify-content: center;
  }

  .mobile-dock {
    position: fixed;
    bottom: calc(12px + env(safe-area-inset-bottom, 0px));
    left: 14px;
    right: 14px;
    background: rgba(24, 24, 27, 0.94);
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
    border-radius: 999px;
    padding: 8px 8px 8px 18px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    z-index: 80;
    box-shadow: 0 14px 34px rgba(0, 0, 0, 0.28);
    border: 1px solid rgba(255, 255, 255, 0.12);
  }

  .mobile-dock-info {
    display: flex;
    flex-direction: column;
    min-width: 0;
  }

  .mobile-dock-info small {
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: #a1a1aa;
  }

  .mobile-dock-info span {
    font-size: 12.5px;
    font-weight: 500;
    color: #ffffff;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .mobile-dock-btn {
    background: #ffffff;
    color: var(--ink-pill);
    border: none;
    border-radius: 999px;
    padding: 11px 22px;
    font-family: inherit;
    font-size: 13.5px;
    font-weight: 600;
    cursor: pointer;
    flex-shrink: 0;
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
  if (m1) m1.textContent = text || 'Auto-sync active';
  const m2 = document.getElementById('mobile-msg');
  if (m2) m2.textContent = text || 'Auto-sync active';
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
    const chartCol = document.getElementById(`chart-col-${idx}`);
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
      if (chartCol) chartCol.classList.remove('is-empty');
      if ((rawStatus === 'missing' || !rawStatus) && badge) {
        badge.className = 'state saved';
        badge.textContent = 'SAVED · Ready';
      }
    } else {
      missing++;
      box.classList.remove('is-filled', 'is-error');
      if (chartCol) chartCol.classList.add('is-empty');
      if (badge) {
        badge.className = 'state missing';
        badge.textContent = 'UNFILLED';
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
  setTxt('callout-filled', `${filled} shots`);
  setTxt('callout-pct', `${pct}%`);
  setTxt('callout-missing', missing);
  setTxt('big-pct-text', `${pct}.0%`);
  setTxt('big-delta-text', `+${filled} clips linked`);
  setTxt('overall-badge', `Peak: ${pct}%`);
  setTxt('bar-video-label', `${pct}%`);

  const vFill = document.getElementById('bar-video-fill');
  if (vFill) vFill.style.width = `${pct}%`;
}

function scrollToShot(idx) {
  document.querySelectorAll('.shot-col').forEach(c => c.classList.remove('is-active'));
  const col = document.getElementById(`chart-col-${idx}`);
  if (col) col.classList.add('is-active');

  const box = document.querySelector(`.shot-box[data-shot-box="${idx}"]`);
  if (box) {
    box.scrollIntoView({ behavior: 'smooth', block: 'center' });
    const inp = box.querySelector(`input[data-shot="${idx}"]`);
    if (inp) setTimeout(() => inp.focus(), 350);
  }
}

function filterShots(mode, btn) {
  document.querySelectorAll('.nav-pill').forEach(b => b.classList.remove('active'));
  if (btn) btn.classList.add('active');

  document.querySelectorAll('.card[data-group]').forEach(card => {
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

function seekSourceVideo(seconds) {
  const v = document.getElementById('source-video');
  if (v) {
    v.currentTime = seconds;
    v.play().catch(() => {});
    showToast(`Jumped to ${seconds.toFixed(1)}s`);
  }
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
      showToast(`Link pasted to Shot ${idx + 1}`);
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
      } else {
        setMsg('Gagal simpan');
      }
    } catch (e) {
      setMsg('Gagal simpan');
    }
  }, 750);
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
      body: JSON.stringify({shots})
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
  header.innerHTML = `<b style="font-size:15px;letter-spacing:-0.02em;">Pipeline: ${STATE_LABEL[p.state] || p.state}</b><span class="source-token">/fetch-worker</span>`;
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
async function pollProgress() {
  try {
    const p = await (await fetch('/api/progress')).json();
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


def _shot_row(shot: dict, group: dict, entry: dict | str | None, state: dict) -> str:
    s_idx = shot["index"]
    refs = "".join(f'<img src="/files/{escape(f)}" onclick="openLightbox(this.src)" loading="lazy">' for f in shot.get("ref_frames", []))

    kw_list = []
    for lang in ("en", "zh"):
        kw_list.extend(shot.get("keywords", {}).get(lang, []))
    if not kw_list:
        for lang in ("en", "zh"):
            kw_list.extend(group.get("keywords", {}).get(lang, []))

    keywords = "".join(
        f'<button type="button" class="kw-chip" onclick=\'copyText({escape(json.dumps(k), quote=True)}, this)\'>'
        f'<svg viewBox="0 0 24 24"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>'
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
          <span class="shot-index-title">Shot {s_idx + 1:02d}</span>
          <button type="button" class="time-seek-pill" onclick="seekSourceVideo({shot['start_s']:.1f})">
            <svg width="10" height="10" viewBox="0 0 24 24" fill="currentColor"><polygon points="5 3 19 12 5 21 5 3"/></svg>
            {shot['start_s']:.1f}s – {shot['end_s']:.1f}s
          </button>
          {media_badge}
          {countdown_badge}
        </div>
        <div class="state {css}" data-state-badge="{s_idx}">{label} {message}</div>
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
            <svg viewBox="0 0 24 24"><path d="M12 2L14.8 9.2L22 12L14.8 14.8L12 22L9.2 14.8L2 12L9.2 9.2L12 2Z"/></svg>
            Source media link or local file
          </span>
          <div class="well-trim-group">
            <label class="trim-pill">Mulai <input type="number" step="0.1" min="0" data-time-start="{s_idx}" value="{escape(start_val)}" placeholder="0.0">s</label>
            <label class="trim-pill">Selesai <input type="number" step="0.1" min="0" data-time-end="{s_idx}" value="{escape(end_val)}" placeholder="auto">s</label>
          </div>
        </div>
        <div class="well-input-bar">
          <span class="source-token {token_empty_cls}" data-token-badge="{s_idx}">{token_label}</span>
          <input type="text" data-shot="{s_idx}" value="{escape(url_val)}" placeholder="Paste Douyin, TikTok, Pinterest URL or upload file...">
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


def _card(group: dict, shots: list[dict], links: dict, status: dict) -> str:
    is_hook = group["id"] == "hook"
    refs = "".join(f'<img src="/files/{escape(f)}" onclick="openLightbox(this.src)" loading="lazy">' for f in group.get("ref_frames", []))

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
<section class="z-card card" data-group="{escape(group['id'], quote=True)}">
  <div class="z-card-header">
    <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;">
      <h2 class="z-card-title">{escape(group['label'])}</h2>
      <span class="group-meta-pill {'hook' if is_hook else ''}">Group · {len(shots)} Shots</span>
    </div>
  </div>
  {f'''<div class="refs-strip-wrap">
    <div class="refs-strip-header">
      <span>Reference Frames from Source</span>
      <span>Tap image to inspect</span>
    </div>
    <div class="refs">{refs}</div>
  </div>''' if refs else ''}
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

    total_shots = len(plan["shots"])
    total_duration = plan["shots"][-1]["end_s"] if plan["shots"] else 0.0
    pct = round(100 * filled_shots / total_shots) if total_shots else 0

    # Chart columns & dot columns
    chart_cols = []
    dot_cols = []
    for shot in plan["shots"]:
        s_idx = shot["index"]
        dur = max(0.5, shot["end_s"] - shot["start_s"])
        bar_h = max(24, min(100, int(dur * 22)))

        has_val = False
        if "shots" in links:
            has_val = bool(links["shots"].get(str(s_idx)))
        elif "groups" in links:
            g_id = shot.get("group")
            if g_id and g_id in links["groups"]:
                g_shots = next((g["shots"] for g in groups if g["id"] == g_id), [])
                if s_idx in g_shots and len(links["groups"][g_id]) > g_shots.index(s_idx):
                    has_val = bool(links["groups"][g_id][g_shots.index(s_idx)])

        empty_cls = "" if has_val else "is-empty"
        chart_cols.append(f"""
        <div class="shot-col {empty_cls}" id="chart-col-{s_idx}" onclick="scrollToShot({s_idx})">
          <div>
            <div class="shot-col-label">Shot {s_idx + 1:02d}</div>
            <div class="shot-col-val">{dur:.1f}s</div>
          </div>
          <div class="shot-col-bar-wrap">
            <span class="col-handle"></span>
            <div class="shot-col-bar" style="height: {bar_h}px;"></div>
          </div>
        </div>""")

        c = "active" if has_val else ""
        dot_cols.append(f'<div class="dot-col"><span class="dot-cell {c}"></span><span class="dot-cell {c}"></span></div>')

    # Group striped metric bars
    colors = ["green", "blue", "pink", "amber"]
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
        _card(group, [shots[i] for i in group["shots"]], links, status)
        for group in groups
    )

    if source:
        aside = f"""
        <aside class="source-sticky">
          <div class="z-card">
            <div class="z-card-header">
              <h2 class="z-card-title">Reference Source</h2>
              <span class="z-badge video" id="video-time-indicator">00:00.0</span>
            </div>
            <div class="video-frame">
              <video src="/files/{escape(source, quote=True)}" id="source-video" controls preload="metadata"></video>
            </div>
            <div class="dot-matrix-card">
              <div>
                <div style="font-size:12px;color:var(--text-muted);margin-bottom:2px;">Total Duration</div>
                <div style="font-size:28px;font-weight:500;letter-spacing:-0.03em;">{total_duration:.1f}s</div>
              </div>
              <div class="dot-matrix" id="shot-dot-matrix" title="Status matriks per shot">
                {''.join(dot_cols)}
              </div>
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

<div class="app-shell">
  <header class="top-nav">
    <a href="#" class="brand" onclick="return false;">
      <span class="brand-mark">
        <svg viewBox="0 0 24 24"><path d="M7 17L17 7M7 7h10v10"/></svg>
      </span>
      <span class="brand-name">zentra</span>
    </a>

    <nav class="nav-pills" role="tablist">
      <button type="button" class="nav-pill active" onclick="filterShots('all', this)">
        All Shots <span class="nav-count" id="count-all">{total_shots}</span>
      </button>
      <button type="button" class="nav-pill" onclick="filterShots('missing', this)">
        Unfilled <span class="nav-count" id="count-missing">{total_shots - filled_shots}</span>
      </button>
      <button type="button" class="nav-pill" onclick="filterShots('filled', this)">
        Completed <span class="nav-count" id="count-filled">{filled_shots}</span>
      </button>
      <button type="button" class="nav-pill" onclick="filterShots('issue', this)">
        Flagged <span class="nav-count" id="count-issue">0</span>
      </button>
    </nav>

    <div class="nav-right">
      <div class="sync-status">
        <span class="sync-dot"></span>
        <span id="msg">Auto-sync active</span>
      </div>
      <button type="button" class="btn-primary-dark" onclick="save()">Save Brief</button>
    </div>
  </header>

  <section class="overview-bar">
    <div class="overview-title-group">
      <h1 class="overview-title">Brief #{escape(run_id)}</h1>
      <button type="button" class="circle-icon-btn" onclick="copyText(window.location.href, null)" title="Salin tautan brief">
        <svg viewBox="0 0 24 24"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/></svg>
      </button>
    </div>

    <div class="connected-capsules">
      <button type="button" class="capsule-white" onclick="seekSourceVideo(0)">
        <svg viewBox="0 0 24 24"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>
        <span>0.0s – {total_duration:.1f}s Source</span>
      </button>
      <span class="capsule-bridge">grouped in</span>
      <button type="button" class="capsule-white" id="stats-capsule">
        <svg viewBox="0 0 24 24"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/></svg>
        <span id="stats-text">{filled_shots}/{total_shots} shot ({filled_groups}/{len(groups)} kelompok)</span>
      </button>
    </div>
  </section>

  <section class="bento-top">
    <div class="z-card">
      <div class="z-card-header">
        <h2 class="z-card-title">Shot Timeline & Pacing</h2>
        <button type="button" class="circle-icon-btn" onclick="filterShots('all', document.querySelector('.nav-pill'))">
          <svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="1"/><circle cx="19" cy="12" r="1"/><circle cx="5" cy="12" r="1"/></svg>
        </button>
      </div>

      <div class="shot-columns-chart">
        {''.join(chart_cols)}
        <div class="floating-callout" id="floating-callout-pill">
          <b id="callout-filled">{filled_shots} shots</b> linked &nbsp;|&nbsp; Readiness: <b id="callout-pct">{pct}%</b> &nbsp;|&nbsp; Unfilled: <b id="callout-missing">{total_shots - filled_shots}</b>
        </div>
      </div>
    </div>

    <div class="z-card">
      <div class="z-card-header">
        <h2 class="z-card-title">Brief Readiness</h2>
        <span class="state" id="overall-badge">Peak: {pct}%</span>
      </div>

      <div class="big-metric-number">
        <span id="big-pct-text">{pct}.0%</span>
        <span class="big-metric-sub" id="big-delta-text">+{filled_shots} clips linked</span>
      </div>

      <div class="striped-metric-list">
        {''.join(group_metrics_html)}
      </div>
    </div>
  </section>

  <div class="workspace-grid{'' if source else ' nosource'}">
    {aside}
    <main class="cards-stack">
      <section id="progress"></section>
      {cards}
    </main>
  </div>
</div>

<div class="mobile-dock">
  <div class="mobile-dock-info">
    <small>Brief Sync</small>
    <span id="mobile-msg">Auto-sync active</span>
  </div>
  <button type="button" class="mobile-dock-btn" onclick="save()">Save Brief</button>
</div>

<div id="toast" class="toast-pill"></div>
<div id="lightbox" class="lightbox" onclick="this.classList.remove('open')">
  <img id="lightbox-img" src="" alt="Preview Frame">
</div>

<script>{_JS}</script>
</body>
</html>"""
