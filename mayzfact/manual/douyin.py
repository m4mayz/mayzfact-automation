"""Resolver link Douyin → URL media. Port dari scrapr (MIT): ttwid + data SSR + WAF proof-of-work + API iteminfo."""

from __future__ import annotations

import json
import re
from typing import Any
from urllib.parse import unquote

import httpx

from mayzfact.errors import PipelineError
from mayzfact.manual.types import Media
from mayzfact.manual.waf import solve_waf

MOBILE_UA = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1"
)
_IDS = (
    re.compile(r"(?:video|note|share/(?:video|slides))[/?](\d{15,22})", re.IGNORECASE),
    re.compile(r"(?:modal_id|group_id|aweme_id)=(\d{15,22})", re.IGNORECASE),
)
_MARKERS = ("window._ROUTER_DATA =", "window._SSR_DATA =", "window._RENDER_DATA =", "window.__INIT_PROPS__ =")
_RENDER_DATA = re.compile(r'<script[^>]*id="RENDER_DATA"[^>]*>(.*?)</script>', re.S)


def item_id(text: str) -> str | None:
    for pattern in _IDS:
        match = pattern.search(text or "")
        if match:
            return match.group(1)
    return None


def router_data(html: str) -> dict | None:
    decoder = json.JSONDecoder()
    for marker in _MARKERS:
        start = html.find(marker)
        if start == -1:
            continue
        rest = html[start + len(marker):].lstrip()
        if rest.startswith("%7B"):
            rest = unquote(rest)
        try:
            data, _ = decoder.raw_decode(rest)
            return data
        except ValueError:
            continue
    for block in _RENDER_DATA.findall(html):
        try:
            return json.loads(unquote(block.strip()))
        except ValueError:
            continue
    return None


def find_item(data: Any) -> dict | None:
    if not isinstance(data, dict):
        return None
    for value in (data.get("loaderData") or {}).values():
        items = ((value or {}).get("videoInfoRes") or {}).get("item_list") or []
        if items:
            return items[0]
    detail = (data.get("aweme") or {}).get("detail")
    if detail:
        return detail
    if data.get("item_list"):
        return data["item_list"][0]
    return data.get("aweme_detail")


def _https(url: str) -> str:
    return re.sub(r"^http:", "https:", url)


def item_media(item: dict) -> list[Media]:
    images = item.get("images") or []
    if images:
        out = []
        for image in images:
            urls = (image or {}).get("url_list") or (image or {}).get("download_url_list") or []
            if urls:
                out.append(Media("photo", _https(urls[0])))
        return out
    video = item.get("video") or {}
    urls = ((video.get("play_addr") or {}).get("url_list") or []) + ((video.get("download_addr") or {}).get("url_list") or [])
    if not urls:
        return []
    url = _https(urls[0]).replace("playwm", "play")
    match = re.search(r"video_id=([^&]+)", url)
    out = [Media("video", f"https://aweme.snssdk.com/aweme/v1/play/?video_id={match.group(1)}")] if match else []
    return out + [Media("video", url)]


def resolve_douyin(url: str, *, transport: httpx.BaseTransport | None = None) -> list[Media]:
    headers = {"User-Agent": MOBILE_UA, "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8", "Referer": "https://www.douyin.com/"}
    with httpx.Client(headers=headers, timeout=15.0, transport=transport) as client:
        try:
            register = client.post(
                "https://ttwid.bytedance.com/ttwid/union/register/",
                json={"region": "cn", "aid": 1768, "needFparam": "0", "service": "www.ixigua.com",
                      "migrate_info": {"ticket": "", "src": "ucp"}, "cbUrlProtocol": "https", "union": True},
            )
            ttwid = register.cookies.get("ttwid")
            if ttwid:  # cookie-nya punya bytedance.com, dipasang ulang biar kekirim ke douyin juga
                client.cookies.set("ttwid", ttwid)
        except httpx.HTTPError:
            pass
        target = url
        if "v.douyin.com" in url:
            response = client.get(url)
            target = response.headers.get("location") or url
        iid = item_id(target)
        target = re.sub(r"share/slides/", "share/video/", target)
        response = client.get(target, follow_redirects=True)
        html = response.text
        if "_wafchallengeid" in html:
            token = solve_waf(html)
            if token:
                client.cookies.set("_wafchallengeid", token)
                html = client.get(target, follow_redirects=True).text
        item = find_item(router_data(html))
        iid = iid or item_id(str(response.url)) or item_id(html)
        if not item and iid:
            api = client.get(f"https://www.iesdouyin.com/web/api/v2/aweme/iteminfo/?item_ids={iid}")
            try:
                item = find_item(api.json())
            except ValueError:
                item = None
    if not item:
        raise PipelineError("fetch", "Data Douyin nggak ketemu di halaman. Coba link lain atau upload file-nya.")
    media = item_media(item)
    if not media:
        raise PipelineError("fetch", "Post Douyin ini nggak punya video/foto yang bisa diambil.")
    return media
