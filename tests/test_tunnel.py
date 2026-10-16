import io
import json

import pytest

from mayzfact.errors import PipelineError
from mayzfact.tunnel import start_tunnel

STARTED = json.dumps({"lvl": "info", "msg": "started tunnel", "addr": {"Host": "localhost:3100"},
                      "url": "https://abc.ngrok-free.dev"})
NOISE = json.dumps({"lvl": "eror", "msg": "unable to evaluate ngrok agent binary path for symlinks"})


class FakeProc:
    def __init__(self, lines, exit_code=None):
        self.stdout = io.StringIO("".join(line + "\n" for line in lines))
        self.exit_code = exit_code
        self.terminated = False

    def poll(self):
        return self.exit_code

    def terminate(self):
        self.terminated = True

    def wait(self, timeout=None):
        return 0


def fake_popen(proc, calls):
    def popen(cmd, **kwargs):
        calls.append(cmd)
        return proc
    return popen


def test_tunnel_returns_public_url_and_uses_basic_auth():
    calls = []
    proc = FakeProc([NOISE, STARTED])
    tunnel = start_tunnel(3100, "akmal:akmalganteng", popen=fake_popen(proc, calls), which=lambda name: "ngrok")
    assert tunnel.url == "https://abc.ngrok-free.dev"
    assert calls[0][:3] == ["ngrok", "http", "3100"]
    assert calls[0][calls[0].index("--basic-auth") + 1] == "akmal:akmalganteng"
    tunnel.stop(windows=False)
    assert proc.terminated


@pytest.mark.parametrize("auth", ["", "akmal", "akmal:pendek"])
def test_tunnel_refuses_without_valid_basic_auth(auth):
    calls = []
    with pytest.raises(PipelineError, match="NGROK_BASIC_AUTH"):
        start_tunnel(3100, auth, popen=fake_popen(FakeProc([STARTED]), calls), which=lambda name: "ngrok")
    assert calls == []  # tanpa password, ngrok nggak pernah dinyalain


def test_tunnel_reports_why_ngrok_died():
    died = json.dumps({"lvl": "crit", "msg": "command failed", "err": "Your account is limited to 1 simultaneous ngrok agent sessions."})
    with pytest.raises(PipelineError, match="1 simultaneous"):
        start_tunnel(3000, "akmal:akmalganteng", popen=fake_popen(FakeProc([NOISE, died], exit_code=1), []),
                     which=lambda name: "ngrok", timeout_s=1)


def test_stop_kills_whole_process_tree_on_windows():
    """ngrok dari scoop jalan lewat shim: kalau cuma shim yang di-terminate, ngrok aslinya nyangkut."""
    proc = FakeProc([STARTED])
    proc.pid = 4242
    ran = []
    tunnel = start_tunnel(3100, "akmal:akmalganteng", popen=fake_popen(proc, []), which=lambda name: "ngrok")
    tunnel.stop(windows=True, run=lambda cmd, **kw: ran.append(cmd))
    assert ran == [["taskkill", "/PID", "4242", "/T", "/F"]]
    assert not proc.terminated


def test_tunnel_needs_ngrok_installed():
    with pytest.raises(PipelineError, match="ngrok belum ke-install"):
        start_tunnel(3000, "akmal:akmalganteng", popen=fake_popen(FakeProc([]), []), which=lambda name: None)
