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

    def fake_run(video, *, settings, from_step, new_voice):
        seen.update(video=video, from_step=from_step, new_voice=new_voice)
        return RunPaths(tmp_path)

    monkeypatch.setattr(cli, "load_settings", lambda: Settings())
    monkeypatch.setattr(cli, "run_pipeline", fake_run)
    assert cli.main(["run", "https://youtu.be/i2xag_1OJfM", "--new-voice"]) == 0
    assert seen == {"video": "https://youtu.be/i2xag_1OJfM", "from_step": None, "new_voice": True}
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
