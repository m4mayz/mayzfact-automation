
import httpx
import pytest
from PIL import Image

from mayzfact.errors import PipelineError
from mayzfact.manual.obtain import Obtainer, cache_key, media_kind
from mayzfact.manual.types import Media


def client_serving(files):
    return httpx.Client(transport=httpx.MockTransport(
        lambda r: httpx.Response(200, content=files[r.url.path]) if r.url.path in files else httpx.Response(404)))


def test_media_kind(tmp_path, make_video):
    photo = tmp_path / "a.jpg"
    Image.new("RGB", (8, 8)).save(photo)
    junk = tmp_path / "b.bin"
    junk.write_bytes(b"<html>")
    assert media_kind(photo) == "photo"
    assert media_kind(make_video(320, 240, 1.0)) == "video"
    assert media_kind(junk) is None


def test_uploaded_file_is_used_and_must_stay_in_run(tmp_path):
    run = tmp_path / "run"
    (run / "manual").mkdir(parents=True)
    (run / "manual" / "shot_01.jpg").write_bytes(b"x")
    obtainer = Obtainer(tmp_path / "cache", client_serving({}))
    assert obtainer.obtain({"file": "manual/shot_01.jpg"}, run) == [run / "manual" / "shot_01.jpg"]
    with pytest.raises(PipelineError, match="nggak ketemu"):
        obtainer.obtain({"file": "manual/shot_09.jpg"}, run)


def test_direct_link_downloads_once(tmp_path):
    hits = []

    def handler(request):
        hits.append(request.url.path)
        return httpx.Response(200, content=b"jpg-bytes")

    obtainer = Obtainer(tmp_path / "cache", httpx.Client(transport=httpx.MockTransport(handler)))
    entry = {"url": "https://cdn.example.com/a.jpg"}
    first = obtainer.obtain(entry, tmp_path)
    second = obtainer.obtain(entry, tmp_path)
    assert first == second and first[0].name.startswith(cache_key(entry["url"]))
    assert hits == ["/a.jpg"]


def test_ytdlp_first_then_resolver_then_og(tmp_path, make_video):
    video = make_video(320, 240, 1.0)
    calls = []

    def failing_ytdlp(url, dest, **kwargs):
        calls.append("ytdlp")
        raise PipelineError("fetch", "yt-dlp gagal")

    def douyin_resolver(url):
        calls.append("douyin")
        return [Media("video", "https://cdn.example.com/v.mp4")]

    obtainer = Obtainer(tmp_path / "cache", client_serving({"/v.mp4": video.read_bytes()}),
                        ytdlp=failing_ytdlp, resolvers={"douyin": douyin_resolver, "og": lambda url: []})
    files = obtainer.obtain({"url": "https://www.douyin.com/video/7694448955383418155"}, tmp_path)
    assert calls == ["ytdlp", "douyin"]
    assert files[0].suffix == ".mp4"


def test_photo_post_downloads_all_photos(tmp_path):
    jpg = tmp_path / "src.jpg"
    Image.new("RGB", (8, 8)).save(jpg)
    resolvers = {"rednote": lambda url: [Media("photo", "https://img.example/1.jpg"), Media("photo", "https://img.example/2.webp")],
                 "og": lambda url: []}
    obtainer = Obtainer(tmp_path / "cache", client_serving({"/1.jpg": jpg.read_bytes(), "/2.webp": jpg.read_bytes()}),
                        ytdlp=lambda *a, **k: (_ for _ in ()).throw(PipelineError("fetch", "no video")), resolvers=resolvers)
    files = obtainer.obtain({"url": "https://www.xiaohongshu.com/explore/66a1b2c3d4e5f6a7b8c9d0e1"}, tmp_path)
    assert [f.suffix for f in files] == [".jpg", ".webp"]


def test_all_methods_failing_suggests_upload(tmp_path):
    obtainer = Obtainer(tmp_path / "cache", client_serving({}),
                        ytdlp=lambda *a, **k: (_ for _ in ()).throw(PipelineError("fetch", "ytdlp x")),
                        resolvers={"og": lambda url: []})
    with pytest.raises(PipelineError, match="upload"):
        obtainer.obtain({"url": "https://example.com/page"}, tmp_path)
