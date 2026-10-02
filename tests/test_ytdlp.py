from types import SimpleNamespace

import pytest

from mayzfact.errors import PipelineError
from mayzfact.ytdlp import run_ytdlp, youtube_url, ytdlp_command


def test_ytdlp_command_with_and_without_cookies(tmp_path):
    cmd = ytdlp_command("https://www.tiktok.com/@a/video/1", tmp_path / "x.mp4", tmp_path / "c.txt")
    assert cmd[1:3] == ["-m", "yt_dlp"]
    assert cmd[-1] == "https://www.tiktok.com/@a/video/1"
    assert cmd[cmd.index("--cookies") + 1] == str(tmp_path / "c.txt")
    assert cmd[cmd.index("-o") + 1] == str(tmp_path / "x.mp4")
    assert "--cookies" not in ytdlp_command("u", tmp_path / "y.mp4")
    assert youtube_url("i2xag_1OJfM") == "https://www.youtube.com/watch?v=i2xag_1OJfM"


def test_run_ytdlp_skips_existing_file(tmp_path, monkeypatch):
    dest = tmp_path / "s.mp4"
    dest.write_bytes(b"ada")
    monkeypatch.setattr("mayzfact.ytdlp.subprocess.run", lambda *a, **k: pytest.fail("nggak boleh download ulang"))
    assert run_ytdlp("u", dest) == dest


def test_run_ytdlp_failure_cleans_tmp(tmp_path, monkeypatch):
    def fake_run(cmd, **kwargs):
        (tmp_path / "z.tmp.mp4").write_bytes(b"setengah")
        return SimpleNamespace(returncode=1, stderr="ERROR: Unsupported URL", stdout="")

    monkeypatch.setattr("mayzfact.ytdlp.subprocess.run", fake_run)
    with pytest.raises(PipelineError, match="Unsupported URL"):
        run_ytdlp("u", tmp_path / "z.mp4")
    assert list(tmp_path.iterdir()) == []
