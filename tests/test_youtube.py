import os
from datetime import datetime

import httplib2
import pytest
from googleapiclient.errors import HttpError

from mayzfact import youtube
from mayzfact.config import load_settings
from mayzfact.errors import PipelineError
from mayzfact.store import RunPaths, read_json, write_json_atomic

TOKEN = '{"token": "a", "refresh_token": "r", "client_id": "c", "client_secret": "s"}'
META = {"title": "5 Birds With Real Superpowers #Shorts", "description": "Birds that break the rules.\n#birds",
        "tags": ["birds", "animals"], "category_id": "15"}


def wib(text):
    return datetime.strptime(text, "%Y-%m-%d %H:%M").replace(tzinfo=youtube.WIB)


def test_set_env_value_replaces_only_that_line(tmp_path):
    env = tmp_path / ".env"
    env.write_bytes(b"# komentar\r\nGEMINI_MODEL=x\r\n\r\nYOUTUBE_TOKEN_JSON=\r\nBRIEF_PORT=3100\r\n")
    youtube.set_env_value(env, "YOUTUBE_TOKEN_JSON", TOKEN)
    lines = env.read_text(encoding="utf-8").splitlines()
    assert lines == ["# komentar", "GEMINI_MODEL=x", "", f"YOUTUBE_TOKEN_JSON='{TOKEN}'", "BRIEF_PORT=3100"]
    assert load_settings(env).youtube_token_json == TOKEN  # python-dotenv bisa baca balik


def test_set_env_value_appends_when_missing(tmp_path):
    env = tmp_path / ".env"
    env.write_text("GEMINI_MODEL=x\n", encoding="utf-8")
    youtube.set_env_value(env, "YOUTUBE_TOKEN_JSON", TOKEN)
    assert env.read_text(encoding="utf-8").splitlines()[-1] == f"YOUTUBE_TOKEN_JSON='{TOKEN}'"


def test_bad_json_env_never_echoes_its_value():
    with pytest.raises(PipelineError) as exc:
        youtube.parse_json_env("YOUTUBE_CLIENT_SECRET_JSON", "{rahasia-banget")
    assert "rahasia" not in str(exc.value) and "YOUTUBE_CLIENT_SECRET_JSON" in str(exc.value)
    with pytest.raises(PipelineError, match="kosong"):
        youtube.parse_json_env("YOUTUBE_CLIENT_SECRET_JSON", "  ")


def test_settings_hide_youtube_secrets_from_repr(tmp_path):
    env = tmp_path / ".env"
    env.write_text(f"YOUTUBE_CLIENT_SECRET_JSON='{TOKEN}'\n", encoding="utf-8")
    settings = load_settings(env)
    assert settings.youtube_client_secret_json == TOKEN and "refresh_token" not in repr(settings)


def test_login_writes_token_to_env(monkeypatch, tmp_path):
    env = tmp_path / ".env"
    env.write_text("YOUTUBE_TOKEN_JSON=\n", encoding="utf-8")
    seen = {}

    class FakeFlow:
        @classmethod
        def from_client_config(cls, config, scopes):
            seen.update(config=config, scopes=scopes)
            return cls()

        def run_local_server(self, port):
            return type("Creds", (), {"to_json": lambda self: TOKEN})()

    monkeypatch.setattr(youtube, "_flow_class", lambda: FakeFlow)
    youtube.login('{"installed": {}}', env)
    assert seen == {"config": {"installed": {}}, "scopes": youtube.SCOPES}
    assert load_settings(env).youtube_token_json == TOKEN


@pytest.mark.parametrize("bad", [{"title": "x" * 101}, {"title": "a <b>"}, {"description": "a > b"},
                                 {"tags": ["x" * 300, "y" * 300]}, {"category_id": "pets"}])
def test_upload_meta_rejects_bad_fields(bad):
    with pytest.raises(ValueError):
        youtube.UploadMeta(**{**META, **bad})


def test_load_meta_reports_problems(tmp_path):
    paths = RunPaths(tmp_path)
    with pytest.raises(PipelineError, match="upload.json"):
        youtube.load_meta(paths)
    write_json_atomic(paths.root / "upload.json", {**META, "title": ""})
    with pytest.raises(PipelineError, match="title"):
        youtube.load_meta(paths)
    write_json_atomic(paths.root / "upload.json", META)
    assert youtube.load_meta(paths).category_id == "15"


def test_next_slot_skips_taken_and_too_soon():
    now = wib("2026-10-15 20:50")  # 21.00 cuma 10 menit lagi, jadi dilewat
    assert youtube.next_slot([], now) == wib("2026-10-16 04:00")
    assert youtube.next_slot([wib("2026-10-16 04:00")], now) == wib("2026-10-16 21:00")
    assert youtube.next_slot([], wib("2026-10-15 12:00")) == wib("2026-10-15 21:00")


def test_taken_slots_reads_uploaded_runs(tmp_path):
    write_json_atomic(tmp_path / "a" / "youtube.json", {"publish_at": "2026-10-15T21:00:00+07:00"})
    (tmp_path / "b").mkdir()
    assert youtube.taken_slots(tmp_path) == [wib("2026-10-15 21:00")]


def test_parse_publish_at_is_wib_and_in_the_future():
    now = wib("2026-10-15 12:00")
    assert youtube.parse_publish_at("2026-10-15 21:00", now) == wib("2026-10-15 21:00")
    for bad in ("2026-10-15 12:10", "15-10-2026 21:00", "besok"):
        with pytest.raises(PipelineError):
            youtube.parse_publish_at(bad, now)


def test_video_body_schedules_private_video():
    body = youtube.video_body(youtube.UploadMeta(**META), wib("2026-10-15 21:00"))
    assert body["status"] == {"privacyStatus": "private", "publishAt": "2026-10-15T14:00:00Z",
                              "selfDeclaredMadeForKids": False}
    assert body["snippet"] == {"title": META["title"], "description": META["description"], "tags": META["tags"],
                               "categoryId": "15", "defaultLanguage": "en", "defaultAudioLanguage": "en"}


class FakeRequest:
    def __init__(self, error=None):
        self.error, self.calls = error, 0

    def next_chunk(self, num_retries=0):
        self.calls += 1
        if self.error:
            raise self.error
        if self.calls == 1:
            return type("Status", (), {"progress": lambda self: 0.5})(), None
        return None, {"id": "abc123"}


class FakeService:
    def __init__(self, request):
        self.request, self.inserted = request, []

    def videos(self):
        return self

    def insert(self, part, body, media_body):
        self.inserted.append((part, body))
        return self.request


def ready_run(tmp_path):
    paths = RunPaths(tmp_path / "vid")
    paths.root.mkdir()
    paths.final_mp4.write_bytes(b"mp4")
    return paths


def test_upload_writes_result_and_logs_progress(tmp_path):
    paths, logs = ready_run(tmp_path), []
    fake = FakeService(FakeRequest())
    data = youtube.upload_video(paths, youtube.UploadMeta(**META), wib("2026-10-15 21:00"), lambda: fake, logs.append)
    assert data["video_id"] == "abc123" and data["url"] == "https://youtube.com/shorts/abc123"
    assert data["studio_url"] == "https://studio.youtube.com/video/abc123/edit"
    assert data["publish_at"] == "2026-10-15T21:00:00+07:00"
    assert read_json(paths.root / "youtube.json") == data
    assert fake.inserted[0][0] == "snippet,status" and fake.inserted[0][1]["status"]["privacyStatus"] == "private"
    assert any("50%" in line for line in logs)


def test_upload_refuses_second_upload_without_calling_youtube(tmp_path):
    paths = ready_run(tmp_path)
    write_json_atomic(paths.root / "youtube.json", {"url": "https://youtube.com/shorts/old"})
    called = []
    with pytest.raises(PipelineError, match="shorts/old"):
        youtube.upload_video(paths, youtube.UploadMeta(**META), wib("2026-10-15 21:00"), lambda: called.append(1), print)
    assert called == []


def test_upload_needs_final_mp4(tmp_path):
    paths = RunPaths(tmp_path / "vid")
    paths.root.mkdir()
    with pytest.raises(PipelineError, match="final.mp4"):
        youtube.upload_video(paths, youtube.UploadMeta(**META), wib("2026-10-15 21:00"), lambda: None, print)


def test_youtube_error_leaves_no_result(tmp_path):
    paths = ready_run(tmp_path)
    error = HttpError(httplib2.Response({"status": 403}), b'{"error": {"message": "quotaExceeded"}}')
    with pytest.raises(PipelineError, match="403"):
        youtube.upload_video(paths, youtube.UploadMeta(**META), wib("2026-10-15 21:00"),
                             lambda: FakeService(FakeRequest(error)), print)
    assert not (paths.root / "youtube.json").exists()


def test_service_needs_login():
    with pytest.raises(PipelineError, match="login youtube"):
        youtube.service("")


def test_service_turns_offline_refresh_into_clean_error(monkeypatch):
    from google.auth.exceptions import TransportError
    from google.oauth2.credentials import Credentials

    def offline(self, request):
        raise TransportError("offline")

    monkeypatch.setattr(Credentials, "refresh", offline)
    no_access_token = '{"refresh_token": "r", "client_id": "c", "client_secret": "s"}'  # token kosong → harus refresh
    with pytest.raises(PipelineError, match="koneksi"):
        youtube.service(no_access_token)


def test_service_asks_relogin_for_incomplete_token():
    with pytest.raises(PipelineError, match="login youtube"):
        youtube.service('{"token": "a"}')


@pytest.mark.parametrize("error", ["dns", "incomplete", "auth", "reset"])
def test_connection_errors_tell_to_check_studio_first(tmp_path, error):
    import http.client

    from google.auth.exceptions import TransportError

    exc = {"dns": httplib2.error.ServerNotFoundError("dns"), "incomplete": http.client.IncompleteRead(b""),
           "auth": TransportError("offline"), "reset": ConnectionResetError("reset")}[error]
    paths = ready_run(tmp_path)
    with pytest.raises(PipelineError, match="YouTube Studio"):
        youtube.upload_video(paths, youtube.UploadMeta(**META), wib("2026-10-15 21:00"),
                             lambda: FakeService(FakeRequest(exc)), print)
    assert not (paths.root / "youtube.json").exists()


def test_load_meta_reports_broken_json(tmp_path):
    paths = RunPaths(tmp_path)
    (paths.root / "upload.json").write_text('{"title": "a', encoding="utf-8")
    with pytest.raises(PipelineError, match="upload.json"):
        youtube.load_meta(paths)


def test_set_env_value_cleans_up_when_env_is_locked(monkeypatch, tmp_path):
    env = tmp_path / ".env"
    env.write_text("GEMINI_MODEL=x\n", encoding="utf-8")

    def locked(src, dst):
        raise PermissionError("dikunci proses lain")

    monkeypatch.setattr(os, "replace", locked)
    with pytest.raises(PipelineError, match="login ulang"):
        youtube.set_env_value(env, "YOUTUBE_TOKEN_JSON", TOKEN)
    assert [p.name for p in tmp_path.iterdir()] == [".env"]  # file sementara (isinya secret) nggak ketinggalan
    assert env.read_text(encoding="utf-8") == "GEMINI_MODEL=x\n"


@pytest.mark.skipif(os.name == "nt", reason="permission POSIX; di Windows ngikut ACL folder")
def test_set_env_value_keeps_env_owner_only(tmp_path):
    env = tmp_path / ".env"
    env.write_text("GEMINI_MODEL=x\n", encoding="utf-8")
    env.chmod(0o644)
    youtube.set_env_value(env, "YOUTUBE_TOKEN_JSON", TOKEN)
    assert env.stat().st_mode & 0o777 == 0o600


def test_video_body_without_schedule_is_public_now():
    body = youtube.video_body(youtube.UploadMeta(**META), None)
    assert body["status"] == {"privacyStatus": "public", "selfDeclaredMadeForKids": False}


def test_upload_now_records_publish_time_as_upload_time(tmp_path):
    paths = ready_run(tmp_path)
    fake = FakeService(FakeRequest())
    data = youtube.upload_video(paths, youtube.UploadMeta(**META), None, lambda: fake, print)
    assert fake.inserted[0][1]["status"]["privacyStatus"] == "public"
    assert data["publish_at"] == data["uploaded_at"]
