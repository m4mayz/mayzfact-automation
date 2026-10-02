"""Thumbnail kandidat: di-download sekali ke cache, terus dipakai hook dan rerank."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from mayzfact.errors import PipelineError
from mayzfact.net import download
from mayzfact.providers.types import Candidate


def thumb_path(root: Path, candidate: Candidate) -> Path:
    return root / f"{candidate.provider}_{candidate.id}.jpg"


def fetch_thumbnail(client: Any, root: Path, candidate: Candidate) -> Path | None:
    if not candidate.thumbnail_url:
        return None
    try:
        return download(client, candidate.thumbnail_url, thumb_path(root, candidate), step="clips")
    except PipelineError:
        return None
