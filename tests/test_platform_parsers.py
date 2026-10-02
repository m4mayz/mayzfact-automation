from mayzfact.platforms.parsers import parse_douyin, parse_pinterest, parse_rednote, parse_tiktok, search_url


def tiktok_item(vid, **video):
    base = {"cover": f"https://p16.tiktokcdn.com/{vid}.jpeg", "duration": 12, "width": 576, "height": 1024,
            "playAddr": f"https://v16.tiktokcdn.com/{vid}.mp4"}
    return {"id": vid, "author": {"uniqueId": "crabguy"}, "video": {**base, **video}}


def test_parse_tiktok_item_list_and_general_format():
    payload = {"item_list": [tiktok_item("1"), {"id": "2", "video": {}}, tiktok_item("3", playAddr="")]}
    cands = parse_tiktok(payload, start_rank=4)
    assert [c.id for c in cands] == ["1", "3"]
    first = cands[0]
    assert (first.provider, first.kind, first.duration_s, first.author, first.rank) == ("tiktok", "video", 12.0, "crabguy", 4)
    assert first.page_url == "https://www.tiktok.com/@crabguy/video/1"
    assert first.thumbnail_url == "https://p16.tiktokcdn.com/1.jpeg"
    assert (first.renditions[0].width, first.renditions[0].height) == (576, 1024)
    assert cands[1].renditions == ()
    general = {"data": [{"type": 1, "item": tiktok_item("9")}, {"type": 4, "user_list": []}]}
    assert [c.id for c in parse_tiktok(general)] == ["9"]
    assert parse_tiktok({}) == []


def test_parse_douyin_video_and_image_post():
    video = {"aweme_info": {"aweme_id": "11", "duration": 8500, "author": {"nickname": "鲎哥"},
                            "video": {"cover": {"url_list": ["https://p3.douyinpic.com/11.jpeg"]}, "width": 1080, "height": 1920,
                                      "play_addr": {"url_list": ["https://v3.douyinvod.com/11.mp4"]}}}}
    images = {"aweme_info": {"aweme_id": "12", "author": {"nickname": "x"},
                             "video": {"cover": {"url_list": ["https://p3.douyinpic.com/12.jpeg"]}},
                             "images": [{"url_list": ["https://p3.douyinpic.com/12-1.jpeg"], "width": 1080, "height": 1440}]}}
    broken = {"aweme_info": {"aweme_id": "13", "video": {}}}
    cands = parse_douyin({"data": [video, images, broken, None]})
    assert [(c.id, c.kind) for c in cands] == [("11", "video"), ("12", "photo")]
    assert cands[0].duration_s == 8.5
    assert cands[0].page_url == "https://www.douyin.com/video/11"
    assert cands[1].renditions[0].url == "https://p3.douyinpic.com/12-1.jpeg"


def test_parse_rednote_notes():
    payload = {"data": {"items": [
        {"id": "a1", "model_type": "note", "xsec_token": "tok=",
         "note_card": {"type": "video", "user": {"nickname": "小红"},
                       "cover": {"url_default": "https://sns-webpic.xhscdn.com/a1.jpg", "width": 1080, "height": 1440}}},
        {"id": "b2", "model_type": "note", "xsec_token": "t2",
         "note_card": {"type": "normal", "user": {"nick_name": "绿"},
                       "cover": {"url_default": "https://sns-webpic.xhscdn.com/b2.jpg", "width": 1080, "height": 1350}}},
        {"id": "q", "model_type": "rec_query", "note_card": {}},
        {"id": "c3", "model_type": "note", "note_card": {"type": "video", "cover": {}}},
    ]}}
    cands = parse_rednote(payload)
    assert [(c.id, c.kind, c.author) for c in cands] == [("a1", "video", "小红"), ("b2", "photo", "绿")]
    assert cands[0].page_url == "https://www.xiaohongshu.com/explore/a1?xsec_token=tok%3D&xsec_source=pc_search"
    assert cands[0].renditions == ()
    assert cands[1].renditions[0].height == 1350


def test_parse_pinterest_video_and_photo():
    payload = {"resource_response": {"data": {"results": [
        {"id": "p1", "pinner": {"username": "ana"},
         "images": {"474x": {"url": "https://i.pinimg.com/474x/p1.jpg"}, "orig": {"url": "https://i.pinimg.com/originals/p1.jpg", "width": 800, "height": 1200}},
         "videos": {"video_list": {"V_HLSV4": {"url": "https://v.pinimg.com/p1.m3u8"},
                                   "V_720P": {"url": "https://v.pinimg.com/p1.mp4", "width": 720, "height": 1280, "duration": 6400}}}},
        {"id": "p2", "pinner": {"username": "budi"},
         "images": {"orig": {"url": "https://i.pinimg.com/originals/p2.jpg", "width": 1000, "height": 1000}}},
        {"id": "p3", "images": {}},
    ]}}}
    cands = parse_pinterest(payload)
    assert [(c.id, c.kind) for c in cands] == [("p1", "video"), ("p2", "photo")]
    assert cands[0].duration_s == 6.4
    assert cands[0].renditions[0].url == "https://v.pinimg.com/p1.mp4"
    assert cands[0].thumbnail_url == "https://i.pinimg.com/474x/p1.jpg"
    assert cands[1].thumbnail_url == "https://i.pinimg.com/originals/p2.jpg"
    assert cands[1].page_url == "https://www.pinterest.com/pin/p2/"


def test_search_url_quotes_query():
    assert search_url("tiktok", "horseshoe crab") == "https://www.tiktok.com/search/video?q=horseshoe%20crab"
    assert search_url("douyin", "鲎 视频") == "https://www.douyin.com/search/%E9%B2%8E%20%E8%A7%86%E9%A2%91?type=video"


def test_parsers_skip_items_with_wrong_field_types():
    tiktok = {"item_list": [
        {"id": "a", "author": "bukan dict", "video": {"cover": "https://c/a.jpg", "duration": "n/a"}},
        tiktok_item("b"),
    ]}
    cands = parse_tiktok(tiktok)
    assert [c.id for c in cands] == ["a", "b"]
    assert cands[0].author == "" and cands[0].duration_s is None
    rednote = {"data": {"items": [
        {"id": "n1", "model_type": "note", "xsec_token": None,
         "note_card": {"type": "video", "user": "x", "cover": {"url_default": "https://c/n1.jpg"}}},
    ]}}
    assert parse_rednote(rednote)[0].page_url == "https://www.xiaohongshu.com/explore/n1?xsec_token=&xsec_source=pc_search"
    assert parse_douyin({"data": [{"aweme_info": {"aweme_id": "1", "video": "rusak"}}]}) == []
    assert parse_pinterest({"resource_response": {"data": {"results": [{"id": "p", "images": "rusak"}]}}}) == []
