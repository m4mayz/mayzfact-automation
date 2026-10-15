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

    def fake_run(video, *, settings, from_step, no_render):
        seen.update(video=video, from_step=from_step, no_render=no_render)
        return RunPaths(tmp_path)

    monkeypatch.setattr(cli, "load_settings", lambda: Settings())
    monkeypatch.setattr(cli, "run_pipeline", fake_run)
    assert cli.main(["run", "https://youtu.be/i2xag_1OJfM"]) == 0
    assert seen == {"video": "https://youtu.be/i2xag_1OJfM", "from_step": None, "no_render": False}
    assert "Selesai:" in capsys.readouterr().out


def test_cli_prints_pipeline_error(monkeypatch, capsys):
    def boom(*args, **kwargs):
        raise PipelineError("cli", "voice.mp3 udah ada")

    monkeypatch.setattr(cli, "load_settings", lambda: Settings())
    monkeypatch.setattr(cli, "run_pipeline", boom)
    assert cli.main(["run", "i2xag_1OJfM", "--from", "tts"]) == 1
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


def test_awaiting_input_exits_with_code_3(monkeypatch, capsys):
    from mayzfact.errors import AwaitingInput

    def wait(*args, **kwargs):
        raise AwaitingInput("fetch", "3 shot perlu diisi. Buka: mayzfact brief abc")

    monkeypatch.setattr(cli, "load_settings", lambda: Settings())
    monkeypatch.setattr(cli, "run_pipeline", wait)
    assert cli.main(["run", "i2xag_1OJfM", "--from", "fetch"]) == 3
    assert "mayzfact brief abc" in capsys.readouterr().out


def test_brief_needs_plan_first(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(cli, "load_settings", lambda: Settings())
    monkeypatch.setattr(cli, "RUNS_DIR", tmp_path)
    assert cli.main(["brief", "i2xag_1OJfM"]) == 1
    assert "--no-render" in capsys.readouterr().err


@pytest.mark.parametrize("flags", [[], ["--lan"]])
def test_brief_opens_lan_by_default(monkeypatch, tmp_path, capsys, flags):
    from unittest.mock import Mock

    from mayzfact.brief import server

    paths = RunPaths(tmp_path / "i2xag_1OJfM")
    paths.root.mkdir()
    paths.shots_plan_json.write_text("{}")
    brief_server = Mock(server_address=("0.0.0.0", 3100))
    make_server = Mock(return_value=brief_server)
    monkeypatch.setattr(cli, "load_settings", lambda: Settings())
    monkeypatch.setattr(cli, "RUNS_DIR", tmp_path)
    monkeypatch.setattr(cli, "_lan_ip", lambda: "192.168.1.20")
    monkeypatch.setattr(server, "make_server", make_server)

    assert cli.main(["brief", "i2xag_1OJfM", *flags]) == 0
    make_server.assert_called_once_with(paths, 3100, host="0.0.0.0")
    out = capsys.readouterr().out
    assert "http://192.168.1.20:3100" in out
    assert "http://127.0.0.1:3100" in out
    brief_server.server_close.assert_called_once()


def test_login_youtube_writes_into_project_env(monkeypatch):
    from mayzfact import youtube

    seen = {}
    monkeypatch.setattr(cli, "load_settings", lambda: Settings(youtube_client_secret_json='{"installed": {}}'))
    monkeypatch.setattr(youtube, "login", lambda secret, env: seen.update(secret=secret, env=env))
    assert cli.main(["login", "youtube"]) == 0
    assert seen["secret"] == '{"installed": {}}' and seen["env"].name == ".env"


def test_next_slot_prints_wib_time(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(cli, "load_settings", lambda: Settings())
    monkeypatch.setattr(cli, "RUNS_DIR", tmp_path)
    assert cli.main(["next-slot"]) == 0
    out = capsys.readouterr().out.strip()
    assert out.endswith(("04:00", "21:00")) and len(out) == len("2026-10-15 21:00")


def test_upload_without_login_fails_cleanly(monkeypatch, tmp_path, capsys):
    from mayzfact.store import write_json_atomic

    paths = RunPaths(tmp_path / "NSua7RPoFJg")
    paths.root.mkdir()
    paths.final_mp4.write_bytes(b"mp4")
    write_json_atomic(paths.root / "upload.json", {"title": "T #Shorts", "description": "d", "tags": [], "category_id": "15"})
    monkeypatch.setattr(cli, "load_settings", lambda: Settings())
    monkeypatch.setattr(cli, "RUNS_DIR", tmp_path)
    assert cli.main(["upload", "NSua7RPoFJg", "--at", "2099-01-01 21:00"]) == 1
    assert "login youtube" in capsys.readouterr().err


@pytest.mark.parametrize("flags", [[], ["--now", "--at", "2099-01-01 21:00"]])
def test_upload_needs_exactly_one_of_at_or_now(flags):
    with pytest.raises(SystemExit) as exc:
        cli.main(["upload", "NSua7RPoFJg", *flags])
    assert exc.value.code == 2


def test_upload_now_without_login_fails_cleanly(monkeypatch, tmp_path, capsys):
    from mayzfact.store import write_json_atomic

    paths = RunPaths(tmp_path / "NSua7RPoFJg")
    paths.root.mkdir()
    paths.final_mp4.write_bytes(b"mp4")
    write_json_atomic(paths.root / "upload.json", {"title": "T #Shorts", "description": "d", "tags": [], "category_id": "15"})
    monkeypatch.setattr(cli, "load_settings", lambda: Settings())
    monkeypatch.setattr(cli, "RUNS_DIR", tmp_path)
    assert cli.main(["upload", "NSua7RPoFJg", "--now"]) == 1
    assert "login youtube" in capsys.readouterr().err


def test_check_script_reports_problems_and_exit_code(monkeypatch, tmp_path, capsys):
    from mayzfact.store import write_json_atomic

    paths = RunPaths(tmp_path / "abcdefghijk")
    paths.root.mkdir()
    write_json_atomic(paths.source_json, {"video_id": "abcdefghijk", "duration_s": 40.0,
                                          "transcript": [{"text": "like and subscribe. " + "word " * 80, "start": 0.0, "duration": 40.0}]})
    monkeypatch.setattr(cli, "load_settings", lambda: Settings())
    monkeypatch.setattr(cli, "RUNS_DIR", tmp_path)
    assert cli.main(["check-script", "abcdefghijk"]) == 1
    assert "script.json" in capsys.readouterr().err  # belum ada
    paths.script_json.write_text("{not json", encoding="utf-8")
    assert cli.main(["check-script", "abcdefghijk"]) == 1
    assert "JSON" in capsys.readouterr().err
    write_json_atomic(paths.script_json, {"beats": [{"text": "Hello there.", "media": "video", "queries": ["q"]}], "fallback_query": "f"})
    assert cli.main(["check-script", "abcdefghijk"]) == 1
    out = capsys.readouterr().out
    assert "subscribe" in out and "words" in out


def test_check_script_passes_a_good_script(monkeypatch, tmp_path, capsys):
    from mayzfact.store import write_json_atomic
    from tests.factories import make_script

    paths = RunPaths(tmp_path / "abcdefghijk")
    paths.root.mkdir()
    write_json_atomic(paths.source_json, {"video_id": "abcdefghijk", "duration_s": 52.9,
                                          "transcript": [{"text": "unique source words only here", "start": 0.0, "duration": 52.9}]})
    write_json_atomic(paths.script_json, make_script().model_dump())  # 110 kata = 0.8 * 52.9 * 2.6
    monkeypatch.setattr(cli, "load_settings", lambda: Settings())
    monkeypatch.setattr(cli, "RUNS_DIR", tmp_path)
    assert cli.main(["check-script", "abcdefghijk"]) == 0
    assert "OK" in capsys.readouterr().out
