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
    pf.enqueue(["https://a/bad"])  # simpan ulang link yang sama = coba lagi
    assert wait_until(lambda: calls.count("https://a/bad") == 2)
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
    finally:
        srv.shutdown()
        srv.server_close()
        pf.stop()
