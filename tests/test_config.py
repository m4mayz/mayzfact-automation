import pytest

from mayzfact.config import Settings, load_settings, missing_env, settings_from_env
from mayzfact.errors import PipelineError


def test_defaults_when_env_empty():
    settings = settings_from_env({})
    assert settings == Settings()
    assert settings.max_shot_seconds == 4.0
    assert settings.fg_min_height_ratio == 0.5
    assert settings.gemini_model == "gemini-3.8-flash"


def test_reads_and_casts_values():
    settings = settings_from_env({"GEMINI_API_KEYS": " abc,def ", "MAX_SHOT_SECONDS": "2.0", "PHOTO_RATIO": "0.25"})
    assert settings.gemini_api_keys == ("abc", "def")
    assert settings.max_shot_seconds == 2.0
    assert settings.photo_ratio == 0.25


def test_blank_value_keeps_default():
    settings = settings_from_env({"GEMINI_MODEL": "   ", "PEXELS_API_KEY": None})
    assert settings.gemini_model == "gemini-3.8-flash"
    assert settings.pexels_api_key == ""


def test_invalid_number_names_the_variable():
    with pytest.raises(PipelineError, match="MAX_SHOT_SECONDS"):
        settings_from_env({"MAX_SHOT_SECONDS": "dua"})


def test_missing_env_lists_empty_keys_once():
    settings = settings_from_env({"GEMINI_API_KEYS": "x"})
    assert missing_env(settings, ["GEMINI_API_KEYS", "PEXELS_API_KEY", "PEXELS_API_KEY"]) == ["PEXELS_API_KEY"]


def test_environment_overrides_dotenv(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("GEMINI_API_KEYS=from-file\nPEXELS_API_KEY=file-key\n", encoding="utf-8")
    monkeypatch.delenv("GEMINI_API_KEYS", raising=False)
    monkeypatch.setenv("PEXELS_API_KEY", "")
    settings = load_settings(env_file)
    assert settings.gemini_api_keys == ("from-file",)
    assert settings.pexels_api_key == ""


def test_elevenlabs_keys_are_split_by_comma():
    settings = settings_from_env({"ELEVENLABS_API_KEYS": "k1,k2,,k3 "})
    assert settings.elevenlabs_api_keys == ("k1", "k2", "k3")
    assert missing_env(settings_from_env({}), ["ELEVENLABS_API_KEYS"]) == ["ELEVENLABS_API_KEYS"]


def test_hook_settings_defaults_and_parsing():
    settings = settings_from_env({})
    assert (settings.hook_seconds, settings.hook_exact_threshold, settings.browser_headless) == (10.0, 0.85, False)
    assert settings.hook_platforms == ("tiktok", "pinterest")
    assert settings.clip_platforms == ("pinterest",)
    assert settings.max_shot_seconds == 4.0
    settings = settings_from_env({"HOOK_SECONDS": "8", "HOOK_PLATFORMS": "tiktok,pinterest", "BROWSER_HEADLESS": "TRUE"})
    assert (settings.hook_seconds, settings.hook_platforms, settings.browser_headless) == (8.0, ("tiktok", "pinterest"), True)
    assert settings_from_env({"BROWSER_HEADLESS": "off"}).browser_headless is False


def test_invalid_flag_names_the_variable():
    with pytest.raises(PipelineError, match="BROWSER_HEADLESS"):
        settings_from_env({"BROWSER_HEADLESS": "kadang"})
