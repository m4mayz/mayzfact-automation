import json

import httpx
import pytest

from mayzfact.errors import PipelineError
from mayzfact.manual.og import og_media
from mayzfact.manual.rednote import find_note, note_media, rednote_state, resolve_rednote
from mayzfact.manual.types import Media

VIDEO_NOTE = {"title": "鲎", "video": {"media": {"stream": {"h264": [{"masterUrl": "//sns-video.xhscdn.com/a.mp4"}]}}}}
PHOTO_NOTE = {"title": "鹦鹉螺", "imageList": [{"urlDefault": "//sns-img.xhscdn.com/1.jpg"}, {"urlOriginal": "https://sns-img.xhscdn.com/2.jpg"}]}


def state_html(note):
    state = {"note": {"noteDetailMap": {"abc": {"note": note}}}, "x": "__UNDEF__"}
    raw = json.dumps(state).replace('"__UNDEF__"', "undefined")
    return f"<script>window.__INITIAL_STATE__={raw}</script>"


def test_state_parsing_and_media():
    assert find_note(rednote_state(state_html(VIDEO_NOTE)))["title"] == "鲎"
    assert note_media(VIDEO_NOTE) == [Media("video", "https://sns-video.xhscdn.com/a.mp4")]
    assert note_media(PHOTO_NOTE) == [Media("photo", "https://sns-img.xhscdn.com/1.jpg"), Media("photo", "https://sns-img.xhscdn.com/2.jpg")]
    assert rednote_state("<html></html>") is None


def test_resolve_rednote_reads_note_page():
    transport = httpx.MockTransport(lambda r: httpx.Response(200, text=state_html(PHOTO_NOTE)))
    assert len(resolve_rednote("https://www.xiaohongshu.com/explore/66a1b2c3d4e5f6a7b8c9d0e1", transport=transport)) == 2


def test_resolve_rednote_reports_ip_block():
    def handler(request):
        if "website-login" in request.url.path:
            return httpx.Response(200, text="安全限制 IP at risk")
        return httpx.Response(302, headers={"location": "https://www.xiaohongshu.com/website-login/error?error_code=300012"})

    with pytest.raises(PipelineError, match="upload"):
        resolve_rednote("https://www.xiaohongshu.com/explore/66a1b2c3d4e5f6a7b8c9d0e1", transport=httpx.MockTransport(handler))


def test_og_media():
    html = ('<meta property="og:video" content="https://v.example/a.mp4">'
            '<meta property="og:image" content="//img.example/a.jpg">')
    transport = httpx.MockTransport(lambda r: httpx.Response(200, text=html))
    assert og_media("https://example.com/p", transport=transport) == [
        Media("video", "https://v.example/a.mp4"), Media("photo", "https://img.example/a.jpg")]
    empty = httpx.MockTransport(lambda r: httpx.Response(200, text="<html></html>"))
    assert og_media("https://example.com/p", transport=empty) == []
