"""Step render: panggil Remotion CLI buat bikin final.mp4 dari timeline.json."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from mayzfact.config import PROJECT_ROOT
from mayzfact.errors import PipelineError
from mayzfact.store import RunPaths, tmp_path_for

REMOTION_DIR = PROJECT_ROOT / "remotion"
COMPOSITION_ID = "ShortVideo"


def render_command(npx: str, paths: RunPaths, output: Path) -> list[str]:
    return [
        npx, "remotion", "render", "src/index.ts", COMPOSITION_ID, str(output),
        f"--props={paths.timeline_json}", f"--public-dir={paths.root}", "--codec=h264",
    ]


def run_render(paths: RunPaths, remotion_dir: Path = REMOTION_DIR) -> Path:
    npx = shutil.which("npx")
    if npx is None:
        raise PipelineError("render", "npx nggak ketemu. Aktifin Node dulu: nvm use 22.23.1")
    if not (remotion_dir / "node_modules").exists():
        raise PipelineError("render", "Dependency Remotion belum ke-install. Jalanin: cd remotion && npm install")
    output = tmp_path_for(paths.final_mp4)
    result = subprocess.run(
        render_command(npx, paths, output),
        cwd=remotion_dir, capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if result.returncode != 0:
        raise PipelineError("render", "Remotion gagal:\n" + (result.stderr or result.stdout)[-2000:])
    os.replace(output, paths.final_mp4)
    return paths.final_mp4
