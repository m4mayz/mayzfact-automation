"""Urutan step, aturan kunci naskah + suara (spec 3.4), dan runner utama pipeline."""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import httpx

from mayzfact.config import CACHE_DIR, RUNS_DIR, Settings, missing_env
from mayzfact.errors import AwaitingInput, PipelineError
from mayzfact.net import make_client
from mayzfact.providers.elevenlabs import ElevenLabsTTS
from mayzfact.steps.render import run_render
from mayzfact.steps.script import AWAIT_SCRIPT_HINT, check_script_file, load_script
from mayzfact.steps.source import parse_video_id, run_source, youtube_transcript
from mayzfact.steps.timeline import run_timeline
from mayzfact.steps.tts import TTSProvider, run_tts
from mayzfact.store import RunPaths, read_json
from mayzfact.text import script_text, text_hash

STEPS = ["source", "tts", "plan", "fetch", "timeline", "render"]
ALL_STEPS = STEPS
VOICE_LOCKED = ("source", "tts")
AFTER_VOICE = ("plan", "fetch", "timeline", "render")
MIN_AUDIO_SECONDS = 30.0
STEP_ENV = {
    "tts": ["ELEVENLABS_API_KEYS"],
}
NEW_SCRIPT_HINT = "Hapus voice.mp3 + script.json kalau emang mau naskah + suara baru (pakai kredit ElevenLabs)."


def step_outputs(step: str, paths: RunPaths) -> list[Path]:
    return {
        "source": [paths.source_json],
        "tts": [paths.script_json, paths.voice_mp3, paths.tts_json],  # naskah dikunci bareng suaranya
        "plan": [paths.shots_plan_json],
        "fetch": [paths.clips_json],
        "timeline": [paths.timeline_json],
        "render": [paths.final_mp4],
    }[step]


def step_done(step: str, paths: RunPaths) -> bool:
    return all(path.exists() for path in step_outputs(step, paths))


def plan_steps(done: dict[str, bool], voice_exists: bool, from_step: str | None, steps: list[str] = STEPS) -> list[str]:
    if voice_exists:
        broken = [step for step in VOICE_LOCKED if not done[step]]
        if broken:
            raise PipelineError("cli", f"voice.mp3 ada tapi hasil step {', '.join(broken)} hilang. {NEW_SCRIPT_HINT}")
    if from_step:
        if from_step not in steps:
            raise PipelineError("cli", f"Step {from_step} nggak ada. Pilihan: {', '.join(steps)}.")
        if voice_exists and from_step in VOICE_LOCKED:
            raise PipelineError(
                "cli", f"voice.mp3 udah ada, jadi naskah + suara dikunci. Pakai --from {steps[2]}. {NEW_SCRIPT_HINT}"
            )
        index = steps.index(from_step)
        missing = [step for step in steps[:index] if not done[step]]
        if missing:
            raise PipelineError("cli", f"Step {', '.join(missing)} belum pernah selesai. Jalanin tanpa --from dulu.")
        return steps[index:]
    for index, step in enumerate(steps):
        if not done[step]:
            return steps[index:]
    return []


def check_voice(paths: RunPaths) -> dict:
    """Dicek tiap run sebelum plan: naskah masih sama dengan suara, dan suaranya cukup panjang."""
    tts = read_json(paths.tts_json)
    script = read_json(paths.script_json)
    if text_hash(script_text(script["beats"])) != tts["text_sha256"]:
        raise PipelineError(
            "tts", f"script.json beda sama naskah yang dipakai buat voice.mp3. Balikin script.json. {NEW_SCRIPT_HINT}"
        )
    if tts["duration_s"] < MIN_AUDIO_SECONDS:
        raise PipelineError(
            "tts", f"Audio cuma {tts['duration_s']:.1f} detik (minimal {MIN_AUDIO_SECONDS:.0f}). {NEW_SCRIPT_HINT}"
        )
    return tts


@dataclass
class Deps:
    fetch_transcript: Callable[[str], list[dict]]
    tts: Callable[[], TTSProvider]
    http: Callable[[], httpx.Client]
    render: Callable[[RunPaths], Path]
    plan: Callable[[RunPaths, Callable[[str], None]], dict]
    fetch: Callable[[RunPaths, Callable[[str], None]], dict]
    close: Callable[[], None] = lambda: None
    audio: Callable[[RunPaths, Callable[[str], None]], dict] | None = None  # None = video tanpa BGM/SFX
    overlay: Callable[..., dict] | None = None  # (paths, log, point_beats) → deteksi subjek; None = tanpa panah/lingkaran
    marks: Callable[[RunPaths, Callable[[str], None]], dict] | None = None  # tanda beat: point + emoji (Fase 3C-2)
    download_source: Callable[[str, Path], Path] | None = None  # download source.mp4 di step source; None = lewat


def real_deps(settings: Settings) -> Deps:
    shared: dict[str, httpx.Client] = {}

    def http() -> httpx.Client:
        if "client" not in shared:
            shared["client"] = make_client()
        return shared["client"]

    encoders: dict[str, object] = {}

    def encoder():
        if "siglip" not in encoders:
            from mayzfact.embed import SiglipEncoder

            encoders["siglip"] = SiglipEncoder()
        return encoders["siglip"]

    closers: list[Callable[[], None]] = []

    def plan(paths: RunPaths, log: Callable[[str], None]) -> dict:
        from mayzfact.steps.plan import run_plan
        from mayzfact.ytdlp import run_ytdlp, youtube_url

        return run_plan(
            paths, read_json(paths.script_json), read_json(paths.tts_json), read_json(paths.source_json),
            max_shot_s=settings.max_shot_seconds, hook_seconds=settings.hook_seconds,
            download_source=lambda video_id, dest: run_ytdlp(youtube_url(video_id), dest),
            log=log,
        )

    def fetch(paths: RunPaths, log: Callable[[str], None]) -> dict:
        from mayzfact.manual.obtain import Obtainer
        from mayzfact.manual.og import DESKTOP_UA
        from mayzfact.steps.fetch import run_fetch

        client = httpx.Client(headers={"User-Agent": DESKTOP_UA}, timeout=httpx.Timeout(120.0, connect=15.0), follow_redirects=True)
        closers.append(client.close)
        obtainer = Obtainer(CACHE_DIR / "manual", client, log=log)
        return run_fetch(
            paths, read_json(paths.shots_plan_json), obtain=obtainer.obtain, encoder=encoder(),
            fg_min_ratio=settings.fg_min_height_ratio, log=log,
        )

    def audio(paths: RunPaths, log: Callable[[str], None]) -> dict:
        from mayzfact.audio import BGM_DIR, SFX_DIR, prepare_audio

        # Client sendiri yang cepat nyerah: myinstants lambat jangan sampai nahan step timeline.
        client = httpx.Client(timeout=httpx.Timeout(10.0, connect=5.0), headers={"User-Agent": "mayzfact-automation/0.1"})
        closers.append(client.close)
        return prepare_audio(paths, read_json(paths.script_json), bgm_dir=BGM_DIR, sfx_dir=SFX_DIR, client=client, log=log)

    detectors: dict[str, object] = {}

    def overlay(paths: RunPaths, log: Callable[[str], None], point_beats: set[int] | None = None) -> dict:
        from mayzfact.detect import Owlv2Detector
        from mayzfact.overlay import prepare_overlays

        detector = detectors.setdefault("owl", Owlv2Detector())
        plan = read_json(paths.shots_plan_json) if paths.shots_plan_json.exists() else None
        return prepare_overlays(paths, read_json(paths.clips_json), read_json(paths.script_json), plan, detector,
                                fg_min_ratio=settings.fg_min_height_ratio, log=log, point_beats=point_beats)

    def marks(paths: RunPaths, log: Callable[[str], None]) -> dict:
        from mayzfact.emoji import EMOJI_DIR
        from mayzfact.marks import prepare_marks

        return prepare_marks(paths, read_json(paths.script_json), client=http(), emoji_dir=EMOJI_DIR, log=log)

    def close() -> None:
        while closers:
            closers.pop()()

    from mayzfact.ytdlp import run_ytdlp, youtube_url

    return Deps(
        fetch_transcript=youtube_transcript,
        download_source=lambda video_id, dest: run_ytdlp(youtube_url(video_id), dest),
        tts=lambda: ElevenLabsTTS(
            settings.elevenlabs_api_keys,
            settings.elevenlabs_voice_id,
            settings.elevenlabs_model,
            http(),
            stability=settings.elevenlabs_stability,
        ),
        http=http,
        render=run_render,
        plan=plan,
        fetch=fetch,
        audio=audio,
        overlay=overlay,
        marks=marks,
        close=close,
    )


def run_pipeline(
    video: str,
    *,
    settings: Settings,
    from_step: str | None = None,
    no_render: bool = False,
    deps: Deps | None = None,
    runs_dir: Path = RUNS_DIR,
    log: Callable[[str], None] = print,
) -> RunPaths:
    video_id = parse_video_id(video)
    paths = RunPaths(runs_dir / video_id)
    done = {step: step_done(step, paths) for step in STEPS}
    steps = plan_steps(done, paths.voice_mp3.exists(), from_step)
    if no_render:
        # Review lewat Remotion Studio dulu. final.mp4 lama jadi basi kalau step sebelumnya diulang.
        if any(step in steps for step in ("plan", "fetch", "timeline")):
            paths.final_mp4.unlink(missing_ok=True)
        steps = [step for step in steps if step != "render"]
    if not steps:
        log(f"Semua step {video_id} udah selesai: {paths.final_mp4}. Pakai --from plan/fetch/timeline/render buat bikin ulang.")
        return paths
    missing = missing_env(settings, [name for step in steps for name in STEP_ENV.get(step, [])])
    if missing:
        raise PipelineError("config", "Isi dulu di .env: " + ", ".join(missing))
    missing_tools = [tool for tool in ("ffmpeg", "ffprobe") if shutil.which(tool) is None]
    if missing_tools:
        raise PipelineError("config", f"{', '.join(missing_tools)} nggak ketemu di PATH. Install ffmpeg dulu.")
    # Output step yang mau diulang dihapus duluan, biar kalau gagal di tengah, run berikutnya nggak
    # nganggep step itu udah selesai pakai file lama. File yang dikunci (naskah + suara) nggak disentuh.
    for step in steps:
        if step in AFTER_VOICE:
            for path in step_outputs(step, paths):
                path.unlink(missing_ok=True)
    deps = deps or real_deps(settings)
    voice_checked = False
    try:
        for step in steps:
            if step == "tts":
                _require_script(paths, settings)  # naskah dari agent: harus ada + lolos cek sebelum bayar TTS
            if step in AFTER_VOICE and not voice_checked:
                check_voice(paths)
                voice_checked = True
            log(f"[{step}] mulai")
            _run_step(step, paths, settings, deps, log)
    finally:
        deps.close()
    return paths


def _require_script(paths: RunPaths, settings: Settings) -> None:
    if not paths.script_json.exists():
        raise AwaitingInput("script", AWAIT_SCRIPT_HINT)
    from mayzfact.audio import BGM_DIR, list_bgm

    load_script(paths)
    problems = check_script_file(paths, read_json(paths.source_json), ratio=settings.target_duration_ratio,
                                 minimum_s=settings.min_duration_seconds, bgm_choices=list_bgm(BGM_DIR))
    if problems:
        raise PipelineError("script", "Naskah belum lolos cek: " + " ".join(problems))


def _run_step(step: str, paths: RunPaths, settings: Settings, deps: Deps, log: Callable[[str], None]) -> None:
    if step == "source":
        run_source(paths.root.name, paths, fetch=deps.fetch_transcript, download_source=deps.download_source,
                   hook_seconds=settings.hook_seconds, log=log)
    elif step == "tts":
        run_tts(paths, read_json(paths.script_json), deps.tts(), log=log)
    elif step == "plan":
        deps.plan(paths, log)
    elif step == "fetch":
        deps.fetch(paths, log)
    elif step == "timeline":
        audio = None
        if deps.audio:
            try:
                audio = deps.audio(paths, log)
            except Exception as exc:  # BGM/SFX cuma hiasan: timeline tetap jadi tanpa audio
                log(f"[timeline] BGM/SFX dilewat: {type(exc).__name__}: {exc}")
        marks = None
        if deps.marks:
            try:
                marks = deps.marks(paths, log)
            except Exception as exc:  # emoji/panah cuma hiasan
                log(f"[timeline] tanda beat (emoji/panah) dilewat: {type(exc).__name__}: {exc}")
        point_beats = {i for i, mark in enumerate(marks["beats"]) if mark.get("point")} if marks else None
        overlays = None
        if deps.overlay:
            try:
                overlays = deps.overlay(paths, log, point_beats)
            except Exception as exc:  # panah/lingkaran cuma hiasan
                log(f"[timeline] panah/lingkaran dilewat: {type(exc).__name__}: {exc}")
        run_timeline(paths, read_json(paths.clips_json), read_json(paths.tts_json), fg_min_ratio=settings.fg_min_height_ratio,
                     script=read_json(paths.script_json), audio=audio, overlays=overlays, marks=marks, log=log)
    elif step == "render":
        deps.render(paths)
