"""HTTP helper: retry buat 429/5xx/network error, dan download file."""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Callable, TypeVar

import httpx

from mayzfact.errors import PipelineError

RETRYABLE_STATUS = {429, 500, 502, 503, 504}
RETRIES = 3
T = TypeVar("T")


def retry_call(
    fn: Callable[[], T],
    *,
    is_retryable: Callable[[Exception], bool],
    step: str,
    what: str,
    retries: int = RETRIES,
    backoff_s: float = 1.0,
    sleep: Callable[[float], None] = time.sleep,
) -> T:
    """Jalanin fn. Error yang retryable diulang max `retries` kali (jeda 1s, 2s, 4s)."""
    for attempt in range(retries + 1):
        try:
            return fn()
        except Exception as exc:
            if attempt == retries or not is_retryable(exc):
                if isinstance(exc, PipelineError):
                    raise
                raise PipelineError(step, f"{what} gagal: {exc}") from exc
            sleep(backoff_s * 2**attempt)
    raise AssertionError("unreachable")


class HttpStatusError(PipelineError):
    """HTTP 4xx yang nggak di-retry. `status` dipakai caller, misal buat ganti API key."""

    def __init__(self, step: str, message: str, status: int) -> None:
        super().__init__(step, message)
        self.status = status


class RetryableHttpError(Exception):
    def __init__(self, status: int, body: str) -> None:
        super().__init__(f"HTTP {status}: {body[:300]}")
        self.status = status


def _http_retryable(exc: Exception) -> bool:
    return isinstance(exc, (RetryableHttpError, httpx.TransportError))


def _connect_retryable(exc: Exception) -> bool:
    """Buat request berbayar: retry cuma kalau request jelas belum diproses server."""
    return isinstance(exc, (RetryableHttpError, httpx.ConnectError, httpx.ConnectTimeout))


def request_json(
    client: httpx.Client,
    method: str,
    url: str,
    *,
    step: str,
    idempotent: bool = True,
    sleep: Callable[[float], None] = time.sleep,
    **kwargs,
) -> dict:
    """Request yang ngarepin JSON. Error 4xx selain 429 langsung stop tanpa retry.

    idempotent=False (request berbayar): read timeout/putus nggak di-retry, karena server mungkin udah nagih.
    """

    def call() -> dict:
        response = client.request(method, url, **kwargs)
        if response.status_code in RETRYABLE_STATUS:
            raise RetryableHttpError(response.status_code, response.text)
        if response.status_code >= 400:
            raise HttpStatusError(
                step, f"{method} {url} -> HTTP {response.status_code}: {response.text[:300]}", response.status_code
            )
        return response.json()

    is_retryable = _http_retryable if idempotent else _connect_retryable
    return retry_call(call, is_retryable=is_retryable, step=step, what=f"{method} {url}", sleep=sleep)


def download(
    client: httpx.Client,
    url: str,
    dest: Path,
    *,
    step: str,
    sleep: Callable[[float], None] = time.sleep,
) -> Path:
    """Download ke dest. Kalau dest udah ada, dianggap cache dan nggak di-download ulang."""
    if dest.exists():
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_name(dest.name + ".part")

    def call() -> Path:
        with client.stream("GET", url, follow_redirects=True) as response:
            if response.status_code in RETRYABLE_STATUS:
                raise RetryableHttpError(response.status_code, "")
            if response.status_code >= 400:
                raise PipelineError(step, f"Download {url} -> HTTP {response.status_code}")
            with part.open("wb") as fh:
                for chunk in response.iter_bytes():
                    fh.write(chunk)
        os.replace(part, dest)
        return dest

    return retry_call(call, is_retryable=_http_retryable, step=step, what=f"Download {url}", sleep=sleep)


def make_client(timeout_s: float = 60.0) -> httpx.Client:
    return httpx.Client(
        timeout=httpx.Timeout(timeout_s, connect=15.0),
        headers={"User-Agent": "mayzfact-automation/0.1"},
    )
