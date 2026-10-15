import pytest

from mayzfact import youtube
from mayzfact.config import load_settings
from mayzfact.errors import PipelineError

TOKEN = '{"token": "a", "refresh_token": "r", "client_id": "c", "client_secret": "s"}'


def test_set_env_value_replaces_only_that_line(tmp_path):
    env = tmp_path / ".env"
    env.write_bytes(b"# komentar\r\nGEMINI_MODEL=x\r\n\r\nYOUTUBE_TOKEN_JSON=\r\nBRIEF_PORT=3100\r\n")
    youtube.set_env_value(env, "YOUTUBE_TOKEN_JSON", TOKEN)
    lines = env.read_text(encoding="utf-8").splitlines()
    assert lines == ["# komentar", "GEMINI_MODEL=x", "", f"YOUTUBE_TOKEN_JSON='{TOKEN}'", "BRIEF_PORT=3100"]
    assert load_settings(env).youtube_token_json == TOKEN  # python-dotenv bisa baca balik


def test_set_env_value_appends_when_missing(tmp_path):
    env = tmp_path / ".env"
    env.write_text("GEMINI_MODEL=x\n", encoding="utf-8")
    youtube.set_env_value(env, "YOUTUBE_TOKEN_JSON", TOKEN)
    assert env.read_text(encoding="utf-8").splitlines()[-1] == f"YOUTUBE_TOKEN_JSON='{TOKEN}'"


def test_bad_json_env_never_echoes_its_value():
    with pytest.raises(PipelineError) as exc:
        youtube.parse_json_env("YOUTUBE_CLIENT_SECRET_JSON", "{rahasia-banget")
    assert "rahasia" not in str(exc.value) and "YOUTUBE_CLIENT_SECRET_JSON" in str(exc.value)
    with pytest.raises(PipelineError, match="kosong"):
        youtube.parse_json_env("YOUTUBE_CLIENT_SECRET_JSON", "  ")


def test_settings_hide_youtube_secrets_from_repr(tmp_path):
    env = tmp_path / ".env"
    env.write_text(f"YOUTUBE_CLIENT_SECRET_JSON='{TOKEN}'\n", encoding="utf-8")
    settings = load_settings(env)
    assert settings.youtube_client_secret_json == TOKEN and "refresh_token" not in repr(settings)


def test_login_writes_token_to_env(monkeypatch, tmp_path):
    env = tmp_path / ".env"
    env.write_text("YOUTUBE_TOKEN_JSON=\n", encoding="utf-8")
    seen = {}

    class FakeFlow:
        @classmethod
        def from_client_config(cls, config, scopes):
            seen.update(config=config, scopes=scopes)
            return cls()

        def run_local_server(self, port):
            return type("Creds", (), {"to_json": lambda self: TOKEN})()

    monkeypatch.setattr(youtube, "_flow_class", lambda: FakeFlow)
    youtube.login('{"installed": {}}', env)
    assert seen == {"config": {"installed": {}}, "scopes": youtube.SCOPES}
    assert load_settings(env).youtube_token_json == TOKEN
