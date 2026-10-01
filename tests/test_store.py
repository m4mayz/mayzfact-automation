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
