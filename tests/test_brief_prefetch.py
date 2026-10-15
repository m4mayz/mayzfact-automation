import threading
import time
from pathlib import Path

import httpx

from mayzfact.brief.prefetch import Prefetcher
from mayzfact.brief.server import make_server
from mayzfact.errors import PipelineError
from mayzfact.store import RunPaths, read_json, write_json_atomic
from tests.test_brief_server import PLAN


def wait_until(cond, timeout=5.0):
    end = time.time() + timeout
    while time.time() < end:
        if cond():
            return True
        time.sleep(0.02)
    return False


def test_prefetcher_downloads_each_url_once_and_records_state(tmp_path):
    paths = RunPaths(tmp_path / "run")
    paths.root.mkdir()
    calls = []

    def obtain(entry, run_root):
        calls.append(entry["url"])
        if "bad" in entry["url"]:
            raise PipelineError("fetch", "Link tiktok nggak bisa di-download")
        return [Path("cache/manual/abc_0.mp4")]

    pf = Prefetcher(paths, obtain, log=lambda m: None)
    pf.start()
    pf.enqueue(["https://a/ok", "https://a/bad", "https://a/ok"])
    assert wait_until(lambda: len(pf.snapshot()) == 2 and all(s["state"] in ("siap", "gagal") for s in pf.snapshot().values()))
    snap = pf.snapshot()
    assert snap["https://a/ok"] == {"state": "siap", "message": "", "files": ["abc_0.mp4"]}
    assert snap["https://a/bad"]["state"] == "gagal" and "nggak bisa" in snap["https://a/bad"]["message"]
    assert calls.count("https://a/ok") == 1
    assert read_json(paths.prefetch_json) == snap
    pf.enqueue(["https://a/ok", "https://a/bad"])  # autosave: yang siap/gagal nggak diulang
    time.sleep(0.2)
    assert calls.count("https://a/ok") == 1 and calls.count("https://a/bad") == 1
    pf.enqueue(["https://a/bad"], retry_failed=True)  # klik Simpan = coba lagi yang gagal
    assert wait_until(lambda: calls.count("https://a/bad") == 2)
    assert calls.count("https://a/ok") == 1
    pf.stop()


def test_worker_survives_log_and_write_errors(tmp_path):
    """stdout cp1252 nggak bisa nulis URL CJK: log boleh gagal, state tetap bener dan worker lanjut ke URL berikutnya."""
    paths = RunPaths(tmp_path / "run")
    paths.root.mkdir()

    def log(message):
        raise UnicodeEncodeError("charmap", "\u4e2d", 0, 1, "character maps to <undefined>")

    def obtain(entry, run_root):
        if "bad" in entry["url"]:
            raise PipelineError("fetch", "Link mati")
        return [Path("x_0.mp4")]

    pf = Prefetcher(paths, obtain, log=log)
    pf.start()
    pf.enqueue(["https://a/ok", "https://a/bad", "https://a/ok2"])
    assert wait_until(lambda: pf.snapshot().get("https://a/ok2", {}).get("state") == "siap")
    snap = pf.snapshot()
    assert snap["https://a/ok"]["state"] == "siap" and snap["https://a/bad"]["state"] == "gagal"
    assert pf.is_alive()
    pf.stop()


def test_prefetcher_stop_does_not_hang_on_pending_queue(tmp_path):
    paths = RunPaths(tmp_path / "run")
    paths.root.mkdir()
    started = threading.Event()

    def slow(entry, run_root):
        started.set()
        time.sleep(0.3)
        return []

    pf = Prefetcher(paths, slow, log=lambda m: None)
    pf.start()
    pf.enqueue([f"https://a/{i}" for i in range(20)])
    assert started.wait(2.0)
    t0 = time.time()
    pf.stop(timeout_s=1.0)
    assert time.time() - t0 < 2.0
    assert not pf.is_alive()


def test_saving_links_queues_downloads_and_progress_shows_them(tmp_path):
    paths = RunPaths(tmp_path / "abc")
    (paths.root / "plan").mkdir(parents=True)
    write_json_atomic(paths.shots_plan_json, PLAN)
    seen = []
    pf = Prefetcher(paths, lambda entry, root: seen.append(entry["url"]) or [Path("x_0.mp4")], log=lambda m: None)
    pf.start()
    srv = make_server(paths, 0, prefetcher=pf)
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{srv.server_address[1]}"
    try:
        ok = httpx.post(base + "/api/links", json={"shots": {"0": "https://vt.tiktok.com/ZS1/", "1": "https://vt.tiktok.com/ZS1/", "2": "file:manual/x.mp4"}})
        assert ok.status_code == 200
        assert wait_until(lambda: seen == ["https://vt.tiktok.com/ZS1/"])
        assert wait_until(lambda: httpx.get(base + "/api/progress").json().get("prefetch", {}).get("https://vt.tiktok.com/ZS1/", {}).get("state") == "siap")
        html = httpx.get(base + "/").text
        assert 'data-prefetch-url="https://vt.tiktok.com/ZS1/"' in html
        # Badge ada di tiap shot (yang kosong juga), dan hasil simpan ngasih URL per shot biar JS bisa nempelin badge tanpa reload.
        assert html.count('class="prefetch') == len(PLAN["shots"]) and 'data-shot-badge="2"' in html
        assert ok.json()["urls"] == {"0": "https://vt.tiktok.com/ZS1/", "1": "https://vt.tiktok.com/ZS1/", "2": ""}
        assert "setPrefetchUrls" in html
    finally:
        srv.shutdown()
        srv.server_close()
        pf.stop()


def test_links_downloaded_bar_counts_prefetch_not_fetch(tmp_path):
    """Bar 'Links Downloaded' di panel progress ngambil dari status prefetch (siap/total), bukan dari fetch."""
    paths = RunPaths(tmp_path / "abc")
    (paths.root / "plan").mkdir(parents=True)
    write_json_atomic(paths.shots_plan_json, PLAN)
    write_json_atomic(paths.fetch_progress_json, {"state": "running", "links_done": 0, "links_total": 2, "shots_done": 1, "shots_total": 3, "log": []})
    pf = Prefetcher(paths, lambda entry, root: [Path("x_0.mp4")], log=lambda m: None)
    pf.start()
    srv = make_server(paths, 0, prefetcher=pf)
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{srv.server_address[1]}"
    try:
        httpx.post(base + "/api/links", json={"shots": {"0": "https://vt.tiktok.com/ZS1/", "1": "https://vt.tiktok.com/ZS2/"}})
        assert wait_until(lambda: all(s["state"] == "siap" for s in pf.snapshot().values()) and len(pf.snapshot()) == 2)
        p = httpx.get(base + "/api/progress").json()
        assert (p["links_done"], p["links_total"]) == (2, 2)  # dari prefetch, bukan angka 0 dari fetch
        httpx.post(base + "/api/links", json={"shots": {"0": "https://vt.tiktok.com/ZS1/"}})  # link lama diganti/dihapus nggak dihitung lagi
        p = httpx.get(base + "/api/progress").json()
        assert (p["links_done"], p["links_total"]) == (1, 1)
        html = httpx.get(base + "/").text
        assert "renderPrefetch" in html and "links_done" in html
    finally:
        srv.shutdown()
        srv.server_close()
        pf.stop()
