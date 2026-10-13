
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
        return httpx.Response(200, content=jpg_bytes(tmp_path))

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
    resolvers = {"douyin": lambda url: [Media("photo", "https://img.example/1.jpg"), Media("photo", "https://img.example/2.webp")],
                 "og": lambda url: []}
    obtainer = Obtainer(tmp_path / "cache", client_serving({"/1.jpg": jpg.read_bytes(), "/2.webp": jpg.read_bytes()}),
                        ytdlp=lambda *a, **k: (_ for _ in ()).throw(PipelineError("fetch", "no video")), resolvers=resolvers)
    files = obtainer.obtain({"url": "https://www.douyin.com/note/7111222233334444555"}, tmp_path)
    assert [f.suffix for f in files] == [".jpg", ".webp"]


def test_all_methods_failing_suggests_upload(tmp_path):
    obtainer = Obtainer(tmp_path / "cache", client_serving({}),
                        ytdlp=lambda *a, **k: (_ for _ in ()).throw(PipelineError("fetch", "ytdlp x")),
                        resolvers={"og": lambda url: []})
    with pytest.raises(PipelineError, match="upload"):
        obtainer.obtain({"url": "https://example.com/page"}, tmp_path)


def jpg_bytes(tmp_path):
    path = tmp_path / "real.jpg"
    Image.new("RGB", (8, 8)).save(path)
    return path.read_bytes()


def test_cached_photos_keep_numeric_order(tmp_path):
    url = "https://www.douyin.com/note/7111222233334444555"
    cache = tmp_path / "cache"
    cache.mkdir()
    for i in range(12):
        (cache / f"{cache_key(url)}_{i}.jpg").write_bytes(jpg_bytes(tmp_path))
    (cache / f"{cache_key(url)}_0.tmp.f137.mp4").write_bytes(b"sisa yt-dlp")
    files = Obtainer(cache, client_serving({})).obtain({"url": url}, tmp_path)
    assert [f.name.split("_")[1] for f in files] == [f"{i}.jpg" for i in range(12)]


def test_junk_download_is_dropped_and_next_method_used(tmp_path, make_video):
    video = make_video(320, 240, 1.0)

    def junk_ytdlp(url, dest, **kwargs):
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(b"cuma audio / html")
        return dest

    files = {"/bad.mp4": b"<html>hotlink</html>", "/good.mp4": video.read_bytes()}
    resolvers = {"douyin": lambda url: [Media("video", "https://cdn.example.com/bad.mp4"), Media("video", "https://cdn.example.com/good.mp4")],
                 "og": lambda url: []}
    obtainer = Obtainer(tmp_path / "cache", client_serving(files), ytdlp=junk_ytdlp, resolvers=resolvers)
    out = obtainer.obtain({"url": "https://www.douyin.com/video/7694448955383418155"}, tmp_path)
    assert media_kind(out[0]) == "video" and out[0].read_bytes() == video.read_bytes()


def test_failed_photo_post_leaves_no_partial_cache(tmp_path):
    url = "https://www.douyin.com/note/7111222233334444555"
    served = {"/1.jpg": jpg_bytes(tmp_path)}
    resolvers = {"douyin": lambda u: [Media("photo", "https://img.example/1.jpg"), Media("photo", "https://img.example/2.jpg")],
                 "og": lambda u: []}
    no_ytdlp = lambda *a, **k: (_ for _ in ()).throw(PipelineError("fetch", "no video"))  # noqa: E731
    obtainer = Obtainer(tmp_path / "cache", client_serving(served), ytdlp=no_ytdlp, resolvers=resolvers)
    with pytest.raises(PipelineError):
        obtainer.obtain({"url": url}, tmp_path)
    served["/2.jpg"] = served["/1.jpg"]
    assert len(obtainer.obtain({"url": url}, tmp_path)) == 2


def test_unexpected_resolver_crash_becomes_pipeline_error(tmp_path):
    def broken(url):
        raise AttributeError("'str' object has no attribute 'get'")

    obtainer = Obtainer(tmp_path / "cache", client_serving({}),
                        ytdlp=lambda *a, **k: (_ for _ in ()).throw(PipelineError("fetch", "ytdlp x")),
                        resolvers={"douyin": broken, "og": lambda url: []})
    with pytest.raises(PipelineError, match="upload"):
        obtainer.obtain({"url": "https://www.douyin.com/video/7694448955383418155"}, tmp_path)
