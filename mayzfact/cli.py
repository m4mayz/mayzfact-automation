"""Entry point: `uv run mayzfact run <video> [--from STEP]`, `check-script`, `brief`, `upload`, dll."""

from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime

from mayzfact import tunnel as tunnel_mod
from mayzfact.config import (
    CACHE_DIR,
    PROJECT_ROOT,
    RUNS_DIR,
    Settings,
    load_settings,
    missing_env,
)
from mayzfact.errors import AwaitingInput, PipelineError
from mayzfact.faktacuil import VOICE_SAMPLE_TEXT_ID
from mayzfact.ffmpeg import audio_duration
from mayzfact.net import make_client
from mayzfact.pipeline import ALL_STEPS, run_pipeline
from mayzfact.providers.elevenlabs import ElevenLabsTTS, list_voices
from mayzfact.store import write_bytes_atomic
from mayzfact.text import words

VOICE_SAMPLE_DIR = CACHE_DIR / "voice-samples"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="mayzfact", description="Pipeline shorts: naskah ulang + TTS + klip manual")
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run", help="Bikin video dari 1 YouTube Shorts source")
    run.add_argument("video", help="Video ID atau URL YouTube")
    run.add_argument("--from", dest="from_step", choices=ALL_STEPS, help="Ulang dari step ini (source/tts dikunci kalau voice.mp3 udah ada)")
    run.add_argument("--no-render", action="store_true", help="Berhenti setelah timeline.json, buat review di Remotion Studio")
    check = sub.add_parser("check-script", help="Cek runs/<id>/script.json yang ditulis agent")
    check.add_argument("video", help="Video ID atau URL YouTube source")
    sub.add_parser("voices", help="List voice ElevenLabs di akun lu")
    sample = sub.add_parser("voice-sample", help="Bikin sampel suara FaktaCuil buat milih voice (pakai kredit ElevenLabs)")
    sample.add_argument("voice_id")
    sample.add_argument("--name", required=True, help="Nama file sampel, huruf kecil/angka/strip")
    login = sub.add_parser("login", help="Login YouTube buat upload (token disimpan di .env)")
    login.add_argument("platform", choices=["youtube"])
    login.add_argument("--channel", choices=["faktacuil"], help="Login channel FaktaCuil (token kedua)")
    next_slot = sub.add_parser("next-slot", help="Slot jadwal YouTube kosong berikutnya (01.00/04.00 WIB)")
    next_slot.add_argument("--channel", choices=["faktacuil"], help="Pakai jam slot FaktaCuil (12.00/18.00 WIB)")
    upload = sub.add_parser("upload", help="Upload final.mp4 ke YouTube sebagai video terjadwal")
    upload.add_argument("video", help="Video ID atau URL YouTube source")
    when = upload.add_mutually_exclusive_group(required=True)
    when.add_argument("--at", help='Jam tayang WIB, format "YYYY-MM-DD HH:MM"')
    when.add_argument("--now", action="store_true", help="Langsung public sekarang, tanpa jadwal")
    brief = sub.add_parser("brief", help="Buka halaman brief buat ngisi link klip (mode manual)")
    brief.add_argument("video", help="Video ID atau URL YouTube")
    brief.add_argument("--port", type=int, default=None, help="Port lokal (default BRIEF_PORT)")
    brief.add_argument("--lan", action="store_true", help=argparse.SUPPRESS)
    brief.add_argument("--no-ngrok", action="store_true", help="Jangan buka tunnel ngrok (cuma lokal/LAN)")
    tunnel = sub.add_parser("tunnel", help="Buka tunnel ngrok ber-password ke port lokal, misal 3000 buat Studio")
    tunnel.add_argument("port", type=int)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        settings = load_settings()
        if args.command == "voices":
            return _print_voices(settings)
        if args.command == "voice-sample":
            return _voice_sample(args, settings)
        if args.command == "check-script":
            return _check_script(args, settings)
        if args.command == "login":
            return _login(args, settings)
        if args.command == "brief":
            return _brief(args, settings)
        if args.command == "tunnel":
            return _tunnel(args, settings)
        if args.command == "next-slot":
            return _next_slot(args, settings)
        if args.command == "upload":
            return _upload(args, settings)
        paths = run_pipeline(
            args.video, settings=settings, from_step=args.from_step, no_render=args.no_render
        )
        if args.no_render:
            print(
                f"Timeline siap: {paths.timeline_json}\nReview: cd remotion && npx remotion studio src/index.ts "
                f"--public-dir=../runs/{paths.root.name} --props=../runs/{paths.root.name}/timeline.json"
            )
        else:
            print(f"Selesai: {paths.final_mp4}")
        return 0
    except AwaitingInput as exc:
        print(f"Nunggu input: {exc.message}")
        return 3
    except PipelineError as exc:
        print(f"Error {exc}", file=sys.stderr)
        return 1


def _check_script(args: argparse.Namespace, settings: Settings) -> int:
    from mayzfact.audio import BGM_DIR, list_bgm
    from mayzfact.steps.script import (
        check_script_file,
        load_script,
        narration_word_range,
    )
    from mayzfact.steps.source import parse_video_id
    from mayzfact.store import RunPaths, read_json
    from mayzfact.text import words

    paths = RunPaths(RUNS_DIR / parse_video_id(args.video))
    if not paths.source_json.exists():
        raise PipelineError("check-script", f"{paths.source_json} belum ada. Jalanin dulu: mayzfact run {paths.root.name}")
    source = read_json(paths.source_json)
    problems = check_script_file(paths, source, bgm_choices=list_bgm(BGM_DIR), video_speed=settings.video_speed)
    if problems:
        print("\n".join(f"- {p}" for p in problems))
        return 1
    script = read_json(paths.script_json)
    count = len(words(" ".join(b["text"] for b in script["beats"])))
    target, _, _ = narration_word_range(load_script(paths), settings.video_speed)
    print(f"OK: naskah lolos cek ({count} kata, target {target})")
    return 0


def _print_voices(settings: Settings) -> int:
    missing = missing_env(settings, ["ELEVENLABS_API_KEYS"])
    if missing:
        raise PipelineError("voices", "Isi dulu di .env: " + ", ".join(missing))
    for voice in list_voices(settings.elevenlabs_api_keys, make_client()):
        labels = ", ".join(f"{key}={value}" for key, value in voice["labels"].items())
        print(f"{voice['voice_id']}  {voice['name']}  {labels}")
    return 0


def _voice_sample(args: argparse.Namespace, settings: Settings) -> int:
    if not re.fullmatch(r"[a-z0-9-]{1,40}", args.name):
        raise PipelineError("voice-sample", "--name cuma boleh huruf kecil, angka, dan strip (maks 40 karakter)")
    target = VOICE_SAMPLE_DIR / f"{args.name}.mp3"
    if target.exists():
        raise PipelineError("voice-sample", f"{target} udah ada, sampel nggak di-generate ulang")
    missing = missing_env(settings, ["ELEVENLABS_API_KEYS"])
    if missing:
        raise PipelineError("voice-sample", "Isi dulu di .env: " + ", ".join(missing))
    tts = ElevenLabsTTS(settings.elevenlabs_api_keys, args.voice_id, "eleven_v3", make_client(), stability=0.5, delivery_tag="")
    audio, _ = tts.synthesize(VOICE_SAMPLE_TEXT_ID)
    write_bytes_atomic(target, audio)
    duration = audio_duration(target)
    print(f"Sampel: {target}")
    print(f"Teks: {len(VOICE_SAMPLE_TEXT_ID)} karakter, durasi {duration:.2f} detik")
    print(f"kata/detik mentah: {len(words(VOICE_SAMPLE_TEXT_ID)) / duration:.2f}")
    return 0


def _login(args: argparse.Namespace, settings: Settings) -> int:
    from mayzfact import youtube

    if args.channel == "faktacuil":
        token = youtube.login(settings.youtube_client_secret_json, PROJECT_ROOT / ".env",
                              token_env="YOUTUBE_TOKEN_JSON_FAKTACUIL")
        channel_id, title = youtube.channel_info(youtube.service(token))
        print("YouTube: login berhasil, token FaktaCuil disimpan di .env (YOUTUBE_TOKEN_JSON_FAKTACUIL)")
        print(f"Channel: {title} ({channel_id})")
        print("Cek ini channel FaktaCuil, terus isi Settings.faktacuil_youtube_channel_id.")
        return 0
    youtube.login(settings.youtube_client_secret_json, PROJECT_ROOT / ".env")
    print("YouTube: login berhasil, token disimpan di .env")
    return 0


def _lan_ip() -> str:
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def _next_slot(args: argparse.Namespace, settings: Settings) -> int:
    from mayzfact import youtube

    if args.channel == "faktacuil":
        slot = youtube.next_slot(youtube.taken_slots(RUNS_DIR, "faktacuil"), datetime.now(youtube.WIB),
                                 settings.faktacuil_slot_hours)
    else:
        slot = youtube.next_slot(youtube.taken_slots(RUNS_DIR), datetime.now(youtube.WIB))
    print(slot.strftime("%Y-%m-%d %H:%M"))
    return 0


def _upload(args: argparse.Namespace, settings: Settings) -> int:
    from mayzfact import youtube
    from mayzfact.steps.source import parse_video_id
    from mayzfact.store import RunPaths

    paths = RunPaths(RUNS_DIR / parse_video_id(args.video))
    meta = youtube.load_meta(paths)
    publish_at = None if args.now else youtube.parse_publish_at(args.at, datetime.now(youtube.WIB))
    mode = youtube.run_mode(paths)
    if mode == "faktacuil":
        def make_service():
            if not settings.youtube_token_json_faktacuil.strip():
                raise PipelineError("youtube", f"Belum login channel FaktaCuil. {youtube.FAKTACUIL_LOGIN_HINT}")
            return youtube.service(settings.youtube_token_json_faktacuil)

        data = youtube.upload_video(paths, meta, publish_at, make_service, print, channel="faktacuil",
                                    expected_channel_id=settings.faktacuil_youtube_channel_id)
    elif mode == "top3":
        data = youtube.upload_video(paths, meta, publish_at, lambda: youtube.service(settings.youtube_token_json), print)
    else:
        raise PipelineError("upload", f"narration_mode {mode!r} nggak dikenal, channel tujuan nggak bisa dipastiin.")
    when = "langsung public" if args.now else f"tayang {args.at} WIB"
    print(f"Ke-upload, {when}\n  Video : {data['url']}\n  Studio: {data['studio_url']}")
    return 0


def _brief(args: argparse.Namespace, settings: Settings) -> int:
    import httpx

    from mayzfact.audio import SFX_DIR
    from mayzfact.brief.prefetch import Prefetcher
    from mayzfact.brief.server import link_urls, make_server, missing_frames
    from mayzfact.config import CACHE_DIR
    from mayzfact.manual.links import load_links
    from mayzfact.manual.obtain import Obtainer
    from mayzfact.manual.og import DESKTOP_UA
    from mayzfact.steps.source import parse_video_id
    from mayzfact.store import RunPaths, read_json

    paths = RunPaths(RUNS_DIR / parse_video_id(args.video))
    if not paths.shots_plan_json.exists():
        raise PipelineError("brief", f"Plan belum ada. Jalanin dulu: mayzfact run {paths.root.name} --no-render")
    plan = read_json(paths.shots_plan_json)
    missing = missing_frames(paths, plan)
    if missing:
        raise PipelineError("brief", f"Shot {', '.join(str(i + 1) for i in missing)} belum punya frame referensi. "
                            f"Jalanin: mayzfact run {paths.root.name} --from plan --no-render")
    # Link yang disimpan langsung di-download di background (cache sama kayak fetch), biar fetch tinggal motong.
    client = httpx.Client(headers={"User-Agent": DESKTOP_UA}, timeout=httpx.Timeout(120.0, connect=15.0), follow_redirects=True)
    prefetcher = Prefetcher(paths, Obtainer(CACHE_DIR / "manual", client, log=print).obtain, log=print)
    server = make_server(paths, args.port or settings.brief_port, host="0.0.0.0", prefetcher=prefetcher,
                         sfx_dir=SFX_DIR, media_dir=CACHE_DIR / "manual")  # port bentrok = berhenti di sini
    prefetcher.start()
    prefetcher.enqueue(link_urls(load_links(paths.links_json), plan), retry_failed=True)  # CTA otomatis nggak butuh download
    port = server.server_address[1]
    lan_ip = _lan_ip()
    link = None
    if not args.no_ngrok:
        try:
            link = tunnel_mod.start_tunnel(port, settings.ngrok_basic_auth)
        except PipelineError as exc:  # brief tetap jalan lokal/LAN, tapi kasih tau kenapa ngrok nggak kebuka
            print(f"  ngrok gagal: {exc.message}")
    print(f"Brief {paths.root.name} (akses LAN/HP aktif):")
    if link:
        print(f"  Internet : {link.url} (login pakai NGROK_BASIC_AUTH)")
    print(f"  HP / LAN : http://{lan_ip}:{port}")
    print(f"  Lokal PC : http://127.0.0.1:{port}")
    print("  (Ctrl+C buat stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        if link:
            link.stop()
        prefetcher.stop()
        client.close()
    return 0


def _tunnel(args: argparse.Namespace, settings: Settings) -> int:
    link = tunnel_mod.start_tunnel(args.port, settings.ngrok_basic_auth)
    print(f"Port {args.port} kebuka di: {link.url} (login pakai NGROK_BASIC_AUTH)")
    print("  (Ctrl+C buat stop)")
    try:
        link.proc.wait()
    except KeyboardInterrupt:
        pass
    finally:
        link.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
