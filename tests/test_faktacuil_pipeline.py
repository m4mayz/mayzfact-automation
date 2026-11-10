import json

import pytest

from mayzfact import pipeline
from mayzfact.config import Settings, load_settings, settings_for_mode
from mayzfact.errors import PipelineError
from mayzfact.pipeline import _require_script, check_voice, real_deps, run_pipeline
from mayzfact.providers.voicestudio import VoiceStudioTTS
from mayzfact.store import RunPaths, write_json_atomic
from mayzfact.text import script_text, text_hash
from tests.faktacuil_fixtures import SOURCE_TEXT_EN, faktacuil_script
from tests.test_pipeline import QUIET, VIDEO_ID, build_world

ERIC = "cjVigY5qzO86Huf0OWal"


def write_faktacuil_run(paths, duration_s=None):
    script = faktacuil_script().model_dump()
    write_json_atomic(paths.script_json, script)
    write_json_atomic(paths.source_json, {"video_id": VIDEO_ID, "transcript": [{"text": SOURCE_TEXT_EN, "start": 0.0, "duration": 10.0}]})
    if duration_s is not None:
        write_json_atomic(paths.tts_json, {"text_sha256": text_hash(script_text(script["beats"])), "duration_s": duration_s})


def test_settings_for_top3_is_identity():
    s = Settings()
    assert settings_for_mode(s, "top3") is s


def test_faktacuil_defaults():
    s = Settings()
    assert (s.faktacuil_elevenlabs_voice_id, s.faktacuil_elevenlabs_delivery_tag, s.faktacuil_tts_provider,
            s.faktacuil_voicestudio_voice, s.faktacuil_voicestudio_instruct, s.faktacuil_max_shot_seconds) == (
        ERIC, "", "elevenlabs", "", "", 2.0)


def test_settings_for_faktacuil_swaps_voice_tag_hook_and_shot_length():
    base = Settings(faktacuil_elevenlabs_voice_id="IDVOICE")
    s = settings_for_mode(base, "faktacuil")
    assert (s.elevenlabs_voice_id, s.elevenlabs_delivery_tag, s.elevenlabs_model, s.hook_seconds,
            s.max_shot_seconds) == ("IDVOICE", "", "eleven_v3", 0.0, 2.0)
    assert (base.elevenlabs_voice_id, base.max_shot_seconds, base.hook_seconds) == ("TX3LPaxmHKxFdv7VOQHJ", 4.0, 10.0)


def test_faktacuil_uses_eric_by_default():
    assert settings_for_mode(Settings(), "faktacuil").elevenlabs_voice_id == ERIC


def test_empty_faktacuil_voice_stops_before_request(monkeypatch):
    monkeypatch.setattr(pipeline, "ElevenLabsTTS", lambda *a, **k: pytest.fail("nggak boleh bikin provider"))
    deps = real_deps(settings_for_mode(Settings(elevenlabs_api_keys=("k",), faktacuil_elevenlabs_voice_id=""), "faktacuil"))
    with pytest.raises(PipelineError, match="faktacuil_elevenlabs_voice_id"):
        deps.tts()


def test_global_tts_override_does_not_leak_into_faktacuil():
    base = Settings(tts_provider="voicestudio", voicestudio_voice="Gen", voicestudio_instruct="ceria")
    s = settings_for_mode(base, "faktacuil")
    assert (s.tts_provider, s.voicestudio_voice, s.voicestudio_instruct) == ("elevenlabs", "", "")
    assert settings_for_mode(base, "top3") is base


def test_faktacuil_voicestudio_uses_faktacuil_fields():
    base = Settings(faktacuil_tts_provider="voicestudio", faktacuil_voicestudio_voice="Indo",
                    faktacuil_voicestudio_instruct="santai")
    s = settings_for_mode(base, "faktacuil")
    assert (s.tts_provider, s.voicestudio_voice, s.voicestudio_instruct) == ("voicestudio", "Indo", "santai")
    deps = real_deps(s)
    try:
        tts = deps.tts()
        assert isinstance(tts, VoiceStudioTTS) and tts.voice_id == "Indo"
    finally:
        deps.close()


def test_video_speed_follows_faktacuil_provider():
    assert settings_for_mode(Settings(faktacuil_tts_provider="voicestudio"), "faktacuil").video_speed == 1.15
    # 1.15 di MayzFact cuma hasil auto-bump voicestudio, jangan kebawa ke FaktaCuil ElevenLabs
    assert settings_for_mode(Settings(tts_provider="voicestudio"), "faktacuil").video_speed == 1.1
    assert settings_for_mode(Settings(tts_provider="voicestudio", video_speed=1.2), "faktacuil").video_speed == 1.2
    assert settings_for_mode(Settings(video_speed=1.05), "faktacuil").video_speed == 1.05


def test_require_script_rejects_faktacuil_voicestudio_without_voice(tmp_path):
    paths = RunPaths(tmp_path)
    write_faktacuil_run(paths)
    settings = settings_for_mode(Settings(faktacuil_tts_provider="voicestudio"), "faktacuil")
    with pytest.raises(PipelineError, match="faktacuil_voicestudio_voice"):
        _require_script(paths, settings)


def test_require_script_accepts_faktacuil_voicestudio_with_voice(tmp_path):
    paths = RunPaths(tmp_path)
    write_faktacuil_run(paths)
    settings = settings_for_mode(Settings(faktacuil_tts_provider="voicestudio", faktacuil_voicestudio_voice="Indo"), "faktacuil")
    _require_script(paths, settings)


def test_unknown_faktacuil_provider_is_rejected(world):
    write_faktacuil_run(RunPaths(world.runs / VIDEO_ID))
    with pytest.raises(PipelineError, match="tts_provider"):
        run_pipeline(VIDEO_ID, settings=Settings(faktacuil_tts_provider="typo"), deps=world.deps,
                     runs_dir=world.runs, **QUIET)
    assert world.tts.calls == 0


def test_check_voice_warns_outside_20_30_for_faktacuil(tmp_path):
    paths = RunPaths(tmp_path)
    write_faktacuil_run(paths, duration_s=40.0)  # 40 / 1.1 = 36,4 detik
    logs = []
    check_voice(paths, video_speed=1.1, log=logs.append)
    assert any("FaktaCuil" in line and "36.4" in line for line in logs)
    assert any("20-30 detik" in line for line in logs)


def test_check_voice_no_warning_inside_window_for_faktacuil(tmp_path):
    paths = RunPaths(tmp_path)
    write_faktacuil_run(paths, duration_s=27.5)  # 25 detik
    logs = []
    check_voice(paths, video_speed=1.1, log=logs.append)
    assert not any("PERINGATAN" in line for line in logs)


@pytest.fixture
def world(tmp_path, long_mp3, make_video, make_photo):
    return build_world(tmp_path, long_mp3, 30.0, make_video, make_photo)


def test_run_pipeline_switches_settings_before_checks(world, monkeypatch):
    write_faktacuil_run(RunPaths(world.runs / VIDEO_ID))
    calls = []
    real_switch, real_require, real_check = pipeline.settings_for_mode, pipeline._require_script, pipeline.check_voice

    def switch(settings, mode):
        calls.append(("switch", mode))
        return real_switch(settings, mode)

    def require(paths, settings):
        calls.append(("require", settings.elevenlabs_voice_id, settings.video_speed))
        return real_require(paths, settings)

    def check(paths, **kwargs):
        calls.append(("check_voice",))
        return real_check(paths, **kwargs)

    monkeypatch.setattr(pipeline, "settings_for_mode", switch)
    monkeypatch.setattr(pipeline, "_require_script", require)
    monkeypatch.setattr(pipeline, "check_voice", check)
    run_pipeline(VIDEO_ID, settings=Settings(elevenlabs_api_keys=("k",), faktacuil_elevenlabs_voice_id="IDVOICE"),
                 deps=world.deps, runs_dir=world.runs, no_render=True, **QUIET)
    assert calls[0] == ("switch", "faktacuil")
    assert ("require", "IDVOICE", 1.1) in calls
    assert [c[0] for c in calls].index("require") < [c[0] for c in calls].index("check_voice")


def test_real_plan_reads_max_shot_seconds_from_settings(tmp_path, monkeypatch):
    seen = {}
    monkeypatch.setattr("mayzfact.steps.plan.run_plan", lambda *a, **k: seen.update(k) or {})
    paths = RunPaths(tmp_path)
    for p in (paths.script_json, paths.tts_json, paths.source_json):
        write_json_atomic(p, {})
    for mode, expected in (("faktacuil", (2.0, 0.0)), ("top3", (4.0, 10.0))):
        deps = real_deps(settings_for_mode(Settings(), mode))
        deps.plan(paths, lambda m: None)
        assert (seen["max_shot_s"], seen["hook_seconds"]) == expected


def test_local_json_accepts_faktacuil_voice_fields(tmp_path):
    (tmp_path / "settings.local.json").write_text(json.dumps({
        "faktacuil_tts_provider": "voicestudio", "faktacuil_voicestudio_voice": "Indo",
        "faktacuil_voicestudio_instruct": "santai",
    }), encoding="utf-8")
    s = load_settings(tmp_path / ".env")
    assert (s.faktacuil_tts_provider, s.faktacuil_voicestudio_voice, s.faktacuil_voicestudio_instruct) == (
        "voicestudio", "Indo", "santai")
    assert s.tts_provider == "elevenlabs"


@pytest.mark.parametrize("value", [{"faktacuil_tts_provider": "typo"}, {"faktacuil_voicestudio_voice": ""}])
def test_local_json_rejects_bad_faktacuil_fields(tmp_path, value):
    (tmp_path / "settings.local.json").write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(PipelineError, match="settings.local.json"):
        load_settings(tmp_path / ".env")


def test_faktacuil_settings_are_not_env_secrets():
    from mayzfact.config import ENV_FIELDS

    assert not any(name.startswith("faktacuil") for name, _ in ENV_FIELDS.values())
