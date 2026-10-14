import math
from types import SimpleNamespace

import httpx
import pytest

import mayzfact.pipeline as pipeline_mod
from mayzfact.config import Settings
from mayzfact.errors import PipelineError
from mayzfact.pipeline import STEPS, Deps, check_voice, plan_steps, run_pipeline
from mayzfact.store import RunPaths, read_json, write_json_atomic
from mayzfact.text import script_text, text_hash
from tests.factories import cand, fake_alignment, make_script

VIDEO_ID = "i2xag_1OJfM"
KEYS = {"gemini_api_keys": ("g",), "elevenlabs_api_keys": ("e",), "elevenlabs_voice_id": "v", "pexels_api_key": "p", "pixabay_api_key": "x"}
SETTINGS = Settings(**KEYS, max_shot_seconds=10.0, clip_source="auto", target_duration_ratio=0.6, min_duration_seconds=32.0)
TRANSCRIPT = [{"text": "Five ancient creatures are still alive today", "start": 0.0, "duration": 53.3}]
NONE_DONE = {step: False for step in STEPS}
ALL_DONE = {step: True for step in STEPS}
QUIET = {"log": lambda message: None}


def done_until(last: str) -> dict:
    return {step: STEPS.index(step) <= STEPS.index(last) for step in STEPS}


# --- plan_steps -------------------------------------------------------------

def test_fresh_run_runs_everything():
    assert plan_steps(NONE_DONE, False, None, False) == STEPS


def test_plain_run_resumes_from_first_missing_step():
    assert plan_steps(done_until("script"), False, None, False) == ["tts", "hook", "clips", "timeline", "render"]
    assert plan_steps(ALL_DONE, True, None, False) == []


def test_from_clips_is_allowed_with_voice():
    assert plan_steps(ALL_DONE, True, "clips", False) == ["clips", "timeline", "render"]


@pytest.mark.parametrize("step", ["source", "script", "tts"])
def test_from_locked_step_is_rejected_when_voice_exists(step):
    with pytest.raises(PipelineError, match="dikunci"):
        plan_steps(ALL_DONE, True, step, False)


def test_from_script_is_allowed_before_voice_exists():
    assert plan_steps(done_until("script"), False, "script", False) == STEPS[1:]


def test_from_step_needs_previous_outputs():
    with pytest.raises(PipelineError, match="belum pernah selesai"):
        plan_steps(done_until("tts"), True, "timeline", False)


def test_new_voice_reruns_script_and_after():
    assert plan_steps(ALL_DONE, True, None, True) == STEPS[1:]
    assert plan_steps(NONE_DONE, False, None, True) == STEPS
    with pytest.raises(PipelineError, match="nggak bisa digabung"):
        plan_steps(ALL_DONE, True, "clips", True)


def test_voice_without_metadata_needs_new_voice():
    broken = {**ALL_DONE, "tts": False}
    with pytest.raises(PipelineError, match="--new-voice"):
        plan_steps(broken, True, None, False)


# --- check_voice ------------------------------------------------------------

def write_voice_state(paths, text_beats, duration_s, sha=None):
    script = {"beats": [{"text": t, "media": "video", "queries": ["q"]} for t in text_beats], "fallback_query": "f"}
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
    with pytest.raises(PipelineError, match="--new-voice"):
        check_voice(paths)


# --- run_pipeline dengan dependency palsu ----------------------------------

class FakeWriter:
    def write(self, system, user):
        return make_script(n_beats=8, words_per_beat=10)


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


class FakeSearch:
    def candidates(self, kind, query):
        if kind == "video":
            return [cand("pexels", f"v{i}", "video", 1080, 1920, duration_s=30.0, rank=i, url=f"https://cdn.test/v{i}.mp4") for i in range(10)]
        return [cand("pexels", f"p{i}", "photo", 1600, 1000, rank=i, url=f"https://cdn.test/p{i}.jpg") for i in range(10)]


def build_world(tmp_path, audio_path, total_s, make_video, make_photo):
    video_bytes = make_video(1080, 1920, 5.0).read_bytes()
    photo_bytes = make_photo(1600, 1000).read_bytes()
    client = httpx.Client(transport=httpx.MockTransport(
        lambda request: httpx.Response(200, content=video_bytes if request.url.path.endswith(".mp4") else photo_bytes)
    ))
    tts = FakeTTS(audio_path.read_bytes(), total_s)
    world = SimpleNamespace(tts=tts, writer_calls=0, renders=0, runs=tmp_path / "runs")

    def writer():
        world.writer_calls += 1
        return FakeWriter()

    def render(paths):
        world.renders += 1
        paths.final_mp4.write_bytes(b"fake-mp4")
        return paths.final_mp4

    world.deps = Deps(
        fetch_transcript=lambda video_id: TRANSCRIPT,
        script_writer=writer,
        tts=lambda: tts,
        search=FakeSearch,
        http=lambda: client,
        render=render,
        media_cache=tmp_path / "media",
    )
    return world


@pytest.fixture
def world(tmp_path, long_mp3, make_video, make_photo):
    return build_world(tmp_path, long_mp3, 30.0, make_video, make_photo)


def run(world, **kwargs):
    return run_pipeline(VIDEO_ID, settings=kwargs.pop("settings", SETTINGS), deps=world.deps, runs_dir=world.runs, **QUIET, **kwargs)


def test_full_run_then_rerun_from_clips_reuses_voice(world):
    paths = run(world)
    assert paths.final_mp4.read_bytes() == b"fake-mp4"
    assert (world.tts.calls, world.writer_calls, world.renders) == (1, 1, 1)
    timeline = read_json(paths.timeline_json)
    assert len(timeline["shots"]) == 8
    assert timeline["durationInFrames"] == math.ceil(read_json(paths.tts_json)["duration_s"] * 30 - 1e-6)
    voice_mtime = paths.voice_mp3.stat().st_mtime_ns

    run(world, from_step="clips")
    assert (world.tts.calls, world.writer_calls, world.renders) == (1, 1, 2)
    assert paths.voice_mp3.stat().st_mtime_ns == voice_mtime


def test_second_plain_run_does_nothing(world):
    run(world)
    run(world)
    assert (world.tts.calls, world.renders) == (1, 1)


def test_from_script_is_rejected_after_voice(world):
    run(world)
    with pytest.raises(PipelineError, match="dikunci"):
        run(world, from_step="script")
    assert world.tts.calls == 1


def test_new_voice_regenerates_script_and_voice(world):
    run(world)
    run(world, new_voice=True)
    assert (world.tts.calls, world.writer_calls, world.renders) == (2, 2, 2)


def test_edited_script_blocks_clips_without_calling_tts(world):
    paths = run(world)
    script = read_json(paths.script_json)
    script["beats"][0]["text"] = "Diedit manual."
    write_json_atomic(paths.script_json, script)
    with pytest.raises(PipelineError, match="beda"):
        run(world, from_step="clips")
    assert world.tts.calls == 1


def test_short_audio_stops_before_clips(tmp_path, sine_mp3, make_video, make_photo):
    world = build_world(tmp_path, sine_mp3, 2.5, make_video, make_photo)
    with pytest.raises(PipelineError, match="--new-voice"):
        run(world)
    paths = RunPaths(world.runs / VIDEO_ID)
    assert paths.voice_mp3.exists()
    assert not paths.clips_json.exists()


def test_missing_keys_fail_before_any_step(world):
    with pytest.raises(PipelineError, match="GEMINI_API_KEYS.*ELEVENLABS_API_KEYS.*ELEVENLABS_VOICE_ID.*PEXELS_API_KEY.*PIXABAY_API_KEY"):
        run(world, settings=Settings(clip_source="auto"))
    assert not (world.runs / VIDEO_ID / "source.json").exists()


def test_from_clips_does_not_need_gemini_or_elevenlabs_keys(world):
    run(world)
    run(world, from_step="clips", settings=Settings(pexels_api_key="p", pixabay_api_key="x", max_shot_seconds=10.0, clip_source="auto"))
    assert world.renders == 2


def test_failed_render_is_retried_on_next_plain_run(world):
    paths = run(world)
    original_render = world.deps.render

    def failing_render(p):
        raise PipelineError("render", "Remotion gagal")

    world.deps.render = failing_render
    with pytest.raises(PipelineError):
        run(world, from_step="clips")
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


def test_clips_are_unique_across_shots(world):
    paths = run(world)
    ids = [(s["provider"], s["provider_id"]) for s in read_json(paths.clips_json)["shots"]]
    assert len(ids) == len(set(ids)) == 8


EMPTY_HOOK = {"hook_seconds": 10.0, "skipped_platforms": [], "segments": []}


def test_hook_runs_before_clips_and_feeds_it(world, monkeypatch):
    calls = []

    def fake_hook(paths, log):
        calls.append(paths.root.name)
        write_json_atomic(paths.hook_json, EMPTY_HOOK)
        return EMPTY_HOOK

    world.deps.hook = fake_hook
    seen = {}
    real_run_clips = pipeline_mod.run_clips

    def spy(*args, **kwargs):
        seen.update(kwargs)
        return real_run_clips(*args, **kwargs)

    monkeypatch.setattr(pipeline_mod, "run_clips", spy)
    run(world)
    assert calls == [VIDEO_ID]
    assert seen["hook"] == EMPTY_HOOK
    assert seen["hook_seconds"] == 10.0
    assert seen["scorer"] is None


def test_without_hook_runner_writes_empty_hook(world):
    paths = run(world)
    assert read_json(paths.hook_json) == EMPTY_HOOK


def test_from_hook_after_voice_does_not_call_tts(world):
    run(world)
    run(world, from_step="hook")
    assert world.tts.calls == 1
    assert world.renders == 2


def test_old_run_without_hook_json_resumes_from_hook(world):
    paths = run(world)
    paths.hook_json.unlink()
    run(world)
    assert paths.hook_json.exists()
    assert (world.tts.calls, world.renders) == (1, 2)


def test_clips_use_clip_search_and_deps_are_closed(world):
    used, closed = [], []

    class TaggingSearch(FakeSearch):
        def candidates(self, kind, query):
            used.append(kind)
            return super().candidates(kind, query)

    world.deps.clip_search = TaggingSearch
    world.deps.close = lambda: closed.append(1)
    run(world)
    assert used
    assert closed == [1]


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
    paths = run(world, no_render=True)
    assert paths.timeline_json.exists()
    assert not paths.final_mp4.exists()
    assert world.renders == 0
    run(world, from_step="clips", no_render=True)
    assert world.renders == 0


MANUAL = Settings(**KEYS, max_shot_seconds=10.0, clip_source="manual", target_duration_ratio=0.6, min_duration_seconds=32.0)


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
        run(world, settings=MANUAL, no_render=True)
    assert calls == ["plan", "fetch"]
    assert world.tts.calls == 1


def test_manual_mode_rejects_auto_steps_and_auto_rejects_manual(world):
    run(world)
    with pytest.raises(PipelineError, match="hook"):
        run(world, settings=MANUAL, from_step="hook")
    with pytest.raises(PipelineError, match="fetch"):
        run(world, from_step="fetch")


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
    paths = run(world, settings=MANUAL, no_render=True)
    assert paths.timeline_json.exists() and world.renders == 0


def test_timeline_gets_captions_from_script_and_alignment(world):
    paths = run(world, no_render=True)
    timeline = read_json(paths.timeline_json)
    assert timeline["captions"] and timeline["captions"][0]["text"]


def test_timeline_step_uses_audio_deps(world):
    seen = []

    def fake_audio(paths, log):
        seen.append(paths.root.name)
        return {"bgm": "audio/bgm/mystery.mp3", "sfx": {"hook": "audio/sfx/h.mp3"}}

    world.deps.audio = fake_audio
    paths = run(world, no_render=True)
    timeline = read_json(paths.timeline_json)
    assert seen == [VIDEO_ID]
    assert timeline["bgm"]["src"] == "audio/bgm/mystery.mp3" and timeline["sfx"][0]["from"] == 0


def test_audio_failure_never_breaks_timeline(world):
    def broken(paths, log):
        raise RuntimeError("audio rusak")

    world.deps.audio = broken
    paths = run(world, no_render=True)
    assert read_json(paths.timeline_json)["bgm"] is None


def test_timeline_step_uses_overlay_deps_and_survives_errors(world):
    def fake_overlay(paths, log, point_beats=None):
        return {"clips/shot_01.mp4": {"points": [{"t": 0.5, "x": 1, "y": 2, "w": 3, "h": 4}]}}

    world.deps.overlay = fake_overlay
    paths = run(world, no_render=True)
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
    paths = run(world, no_render=True)
    timeline = read_json(paths.timeline_json)
    assert seen["point_beats"] == {0}
    assert timeline["emojis"][0]["src"] == "emoji/1f9d0.json"

    def broken(paths, log):
        raise RuntimeError("gemini rusak")

    world.deps.marks = broken
    paths = run(world, from_step="timeline", no_render=True)
    assert read_json(paths.timeline_json)["emojis"] == []
