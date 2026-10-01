"""Entry point: `uv run mayzfact run <video> [--from STEP] [--new-voice]` dan `uv run mayzfact voices`."""

from __future__ import annotations

import argparse
import sys

from mayzfact.config import Settings, load_settings, missing_env
from mayzfact.errors import PipelineError
from mayzfact.net import make_client
from mayzfact.pipeline import STEPS, run_pipeline
from mayzfact.providers.elevenlabs import list_voices


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="mayzfact", description="Pipeline shorts: naskah ulang + TTS + klip stock")
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run", help="Bikin video dari 1 YouTube Shorts source")
    run.add_argument("video", help="Video ID atau URL YouTube")
    run.add_argument("--from", dest="from_step", choices=STEPS, help="Ulang dari step ini (script/tts dikunci kalau voice.mp3 udah ada)")
    run.add_argument("--new-voice", action="store_true", help="Bikin naskah + suara baru (pakai kredit ElevenLabs)")
    sub.add_parser("voices", help="List voice ElevenLabs di akun lu")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        settings = load_settings()
        if args.command == "voices":
            return _print_voices(settings)
        paths = run_pipeline(args.video, settings=settings, from_step=args.from_step, new_voice=args.new_voice)
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


if __name__ == "__main__":
    raise SystemExit(main())
