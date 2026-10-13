import json
from urllib.parse import quote

import httpx

from mayzfact.manual.douyin import find_item, item_id, item_media, resolve_douyin, router_data
from mayzfact.manual.types import Media
from tests.test_waf import challenge_html

VIDEO_ITEM = {"aweme_id": "7694448955383418155", "desc": "鲎",
              "video": {"play_addr": {"url_list": ["http://v26.douyinvod.com/playwm/?video_id=v0200fg&ratio=720p"]}}}
IMAGE_ITEM = {"aweme_id": "7111", "images": [{"url_list": ["http://p3.douyinpic.com/a.jpeg"]},
                                            {"url_list": ["https://p3.douyinpic.com/b.jpeg"]}]}


def router_html(item):
    data = {"loaderData": {"video_(id)/page": {"videoInfoRes": {"item_list": [item]}}}}
    return f"<script>window._ROUTER_DATA = {json.dumps(data)};</script>"


def test_item_id_and_router_data():
    assert item_id("https://www.douyin.com/video/7694448955383418155?x=1") == "7694448955383418155"
    assert item_id("https://www.douyin.com/note/7111222233334444555") == "7111222233334444555"
    assert item_id("https://v.douyin.com/abc/") is None
    assert find_item(router_data(router_html(VIDEO_ITEM)))["aweme_id"] == "7694448955383418155"
    encoded = f'<script id="RENDER_DATA" type="application/json">{quote(json.dumps({"aweme": {"detail": IMAGE_ITEM}}))}</script>'
    assert find_item(router_data(encoded))["aweme_id"] == "7111"
    assert router_data("<html></html>") is None


def test_item_media_prefers_no_watermark_and_lists_photos():
    assert item_media(VIDEO_ITEM) == [
        Media("video", "https://aweme.snssdk.com/aweme/v1/play/?video_id=v0200fg"),
        Media("video", "https://v26.douyinvod.com/play/?video_id=v0200fg&ratio=720p"),
    ]
    assert item_media(IMAGE_ITEM) == [Media("photo", "https://p3.douyinpic.com/a.jpeg"), Media("photo", "https://p3.douyinpic.com/b.jpeg")]


def test_resolve_follows_short_link_and_solves_waf():
    seen = []

    def handler(request):
        seen.append((request.method, request.url.host, request.headers.get("cookie", "")))
        if request.url.host == "ttwid.bytedance.com":
            return httpx.Response(200, headers={"set-cookie": "ttwid=tt123; Path=/"})
        if request.url.host == "v.douyin.com":
            return httpx.Response(302, headers={"location": "https://www.iesdouyin.com/share/video/7694448955383418155/"})
        if "_wafchallengeid" not in request.headers.get("cookie", ""):
            return httpx.Response(200, text=challenge_html(b"pre", 7) + "<div>_wafchallengeid</div>")
        return httpx.Response(200, text=router_html(VIDEO_ITEM))

    media = resolve_douyin("https://v.douyin.com/iRNBho6u/", transport=httpx.MockTransport(handler))
    assert media[0].url.endswith("video_id=v0200fg")
    assert any("ttwid=tt123" in cookie for _, host, cookie in seen if host == "www.iesdouyin.com")


def test_resolve_falls_back_to_iteminfo_api():
    def handler(request):
        if request.url.host == "ttwid.bytedance.com":
            return httpx.Response(200)
        if "iteminfo" in request.url.path:
            return httpx.Response(200, json={"item_list": [IMAGE_ITEM]})
        return httpx.Response(200, text="<html>kosong</html>")

    media = resolve_douyin("https://www.douyin.com/note/7111222233334444555", transport=httpx.MockTransport(handler))
    assert [m.kind for m in media] == ["photo", "photo"]
