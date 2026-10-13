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
        {"file": "clips/shot_02.mp4", "kind": "video", "start_s": 1.0, "width": 1920, "height": 1080},
        {"file": "clips/shot_03.jpg", "kind": "photo", "start_s": 2.0, "width": 1600, "height": 1000},
    ]}
    text = "Look here. Number one, crab. Old."
    script = {"beats": [{"text": "Look here."}, {"text": "Number one, crab."}, {"text": "Old."}]}
    timeline = build_timeline(clips, audio_duration_s=3.0, fg_min_ratio=0.5, script=script, alignment=fake_alignment(text, 2.97))
    assert timeline["countdown"] and timeline["captions"]
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
