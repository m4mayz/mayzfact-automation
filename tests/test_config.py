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
    s = settings_from_env({"MAX_SHOT_SECONDS": "2", "ELEVENLABS_VOICE_ID": "lain"})
    assert (s.elevenlabs_voice_id, s.elevenlabs_model, s.max_shot_seconds,
            s.fg_min_height_ratio, s.hook_seconds, s.brief_port) == (
        "TX3LPaxmHKxFdv7VOQHJ", "eleven_v3", 4.0, 0.5, 10.0, 3100)


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


def test_elevenlabs_defaults_to_approved_calm_natural_delivery():
    settings = Settings()
    assert settings.elevenlabs_stability == 0.5  # D-047, sample 2
    assert settings.elevenlabs_delivery_tag == "calm"
    assert settings.elevenlabs_voice_id == "TX3LPaxmHKxFdv7VOQHJ"
    assert settings.elevenlabs_model == "eleven_v3"


def test_tts_default_stays_elevenlabs():
    assert Settings().tts_provider == "elevenlabs"


def test_local_tts_override_is_not_a_secret(tmp_path):
    import json

    (tmp_path / "settings.local.json").write_text(json.dumps({
        "tts_provider": "voicestudio", "voicestudio_voice": "Gen",
    }), encoding="utf-8")
    settings = load_settings(tmp_path / ".env")
    assert settings.tts_provider == "voicestudio"
    assert settings.voicestudio_voice == "Gen"
    assert settings.elevenlabs_model == Settings().elevenlabs_model


@pytest.mark.parametrize("value", [
    {"tts_provider": "typo"}, {"voicestudio_url": "https://example.com"},
    {"voicestudio_timeout": -1}, {"voicestudio_voice": ""},
    {"elevenlabs_api_keys": ["not-allowed"]}, {"video_speed": 2.0}, [],
])
def test_invalid_local_tts_settings_fail_closed(tmp_path, value):
    import json

    from mayzfact.errors import PipelineError

    (tmp_path / "settings.local.json").write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(PipelineError, match="settings.local.json"):
        load_settings(tmp_path / ".env")


def test_voice_quality_options_are_local_and_provider_default_is_unchanged(tmp_path):
    import json

    (tmp_path / "settings.local.json").write_text(json.dumps({
        "tts_provider": "voicestudio", "voicestudio_voice": "Gen",
        "voicestudio_instruct": "Speak with lively, natural intonation.", "voicestudio_audio_format": "wav",
    }), encoding="utf-8")
    s = load_settings(tmp_path / ".env")
    assert s.voicestudio_audio_format == "wav"
    assert s.voicestudio_instruct == "Speak with lively, natural intonation."
    assert Settings().tts_provider == "elevenlabs"
    assert Settings().voicestudio_instruct == ""
    assert Settings().voicestudio_audio_format == "mp3"


@pytest.mark.parametrize("value", [
    {"voicestudio_audio_format": "../../bad"}, {"voicestudio_audio_format": "aac"},
    {"voicestudio_instruct": 42},
])
def test_invalid_voice_quality_options_fail_closed(tmp_path, value):
    import json

    from mayzfact.errors import PipelineError

    (tmp_path / "settings.local.json").write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(PipelineError):
        load_settings(tmp_path / ".env")


def test_empty_voice_instruction_is_valid_for_a_b_control(tmp_path):
    (tmp_path / "settings.local.json").write_text('{"voicestudio_instruct": ""}', encoding="utf-8")
    assert load_settings(tmp_path / ".env").voicestudio_instruct == ""


def test_video_speed_defaults_to_1_1():
    assert Settings().video_speed == 1.1  # ElevenLabs tetap 1,1x.


def test_voicestudio_defaults_to_1_15_speed_and_allows_local_override(tmp_path):
    import json
    from dataclasses import replace

    assert Settings(tts_provider="voicestudio").video_speed == 1.15
    assert replace(Settings(), tts_provider="voicestudio").video_speed == 1.15
    (tmp_path / "settings.local.json").write_text(
        json.dumps({"tts_provider": "voicestudio"}), encoding="utf-8")
    assert load_settings(tmp_path / ".env").video_speed == 1.15
    (tmp_path / "settings.local.json").write_text(
        json.dumps({"tts_provider": "voicestudio", "video_speed": 1.15}), encoding="utf-8")
    assert load_settings(tmp_path / ".env").video_speed == 1.15


@pytest.mark.parametrize("tag,stability", [("", 1.0), ("calm", 0.5), ("soft spoken", 0.0)])
def test_elevenlabs_delivery_settings_can_be_overridden_locally(tmp_path, tag, stability):
    import json

    (tmp_path / "settings.local.json").write_text(json.dumps({
        "elevenlabs_delivery_tag": tag, "elevenlabs_stability": stability,
    }), encoding="utf-8")
    settings = load_settings(tmp_path / ".env")
    assert settings.elevenlabs_delivery_tag == tag
    assert settings.elevenlabs_stability == stability
    assert settings.elevenlabs_voice_id == "TX3LPaxmHKxFdv7VOQHJ"
    assert settings.elevenlabs_model == "eleven_v3"


@pytest.mark.parametrize("field,value", [
    ("elevenlabs_delivery_tag", "[calm]"), ("elevenlabs_delivery_tag", "calm\nexcited"),
    ("elevenlabs_delivery_tag", " "), ("elevenlabs_delivery_tag", " calm"),
    ("elevenlabs_delivery_tag", "x" * 65), ("elevenlabs_delivery_tag", 42),
    ("elevenlabs_delivery_tag", None), ("elevenlabs_stability", -0.1),
    ("elevenlabs_stability", 1.1), ("elevenlabs_stability", float("nan")),
    ("elevenlabs_stability", float("inf")), ("elevenlabs_stability", True),
    ("elevenlabs_stability", "0.5"),
])
def test_invalid_elevenlabs_delivery_overrides_fail_closed(tmp_path, field, value):
    import json

    from mayzfact.errors import PipelineError

    (tmp_path / "settings.local.json").write_text(json.dumps({field: value}), encoding="utf-8")
    with pytest.raises(PipelineError, match=field):
        load_settings(tmp_path / ".env")
