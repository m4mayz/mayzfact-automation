"""Source FaktaCuil pakai transkrip asli Indonesia (D-052). Semua fetch di-fake, nggak ada panggilan YouTube."""
import pytest
from youtube_transcript_api import TranscriptsDisabled

from mayzfact.steps.script import check_script_file
from mayzfact.steps.source import run_source, youtube_transcript_id
from mayzfact.store import RunPaths, read_json, write_json_atomic
from tests.faktacuil_fixtures import SOURCE_TEXT_EN, faktacuil_script

EN = [{"text": SOURCE_TEXT_EN, "start": 0.0, "duration": 20.0}]
# Kalimat Indonesia yang sama persis dengan narasi di fixture (kecuali CTA), jadi overlap tinggi.
ID_COPY = [{"text": "Kenapa kucing suka banget, masuk ke kardus yang sempit? Padahal kardus itu keras dan nggak empuk, "
                    "dan sempit buat badan mereka. Ternyata ruang sempit bikin kucing merasa aman, "
                    "jadi dia bisa santai tanpa takut diganggu, dan itu naluri bawaan mereka.",
            "start": 0.0, "duration": 20.0}]
ID_OTHER = [{"text": "Hewan peliharaan sering memilih tempat kecil untuk bersembunyi dan beristirahat.",
             "start": 0.0, "duration": 20.0}]


def _run(tmp_path, fetch_id):
    paths = RunPaths(tmp_path)
    run_source("abcdefghijk", paths, fetch=lambda v: EN, fetch_id=fetch_id)
    return paths


def test_source_saves_transcript_id(tmp_path):
    paths = _run(tmp_path, lambda v: ID_OTHER)
    assert read_json(paths.source_json)["transcript_id"][0]["text"].startswith("Hewan peliharaan")


def test_source_transcript_id_empty_without_fetcher(tmp_path):
    paths = RunPaths(tmp_path)
    run_source("abcdefghijk", paths, fetch=lambda v: EN)
    assert read_json(paths.source_json)["transcript_id"] == []


def test_source_id_failure_does_not_fail_step(tmp_path):
    logs = []

    def boom(v):
        raise RuntimeError("jaringan putus")

    paths = RunPaths(tmp_path)
    run_source("abcdefghijk", paths, fetch=lambda v: EN, fetch_id=boom, log=logs.append)
    data = read_json(paths.source_json)
    assert data["transcript_id"] == [] and data["transcript"]
    assert any("jaringan putus" in line for line in logs)


def test_youtube_transcript_id_asks_id_and_swallows_missing(monkeypatch):
    seen = {}

    class Api:
        def fetch(self, video_id, languages):
            seen["languages"] = languages
            raise TranscriptsDisabled(video_id)

    monkeypatch.setattr("mayzfact.steps.source.YouTubeTranscriptApi", Api)
    assert youtube_transcript_id("abcdefghijk") == []
    assert seen["languages"] == ["id"]


def _check(tmp_path, script, source):
    paths = RunPaths(tmp_path)
    write_json_atomic(paths.script_json, script.model_dump())
    return check_script_file(paths, source, bgm_choices=None)


def _source(transcript_id):
    d = {"duration_s": 20, "transcript": EN}
    if transcript_id is not None:
        d["transcript_id"] = transcript_id
    return d


def test_faktacuil_rejects_copy_of_indonesian_source(tmp_path):
    problems = _check(tmp_path, faktacuil_script(), _source(ID_COPY))
    assert any("copied from the source" in p for p in problems)


def test_faktacuil_accepts_rewritten_indonesian_source(tmp_path):
    problems = _check(tmp_path, faktacuil_script(), _source(ID_OTHER))
    assert not any("copied from the source" in p for p in problems)


@pytest.mark.parametrize("transcript_id", [None, []])
def test_faktacuil_falls_back_to_english(tmp_path, transcript_id):
    script = faktacuil_script()
    script.beats[6].text = SOURCE_TEXT_EN  # overlap Inggris tinggi, tetap kena kalau fallback ke EN
    problems = _check(tmp_path, script, _source(transcript_id))
    assert any("copied from the source" in p for p in problems)


def test_top3_ignores_transcript_id(tmp_path):
    from tests.top3_fixtures import SOURCE_TEXT, top3_script
    paths = RunPaths(tmp_path)
    write_json_atomic(paths.script_json, top3_script().model_dump())
    source = {"duration_s": 90, "transcript": [{"text": SOURCE_TEXT}], "transcript_id": ID_OTHER}
    assert check_script_file(paths, source, bgm_choices=None) == []


def test_pipeline_source_step_passes_fetch_transcript_id(tmp_path):
    from mayzfact.config import Settings
    from mayzfact.pipeline import Deps, _run_step

    deps = Deps(fetch_transcript=lambda v: EN, tts=None, http=None, render=None, plan=None, fetch=None,
                fetch_transcript_id=lambda v: ID_OTHER)
    paths = RunPaths(tmp_path / "abcdefghijk")
    paths.root.mkdir()
    _run_step("source", paths, Settings(), deps, lambda m: None)
    assert read_json(paths.source_json)["transcript_id"][0]["text"].startswith("Hewan")


def test_prefer_id_pakai_transkrip_indonesia_walau_en_hilang(tmp_path):
    """Source Indonesia sering nggak punya track EN: step source nggak boleh gagal."""
    def no_en(v):
        raise TranscriptsDisabled(v)

    paths = RunPaths(tmp_path)
    run_source("abcdefghijk", paths, fetch=no_en, fetch_id=lambda v: ID_OTHER, prefer_id=True)
    data = read_json(paths.source_json)
    assert data["transcript_id"][0]["text"].startswith("Hewan peliharaan")
    assert data["transcript"] == data["transcript_id"]


def test_prefer_id_jatuh_ke_en_kalau_indonesia_kosong(tmp_path):
    paths = RunPaths(tmp_path)
    run_source("abcdefghijk", paths, fetch=lambda v: EN, fetch_id=lambda v: [], prefer_id=True)
    data = read_json(paths.source_json)
    assert data["transcript"][0]["text"] == SOURCE_TEXT_EN
    assert data["transcript_id"] == []


def test_pipeline_top3_tetap_wajib_transkrip_english(tmp_path):
    """Tanpa prefer_id (Top 3), source nggak punya transkrip EN harus tetap gagal."""
    from mayzfact.config import Settings
    from mayzfact.pipeline import Deps, _run_step

    def no_en(v):
        raise TranscriptsDisabled(v)

    deps = Deps(fetch_transcript=no_en, tts=None, http=None, render=None, plan=None, fetch=None,
                fetch_transcript_id=lambda v: ID_OTHER)
    paths = RunPaths(tmp_path / "abcdefghijk")
    paths.root.mkdir()
    with pytest.raises(TranscriptsDisabled):
        _run_step("source", paths, Settings(), deps, lambda m: None)
    assert not paths.source_json.exists()
