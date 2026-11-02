"""Render integrasi opsional; dijalankan eksplisit, bukan bagian suite offline."""
import shutil
import subprocess
from pathlib import Path

import pytest

from tests.cta_scene_fixture import make_fixture
from tests.verify_cta_fixture import verify_fixture


@pytest.mark.render
def test_render_cta_scene_fixture(tmp_path):
    root = tmp_path/'cta-scene'
    info = make_fixture(root)
    remotion = Path(__file__).resolve().parents[1]/'remotion'
    npx = shutil.which('npx')
    assert npx, 'Aktifkan Node 22'
    first, last = info['frames']
    result = subprocess.run([npx, 'remotion', 'render', 'src/index.ts', 'ShortVideo', str(root/'cta.mp4'),
        f'--props={root / "timeline.json"}', f'--public-dir={root}', '--codec=h264',
        f'--frames={first}-{last}', '--concurrency=2', '--log=error'], cwd=remotion,
        capture_output=True, text=True, encoding='utf-8', errors='replace')
    assert result.returncode == 0, result.stdout + result.stderr
    verified = verify_fixture(root)
    assert verified['inspected_frames'] == 9
