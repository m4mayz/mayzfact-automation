"""Entry point: `uv run mayzfact run <video> [--from STEP] [--new-voice]` dan `uv run mayzfact voices`."""

from __future__ import annotations

import argparse
import sys

from mayzfact.config import Settings, load_settings, missing_env
from mayzfact.errors import PipelineError
from mayzfact.net import make_client
from mayzfact.pipeline import STEPS, run_pipeline
from mayzfact.platforms import browser
from mayzfact.platforms.base import PLATFORMS, is_logged_in, platform_info
from mayzfact.providers.elevenlabs import list_voices


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="mayzfact", description="Pipeline shorts: naskah ulang + TTS + klip stock")
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run", help="Bikin video dari 1 YouTube Shorts source")
    run.add_argument("video", help="Video ID atau URL YouTube")
    run.add_argument("--from", dest="from_step", choices=STEPS, help="Ulang dari step ini (script/tts dikunci kalau voice.mp3 udah ada)")
    run.add_argument("--new-voice", action="store_true", help="Bikin naskah + suara baru (pakai kredit ElevenLabs)")
    run.add_argument("--no-render", action="store_true", help="Berhenti setelah timeline.json, buat review di Remotion Studio")
    sub.add_parser("voices", help="List voice ElevenLabs di akun lu")
    login = sub.add_parser("login", help="Login ke platform buat hook (TikTok/Douyin/RedNote/Pinterest)")
    login.add_argument("platform", nargs="?", choices=sorted(PLATFORMS))
    login.add_argument("--check", action="store_true", help="Cek status login semua platform di HOOK_PLATFORMS")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        settings = load_settings()
        if args.command == "voices":
            return _print_voices(settings)
        if args.command == "login":
            return _login(args, settings)
        paths = run_pipeline(
            args.video, settings=settings, from_step=args.from_step, new_voice=args.new_voice, no_render=args.no_render
        )
        if args.no_render:
            print(
                f"Timeline siap: {paths.timeline_json}\nReview: cd remotion && npx remotion studio src/index.ts "
                f"--public-dir=../runs/{paths.root.name} --props=../runs/{paths.root.name}/timeline.json"
            )
        else:
            print(f"Selesai: {paths.final_mp4}")
        return 0
    except PipelineError as exc:
        print(f"Error {exc}", file=sys.stderr)
        return 1


def _print_voices(settings: Settings) -> int:
    missing = missing_env(settings, ["ELEVENLABS_API_KEYS"])
    if missing:
        raise PipelineError("voices", "Isi dulu di .env: " + ", ".join(missing))
    for voice in list_voices(settings.elevenlabs_api_keys, make_client()):
        labels = ", ".join(f"{key}={value}" for key, value in voice["labels"].items())
        print(f"{voice['voice_id']}  {voice['name']}  {labels}")
    return 0


def _login(args: argparse.Namespace, settings: Settings) -> int:
    if args.check:
        all_ok = True
        for name in settings.hook_platforms:
            ok = is_logged_in(platform_info(name), browser.read_profile_cookies(name))
            all_ok = all_ok and ok
            print(f"{name}: login" if ok else f"{name}: belum login (jalanin: mayzfact login {name})")
        return 0 if all_ok else 1
    if not args.platform:
        raise PipelineError("login", "Sebutin platform-nya, misal: mayzfact login tiktok. Atau pakai --check.")
    browser.open_login_browser(args.platform)
    ok = is_logged_in(platform_info(args.platform), browser.read_profile_cookies(args.platform))
    print(f"{args.platform}: login" if ok else f"{args.platform}: belum login, coba lagi")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
