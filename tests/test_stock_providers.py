import httpx

from mayzfact.cache import SearchCache
from mayzfact.providers import pexels as pexels_mod
from mayzfact.providers import pixabay as pixabay_mod
from mayzfact.providers.pexels import Pexels
from mayzfact.providers.pixabay import Pixabay
from mayzfact.providers.stock import StockSearch, merge_candidates
from tests.factories import cand

PEXELS_VIDEO = {
    "id": 101, "width": 2160, "height": 3840, "url": "https://www.pexels.com/video/crab-101/", "duration": 12,
    "user": {"id": 5, "name": "Ana", "url": "https://www.pexels.com/@ana"},
    "video_files": [
        {"id": 1, "quality": "hd", "file_type": "video/mp4", "width": 1080, "height": 1920, "fps": 30, "link": "https://videos.pexels.com/101-hd.mp4"},
        {"id": 2, "quality": "uhd", "file_type": "video/mp4", "width": 2160, "height": 3840, "fps": 30, "link": "https://videos.pexels.com/101-uhd.mp4"},
        {"id": 3, "quality": None, "file_type": "application/x-mpegURL", "width": None, "height": None, "fps": None, "link": "https://videos.pexels.com/101.m3u8"},
    ],
}
PEXELS_PHOTO = {
    "id": 202, "width": 3000, "height": 4500, "url": "https://www.pexels.com/photo/fossil-202/",
    "photographer": "Budi", "src": {"original": "https://images.pexels.com/photos/202/pexels-photo-202.jpeg"},
}
PIXABAY_VIDEO = {
    "id": 303, "pageURL": "https://pixabay.com/videos/id-303/", "duration": 15, "user": "citra",
    "videos": {
        "large": {"url": "", "width": 0, "height": 0, "size": 0},
        "medium": {"url": "https://cdn.pixabay.com/303-medium.mp4", "width": 1920, "height": 1080, "size": 100},
        "small": {"url": "https://cdn.pixabay.com/303-small.mp4", "width": 1280, "height": 720, "size": 50},
    },
}
PIXABAY_PHOTO = {"id": 404, "pageURL": "https://pixabay.com/photos/id-404/", "user": "dewi", "largeImageURL": "https://pixabay.com/get/404_1280.jpg", "imageWidth": 6000, "imageHeight": 4000}


def recording_client(body):
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(200, json=body)

    return httpx.Client(transport=httpx.MockTransport(handler)), requests


def cache_text(root):
    return "".join(p.read_text(encoding="utf-8") for p in root.rglob("*.json"))


def test_pexels_parse_video_skips_non_mp4_files():
    c = pexels_mod.parse_video(PEXELS_VIDEO, 3)
    assert (c.provider, c.id, c.kind, c.duration_s, c.author, c.rank) == ("pexels", "101", "video", 12.0, "Ana", 3)
    assert [(r.width, r.height) for r in c.renditions] == [(1080, 1920), (2160, 3840)]
    assert pexels_mod.parse_video({**PEXELS_VIDEO, "video_files": [PEXELS_VIDEO["video_files"][2]]}, 0) is None


def test_pexels_parse_photo_needs_original_src():
    c = pexels_mod.parse_photo(PEXELS_PHOTO, 0)
    assert (c.kind, c.author, c.renditions[0].width, c.renditions[0].height) == ("photo", "Budi", 3000, 4500)
    assert pexels_mod.parse_photo({**PEXELS_PHOTO, "src": {}}, 0) is None


def test_pexels_search_sends_key_and_uses_cache(tmp_path):
    client, requests = recording_client({"videos": [PEXELS_VIDEO]})
    pexels = Pexels("pexels-key", client, SearchCache(tmp_path))
    first = pexels.videos("horseshoe crab", "portrait")
    second = pexels.videos("horseshoe crab", "portrait")
    assert [c.id for c in first] == [c.id for c in second] == ["101"]
    assert len(requests) == 1
    request = requests[0]
    assert request.url.path == "/v1/videos/search"
    assert request.headers["Authorization"] == "pexels-key"
    assert dict(request.url.params) == {"query": "horseshoe crab", "per_page": "30", "orientation": "portrait"}
    assert "pexels-key" not in cache_text(tmp_path)


def test_pixabay_parse_video_skips_empty_renditions():
    c = pixabay_mod.parse_video(PIXABAY_VIDEO, 0)
    assert [(r.width, r.height) for r in c.renditions] == [(1920, 1080), (1280, 720)]
    assert pixabay_mod.parse_video({**PIXABAY_VIDEO, "videos": {"large": {"url": "", "width": 0, "height": 0}}}, 0) is None


def test_pixabay_parse_photo_uses_large_image_size():
    c = pixabay_mod.parse_photo(PIXABAY_PHOTO, 0)
    assert (c.renditions[0].width, c.renditions[0].height) == (1280, 853)
    assert pixabay_mod.parse_photo({**PIXABAY_PHOTO, "largeImageURL": ""}, 0) is None


def test_pixabay_search_truncates_query_and_hides_key_from_cache(tmp_path):
    client, requests = recording_client({"hits": [PIXABAY_PHOTO]})
    pixabay = Pixabay("pixabay-key", client, SearchCache(tmp_path))
    long_query = "horseshoe crab " * 10
    photos = pixabay.photos(long_query)
    assert [c.id for c in photos] == ["404"]
    params = requests[0].url.params
    assert requests[0].url.path == "/api/"
    assert params["key"] == "pixabay-key"
    assert params["q"] == long_query[:100]
    assert params["image_type"] == "photo"
    assert "pixabay-key" not in cache_text(tmp_path)


def test_pixabay_videos_use_film_type(tmp_path):
    client, requests = recording_client({"hits": [PIXABAY_VIDEO]})
    Pixabay("k", client, SearchCache(tmp_path)).videos("crab")
    assert requests[0].url.path == "/api/videos/"
    assert requests[0].url.params["video_type"] == "film"


def test_merge_candidates_keeps_first_occurrence():
    a = cand("pexels", "1", rank=0)
    a_again = cand("pexels", "1", rank=7)
    b = cand("pixabay", "1", rank=0)
    assert merge_candidates([[a], [a_again, b]]) == [a, b]


def test_stock_search_order_for_videos_and_photos():
    calls = []

    class FakePexels:
        def videos(self, query, orientation=None):
            calls.append(("pexels-videos", query, orientation))
            return [cand("pexels", "p" if orientation else "any")]

        def photos(self, query, orientation=None):
            calls.append(("pexels-photos", query, orientation))
            return [cand("pexels", "pp" if orientation else "pany", kind="photo")]

    class FakePixabay:
        def videos(self, query):
            calls.append(("pixabay-videos", query, None))
            return [cand("pixabay", "x")]

        def photos(self, query):
            calls.append(("pixabay-photos", query, None))
            return [cand("pixabay", "xp", kind="photo")]

    search = StockSearch(FakePexels(), FakePixabay())
    assert [c.id for c in search.candidates("video", "crab")] == ["p", "any", "x"]
    assert [c.id for c in search.candidates("photo", "crab")] == ["pp", "pany", "xp"]
    assert calls == [
        ("pexels-videos", "crab", "portrait"), ("pexels-videos", "crab", None), ("pixabay-videos", "crab", None),
        ("pexels-photos", "crab", "portrait"), ("pexels-photos", "crab", None), ("pixabay-photos", "crab", None),
    ]
