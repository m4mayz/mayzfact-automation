import json
import shutil
import subprocess

import pytest

from mayzfact.steps.render import render_command, run_render
from mayzfact.steps.timeline import build_timeline
from mayzfact.store import RunPaths, write_json_atomic
from tests.factories import fake_alignment


def test_render_command_uses_absolute_props_and_public_dir(tmp_path):
    paths = RunPaths(tmp_path / "runs" / "abc")
    cmd = render_command("npx", paths, paths.root / "final.tmp.mp4")
    assert cmd[:5] == ["npx", "remotion", "render", "src/index.ts", "ShortVideo"]
    assert cmd[5] == str(paths.root / "final.tmp.mp4")
    assert f"--props={paths.timeline_json}" in cmd
    assert f"--public-dir={paths.root}" in cmd
    assert "--codec=h264" in cmd


@pytest.mark.render
def test_render_fixture_timeline(tmp_path, make_video, make_photo, sine_mp3):
    paths = RunPaths(tmp_path / "run")
    paths.clips_dir.mkdir(parents=True)
    shutil.copy(make_video(1080, 1920, 2.0), paths.clips_dir / "shot_01.mp4")
    shutil.copy(make_video(1920, 1080, 2.0), paths.clips_dir / "shot_02.mp4")
    shutil.copy(make_photo(1600, 1000), paths.clips_dir / "shot_03.jpg")
    shutil.copy(sine_mp3, paths.voice_mp3)
    clips = {"shots": [
        {"file": "clips/shot_01.mp4", "kind": "video", "start_s": 0.0, "width": 1080, "height": 1920},
        {"file": "clips/shot_02.mp4", "kind": "video", "start_s": 1.5, "width": 1920, "height": 1080},
        {"file": "clips/shot_03.jpg", "kind": "photo", "start_s": 2.0, "width": 1600, "height": 1000},
    ]}
    text = "Look here. Number one, crab. Old."
    script = {"beats": [{"text": "Look here."}, {"text": "Number one, crab."}, {"text": "Old."}]}
    (paths.root / "audio" / "sfx").mkdir(parents=True)
    shutil.copy(sine_mp3, paths.root / "audio" / "sfx" / "boom.mp3")
    shutil.copy(sine_mp3, paths.root / "audio" / "bgm.mp3")
    audio = {"bgm": "audio/bgm.mp3", "sfx": {"hook": "audio/sfx/boom.mp3", "number": "audio/sfx/boom.mp3"}}
    timeline = build_timeline(clips, audio_duration_s=3.0, fg_min_ratio=0.5, script=script,
                              alignment=fake_alignment(text, 2.97), audio=audio,
                              overlays={"clips/shot_01.mp4": {"points": [{"t": 0.2, "x": 300, "y": 600, "w": 400, "h": 500}]},
                                        "clips/shot_03.jpg": {"points": [{"t": 0.0, "x": 200, "y": 100, "w": 600, "h": 500}]}})
    assert timeline["countdown"] and timeline["captions"] and timeline["bgm"] and timeline["sfx"] and timeline["overlays"]
    (paths.root / "emoji").mkdir()
    write_json_atomic(paths.root / "emoji" / "1f9d0.json",
                      {"v": "5.7.4", "fr": 30, "ip": 0, "op": 30, "w": 100, "h": 100, "nm": "t", "ddd": 0, "assets": [], "layers": []})
    timeline["emojis"] = [{"src": "emoji/1f9d0.json", "from": 5, "durationInFrames": 25}]
    timeline["cta"] = [{"kind": "like", "from": 30, "durationInFrames": 16, "clickAt": 3},
                       {"kind": "subscribe", "from": 46, "durationInFrames": 27, "clickAt": 13}]
    write_json_atomic(paths.timeline_json, timeline)

    run_render(paths)

    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,codec_name,width,height,r_frame_rate:format=duration",
         "-of", "json", str(paths.final_mp4)],
        capture_output=True, text=True, check=True,
    )
    info = json.loads(out.stdout)
    video = next(s for s in info["streams"] if s["codec_type"] == "video")
    audio = next(s for s in info["streams"] if s["codec_type"] == "audio")
    assert (video["codec_name"], video["width"], video["height"], video["r_frame_rate"]) == ("h264", 1080, 1920, "30/1")
    assert audio["codec_name"] == "aac"
    assert abs(float(info["format"]["duration"]) - 3.0) < 0.1
    for t in ("0.5", "1.5", "2.1", "2.9"):
        frame = tmp_path / f"frame_{t}.png"
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", t, "-i", str(paths.final_mp4), "-frames:v", "1", str(frame)], check=True)
        assert frame.exists()
