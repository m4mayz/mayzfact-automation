import httpx

from mayzfact.manual.og import og_media
from mayzfact.manual.types import Media


def test_og_media():
    html = ('<meta property="og:video" content="https://v.example/a.mp4">'
            '<meta property="og:image" content="//img.example/a.jpg">')
    transport = httpx.MockTransport(lambda r: httpx.Response(200, text=html))
    assert og_media("https://example.com/p", transport=transport) == [
        Media("video", "https://v.example/a.mp4"), Media("photo", "https://img.example/a.jpg")]
    empty = httpx.MockTransport(lambda r: httpx.Response(200, text="<html></html>"))
    assert og_media("https://example.com/p", transport=empty) == []


def test_og_ignores_login_pages():
    def handler(request):
        if request.url.path == "/login":
            return httpx.Response(200, text='<meta property="og:image" content="https://site/logo.png">')
        return httpx.Response(302, headers={"location": "https://site/login?next=/p"})

    assert og_media("https://site/p", transport=httpx.MockTransport(handler)) == []
