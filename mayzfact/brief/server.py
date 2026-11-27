"""Server halaman brief: akses lokal/LAN, baca/tulis links.json dan terima upload."""

from __future__ import annotations

import json
import mimetypes
import re
import subprocess
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path, PurePosixPath
from threading import BoundedSemaphore, Lock
from urllib.parse import parse_qs, unquote, urlparse

from mayzfact.audio import (
    FAKTACUIL_BGM_DIR,
    faktacuil_bgm_names,
    faktacuil_bgm_preview_volume,
    list_bgm,
    load_faktacuil_bgm_choice,
)
from mayzfact.brief.page import render_page
from mayzfact.brief.prefetch import Prefetcher
from mayzfact.brief.voice_page import render_voice_page
from mayzfact.manual.links import (
    IMAGE_EXTS,
    VIDEO_EXTS,
    attach_audio,
    attach_sfx,
    attach_speed,
    attach_transition_sfx,
    load_links,
    missing_groups,
    missing_shots,
    normalize_links,
    preview_starts,
    save_links,
)
from mayzfact.providers.manual import (
    REQUEST_FILE,
    UPLOAD_EXTS,
    UPLOAD_STEM,
    find_uploads,
)
from mayzfact.store import RunPaths, read_json, write_json_atomic

MAX_UPLOAD = 500 * 1024 * 1024
MAX_VOICE_UPLOAD = 50 * 1024 * 1024
PORT_TRIES = 10


def missing_frames(paths: RunPaths, plan: dict) -> list[int]:
    """Shot yang belum punya frame referensi (atau file-nya hilang). Brief nolak jalan kalau ada."""
    if plan.get("narration_mode") == "faktacuil":  # frame referensi ada di kartu source_shots, bukan per shot
        return []
    return [s["index"] for s in plan.get("shots", [])
            if not s.get("auto_cta") and (not s.get("ref_frames") or not all((paths.root / f).exists() for f in s["ref_frames"]))]


def link_urls(links: dict, plan: dict | None = None) -> list[str]:
    """Semua URL di links.json (per shot atau per kelompok), urut, tanpa dobel. Upload file nggak ikut."""
    entries: list = []
    auto = {str(s['index']) for s in (plan or {}).get('shots', []) if s.get('auto_cta')}
    auto_groups = {g['id'] for g in (plan or {}).get('groups', []) if g.get('auto_cta')}
    if "shots" in links:
        entries = [v for k, v in links['shots'].items() if str(k) not in auto]
    else:
        for gid, group in links.get("groups", {}).items():
            if gid not in auto_groups:
                entries.extend(group)
    return list(dict.fromkeys(e["url"] for e in entries if isinstance(e, dict) and e.get("url")))


def make_server(paths: RunPaths, port: int, *, host: str = "127.0.0.1", max_upload: int = MAX_UPLOAD,
                prefetcher: Prefetcher | None = None, sfx_dir: Path | None = None,
                media_dir: Path | None = None) -> ThreadingHTTPServer:
    """sfx_dir: library SFX buat pill SFX kustom. media_dir: folder hasil download prefetch (buat preview klip)."""
    root = paths.root.resolve()
    bgm_write_lock = Lock()
    bgm_preview_slots = BoundedSemaphore(2)

    bgm_volume_cache: dict[tuple, float] = {}

    def bgm_volume_percent() -> float:
        """Volume BGM video ini dalam persen; FaktaCuil dihitung sekali per (lagu, file suara)."""
        from mayzfact.steps.timeline import BGM_VOLUME

        if not paths.shots_plan_json.exists() or plan().get("narration_mode") != "faktacuil":
            return round(BGM_VOLUME * 100, 1)
        key = (load_faktacuil_bgm_choice(paths), paths.tts_json.stat().st_mtime if paths.tts_json.exists() else 0)
        if key not in bgm_volume_cache:
            bgm_volume_cache[key] = round(faktacuil_bgm_preview_volume(paths) * 100, 1)
        return bgm_volume_cache[key]

    def plan() -> dict:
        return read_json(paths.shots_plan_json)

    def group_ids() -> list[str]:
        return [group["id"] for group in plan()["groups"]]

    def status() -> dict:
        return read_json(paths.links_status_json) if paths.links_status_json.exists() else {"groups": {}}

    def sfx_names() -> list[str]:
        return list_bgm(sfx_dir) if sfx_dir else []  # semua file audio di folder

    def media_path(key: str) -> Path | None:
        """File buat preview shot: upload di folder run, atau hasil download prefetch di media_dir."""
        entry = load_links(paths.links_json).get("shots", {}).get(key)
        if not isinstance(entry, dict):
            return None
        if entry.get("file"):
            target = (root / entry["file"]).resolve()
            return target if root in target.parents and target.is_file() else None
        if not (prefetcher and media_dir and entry.get("url")):
            return None
        state = prefetcher.snapshot().get(entry["url"], {})
        if state.get("state") != "siap":
            return None
        base = media_dir.resolve()
        files = [f for f in ((base / name).resolve() for name in state.get("files", [])) if base in f.parents and f.is_file()]
        videos = [f for f in files if f.suffix.lower() in VIDEO_EXTS]
        photos = [f for f in files if f.suffix.lower() in IMAGE_EXTS]
        pick = entry.get("pick")
        if videos:  # fetch juga cuma pakai video pertama
            return videos[0]
        if photos:
            return photos[pick - 1] if pick and pick <= len(photos) else photos[0]
        return None

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args) -> None:  # jangan spam terminal
            pass

        def _send(self, code: int, body: bytes, content_type: str) -> None:
            self.send_response(code)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _send_range_headers(self, size: int, content_type: str) -> tuple[int, int] | None:
            start, end, code = 0, size - 1, 200
            match = re.fullmatch(r"bytes=(\d*)-(\d*)", self.headers.get("Range", "").strip())
            if match and (match[1] or match[2]):
                start, end, code = (int(match[1]), int(match[2] or size - 1), 206) if match[1] else (size - int(match[2]), size - 1, 206)
                start, end = max(start, 0), min(end, size - 1)
                if start > end:
                    self.send_response(416)
                    self.send_header("Content-Range", f"bytes */{size}")
                    self.send_header("Content-Length", "0")
                    self.end_headers()
                    return None
            self.send_response(code)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(end - start + 1))
            self.send_header("Accept-Ranges", "bytes")
            if code == 206:
                self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
            self.end_headers()
            return start, end

        def _file(self, target: Path) -> None:
            """Kirim file per 1 MB. Header Range didukung, soalnya Chrome cuma bisa seek video kalau server ngerti Range."""
            bounds = self._send_range_headers(
                target.stat().st_size, mimetypes.guess_type(target.name)[0] or "application/octet-stream",
            )
            if bounds is None:
                return
            start, end = bounds
            remaining = end - start + 1
            try:
                with target.open("rb") as fh:
                    fh.seek(start)
                    while remaining > 0 and (chunk := fh.read(min(remaining, 1024 * 1024))):
                        self.wfile.write(chunk)
                        remaining -= len(chunk)
            except ConnectionError:  # browser batalin request pas video di-seek, normal
                pass

        def _json(self, code: int, data: dict) -> None:
            self._send(code, json.dumps(data, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

        def _bgm_preview(self, track: str) -> None:
            if (not paths.shots_plan_json.exists() or plan().get("narration_mode") != "faktacuil"
                    or track not in faktacuil_bgm_names(FAKTACUIL_BGM_DIR)):
                return self._json(404, {"error": "Lagu nggak ada di koleksi."})
            if not bgm_preview_slots.acquire(blocking=False):
                return self._json(503, {"error": "Preview lagi sibuk. Coba lagi."})
            try:
                clip = subprocess.run([
                    "ffmpeg", "-v", "error", "-nostdin", "-i", str(FAKTACUIL_BGM_DIR / track),
                    "-t", "12", "-map", "0:a:0", "-c:a", "libmp3lame", "-b:a", "96k", "-f", "mp3", "pipe:1",
                ], capture_output=True, check=True, timeout=8, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            except (OSError, subprocess.SubprocessError):
                return self._json(503, {"error": "Preview BGM gagal diputar."})
            finally:
                bgm_preview_slots.release()
            try:
                bounds = self._send_range_headers(len(clip.stdout), "audio/mpeg")
                if bounds is not None:
                    start, end = bounds
                    self.wfile.write(clip.stdout[start:end + 1])
            except ConnectionError:
                pass

        def _host_ok(self) -> bool:
            """Host cuma boleh 127.0.0.1/localhost atau IP LAN privat kalau host=0.0.0.0."""
            port = str(self.server.server_address[1])
            host_header = self.headers.get("Host", "").strip()
            if not host_header:
                return False
            hostname = host_header.split(":")[0].lower()
            header_port = host_header.split(":")[-1] if ":" in host_header else port
            if header_port != port:
                return False
            if hostname in {"127.0.0.1", "localhost"}:
                return True
            # tunnel: ngrok (*.ngrok-free.app/dev/io) atau cloudflared quick tunnel (*.trycloudflare.com)
            if hostname.endswith(".ngrok-free.app") or hostname.endswith(".ngrok-free.dev") or hostname.endswith(".ngrok.io"):
                return True
            if hostname.endswith(".trycloudflare.com"):
                return True
            if host == "0.0.0.0":
                parts = hostname.split(".")
                if len(parts) == 4 and all(p.isdigit() for p in parts):
                    nums = [int(p) for p in parts]
                    if all(0 <= n <= 255 for n in nums):
                        if nums[0] == 10:
                            return True
                        if nums[0] == 192 and nums[1] == 168:
                            return True
                        if nums[0] == 172 and 16 <= nums[1] <= 31:
                            return True
            return False

        def do_GET(self) -> None:
            if not self._host_ok():
                return self._json(403, {"error": "host nggak dikenal"})
            url = urlparse(self.path)
            if url.path == "/" and not paths.shots_plan_json.exists():
                request = paths.root / REQUEST_FILE
                if not request.exists():
                    return self._json(404, {"error": "plan belum ada dan pipeline belum minta suara"})
                uploads = find_uploads(paths.root)
                html = render_voice_page(paths.root.name, request.read_text(encoding="utf-8"),
                                         uploads[0].name if uploads else None)
                return self._send(200, html.encode("utf-8"), "text/html; charset=utf-8")
            if url.path == "/":
                source = paths.source_mp4.name if paths.source_mp4.exists() else None
                voice = paths.voice_mp3.name if paths.voice_mp3.exists() else None
                links = load_links(paths.links_json)
                current = plan()
                faktacuil = current.get("narration_mode") == "faktacuil"
                html = render_page(paths.root.name, current, links, status(), source=source, voice=voice,
                                   prefetch=prefetcher.snapshot() if prefetcher else {}, sfx_names=sfx_names(),
                                   previews=preview_starts(current, links),
                                   bgm_names=faktacuil_bgm_names(FAKTACUIL_BGM_DIR) if faktacuil else None,
                                   bgm_choice=load_faktacuil_bgm_choice(paths) if faktacuil else None)
                return self._send(200, html.encode("utf-8"), "text/html; charset=utf-8")
            if url.path == "/api/progress":
                progress = paths.fetch_progress_json
                payload = read_json(progress) if progress.exists() else {}
                if prefetcher:
                    # Download link udah pindah ke brief, jadi angka "Links Downloaded" diambil dari sini, bukan dari fetch.
                    snap = prefetcher.snapshot()
                    urls = link_urls(load_links(paths.links_json), plan())  # CTA otomatis bukan input download
                    payload["prefetch"] = snap
                    payload["links_total"] = len(urls)
                    payload["links_done"] = sum(1 for u in urls if snap.get(u, {}).get("state") == "siap")
                return self._json(200, payload)
            if url.path == "/api/state":
                return self._json(200, {"plan": plan(), "links": load_links(paths.links_json), "status": status()})
            if url.path == "/api/bgm-volume":
                return self._json(200, {"percent": bgm_volume_percent()})
            if url.path == "/api/bgm-preview":
                return self._bgm_preview(parse_qs(url.query).get("track", [""])[0])
            if url.path.startswith("/files/"):
                target = (root / unquote(url.path[len("/files/"):])).resolve()
                if root in target.parents and target.is_file():
                    return self._file(target)
            if url.path.startswith("/sfx/"):
                name = unquote(url.path[len("/sfx/"):])
                if name in sfx_names():
                    return self._file(sfx_dir / name)
            if url.path.startswith("/media/"):
                target = media_path(url.path[len("/media/"):])
                if target:
                    return self._file(target)
            self._json(404, {"error": "nggak ada"})

        def _body(self, length: int, out=None) -> None:
            """Baca body per 1 MB. Body yang ditolak tetap dibaca (dibuang), kalau nggak Windows ngirim RST ke client."""
            while length > 0:
                chunk = self.rfile.read(min(length, 1024 * 1024))
                if not chunk:
                    break
                length -= len(chunk)
                if out is not None:
                    out.write(chunk)

        def _reject(self, code: int, message: str, length: int) -> None:
            self._body(length)
            self._json(code, {"error": message})

        def do_POST(self) -> None:
            length = int(self.headers.get("Content-Length") or 0)
            if not self._host_ok():
                return self._reject(403, "host nggak dikenal", length)
            origin = self.headers.get("Origin")
            if origin:
                host_header = self.headers.get("Host", "")
                hostname = host_header.split(":")[0].lower()
                is_tunnel = (hostname.endswith(".ngrok-free.app") or hostname.endswith(".ngrok-free.dev")
                             or hostname.endswith(".ngrok.io") or hostname.endswith(".trycloudflare.com"))
                origin_ok = origin == f"http://{host_header}"
                if is_tunnel:
                    # tunnel (ngrok/cloudflared): origin https, host tanpa port
                    origin_ok = origin_ok or origin == f"https://{hostname}"
                if not origin_ok:  # tolak POST dari web lain (CSRF)
                    return self._reject(403, "request dari luar halaman brief ditolak", length)
            url = urlparse(self.path)
            if url.path == "/api/bgm":
                if not paths.shots_plan_json.exists() or plan().get("narration_mode") != "faktacuil":
                    return self._reject(404, "Pilihan BGM cuma buat brief FaktaCuil", length)
                if length > 4096:
                    return self._reject(413, "Pilihan BGM terlalu panjang", length)
                try:
                    body = json.loads(self.rfile.read(length))
                except ValueError:
                    return self._json(400, {"error": "Pilihan BGM nggak valid"})
                if not isinstance(body, dict) or "track" not in body:
                    return self._json(400, {"error": "Pilihan BGM nggak valid"})
                track = body["track"]
                if track is not None and (not isinstance(track, str) or track not in faktacuil_bgm_names(FAKTACUIL_BGM_DIR)):
                    return self._json(400, {"error": "Lagu nggak ada di koleksi. Refresh brief dan pilih lagi."})
                try:
                    with bgm_write_lock:
                        write_json_atomic(paths.bgm_choice_json, {"track": track})
                except OSError:
                    return self._json(500, {"error": "BGM gagal disimpan. Coba pilih lagi."})
                return self._json(200, {"track": track})
            if url.path == "/api/voice":
                suffix = PurePosixPath(unquote(self.headers.get("X-Filename", ""))).suffix.lower()
                if suffix not in UPLOAD_EXTS:
                    return self._reject(400, f"ekstensi {suffix or '?'} nggak didukung (mp3/wav/m4a)", length)
                if paths.voice_mp3.exists():
                    return self._reject(409, "voice.mp3 udah ada, suara udah dikunci", length)
                if (paths.root / "voice.incoming.mp3").exists():
                    return self._reject(409, "suara upload sebelumnya udah diproses, tinggal lanjutin run-nya", length)
                limit = min(max_upload, MAX_VOICE_UPLOAD)
                if length > limit:
                    return self._reject(413, f"file kegedean (maks {limit // (1024 * 1024)} MB)", length)
                if length <= 0:
                    return self._reject(400, "file kosong", length)
                dest = paths.root / f"{UPLOAD_STEM}{suffix}"
                part = dest.with_name(dest.name + ".part")
                with part.open("wb") as fh:
                    self._body(length, fh)
                if part.stat().st_size != length:
                    part.unlink()
                    return self._json(400, {"error": "upload putus di tengah, coba lagi"})
                for old in find_uploads(paths.root):  # pipeline nolak kalau ada lebih dari satu
                    if old != dest:
                        old.unlink()
                part.replace(dest)
                return self._json(200, {"file": dest.name})
            if url.path == "/api/links":
                try:
                    body = json.loads(self.rfile.read(length) or b"{}")
                    current = plan()
                    auto = {str(s['index']) for s in current['shots'] if s.get('auto_cta')}
                    auto_groups = {g['id'] for g in current['groups'] if g.get('auto_cta')}
                    # Input CTA lama nggak boleh ikut antre download setelah scene diaktifkan.
                    body = dict(body)
                    if 'shots' in body:
                        body['shots'] = {k: v for k, v in (body['shots'] or {}).items() if str(k) not in auto}
                    if 'groups' in body:
                        body['groups'] = {k: v for k, v in (body['groups'] or {}).items() if k not in auto_groups}
                    data = normalize_links(body, group_ids(), shot_count=len(current.get("shots", [])))
                    if "shots" in data and "sfx" in body:
                        attach_sfx(data, body["sfx"], set(sfx_names()), plan())
                    if "shots" in data and "speed" in body:
                        attach_speed(data, body["speed"])
                    if "shots" in data and "audio" in body:
                        attach_audio(data, body["audio"])
                    saved = load_links(paths.links_json)
                    if "transition_sfx" in body:
                        attach_transition_sfx(data, body["transition_sfx"])
                    elif saved.get("transition_sfx"):
                        data["transition_sfx"] = saved["transition_sfx"]
                    if "shots" in data:  # key yang nggak dikirim (tab brief lama / upload): nilai lama dibawa
                        old = saved.get("shots", {})
                        for key, entry in data["shots"].items():
                            if not isinstance(old.get(key), dict):
                                continue
                            for field, body_key in (("sfx", "sfx"), ("speed", "speed"), ("volume", "audio")):
                                if body_key not in body and old[key].get(field) is not None:
                                    entry[field] = old[key][field]
                except (ValueError, TypeError, AttributeError) as exc:
                    return self._json(400, {"error": str(exc)})
                save_links(paths.links_json, data)
                if prefetcher:  # download langsung, nggak nunggu agent jalanin fetch; autosave nggak ngulang yang gagal
                    prefetcher.enqueue(link_urls(data), retry_failed=bool(body.get("retry")))
                missing = missing_shots(plan(), data) if "shots" in data else missing_groups(plan(), data)
                # URL hasil normalisasi per shot, buat JS nempelin badge prefetch tanpa reload
                urls = {idx: entry.get("url", "") for idx, entry in data.get("shots", {}).items()}
                return self._json(200, {"ok": True, "missing": missing, "urls": urls,
                                        "previews": preview_starts(plan(), data)})
            if url.path == "/api/upload":
                qs = parse_qs(url.query)
                shot_param = qs.get("shot", [""])[0]
                group = qs.get("group", [""])[0]
                suffix = PurePosixPath(unquote(self.headers.get("X-Filename", ""))).suffix.lower()
                if suffix not in VIDEO_EXTS | IMAGE_EXTS:
                    return self._reject(400, f"ekstensi {suffix or '?'} nggak didukung", length)
                if length > max_upload:
                    return self._reject(413, f"file kegedean (maks {max_upload // (1024 * 1024)} MB)", length)
                if length <= 0:
                    return self._reject(400, "file kosong", length)

                total_shots = len(plan().get("shots", []))
                paths.manual_dir.mkdir(parents=True, exist_ok=True)

                if shot_param:
                    try:
                        shot_idx = int(shot_param)
                    except ValueError:
                        return self._reject(400, f"shot index '{shot_param}' nggak valid", length)
                    if shot_idx < 0 or shot_idx >= total_shots:
                        return self._reject(400, f"shot {shot_idx + 1} nggak ada di plan", length)
                    if any(s['index'] == shot_idx and s.get('auto_cta') for s in plan()['shots']):
                        return self._reject(400, "AUTO CTA tidak perlu upload", length)
                    dest = paths.manual_dir / f"shot_{shot_idx + 1}{suffix}"
                    part = dest.with_name(dest.name + ".part")
                    with part.open("wb") as fh:
                        self._body(length, fh)
                    if part.stat().st_size != length:
                        part.unlink()
                        return self._json(400, {"error": "upload putus di tengah, coba lagi"})
                    part.replace(dest)
                    rel = f"manual/{dest.name}"
                    links = load_links(paths.links_json)
                    old_entry = links.get("shots", {}).get(str(shot_idx))
                    entry = {"file": rel}
                    if isinstance(old_entry, dict):
                        if old_entry.get("start_s") is not None:
                            entry["start_s"] = old_entry["start_s"]
                        if old_entry.get("end_s") is not None:
                            entry["end_s"] = old_entry["end_s"]
                        if old_entry.get("sfx"):
                            entry["sfx"] = old_entry["sfx"]
                        if old_entry.get("speed"):
                            entry["speed"] = old_entry["speed"]
                        if old_entry.get("volume") is not None:
                            entry["volume"] = old_entry["volume"]
                    links.setdefault("shots", {})[str(shot_idx)] = entry
                    save_links(paths.links_json, links)
                    return self._json(200, {"file": rel})

                if group:
                    if any(g['id'] == group and g.get('auto_cta') for g in plan()['groups']):
                        return self._reject(400, "AUTO CTA tidak perlu upload", length)
                    if group not in group_ids():  # id kelompok cuma [a-z0-9-], aman dipakai di nama file
                        return self._reject(400, f"kelompok {group or '?'} nggak ada di plan", length)
                    taken = [int(p.stem.rsplit("_", 1)[1]) for p in paths.manual_dir.glob(f"{group}_*.*") if p.stem.rsplit("_", 1)[1].isdigit()]
                    dest = paths.manual_dir / f"{group}_{max(taken, default=0) + 1}{suffix}"
                    part = dest.with_name(dest.name + ".part")
                    with part.open("wb") as fh:
                        self._body(length, fh)
                    if part.stat().st_size != length:  # koneksi putus di tengah
                        part.unlink()
                        return self._json(400, {"error": "upload putus di tengah, coba lagi"})
                    part.replace(dest)
                    rel = f"manual/{dest.name}"
                    links = load_links(paths.links_json)
                    links.setdefault("groups", {}).setdefault(group, []).append({"file": rel})
                    save_links(paths.links_json, links)
                    return self._json(200, {"file": rel})

                return self._reject(400, "parameter shot atau group wajib diisi", length)
            self._reject(404, "nggak ada", length)

    last: OSError | None = None
    for candidate in [0] if port == 0 else range(port, port + PORT_TRIES):
        try:
            return ThreadingHTTPServer((host, candidate), Handler)
        except OSError as exc:
            last = exc
    raise OSError(f"Port {port}-{port + PORT_TRIES - 1} kepakai semua: {last}")
