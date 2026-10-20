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


def test_login_only_accepts_youtube():
    for argv in (["login", "tiktok"], ["login", "--check"], ["login"]):
        with pytest.raises(SystemExit) as exc:
            cli.main(argv)
        assert exc.value.code == 2


def test_cli_import_does_not_load_playwright():
    import subprocess
    import sys

    out = subprocess.run([sys.executable, "-c", "import sys, mayzfact.cli; print('playwright' in sys.modules)"],
                         capture_output=True, text=True, check=True)
    assert out.stdout.strip() == "False"






def test_cli_no_render_flag(monkeypatch, tmp_path, capsys):
    seen = {}

    def fake_run(video, **kwargs):
        seen.update(kwargs)
        return RunPaths(tmp_path)

    monkeypatch.setattr(cli, "load_settings", lambda: Settings())
    monkeypatch.setattr(cli, "run_pipeline", fake_run)
    assert cli.main(["run", "i2xag_1OJfM", "--from", "fetch", "--no-render"]) == 0
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
    from unittest.mock import ANY, Mock

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
    link = Mock(url="https://abc.ngrok-free.dev")
    start_tunnel = Mock(return_value=link)
    monkeypatch.setattr(cli.tunnel_mod, "start_tunnel", start_tunnel)

    assert cli.main(["brief", "i2xag_1OJfM", *flags]) == 0
    make_server.assert_called_once_with(paths, 3100, host="0.0.0.0", prefetcher=ANY)
    out = capsys.readouterr().out
    assert "http://192.168.1.20:3100" in out
    assert "http://127.0.0.1:3100" in out
    assert "https://abc.ngrok-free.dev" in out  # ngrok nyala default
    start_tunnel.assert_called_once_with(3100, "")
    brief_server.server_close.assert_called_once()
    link.stop.assert_called_once()  # ngrok ikut mati bareng brief


def test_brief_keeps_running_locally_when_ngrok_fails(monkeypatch, tmp_path, capsys):
    from unittest.mock import Mock

    from mayzfact.brief import server

    paths = RunPaths(tmp_path / "i2xag_1OJfM")
    paths.root.mkdir()
    paths.shots_plan_json.write_text("{}")
    brief_server = Mock(server_address=("0.0.0.0", 3100))
    monkeypatch.setattr(cli, "load_settings", lambda: Settings())
    monkeypatch.setattr(cli, "RUNS_DIR", tmp_path)
    monkeypatch.setattr(cli, "_lan_ip", lambda: "192.168.1.20")
    monkeypatch.setattr(server, "make_server", Mock(return_value=brief_server))
    monkeypatch.setattr(cli.tunnel_mod, "start_tunnel", Mock(side_effect=PipelineError("ngrok", "Isi NGROK_BASIC_AUTH di .env")))
    assert cli.main(["brief", "i2xag_1OJfM"]) == 0
    out = capsys.readouterr().out
    assert "ngrok gagal: Isi NGROK_BASIC_AUTH" in out and "http://127.0.0.1:3100" in out


def test_brief_no_ngrok_flag_skips_tunnel(monkeypatch, tmp_path):
    from unittest.mock import Mock

    from mayzfact.brief import server

    paths = RunPaths(tmp_path / "i2xag_1OJfM")
    paths.root.mkdir()
    paths.shots_plan_json.write_text("{}")
    monkeypatch.setattr(cli, "load_settings", lambda: Settings())
    monkeypatch.setattr(cli, "RUNS_DIR", tmp_path)
    monkeypatch.setattr(cli, "_lan_ip", lambda: "192.168.1.20")
    monkeypatch.setattr(server, "make_server", Mock(return_value=Mock(server_address=("0.0.0.0", 3100))))
    start_tunnel = Mock()
    monkeypatch.setattr(cli.tunnel_mod, "start_tunnel", start_tunnel)
    assert cli.main(["brief", "i2xag_1OJfM", "--no-ngrok"]) == 0
    start_tunnel.assert_not_called()


def test_tunnel_command_prints_url_and_stops(monkeypatch, capsys):
    from unittest.mock import Mock

    link = Mock(url="https://abc.ngrok-free.dev")
    monkeypatch.setattr(cli, "load_settings", lambda: Settings(ngrok_basic_auth="user:dummy-pass-123"))
    start_tunnel = Mock(return_value=link)
    monkeypatch.setattr(cli.tunnel_mod, "start_tunnel", start_tunnel)
    assert cli.main(["tunnel", "3000"]) == 0
    start_tunnel.assert_called_once_with(3000, "user:dummy-pass-123")
    assert "https://abc.ngrok-free.dev" in capsys.readouterr().out
    link.stop.assert_called_once()


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
    assert out.endswith(("01:00", "04:00")) and len(out) == len("2026-10-15 21:00")


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
    write_json_atomic(paths.script_json, {"beats": [{"text": "Hello there.", "media": "video", "queries": ["q"]}]})
    assert cli.main(["check-script", "abcdefghijk"]) == 1
    out = capsys.readouterr().out
    assert "subscribe" in out and "words" in out


def test_check_script_passes_a_good_script(monkeypatch, tmp_path, capsys):
    from mayzfact.store import write_json_atomic
    from tests.factories import make_script

    paths = RunPaths(tmp_path / "abcdefghijk")
    paths.root.mkdir()
    write_json_atomic(paths.source_json, {"video_id": "abcdefghijk", "duration_s": 62.5,
                                          "transcript": [{"text": "unique source words only here", "start": 0.0, "duration": 62.5}]})
    write_json_atomic(paths.script_json, make_script().model_dump())  # 110 kata = 0.8 * 62.5 * 2.2
    monkeypatch.setattr(cli, "load_settings", lambda: Settings())
    monkeypatch.setattr(cli, "RUNS_DIR", tmp_path)
    assert cli.main(["check-script", "abcdefghijk"]) == 0
    assert "OK" in capsys.readouterr().out


def test_brief_refuses_shots_without_reference_frames(monkeypatch, tmp_path, capsys):
    from mayzfact.store import write_json_atomic
    from tests.test_brief_server import PLAN

    paths = RunPaths(tmp_path / "i2xag_1OJfM")
    (paths.root / "plan").mkdir(parents=True)
    (paths.root / "plan" / "seg_01_0.jpg").write_bytes(b"jpg")
    write_json_atomic(paths.shots_plan_json, PLAN)  # shot 2 dan 3 ref_frames kosong
    monkeypatch.setattr(cli, "load_settings", lambda: Settings())
    monkeypatch.setattr(cli, "RUNS_DIR", tmp_path)
    assert cli.main(["brief", "i2xag_1OJfM"]) == 1
    err = capsys.readouterr().err
    assert "Shot 2, 3" in err and "--from plan --no-render" in err
