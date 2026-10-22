import math
from types import SimpleNamespace

import httpx
import pytest

from mayzfact import cli
from mayzfact.config import Settings
from mayzfact.errors import AwaitingInput, PipelineError
from mayzfact.pipeline import (
    ALL_STEPS,
    STEPS,
    Deps,
    check_voice,
    plan_steps,
    run_pipeline,
)
from mayzfact.store import RunPaths, read_json, write_json_atomic
from mayzfact.text import script_text, text_hash
from tests.factories import fake_alignment, make_script

VIDEO_ID = "i2xag_1OJfM"
KEYS = {"elevenlabs_api_keys": ("e",), "elevenlabs_voice_id": "v"}
SETTINGS = Settings(**KEYS, max_shot_seconds=10.0, target_duration_ratio=0.6, min_duration_seconds=32.0)
TRANSCRIPT = [{"text": "Five ancient creatures are still alive today", "start": 0.0, "duration": 53.3}]
NONE_DONE = {step: False for step in STEPS}
ALL_DONE = {step: True for step in STEPS}
QUIET = {"log": lambda message: None}


def done_until(last: str) -> dict:
    return {step: STEPS.index(step) <= STEPS.index(last) for step in STEPS}


# --- plan_steps -------------------------------------------------------------

def test_only_manual_steps_exist():
    assert ALL_STEPS == STEPS == ["source", "tts", "plan", "fetch", "timeline", "render"]


@pytest.mark.parametrize("step", ["hook", "clips"])
def test_cli_rejects_removed_steps(step):
    with pytest.raises(SystemExit) as exc:
        cli.main(["run", VIDEO_ID, "--from", step])
    assert exc.value.code == 2


def test_fresh_run_runs_everything():
    assert plan_steps(NONE_DONE, False, None) == STEPS


def test_plain_run_resumes_from_first_missing_step():
    assert plan_steps(done_until("source"), False, None) == ["tts", "plan", "fetch", "timeline", "render"]
    assert plan_steps(ALL_DONE, True, None) == []


def test_from_fetch_is_allowed_with_voice():
    assert plan_steps(ALL_DONE, True, "fetch") == ["fetch", "timeline", "render"]


@pytest.mark.parametrize("step", ["source", "tts"])
def test_from_locked_step_is_rejected_when_voice_exists(step):
    with pytest.raises(PipelineError, match="dikunci"):
        plan_steps(ALL_DONE, True, step)



def test_from_step_needs_previous_outputs():
    with pytest.raises(PipelineError, match="belum pernah selesai"):
        plan_steps(done_until("tts"), True, "timeline")



def test_voice_without_metadata_needs_new_script():
    broken = {**ALL_DONE, "tts": False}
    with pytest.raises(PipelineError, match="script.json"):
        plan_steps(broken, True, None)


# --- check_voice ------------------------------------------------------------

def write_voice_state(paths, text_beats, duration_s, sha=None):
    script = {"beats": [{"text": t, "media": "video", "queries": ["q"]} for t in text_beats]}
    write_json_atomic(paths.script_json, script)
    write_json_atomic(paths.tts_json, {"text_sha256": sha or text_hash(script_text(script["beats"])), "duration_s": duration_s})


def test_check_voice_accepts_matching_long_audio(tmp_path):
    paths = RunPaths(tmp_path)
    write_voice_state(paths, ["Look at this.", "It is old."], 31.0)
    assert check_voice(paths)["duration_s"] == 31.0


def test_check_voice_rejects_edited_script(tmp_path):
    paths = RunPaths(tmp_path)
    write_voice_state(paths, ["Look at this.", "It is old."], 31.0, sha="beda")
    with pytest.raises(PipelineError, match="beda"):
        check_voice(paths)


def test_check_voice_rejects_short_audio(tmp_path):
    paths = RunPaths(tmp_path)
    write_voice_state(paths, ["Look at this."], 29.0)
    with pytest.raises(PipelineError, match="script.json"):
        check_voice(paths)


# --- run_pipeline dengan dependency palsu ----------------------------------

class FakeTTS:
    voice_id = "v"
    model_id = "eleven_v3"

    def __init__(self, audio: bytes, total_s: float):
        self.audio = audio
        self.total_s = total_s
        self.calls = 0

    def synthesize(self, text):
        self.calls += 1
        return self.audio, fake_alignment(text, self.total_s)




def fake_plan(paths, log):
    beats = read_json(paths.script_json)["beats"]
    plan = {"groups": [], "shots": [{"index": i, "beat": i} for i in range(len(beats))]}
    write_json_atomic(paths.shots_plan_json, plan)
    return plan


def fake_fetch(paths, log):
    """1 foto per beat, rata sepanjang suara: cukup buat timeline tanpa download beneran."""
    n = len(read_json(paths.script_json)["beats"])
    step = read_json(paths.tts_json)["duration_s"] / n
    clips = {"shots": [{"index": i, "beat": i, "start_s": round(i * step, 3), "end_s": round((i + 1) * step, 3),
                        "kind": "photo", "file": f"clips/shot_{i + 1:02d}.jpg", "width": 1080, "height": 1920,
                        "provider": "manual", "provider_id": f"s{i}"} for i in range(n)]}
    write_json_atomic(paths.clips_json, clips)
    return clips


def build_world(tmp_path, audio_path, total_s, make_video, make_photo):
    client = httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(404)))
    tts = FakeTTS(audio_path.read_bytes(), total_s)
    world = SimpleNamespace(tts=tts, renders=0, runs=tmp_path / "runs")

    def render(paths):
        world.renders += 1
        paths.final_mp4.write_bytes(b"fake-mp4")
        return paths.final_mp4

    world.deps = Deps(
        fetch_transcript=lambda video_id: TRANSCRIPT,
        tts=lambda: tts,
        http=lambda: client,
        render=render,
        plan=fake_plan,
        fetch=fake_fetch,
    )
    return world


@pytest.fixture
def world(tmp_path, long_mp3, make_video, make_photo):
    return build_world(tmp_path, long_mp3, 30.0, make_video, make_photo)


def run(world, **kwargs):
    return run_pipeline(VIDEO_ID, settings=kwargs.pop("settings", SETTINGS), deps=world.deps, runs_dir=world.runs, **QUIET, **kwargs)


def write_fake_script(paths):
    write_json_atomic(paths.script_json, make_script(n_beats=8, words_per_beat=10).model_dump())


def start(world, **kwargs):
    """Run pertama cuma source, terus berhenti nunggu naskah. Di test, naskahnya ditulis langsung, terus lanjut."""
    paths = RunPaths(world.runs / VIDEO_ID)
    if not paths.script_json.exists():
        with pytest.raises(AwaitingInput):
            run(world, **{k: v for k, v in kwargs.items() if k == "settings"})
        write_fake_script(paths)
    return run(world, **kwargs)


def test_full_run_then_rerun_from_fetch_reuses_voice(world):
    paths = start(world)
    assert paths.final_mp4.read_bytes() == b"fake-mp4"
    assert (world.tts.calls, world.renders) == (1, 1)
    timeline = read_json(paths.timeline_json)
    assert len(timeline["shots"]) == 8
    assert timeline["durationInFrames"] == math.ceil(read_json(paths.tts_json)["duration_s"] * 30 - 1e-6)
    voice_mtime = paths.voice_mp3.stat().st_mtime_ns

    run(world, from_step="fetch")
    assert (world.tts.calls, world.renders) == (1, 2)
    assert paths.voice_mp3.stat().st_mtime_ns == voice_mtime


def test_second_plain_run_does_nothing(world):
    start(world)
    run(world)
    assert (world.tts.calls, world.renders) == (1, 1)




def test_edited_script_blocks_fetch_without_calling_tts(world):
    paths = start(world)
    script = read_json(paths.script_json)
    script["beats"][0]["text"] = "Diedit manual."
    write_json_atomic(paths.script_json, script)
    with pytest.raises(PipelineError, match="beda"):
        run(world, from_step="fetch")
    assert world.tts.calls == 1


def test_short_audio_stops_before_plan(tmp_path, sine_mp3, make_video, make_photo):
    world = build_world(tmp_path, sine_mp3, 2.5, make_video, make_photo)
    with pytest.raises(PipelineError, match="script.json"):
        start(world)
    paths = RunPaths(world.runs / VIDEO_ID)
    assert paths.voice_mp3.exists()
    assert not paths.clips_json.exists()


def test_missing_keys_fail_before_any_step(world):
    with pytest.raises(PipelineError, match="ELEVENLABS_API_KEYS"):
        run(world, settings=Settings(elevenlabs_api_keys=()))
    assert not (world.runs / VIDEO_ID / "source.json").exists()


def test_from_fetch_does_not_need_elevenlabs_keys(world):
    start(world)
    run(world, from_step="fetch", settings=Settings(max_shot_seconds=10.0))
    assert world.renders == 2


def test_failed_render_is_retried_on_next_plain_run(world):
    paths = start(world)
    original_render = world.deps.render

    def failing_render(p):
        raise PipelineError("render", "Remotion gagal")

    world.deps.render = failing_render
    with pytest.raises(PipelineError):
        run(world, from_step="fetch")
    assert not paths.final_mp4.exists()

    world.deps.render = original_render
    run(world)
    assert paths.final_mp4.read_bytes() == b"fake-mp4"
    assert world.renders == 2
    assert world.tts.calls == 1


def test_missing_ffmpeg_fails_before_any_step(world, monkeypatch):
    monkeypatch.setattr("mayzfact.pipeline.shutil.which", lambda name: None)
    with pytest.raises(PipelineError, match="ffmpeg"):
        run(world)
    assert not (world.runs / VIDEO_ID / "source.json").exists()














def test_deps_are_closed_after_each_run(world):
    closed = []
    world.deps.close = lambda: closed.append(1)
    start(world)  # 2 run: source (berhenti nunggu naskah) + lanjutan; deps ditutup tiap run
    assert closed == [1, 1]


def test_deps_are_closed_when_a_step_fails(world):
    closed = []

    def failing_render(paths):
        raise PipelineError("render", "Remotion gagal")

    world.deps.render = failing_render
    world.deps.close = lambda: closed.append(1)
    with pytest.raises(PipelineError):
        run(world)
    assert closed == [1]


def test_no_render_stops_after_timeline(world):
    paths = start(world, no_render=True)
    assert paths.timeline_json.exists()
    assert not paths.final_mp4.exists()
    assert world.renders == 0
    run(world, from_step="fetch", no_render=True)
    assert world.renders == 0




def test_manual_mode_runs_plan_then_waits_for_links(world):
    from mayzfact.errors import AwaitingInput

    calls = []

    def fake_plan(paths, log):
        calls.append("plan")
        write_json_atomic(paths.shots_plan_json, {"shots": []})
        return {"shots": []}

    def fake_fetch(paths, log):
        calls.append("fetch")
        raise AwaitingInput("fetch", "2 shot perlu diisi")

    world.deps.plan, world.deps.fetch = fake_plan, fake_fetch
    with pytest.raises(AwaitingInput):
        start(world, no_render=True)
    assert calls == ["plan", "fetch"]
    assert world.tts.calls == 1




def test_manual_fetch_success_continues_to_timeline(world):
    def fake_plan(paths, log):
        write_json_atomic(paths.shots_plan_json, {"shots": []})
        return {}

    def fake_fetch(paths, log):
        clips = {"shots": [{"index": 0, "beat": 0, "start_s": 0.0, "end_s": 30.0, "kind": "photo",
                            "file": "clips/shot_01.jpg", "width": 1080, "height": 1920}]}
        write_json_atomic(paths.clips_json, clips)
        return clips

    world.deps.plan, world.deps.fetch = fake_plan, fake_fetch
    paths = start(world, no_render=True)
    assert paths.timeline_json.exists() and world.renders == 0


def test_timeline_gets_captions_from_script_and_alignment(world):
    paths = start(world, no_render=True)
    timeline = read_json(paths.timeline_json)
    assert timeline["captions"] and timeline["captions"][0]["text"]


def test_timeline_step_uses_audio_deps(world):
    seen = []

    def fake_audio(paths, log):
        seen.append(paths.root.name)
        return {"bgm": "audio/bgm/mystery.mp3", "sfx": {"hook": "audio/sfx/h.mp3"}}

    world.deps.audio = fake_audio
    paths = start(world, no_render=True)
    timeline = read_json(paths.timeline_json)
    assert seen == [VIDEO_ID]
    assert timeline["bgm"][0]["src"] == "audio/bgm/mystery.mp3" and timeline["sfx"][0]["from"] == 0


def test_audio_failure_never_breaks_timeline(world):
    def broken(paths, log):
        raise RuntimeError("audio rusak")

    world.deps.audio = broken
    paths = start(world, no_render=True)
    assert read_json(paths.timeline_json)["bgm"] == []


def test_timeline_step_uses_overlay_deps_and_survives_errors(world):
    def fake_overlay(paths, log, point_beats=None):
        return {"clips/shot_01.mp4": {"points": [{"t": 0.5, "x": 1, "y": 2, "w": 3, "h": 4}]}}

    world.deps.overlay = fake_overlay
    paths = start(world, no_render=True)
    first_src = read_json(paths.timeline_json)["shots"][0]["src"]
    world.deps.overlay = lambda p, log, point_beats=None: {first_src: {"points": [{"t": 0.5, "x": 1, "y": 2, "w": 3, "h": 4}]}}
    paths = run(world, from_step="timeline", no_render=True)
    assert read_json(paths.timeline_json)["overlays"][0]["type"] == "arrow"

    def broken(paths, log, point_beats=None):
        raise RuntimeError("model rusak")

    world.deps.overlay = broken
    paths = run(world, from_step="timeline", no_render=True)
    assert read_json(paths.timeline_json)["overlays"] == []



def test_timeline_step_uses_beat_marks_for_emoji_and_arrows(world):
    seen = {}

    def fake_marks(paths, log):
        beats = read_json(paths.script_json)["beats"]
        marks = [{"point": False, "emoji": "", "emoji_word": ""} for _ in beats]
        marks[0] = {"point": True, "emoji": "🧐", "emoji_word": ""}
        return {"beats": marks, "emoji": {"🧐": "emoji/1f9d0.json"}}

    def fake_overlay(paths, log, point_beats=None):
        seen["point_beats"] = point_beats
        return {}

    world.deps.marks, world.deps.overlay = fake_marks, fake_overlay
    paths = start(world, no_render=True)
    timeline = read_json(paths.timeline_json)
    assert seen["point_beats"] == {0}
    assert timeline["emojis"][0]["src"] == "emoji/1f9d0.json"

    def broken(paths, log):
        raise RuntimeError("emoji rusak")

    world.deps.marks = broken
    paths = run(world, from_step="timeline", no_render=True)
    assert read_json(paths.timeline_json)["emojis"] == []


def test_run_waits_for_script_when_only_source_exists(world):
    paths = RunPaths(world.runs / VIDEO_ID)
    with pytest.raises(AwaitingInput, match="check-script"):
        run(world)
    assert paths.source_json.exists() and not paths.script_json.exists()
    with pytest.raises(AwaitingInput, match="check-script"):
        run(world)
    assert world.tts.calls == 0  # TTS nggak kepanggil tanpa naskah


def test_run_continues_once_script_is_written(world):
    paths = RunPaths(world.runs / VIDEO_ID)
    with pytest.raises(AwaitingInput):
        run(world)
    write_fake_script(paths)
    run(world)
    assert paths.voice_mp3.exists() and world.tts.calls == 1


def test_run_rejects_script_that_fails_checks_before_tts(world):
    paths = RunPaths(world.runs / VIDEO_ID)
    with pytest.raises(AwaitingInput):
        run(world)
    write_json_atomic(paths.script_json, {"beats": [{"text": "Too short.", "media": "video", "queries": ["q"]}]})
    with pytest.raises(PipelineError, match="lolos cek"):
        run(world)
    assert world.tts.calls == 0


def test_deleted_script_with_voice_present_is_a_clean_error(world):
    paths = start(world)
    paths.script_json.unlink()
    with pytest.raises(PipelineError, match="script.json"):
        run(world, from_step="fetch")


def test_real_deps_passes_stability_to_elevenlabs():
    from mayzfact.pipeline import real_deps

    assert real_deps(Settings(**KEYS, elevenlabs_stability=0.5)).tts().stability == 0.5


def test_timeline_step_uses_text_blurs_and_survives_errors(world):
    paths = start(world, no_render=True)
    first = read_json(paths.timeline_json)["shots"][0]["src"]
    world.deps.textblur = lambda p, log: {first: [(0.4, 0.9, 0.6, 0.95)]}
    paths = run(world, from_step="timeline", no_render=True)
    assert read_json(paths.timeline_json)["shots"][0]["blurs"]

    def broken(p, log):
        raise RuntimeError("ocr rusak")

    world.deps.textblur = broken
    paths = run(world, from_step="timeline", no_render=True)
    assert "blurs" not in read_json(paths.timeline_json)["shots"][0]
