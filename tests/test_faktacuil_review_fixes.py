import pytest
from google.auth.exceptions import RefreshError
from google.oauth2.credentials import Credentials

from mayzfact import cli, youtube
from mayzfact.config import Settings
from mayzfact.errors import PipelineError
from mayzfact.models import Script
from mayzfact.steps.script import check_script
from mayzfact.steps.timeline import build_timeline
from mayzfact.store import RunPaths, write_json_atomic
from tests.faktacuil_fixtures import (
    SOURCE_TEXT_EN,
    faktacuil_script,
    faktacuil_timeline_fixture,
)
from tests.test_faktacuil_upload import META_ID, TOK1, VIDEO, env, make_run  # noqa: F401 (env = fixture)


def problems_for(mutate):
    data = faktacuil_script().model_dump()
    mutate(data["beats"])
    return check_script(Script(**data), SOURCE_TEXT_EN)[0]


# --- 1. kata "like" di beat jawaban yang nempel ke blok CTA ---

def test_like_in_answer_beat_next_to_cta_is_rejected():
    problems = problems_for(lambda b: b[6].update(text="rasanya like permen buat kucing."))
    assert any("Beat 7" in p and "outside the CTA" in p for p in problems)
    assert not any("CTA beat 7" in p for p in problems)  # bukan saran ngosongin subject


def test_clearing_subject_does_not_hide_like_outside_cta():
    def mutate(beats):
        beats[6].update(text="rasanya like permen buat kucing.", subject="")
    assert any("outside the CTA" in p for p in problems_for(mutate))


def test_valid_three_beat_cta_with_lead_in_still_passes():
    def mutate(beats):  # beat tengah tanpa kata like/transform = lead-in gimmick yang sah
        beats[4].update(text="Tapi coba tekan like dulu,")
        beats[5].update(text="kamu pasti penasaran banget,")
        beats.insert(6, {**beats[5], "text": "apakah like-mu berubah jadi madu?"})
    assert problems_for(mutate) == []


# --- 2. check-script pakai settings per format ---

def write_check_run(tmp_path, monkeypatch, total_words):
    monkeypatch.setattr(cli, "RUNS_DIR", tmp_path)
    paths = RunPaths(tmp_path / VIDEO)
    paths.root.mkdir()
    write_json_atomic(paths.source_json, {"video_id": VIDEO, "duration_s": 10,
                                         "transcript": [{"text": SOURCE_TEXT_EN, "start": 0.0, "duration": 10.0}]})
    write_json_atomic(paths.script_json, faktacuil_script(total_words).model_dump())
    return paths


def test_check_script_cli_uses_faktacuil_speed_not_global_voicestudio(tmp_path, monkeypatch, capsys):
    write_check_run(tmp_path, monkeypatch, 69)
    monkeypatch.setattr(cli, "load_settings", lambda: Settings(tts_provider="voicestudio"))  # global 1.15
    assert cli.main(["check-script", VIDEO]) == 0
    assert "target 62" in capsys.readouterr().out  # 1.1 x 2.27, bukan 65 (1.15)


def test_check_script_cli_range_matches_pipeline(tmp_path, monkeypatch, capsys):
    write_check_run(tmp_path, monkeypatch, 51)  # lolos 50-74 (ElevenLabs), gagal 53-78 (speed 1.15)
    monkeypatch.setattr(cli, "load_settings", lambda: Settings(tts_provider="voicestudio"))
    assert cli.main(["check-script", VIDEO]) == 0, capsys.readouterr().out


def test_check_script_cli_top3_keeps_global_speed(tmp_path, monkeypatch, capsys):
    from tests.top3_fixtures import SOURCE_TEXT, top3_script

    monkeypatch.setattr(cli, "RUNS_DIR", tmp_path)
    paths = RunPaths(tmp_path / VIDEO)
    paths.root.mkdir()
    write_json_atomic(paths.source_json, {"video_id": VIDEO, "duration_s": 10,
                                         "transcript": [{"text": SOURCE_TEXT, "start": 0.0, "duration": 10.0}]})
    write_json_atomic(paths.script_json, top3_script(80).model_dump())
    monkeypatch.setattr(cli, "load_settings", lambda: Settings(video_speed=1.0))
    assert cli.main(["check-script", VIDEO]) == 1  # top3 80 kata di speed 1.0: di luar 70-76
    assert "between" in capsys.readouterr().out


# --- 3. top3 menolak metadata bahasa Indonesia ---

def test_top3_upload_rejects_indonesian_metadata(env, tmp_path, capsys):  # noqa: F811
    paths = make_run(tmp_path, mode="top3", meta=META_ID)
    assert cli.main(["upload", VIDEO, "--at", "2099-01-01 21:00"]) == 1
    err = capsys.readouterr().err
    assert "narration_mode" in err and "faktacuil" in err
    assert env["tokens"] == [] and not (paths.root / "youtube.json").exists()


def test_upload_without_script_json_rejects_indonesian_metadata(env, tmp_path):  # noqa: F811
    make_run(tmp_path, mode=None, meta=META_ID)
    assert cli.main(["upload", VIDEO, "--at", "2099-01-01 21:00"]) == 1
    assert env["tokens"] == []


@pytest.mark.parametrize("language", ["en", "es"])
def test_top3_upload_other_languages_unchanged(env, tmp_path, language):  # noqa: F811
    make_run(tmp_path, mode="top3", meta={**META_ID, "language": language})
    assert cli.main(["upload", VIDEO, "--at", "2099-01-01 21:00"]) == 0
    assert env["tokens"] == [TOK1]


# --- 4. keyword dengan tanda baca di pinggir ---

def test_keyword_with_edge_punctuation_is_still_yellow():
    script = faktacuil_script().model_dump()
    script["beats"][2]["keyword"] = "kardus?"
    script, alignment, clips = faktacuil_timeline_fixture(25, script)
    tl = build_timeline(clips, 25, 0.5, script=script, alignment=alignment, log=lambda m: None)
    colored = {c["text"] for c in tl["captions"] if c["color"] != "#ffffff"}
    assert "KARDUS" in colored


# --- 5. hint login token FaktaCuil ---

def test_service_empty_token_faktacuil_hint():
    with pytest.raises(PipelineError, match="--channel faktacuil"):
        youtube.service("", channel="faktacuil")


def test_service_incomplete_token_faktacuil_hint():
    with pytest.raises(PipelineError, match="--channel faktacuil") as exc:
        youtube.service('{"token": "a"}', channel="faktacuil")
    assert "YOUTUBE_TOKEN_JSON_FAKTACUIL" in exc.value.message


def test_service_rejected_token_faktacuil_hint(monkeypatch):
    def refuse(self, request):
        raise RefreshError("revoked")

    monkeypatch.setattr(Credentials, "refresh", refuse)
    expired = '{"refresh_token": "r", "client_id": "c", "client_secret": "s"}'
    with pytest.raises(PipelineError, match="--channel faktacuil"):
        youtube.service(expired, channel="faktacuil")


def test_service_default_hint_has_no_channel_flag():
    with pytest.raises(PipelineError) as exc:
        youtube.service("")
    assert "--channel" not in exc.value.message


def test_cli_faktacuil_upload_passes_channel_to_service(env, tmp_path):  # noqa: F811
    seen = []
    import mayzfact.youtube as yt

    original = yt.service
    yt.service = lambda token, channel="mayzfact": seen.append(channel) or original(token, channel)
    try:
        make_run(tmp_path)
        cli.main(["upload", VIDEO, "--at", "2099-01-01 12:00"])
    finally:
        yt.service = original
    assert seen == ["faktacuil"]

