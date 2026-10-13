import json

import httpx
import pytest

from mayzfact.errors import PipelineError
from mayzfact.manual.obtain import Obtainer
from mayzfact.manual.tiktok import resolve_tiktok
from mayzfact.manual.types import Media

VIDEO_HTML = """
<div class="tk-result-content"><div class="video-info"><img src="https://p16.example/thumb.jpeg"><h3>Platypus</h3></div>
<div class="download-links">
  <a href="https://dl.tiktokio.com/download?token=SD&#38;x=1" class="download-btn download-btn-blue">Download without watermark</a>
  <a href="https://dl.tiktokio.com/download?token=HD" class="download-btn download-btn-green">Download without watermark (HD)</a>
  <a href="https://dl.tiktokio.com/download?token=WM" class="download-btn download-btn-gray" onclick="handleAdClick()">Download watermark</a>
  <a href="https://dl.tiktokio.com/download?token=MP3" class="download-btn download-btn-purple">Download Mp3</a>
</div></div>
"""
PHOTO_HTML = """
<div class="images-grid">
  <div class="image-item"><img src="https://p16.example/1.jpeg"><a href="https://dl.tiktokio.com/download?token=P1">Download</a></div>
  <div class="image-item"><img src="https://p16.example/2.jpeg"></div>
</div>
<a href="https://dl.tiktokio.com/download?token=MP3" class="download-btn download-btn-purple">Download Mp3</a>
"""


def test_resolve_tiktok_posts_clean_url_and_prefers_hd():
    seen = []

    def handler(request):
        seen.append((str(request.url), json.loads(request.content)))
        return httpx.Response(200, text=VIDEO_HTML)

    media = resolve_tiktok("https://www.tiktok.com/@unsw/video/7206163208862797058?is_from_webapp=1",
                           transport=httpx.MockTransport(handler))
    assert media == [Media("video", "https://dl.tiktokio.com/download?token=HD"),
                     Media("video", "https://dl.tiktokio.com/download?token=SD&x=1")]
    assert seen == [("https://tiktokio.com/api/v1/tk/html",
                     {"vid": "https://www.tiktok.com/@unsw/video/7206163208862797058", "prefix": "tiktokio.com"})]


def test_resolve_tiktok_photo_post():
    media = resolve_tiktok("https://www.tiktok.com/@a/photo/1", transport=httpx.MockTransport(lambda r: httpx.Response(200, text=PHOTO_HTML)))
    assert media == [Media("photo", "https://dl.tiktokio.com/download?token=P1"), Media("photo", "https://p16.example/2.jpeg")]


def test_resolve_tiktok_reports_failure():
    transport = httpx.MockTransport(lambda r: httpx.Response(200, text="<p>Please paste a valid link</p>"))
    with pytest.raises(PipelineError, match="upload"):
        resolve_tiktok("https://www.tiktok.com/@a/video/1", transport=transport)


def test_obtainer_uses_tiktok_resolver_by_default(tmp_path):
    obtainer = Obtainer(tmp_path / "cache", httpx.Client())
    assert obtainer._resolvers["tiktok"] is resolve_tiktok
