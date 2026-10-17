import os

from mayzfact.store import RunPaths, read_json, tmp_path_for, write_json_atomic


def test_write_json_atomic_roundtrip_without_leftover(tmp_path):
    target = tmp_path / "nested" / "data.json"
    write_json_atomic(target, {"judul": "Kepiting", "angka": [1, 2]})
    assert read_json(target) == {"judul": "Kepiting", "angka": [1, 2]}
    assert sorted(p.name for p in target.parent.iterdir()) == ["data.json"]


def test_tmp_path_keeps_extension(tmp_path):
    assert tmp_path_for(tmp_path / "shot_01.mp4").name == "shot_01.tmp.mp4"
    assert tmp_path_for(tmp_path / "voice.incoming.mp3").name == "voice.incoming.tmp.mp3"


def test_run_paths_layout(tmp_path):
    paths = RunPaths(tmp_path / "abc")
    assert paths.source_json == tmp_path / "abc" / "source.json"
    assert paths.voice_mp3 == tmp_path / "abc" / "voice.mp3"
    assert paths.clips_dir == tmp_path / "abc" / "clips"
    assert paths.final_mp4.name == "final.mp4"


def test_run_paths_source_mp4_and_no_hook_files(tmp_path):
    paths = RunPaths(tmp_path)
    assert paths.source_mp4 == tmp_path / "source.mp4"
    assert not hasattr(paths, "hook_dir") and not hasattr(paths, "hook_json")


def test_run_paths_manual_files(tmp_path):
    from mayzfact.errors import AwaitingInput, PipelineError

    paths = RunPaths(tmp_path)
    assert paths.shots_plan_json == tmp_path / "shots_plan.json"
    assert paths.plan_dir == tmp_path / "plan"
    assert paths.links_json == tmp_path / "links.json"
    assert paths.links_status_json == tmp_path / "links_status.json"
    assert paths.manual_dir == tmp_path / "manual"
    assert issubclass(AwaitingInput, PipelineError)


def test_atomic_write_retries_when_windows_locks_target(tmp_path, monkeypatch):
    import mayzfact.store as store

    real = os.replace
    calls = []

    def flaky(src, dst):
        calls.append(dst)
        if len(calls) < 3:
            raise PermissionError(13, "file dibuka proses lain")
        real(src, dst)

    monkeypatch.setattr(store.os, "replace", flaky)
    monkeypatch.setattr(store, "REPLACE_WAIT_S", 0.0)
    write_json_atomic(tmp_path / "a.json", {"x": 1})
    assert read_json(tmp_path / "a.json") == {"x": 1} and len(calls) == 3
