"""Generate English WAV files for the ESP32 SD card.

Synthesizes the ten static device phrases with MiMo (default, BMO voice
clone) or Gemini. Each phrase is given a BMO emotion via the shared
``app.audio.director_map`` so the assets do not sound flat.

Output: ``firmware/Lyla-Taskbot/sd_template/sounds/*.wav``

Usage:
    python -m scripts.generate_firmware_sounds [--provider mimo|gemini] [--voice Leda] [--force]

Each file is 24 kHz mono 16-bit PCM. The firmware's ``audio_playback``
reads the WAV header at runtime and reconfigures I2S to match, so 24 kHz
is fine alongside the 16 kHz mic capture path.

Skips files that already exist unless ``--force`` is given. Prints a
short summary at the end.
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

from app.audio._seam import ConfigurationError
from app.audio.director_map import resolve as resolve_director
from app.audio.tts_gemini import GeminiTtsProvider
from app.audio.tts_mimo import MimoTtsProvider
from app.config import settings


PHRASES: dict[str, str] = {
    "greet_hello.wav": "BMO is ready to play!",
    "ack_thinking.wav": "Hmm, let me think about that for a sec.",
    "ack_still_thinking.wav": "Still thinking, hang on.",
    "ack_slow_network.wav": "The network seems slow, one moment.",
    "ok_expense.wav": "Got it, I saved your expense.",
    "ok_task.wav": "Sweet, I've got your task saved!",
    "ok_reminder.wav": "Your reminder is set.",
    "ok_summary.wav": "Here is your summary for today.",
    "ok_generic.wav": "Okay, all done.",
    "err_generic.wav": "Oops, something went wrong, please try again.",
}

#: Maps each static asset filename to a director_map key so MiMo synthesis
#: gives every phrase an appropriate BMO emotion instead of one flat tone.
ASSET_DIRECTOR_KEY: dict[str, str] = {
    "greet_hello.wav": "greet_hello",
    "ack_thinking.wav": "thinking",
    "ack_still_thinking.wav": "thinking",
    "ack_slow_network.wav": "thinking",
    "ok_expense.wav": "ok_expense",
    "ok_task.wav": "ok_task",
    "ok_reminder.wav": "ok_reminder",
    "ok_summary.wav": "ok_summary",
    "ok_generic.wav": "ok_generic",
    "err_generic.wav": "err_generic",
}


def _resolve_output_dir() -> Path:
    project_root = Path(__file__).resolve().parents[1]
    return project_root / "firmware" / "Lyla-Taskbot" / "sd_template" / "sounds"


def _human_kb(num_bytes: int) -> str:
    return f"{num_bytes / 1024:.1f} KB"


def _check_environment(provider_name: str) -> None:
    if provider_name == "mimo":
        if not settings.mimo_api_key:
            print(
                "ERROR: MIMO_API_KEY is empty in .env. Set it before running this script.",
                file=sys.stderr,
            )
            sys.exit(2)
        return
    if not settings.google_api_key:
        print(
            "ERROR: GOOGLE_API_KEY is empty in .env. Set it before running this script.",
            file=sys.stderr,
        )
        sys.exit(2)


def _build_provider(
    provider_name: str, voice: str
) -> GeminiTtsProvider | MimoTtsProvider:
    try:
        if provider_name == "mimo":
            return MimoTtsProvider(
                api_key=settings.mimo_api_key,
                base_url=settings.mimo_base_url,
                model=settings.mimo_model,
                voice_sample_path=settings.mimo_voice_sample_path,
            )
        return GeminiTtsProvider(
            model=settings.audio_tts_provider_model,
            voice=voice,
            api_key=settings.google_api_key,
        )
    except ConfigurationError as exc:
        print(f"ERROR: provider init failed: {exc}", file=sys.stderr)
        sys.exit(2)


def _synthesize_one(
    provider: GeminiTtsProvider | MimoTtsProvider,
    text: str,
    out_path: Path,
    *,
    director: str | None = None,
    tag: str | None = None,
    retries: int = 2,
    delay_s: float = 2.0,
) -> int:
    last_err: Exception | None = None
    for attempt in range(retries + 1):
        try:
            if isinstance(provider, MimoTtsProvider):
                result = provider.synthesize(text, director=director, tag=tag)
            else:
                result = provider.synthesize(text)
            if not result.audio_bytes:
                raise RuntimeError("provider returned empty audio_bytes")
            out_path.write_bytes(result.audio_bytes)
            return len(result.audio_bytes)
        except Exception as exc:
            last_err = exc
            print(
                f"  attempt {attempt + 1} failed: {exc}; "
                f"retrying in {delay_s:.0f}s..."
                if attempt < retries
                else f"  attempt {attempt + 1} failed: {exc}",
                file=sys.stderr,
            )
            if attempt < retries:
                time.sleep(delay_s)
    raise RuntimeError(f"synthesis failed after {retries + 1} attempts: {last_err}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="generate_firmware_sounds",
        description="Generate Bahasa Indonesia WAV files for ESP32 SD card.",
    )
    parser.add_argument(
        "--provider",
        choices=("mimo", "gemini"),
        default="mimo",
        help="TTS provider to synthesize with (default: mimo).",
    )
    parser.add_argument(
        "--voice",
        default=settings.audio_tts_voice,
        help=f"Gemini voice name, only used with --provider gemini (default: {settings.audio_tts_voice}).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Regenerate even if the file already exists.",
    )
    parser.add_argument(
        "--only",
        nargs="+",
        default=None,
        metavar="FILE",
        help="Generate only the specified files (e.g. --only ok_task.wav greet_hello.wav).",
    )
    args = parser.parse_args(argv)

    _check_environment(args.provider)

    out_dir = _resolve_output_dir()
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"Output:   {out_dir}")
    print(f"Provider: {args.provider}")
    if args.provider == "mimo":
        print(f"Model:    {settings.mimo_model}")
    else:
        print(f"Model:    {settings.audio_tts_provider_model}")
        print(f"Voice:    {args.voice}")
    print()

    targets: dict[str, str]
    if args.only:
        invalid = [n for n in args.only if n not in PHRASES]
        if invalid:
            print(
                f"ERROR: unknown filename(s): {', '.join(invalid)}",
                file=sys.stderr,
            )
            return 2
        targets = {n: PHRASES[n] for n in args.only}
    else:
        targets = PHRASES

    provider = _build_provider(args.provider, args.voice)

    generated = 0
    skipped = 0
    failed: list[str] = []
    total_bytes = 0

    for filename, text in targets.items():
        out_path = out_dir / filename
        if out_path.exists() and not args.force:
            size = out_path.stat().st_size
            print(f"  SKIP   {filename:<30} (exists, {_human_kb(size)})")
            skipped += 1
            total_bytes += size
            continue

        print(f"  GEN    {filename:<30} '{text}'")
        try:
            director, tag = resolve_director(ASSET_DIRECTOR_KEY.get(filename))
            size = _synthesize_one(
                provider, text, out_path, director=director, tag=tag
            )
            print(f"         -> {_human_kb(size)}")
            generated += 1
            total_bytes += size
        except Exception as exc:
            print(f"  FAIL   {filename}: {exc}", file=sys.stderr)
            failed.append(filename)

    print()
    print("Summary:")
    print(f"  generated: {generated}")
    print(f"  skipped:   {skipped}")
    print(f"  failed:    {len(failed)}")
    print(f"  total:     {_human_kb(total_bytes)}")

    if failed:
        print()
        print("Failed files (re-run with --force to retry):", file=sys.stderr)
        for f in failed:
            print(f"  - {f}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
