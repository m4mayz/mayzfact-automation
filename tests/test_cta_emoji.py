import httpx

from mayzfact.emoji import emoji_codepoint, prepare_cta_emoji

LOTTIE = {"v": "5.7.4", "fr": 30, "ip": 0, "op": 30, "w": 512, "h": 512, "layers": []}


def lottie_client(*available):
    hits = []

    def handler(request):
        hits.append(request.url.path)
        if any(request.url.path == f"/s/e/notoemoji/latest/{cp}/lottie.json" for cp in available):
            return httpx.Response(200, json=LOTTIE)
        return httpx.Response(404)

    return httpx.Client(transport=httpx.MockTransport(handler)), hits


def prepare(tmp_path, scene, client):
    return prepare_cta_emoji(tmp_path / "run", scene, client=client, emoji_dir=tmp_path / "cache",
                             log=lambda m: None, sleep=lambda s: None)


def test_emoji_codepoint():
    assert emoji_codepoint("📦") == "1f4e6"
    assert emoji_codepoint("❤️") == "2764_fe0f"
    assert emoji_codepoint("🇮🇩") == "1f1ee_1f1e9"


def test_prepare_cta_emoji_copies_lottie_into_run(tmp_path):
    client, hits = lottie_client("1f4e6")
    logs = []
    src = prepare_cta_emoji(tmp_path / "run", {"format": "emoji", "emoji": "📦"}, client=client,
                            emoji_dir=tmp_path / "cache", log=logs.append, sleep=lambda s: None)
    assert src == "emoji/1f4e6.json"
    assert (tmp_path / "run" / "emoji" / "1f4e6.json").is_file()
    assert hits == ["/s/e/notoemoji/latest/1f4e6/lottie.json"] and logs == []


def test_prepare_cta_emoji_retries_without_fe0f(tmp_path):
    client, hits = lottie_client("2764")
    src = prepare(tmp_path, {"format": "emoji", "emoji": "❤️"}, client)
    assert src == "emoji/2764.json"
    assert [h.split("/")[-2] for h in hits] == ["2764_fe0f", "2764"]
    assert (tmp_path / "run" / "emoji" / "2764.json").is_file()


def test_prepare_cta_emoji_missing_lottie_warns(tmp_path):
    client, _ = lottie_client()
    logs = []
    src = prepare_cta_emoji(tmp_path / "run", {"format": "emoji", "emoji": "🫠"}, client=client,
                            emoji_dir=tmp_path / "cache", log=logs.append, sleep=lambda s: None)
    assert src is None
    assert any("PERINGATAN" in line and "statis" in line and "U+1FAE0" in line for line in logs)
    assert all("🫠" not in line for line in logs)  # console Windows cp1252 aman


def test_prepare_cta_emoji_ignores_other_formats(tmp_path):
    client, hits = lottie_client("1f4e6")
    for scene in ({"format": "lucky", "theme": "honey"}, None):
        assert prepare(tmp_path, scene, client) is None
    assert hits == []
