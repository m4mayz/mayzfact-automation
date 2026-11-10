import pytest

from mayzfact import cli, youtube
from mayzfact.config import ENV_FIELDS, Settings, load_settings, settings_from_env
from mayzfact.errors import PipelineError
from mayzfact.store import RunPaths, read_json, write_json_atomic
from tests.test_youtube import TOKEN, FakeRequest, FakeService, wib

TOK1, TOK2 = "TOKEN-MAYZ", "TOKEN-FAKTA"
META_ID = {"title": "Kenapa Kucing Suka Kardus? #Shorts", "description": "Fakta kucing.\n#faktaunik",
           "tags": ["kucing"], "category_id": "27", "language": "id"}
VIDEO = "NSua7RPoFJg"


class FakeYT(FakeService):
    """FakeService + channels().list; nggak pernah nyentuh YouTube beneran."""

    def __init__(self, channel_id="UCfakta", title="FaktaCuil"):
        super().__init__(FakeRequest())
        self.channel = {"items": [{"id": channel_id, "snippet": {"title": title}}]}
        self.channel_calls = []

    def channels(self):
        return self

    def list(self, part, mine):
        self.channel_calls.append((part, mine))
        return type("Req", (), {"execute": lambda _self: self.channel})()


def make_run(tmp_path, mode="faktacuil", meta=META_ID):
    paths = RunPaths(tmp_path / VIDEO)
    paths.root.mkdir()
    paths.final_mp4.write_bytes(b"mp4")
    write_json_atomic(paths.root / "upload.json", meta)
    if mode:
        write_json_atomic(paths.script_json, {"narration_mode": mode})
    return paths


@pytest.fixture
def env(monkeypatch, tmp_path):
    """CLI dengan 2 token dan YouTube palsu; service() ngecatat token yang dipakai."""
    seen = {"tokens": [], "yt": FakeYT()}

    def fake_service(token):
        seen["tokens"].append(token)
        return seen["yt"]

    def configure(**kw):
        values = {"youtube_token_json": TOK1, "youtube_token_json_faktacuil": TOK2,
                  "faktacuil_youtube_channel_id": "UCfakta", **kw}
        monkeypatch.setattr(cli, "load_settings", lambda: Settings(**values))

    monkeypatch.setattr(youtube, "service", fake_service)
    monkeypatch.setattr(cli, "RUNS_DIR", tmp_path)
    configure()
    seen["set"] = configure
    return seen


def test_slots_are_separate_per_channel(tmp_path):
    write_json_atomic(tmp_path / "a/youtube.json", {"publish_at": "2026-11-12T12:00:00+07:00", "channel": "faktacuil"})
    write_json_atomic(tmp_path / "b/youtube.json", {"publish_at": "2026-11-12T01:00:00+07:00"})
    assert youtube.taken_slots(tmp_path, "faktacuil") == [wib("2026-11-12 12:00")]
    assert youtube.taken_slots(tmp_path) == [wib("2026-11-12 01:00")]
    now = wib("2026-11-11 23:00")
    assert youtube.next_slot(youtube.taken_slots(tmp_path, "faktacuil"), now, hours=(12, 18)) == wib("2026-11-12 18:00")
    assert youtube.next_slot(youtube.taken_slots(tmp_path), now) == wib("2026-11-12 04:00")


def test_faktacuil_takes_at_most_two_slots_per_day():
    now = wib("2026-11-11 23:00")
    taken = [wib("2026-11-12 12:00"), wib("2026-11-12 18:00")]
    assert youtube.next_slot(taken, now, hours=(12, 18)) == wib("2026-11-13 12:00")
    assert youtube.next_slot([], wib("2026-11-12 12:00"), hours=(12, 18)) == wib("2026-11-12 18:00")  # 12.00 udah lewat
    assert youtube.next_slot([], now, hours=(18, 12)) == wib("2026-11-12 12:00")  # urutan jam nggak ngaruh


def test_next_slot_cli_faktacuil_uses_settings_hours(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(cli, "load_settings", lambda: Settings(faktacuil_slot_hours=(12,)))
    monkeypatch.setattr(cli, "RUNS_DIR", tmp_path)
    assert cli.main(["next-slot", "--channel", "faktacuil"]) == 0
    assert capsys.readouterr().out.strip().endswith("12:00")


def test_next_slot_cli_faktacuil_skips_faktacuil_uploads_only(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(cli, "load_settings", lambda: Settings())
    monkeypatch.setattr(cli, "RUNS_DIR", tmp_path)
    cli.main(["next-slot", "--channel", "faktacuil"])
    first = capsys.readouterr().out.strip()
    write_json_atomic(tmp_path / "a/youtube.json",
                      {"publish_at": first.replace(" ", "T") + ":00+07:00", "channel": "faktacuil"})
    cli.main(["next-slot", "--channel", "faktacuil"])
    second = capsys.readouterr().out.strip()
    cli.main(["next-slot"])
    mayz = capsys.readouterr().out.strip()
    assert second != first and second.endswith(("12:00", "18:00"))
    assert mayz.endswith(("01:00", "04:00"))  # slot MayzFact nggak keblok upload FaktaCuil


def test_faktacuil_upload_uses_second_token_and_marks_channel(env, tmp_path):
    paths = make_run(tmp_path)
    assert cli.main(["upload", VIDEO, "--at", "2099-01-01 12:00"]) == 0
    assert env["tokens"] == [TOK2]
    assert read_json(paths.root / "youtube.json")["channel"] == "faktacuil"
    assert env["yt"].channel_calls and env["yt"].inserted


def test_faktacuil_upload_refuses_wrong_channel(env, tmp_path):
    paths = make_run(tmp_path)
    env["yt"] = FakeYT("UCmayz", "MayzFact")
    assert cli.main(["upload", VIDEO, "--at", "2099-01-01 12:00"]) == 1
    assert env["yt"].inserted == [] and not (paths.root / "youtube.json").exists()


def test_faktacuil_upload_refuses_empty_channel_id(env, tmp_path, capsys):
    paths = make_run(tmp_path)
    env["set"](faktacuil_youtube_channel_id="")
    assert cli.main(["upload", VIDEO, "--at", "2099-01-01 12:00"]) == 1
    assert env["tokens"] == []  # service belum dibikin
    assert "faktacuil_youtube_channel_id" in capsys.readouterr().err
    assert not (paths.root / "youtube.json").exists()


def test_faktacuil_upload_requires_indonesian_metadata(env, tmp_path):
    make_run(tmp_path, meta={**META_ID, "language": "en"})
    assert cli.main(["upload", VIDEO, "--at", "2099-01-01 12:00"]) == 1
    assert env["tokens"] == [] and env["yt"].inserted == []


def test_faktacuil_upload_without_token_points_to_login(tmp_path, capsys, monkeypatch):
    make_run(tmp_path)
    monkeypatch.setattr(cli, "RUNS_DIR", tmp_path)
    monkeypatch.setattr(cli, "load_settings", lambda: Settings(faktacuil_youtube_channel_id="UCfakta"))
    assert cli.main(["upload", VIDEO, "--at", "2099-01-01 12:00"]) == 1  # service() asli: token kosong ditolak lokal
    assert "login youtube --channel faktacuil" in capsys.readouterr().err


def test_top3_upload_unchanged(env, tmp_path):
    paths = make_run(tmp_path, mode="top3", meta={**META_ID, "language": "en"})
    env["yt"] = FakeYT("UCmayz", "MayzFact")
    assert cli.main(["upload", VIDEO, "--at", "2099-01-01 21:00"]) == 0
    assert env["tokens"] == [TOK1]
    assert "channel" not in read_json(paths.root / "youtube.json")
    assert env["yt"].channel_calls == []  # top3 nggak ngecek channel


def test_upload_without_script_json_stays_top3(env, tmp_path):
    paths = make_run(tmp_path, mode=None, meta={**META_ID, "language": "en"})
    assert cli.main(["upload", VIDEO, "--at", "2099-01-01 21:00"]) == 0
    assert env["tokens"] == [TOK1] and "channel" not in read_json(paths.root / "youtube.json")


def test_run_mode(tmp_path):
    assert youtube.run_mode(RunPaths(tmp_path / "x")) == "top3"
    paths = RunPaths(tmp_path / "y")
    write_json_atomic(paths.script_json, {"beats": []})
    assert youtube.run_mode(paths) == "top3"
    write_json_atomic(paths.script_json, {"narration_mode": "faktacuil"})
    assert youtube.run_mode(paths) == "faktacuil"
    paths.script_json.write_text("{rusak", encoding="utf-8")
    with pytest.raises(PipelineError, match="script.json"):  # jangan nebak channel dari file rusak
        youtube.run_mode(paths)


def test_unknown_mode_blocks_upload(env, tmp_path):
    make_run(tmp_path, mode="source")
    assert cli.main(["upload", VIDEO, "--at", "2099-01-01 12:00"]) == 1
    assert env["tokens"] == []


def test_channel_info():
    assert youtube.channel_info(FakeYT("UCx", "Judul")) == ("UCx", "Judul")
    empty = FakeYT()
    empty.channel = {}
    with pytest.raises(PipelineError, match="channel"):
        youtube.channel_info(empty)


def test_login_faktacuil_writes_second_token_only(monkeypatch, tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text(f"YOUTUBE_TOKEN_JSON='{TOKEN}'\n", encoding="utf-8")

    class FakeFlow:
        @classmethod
        def from_client_config(cls, config, scopes):
            return cls()

        def run_local_server(self, port):
            return type("Creds", (), {"to_json": lambda self: '{"token": "second"}'})()

    monkeypatch.setattr(youtube, "_flow_class", lambda: FakeFlow)
    youtube.login('{"installed": {}}', env_file, token_env="YOUTUBE_TOKEN_JSON_FAKTACUIL")
    s = load_settings(env_file)
    assert s.youtube_token_json == TOKEN and s.youtube_token_json_faktacuil == '{"token": "second"}'


def test_login_faktacuil_cli_prints_channel_not_token(monkeypatch, capsys):
    seen = {}
    monkeypatch.setattr(cli, "load_settings", lambda: Settings(youtube_client_secret_json='{"installed": {}}'))

    def fake_login(secret, env_file, token_env="YOUTUBE_TOKEN_JSON"):
        seen["token_env"] = token_env
        return "SECRET-TOKEN-VALUE"

    monkeypatch.setattr(youtube, "login", fake_login)
    monkeypatch.setattr(youtube, "service", lambda token: seen.update(token=token) or FakeYT("UCfakta", "FaktaCuil"))
    assert cli.main(["login", "youtube", "--channel", "faktacuil"]) == 0
    out = capsys.readouterr()
    assert seen["token_env"] == "YOUTUBE_TOKEN_JSON_FAKTACUIL" and seen["token"] == "SECRET-TOKEN-VALUE"
    assert "FaktaCuil" in out.out and "UCfakta" in out.out
    assert "SECRET-TOKEN-VALUE" not in out.out + out.err


def test_login_rejects_unknown_channel():
    with pytest.raises(SystemExit) as exc:
        cli.main(["login", "youtube", "--channel", "lain"])
    assert exc.value.code == 2


def test_secret_not_in_repr():
    assert "TOK2" not in repr(Settings(youtube_token_json_faktacuil="TOK2"))


def test_settings_defaults_and_env_field():
    s = Settings()
    assert (s.faktacuil_slot_hours, s.faktacuil_youtube_channel_id, s.youtube_token_json_faktacuil) == ((12, 18), "", "")
    assert "YOUTUBE_TOKEN_JSON_FAKTACUIL" in ENV_FIELDS
    assert settings_from_env({"YOUTUBE_TOKEN_JSON_FAKTACUIL": "T2"}).youtube_token_json_faktacuil == "T2"
