"""Urutan step, aturan kunci naskah + suara (spec 3.4), dan runner utama pipeline."""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import httpx

from mayzfact.cache import SearchCache
from mayzfact.config import CACHE_DIR, RUNS_DIR, Settings, missing_env
from mayzfact.errors import PipelineError
from mayzfact.net import make_client
from mayzfact.providers.elevenlabs import ElevenLabsTTS
from mayzfact.providers.gemini import GeminiScriptWriter
from mayzfact.providers.pexels import Pexels
from mayzfact.providers.pixabay import Pixabay
from mayzfact.providers.stock import CombinedSearch, PlatformMediaSearch, StockSearch
from mayzfact.scoring import ThumbScorer
from mayzfact.steps.clips import MediaSearch, Scorer, run_clips
from mayzfact.steps.render import run_render
from mayzfact.steps.script import ScriptWriter, run_script
from mayzfact.steps.source import parse_video_id, run_source, youtube_transcript
from mayzfact.steps.timeline import run_timeline
from mayzfact.steps.tts import TTSProvider, run_tts
from mayzfact.store import RunPaths, read_json, write_json_atomic
from mayzfact.text import script_text, text_hash
from mayzfact.thumbs import fetch_thumbnail

STEPS = ["source", "script", "tts", "hook", "clips", "timeline", "render"]
VOICE_LOCKED = ("source", "script", "tts")
AFTER_VOICE = ("hook", "clips", "timeline", "render")
MIN_AUDIO_SECONDS = 30.0
STEP_ENV = {
    "script": ["GEMINI_API_KEYS"],
    "tts": ["ELEVENLABS_API_KEYS", "ELEVENLABS_VOICE_ID"],
    "clips": ["PEXELS_API_KEY", "PIXABAY_API_KEY"],
}
CLIP_MAX_SEARCHES = 40  # ±16 beat x 2 query; hasil per query di-cache, jadi video & foto cuma 1 search
NEW_VOICE_HINT = "Pakai --new-voice kalau emang mau naskah + suara baru (pakai kredit ElevenLabs)."


def step_outputs(step: str, paths: RunPaths) -> list[Path]:
    return {
        "source": [paths.source_json],
        "script": [paths.script_json],
        "tts": [paths.voice_mp3, paths.tts_json],
        "hook": [paths.hook_json],
        "clips": [paths.clips_json],
        "timeline": [paths.timeline_json],
        "render": [paths.final_mp4],
    }[step]


def step_done(step: str, paths: RunPaths) -> bool:
    return all(path.exists() for path in step_outputs(step, paths))


def plan_steps(done: dict[str, bool], voice_exists: bool, from_step: str | None, new_voice: bool) -> list[str]:
    if new_voice and from_step:
        raise PipelineError("cli", "--new-voice nggak bisa digabung sama --from.")
    if new_voice:
        return STEPS[1:] if done["source"] else list(STEPS)
    if voice_exists:
        broken = [step for step in VOICE_LOCKED if not done[step]]
        if broken:
            raise PipelineError("cli", f"voice.mp3 ada tapi hasil step {', '.join(broken)} hilang. {NEW_VOICE_HINT}")
    if from_step:
        if voice_exists and from_step in VOICE_LOCKED:
            raise PipelineError(
                "cli", f"voice.mp3 udah ada, jadi naskah + suara dikunci. Pakai --from clips. {NEW_VOICE_HINT}"
            )
        index = STEPS.index(from_step)
        missing = [step for step in STEPS[:index] if not done[step]]
        if missing:
            raise PipelineError("cli", f"Step {', '.join(missing)} belum pernah selesai. Jalanin tanpa --from dulu.")
        return STEPS[index:]
    for index, step in enumerate(STEPS):
        if not done[step]:
            return STEPS[index:]
    return []


def check_voice(paths: RunPaths) -> dict:
    """Dicek tiap run sebelum clips: naskah masih sama dengan suara, dan suaranya cukup panjang."""
    tts = read_json(paths.tts_json)
    script = read_json(paths.script_json)
    if text_hash(script_text(script["beats"])) != tts["text_sha256"]:
        raise PipelineError(
            "tts", f"script.json beda sama naskah yang dipakai buat voice.mp3. Balikin script.json. {NEW_VOICE_HINT}"
        )
    if tts["duration_s"] < MIN_AUDIO_SECONDS:
        raise PipelineError(
            "tts", f"Audio cuma {tts['duration_s']:.1f} detik (minimal {MIN_AUDIO_SECONDS:.0f}). {NEW_VOICE_HINT}"
        )
    return tts


@dataclass
class Deps:
    fetch_transcript: Callable[[str], list[dict]]
    script_writer: Callable[[], ScriptWriter]
    tts: Callable[[], TTSProvider]
    search: Callable[[], MediaSearch]
    http: Callable[[], httpx.Client]
    render: Callable[[RunPaths], Path]
    media_cache: Path = CACHE_DIR / "media"
    hook: Callable[[RunPaths, Callable[[str], None]], dict] | None = None
    scorer: Callable[[], Scorer | None] = lambda: None
    clip_search: Callable[[], MediaSearch] | None = None  # None = pakai `search`
    close: Callable[[], None] = lambda: None


def real_deps(settings: Settings) -> Deps:
    shared: dict[str, httpx.Client] = {}

    def http() -> httpx.Client:
        if "client" not in shared:
            shared["client"] = make_client()
        return shared["client"]

    def search() -> StockSearch:
        cache = SearchCache(CACHE_DIR / "search")
        return StockSearch(Pexels(settings.pexels_api_key, http(), cache), Pixabay(settings.pixabay_api_key, http(), cache))

    encoders: dict[str, object] = {}

    def encoder():
        if "siglip" not in encoders:
            from mayzfact.embed import SiglipEncoder

            encoders["siglip"] = SiglipEncoder()
        return encoders["siglip"]

    def fetch_thumb(candidate):
        return fetch_thumbnail(http(), CACHE_DIR / "thumbs", candidate)

    def hook(paths: RunPaths, log: Callable[[str], None]) -> dict:
        from mayzfact.steps.hook import real_hook_deps, run_hook

        hook_deps = real_hook_deps(settings, http(), search(), encoder(), fetch_thumb, log)
        try:
            return run_hook(
                paths, read_json(paths.source_json), hook_deps,
                hook_seconds=settings.hook_seconds, exact_threshold=settings.hook_exact_threshold,
                media_cache=CACHE_DIR / "media",
            )
        finally:
            hook_deps.close()

    closers: list[Callable[[], None]] = []

    def clip_search() -> MediaSearch:
        if not settings.clip_platforms:
            return search()
        from mayzfact.platforms import browser

        shared = browser.SharedPlaywright()
        platforms = [
            browser.BrowserPlatform(name, client=http(), headless=settings.browser_headless, playwright=shared, max_searches=CLIP_MAX_SEARCHES)
            for name in settings.clip_platforms
        ]

        def close_platforms() -> None:
            for platform in platforms:
                platform.close()
            shared.stop()

        closers.append(close_platforms)
        return CombinedSearch([search(), *(PlatformMediaSearch(p) for p in platforms)])

    def close() -> None:
        while closers:
            closers.pop()()

    return Deps(
        fetch_transcript=youtube_transcript,
        script_writer=lambda: GeminiScriptWriter(settings.gemini_api_keys, settings.gemini_model),
        tts=lambda: ElevenLabsTTS(
            settings.elevenlabs_api_keys, settings.elevenlabs_voice_id, settings.elevenlabs_model, http()
        ),
        search=search,
        http=http,
        render=run_render,
        hook=hook,
        scorer=lambda: ThumbScorer(encoder(), fetch_thumb),
        clip_search=clip_search,
        close=close,
    )


def run_pipeline(
    video: str,
    *,
    settings: Settings,
    from_step: str | None = None,
    new_voice: bool = False,
    deps: Deps | None = None,
    runs_dir: Path = RUNS_DIR,
    log: Callable[[str], None] = print,
) -> RunPaths:
    video_id = parse_video_id(video)
    paths = RunPaths(runs_dir / video_id)
    done = {step: step_done(step, paths) for step in STEPS}
    steps = plan_steps(done, paths.voice_mp3.exists(), from_step, new_voice)
    if not steps:
        log(f"Semua step {video_id} udah selesai: {paths.final_mp4}. Pakai --from hook/clips/timeline/render buat bikin ulang.")
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
            if step in AFTER_VOICE and not voice_checked:
                check_voice(paths)
                voice_checked = True
            log(f"[{step}] mulai")
            _run_step(step, paths, settings, deps, log)
    finally:
        deps.close()
    return paths


def _run_step(step: str, paths: RunPaths, settings: Settings, deps: Deps, log: Callable[[str], None]) -> None:
    if step == "source":
        run_source(paths.root.name, paths, fetch=deps.fetch_transcript)
    elif step == "script":
        run_script(
            paths, read_json(paths.source_json), deps.script_writer(),
            ratio=settings.target_duration_ratio, minimum_s=settings.min_duration_seconds, photo_ratio=settings.photo_ratio,
        )
    elif step == "tts":
        run_tts(paths, read_json(paths.script_json), deps.tts(), log=log)
    elif step == "hook":
        if deps.hook is None:
            write_json_atomic(paths.hook_json, {"hook_seconds": settings.hook_seconds, "skipped_platforms": [], "segments": []})
        else:
            deps.hook(paths, log)
    elif step == "clips":
        run_clips(
            paths, read_json(paths.script_json), read_json(paths.tts_json),
            (deps.clip_search or deps.search)(), deps.http(),
            max_shot_s=settings.max_shot_seconds, fg_min_ratio=settings.fg_min_height_ratio,
            media_cache=deps.media_cache, log=log,
            hook=read_json(paths.hook_json), scorer=deps.scorer(), hook_seconds=settings.hook_seconds,
        )
    elif step == "timeline":
        run_timeline(paths, read_json(paths.clips_json), read_json(paths.tts_json), fg_min_ratio=settings.fg_min_height_ratio)
    elif step == "render":
        deps.render(paths)
