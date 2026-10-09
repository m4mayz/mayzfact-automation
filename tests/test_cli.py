import pytest

from mayzfact import cli
from mayzfact.config import Settings
from mayzfact.errors import PipelineError
from mayzfact.store import RunPaths


def test_cli_rejects_unknown_step():
    with pytest.raises(SystemExit) as exc:
        cli.main(["run", "i2xag_1OJfM", "--from", "upload"])
    assert exc.value.code == 2


def test_cli_passes_flags_to_pipeline(monkeypatch, tmp_path, capsys):
    seen = {}

    def fake_run(video, *, settings, from_step, new_voice, no_render):
        seen.update(video=video, from_step=from_step, new_voice=new_voice, no_render=no_render)
        return RunPaths(tmp_path)

    monkeypatch.setattr(cli, "load_settings", lambda: Settings())
    monkeypatch.setattr(cli, "run_pipeline", fake_run)
    assert cli.main(["run", "https://youtu.be/i2xag_1OJfM", "--new-voice"]) == 0
    assert seen == {"video": "https://youtu.be/i2xag_1OJfM", "from_step": None, "new_voice": True, "no_render": False}
    assert "Selesai:" in capsys.readouterr().out


def test_cli_prints_pipeline_error(monkeypatch, capsys):
    def boom(*args, **kwargs):
        raise PipelineError("cli", "voice.mp3 udah ada")

    monkeypatch.setattr(cli, "load_settings", lambda: Settings())
    monkeypatch.setattr(cli, "run_pipeline", boom)
    assert cli.main(["run", "i2xag_1OJfM", "--from", "script"]) == 1
    assert "Error [cli] voice.mp3 udah ada" in capsys.readouterr().err


def test_cli_voices_needs_key(monkeypatch, capsys):
    monkeypatch.setattr(cli, "load_settings", lambda: Settings())
    assert cli.main(["voices"]) == 1
    assert "ELEVENLABS_API_KEYS" in capsys.readouterr().err


def test_login_check_reports_each_platform(monkeypatch, capsys):
    monkeypatch.setattr(cli, "load_settings", lambda: Settings(hook_platforms=("tiktok", "pinterest")))
    cookies = {"tiktok": [{"name": "sessionid", "value": "x", "domain": ".tiktok.com"}], "pinterest": []}
    monkeypatch.setattr(cli.browser, "read_profile_cookies", lambda name: cookies[name])
    assert cli.main(["login", "--check"]) == 1
    out = capsys.readouterr().out
    assert "tiktok: login" in out
    assert "pinterest: belum login (jalanin: mayzfact login pinterest)" in out


def test_login_opens_browser_then_checks(monkeypatch, capsys):
    opened = []
    monkeypatch.setattr(cli, "load_settings", lambda: Settings())
    monkeypatch.setattr(cli.browser, "open_login_browser", lambda name: opened.append(name))
    monkeypatch.setattr(cli.browser, "read_profile_cookies", lambda name: [{"name": "sessionid", "value": "x", "domain": ".douyin.com"}])
    assert cli.main(["login", "douyin"]) == 0
    assert opened == ["douyin"]
    assert "douyin: login" in capsys.readouterr().out


def test_login_needs_platform_or_check(monkeypatch, capsys):
    monkeypatch.setattr(cli, "load_settings", lambda: Settings())
    assert cli.main(["login"]) == 1
    assert "mayzfact login tiktok" in capsys.readouterr().err


def test_cli_no_render_flag(monkeypatch, tmp_path, capsys):
    seen = {}

    def fake_run(video, **kwargs):
        seen.update(kwargs)
        return RunPaths(tmp_path)

    monkeypatch.setattr(cli, "load_settings", lambda: Settings())
    monkeypatch.setattr(cli, "run_pipeline", fake_run)
    assert cli.main(["run", "i2xag_1OJfM", "--from", "clips", "--no-render"]) == 0
    assert seen["no_render"] is True
    assert "remotion studio" in capsys.readouterr().out
