import json
import shutil
import subprocess

import pytest

from mayzfact.steps.render import render_command, run_render, speed_command, speed_up
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


def test_speed_command_speeds_picture_and_voice_together(tmp_path):
    cmd = speed_command(tmp_path / "in.mp4", tmp_path / "out.mp4", 1.2)
    graph = cmd[cmd.index("-filter_complex") + 1]
    assert "setpts=PTS/1.2" in graph and "atempo=1.2" in graph  # atempo: tempo naik, nada suara tetap
    assert cmd[-1] == str(tmp_path / "out.mp4")


def test_speed_up_shortens_video_by_the_factor(tmp_path):
    src = tmp_path / "in.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "color=red:s=320x568:d=3:r=30",
                    "-f", "lavfi", "-i", "sine=frequency=440:duration=3", "-shortest", "-c:v", "libx264",
                    "-pix_fmt", "yuv420p", "-c:a", "aac", str(src)], check=True)
    out = speed_up(src, tmp_path / "out.mp4", 1.2)
    probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(out)],
                           capture_output=True, text=True, check=True)
    assert abs(float(probe.stdout) - 2.5) < 0.1
    streams = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type", "-of", "csv=p=0", str(out)],
                             capture_output=True, text=True, check=True).stdout.split()
    assert sorted(streams) == ["audio", "video"]


def test_run_render_speed_up_does_not_clash_with_its_own_tmp_file(tmp_path, monkeypatch):
    # Regresi: output Remotion dulu final.tmp.mp4, sama kayak file sementara speed_up -> ffmpeg "same as Input"
    paths = RunPaths(tmp_path / "run")
    paths.root.mkdir(parents=True)
    remotion_dir = tmp_path / "remotion"
    (remotion_dir / "node_modules").mkdir(parents=True)
    real_run = subprocess.run

    def fake_run(cmd, **kw):
        if cmd[0] == "npx":  # Remotion palsu: bikin video 3 detik di path output-nya
            return real_run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "color=red:s=320x568:d=3:r=30",
                             "-f", "lavfi", "-i", "sine=frequency=440:duration=3", "-shortest", "-c:v", "libx264",
                             "-pix_fmt", "yuv420p", "-c:a", "aac", cmd[5]], **kw)
        return real_run(cmd, **kw)

    monkeypatch.setattr("mayzfact.steps.render.shutil.which", lambda _name: "npx")
    monkeypatch.setattr("mayzfact.steps.render.subprocess.run", fake_run)
    out = run_render(paths, remotion_dir, speed=1.2)
    assert out == paths.final_mp4
    probe = real_run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(out)],
                     capture_output=True, text=True, check=True)
    assert abs(float(probe.stdout) - 2.5) < 0.1
    assert not list(paths.root.glob("*.tmp.mp4"))  # file sementara dibersihin


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
    timeline["cta"] = [{"kind": "like", "from": 30, "durationInFrames": 16, "clickAt": 4},
                       {"kind": "subscribe", "from": 46, "durationInFrames": 27, "clickAt": 14}]
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
