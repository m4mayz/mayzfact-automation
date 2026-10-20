import pytest

from mayzfact.config import (
    ENV_FIELDS,
    Settings,
    load_settings,
    missing_env,
    settings_from_env,
)


def test_env_holds_only_secrets():
    assert set(ENV_FIELDS) == {"ELEVENLABS_API_KEYS", "YOUTUBE_CLIENT_SECRET_JSON", "YOUTUBE_TOKEN_JSON", "NGROK_BASIC_AUTH"}


def test_non_secret_settings_live_in_code():
    s = settings_from_env({"TARGET_DURATION_RATIO": "0.5", "MAX_SHOT_SECONDS": "2", "ELEVENLABS_VOICE_ID": "lain"})
    assert (s.elevenlabs_voice_id, s.elevenlabs_model, s.target_duration_ratio, s.min_duration_seconds,
            s.max_shot_seconds, s.fg_min_height_ratio, s.hook_seconds, s.brief_port) == (
        "TX3LPaxmHKxFdv7VOQHJ", "eleven_v3", 0.8, 32.0, 4.0, 0.5, 10.0, 3100)


@pytest.mark.parametrize("name", ["clip_source", "pexels_api_key", "pixabay_api_key", "hook_platforms", "clip_platforms",
                                  "browser_headless", "hook_exact_threshold", "photo_ratio", "gemini_api_keys"])
def test_auto_and_gemini_settings_are_gone(name):
    assert not hasattr(Settings(), name)


def test_elevenlabs_keys_are_split_by_comma():
    settings = settings_from_env({"ELEVENLABS_API_KEYS": "k1,k2,,k3 "})
    assert settings.elevenlabs_api_keys == ("k1", "k2", "k3")
    assert missing_env(settings_from_env({}), ["ELEVENLABS_API_KEYS"]) == ["ELEVENLABS_API_KEYS"]


def test_blank_value_keeps_default():
    assert settings_from_env({"ELEVENLABS_API_KEYS": "   ", "NGROK_BASIC_AUTH": None}) == Settings()


def test_missing_env_lists_empty_keys_once():
    settings = settings_from_env({"ELEVENLABS_API_KEYS": "x"})
    assert missing_env(settings, ["ELEVENLABS_API_KEYS", "NGROK_BASIC_AUTH", "NGROK_BASIC_AUTH"]) == ["NGROK_BASIC_AUTH"]


def test_environment_overrides_dotenv(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("ELEVENLABS_API_KEYS=from-file\nNGROK_BASIC_AUTH=a:file-pass\n", encoding="utf-8")
    monkeypatch.delenv("ELEVENLABS_API_KEYS", raising=False)
    monkeypatch.setenv("NGROK_BASIC_AUTH", "")
    settings = load_settings(env_file)
    assert settings.elevenlabs_api_keys == ("from-file",)
    assert settings.ngrok_basic_auth == ""


def test_secrets_are_hidden_from_repr():
    text = repr(Settings(elevenlabs_api_keys=("KEYVAL",), youtube_token_json="TOKVAL", youtube_client_secret_json="SECVAL",
                         ngrok_basic_auth="NGROKVAL"))
    assert not any(v in text for v in ("KEYVAL", "TOKVAL", "SECVAL", "NGROKVAL"))


def test_elevenlabs_stability_defaults_to_robust():
    assert Settings().elevenlabs_stability == 1.0  # D-036
