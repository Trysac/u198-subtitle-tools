"""CLI entry point for subtitle-tools."""

from __future__ import annotations

import argparse
import sys
from fractions import Fraction
from pathlib import Path
from typing import Literal

from subtitle_tools import SubtitleError, check, parse, render, retime, shift


def _detect_format(path: Path) -> Literal["srt", "vtt"]:
    suffix = path.suffix.lower()
    if suffix == ".srt":
        return "srt"
    if suffix in (".vtt", ".webvtt"):
        return "vtt"
    raise SubtitleError("invalid_option", f"Cannot deduce subtitle format from {path.name}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="subtitle-tools",
        description="Parse, convert, shift, retime, and check subtitles (SRT/VTT).",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # convert IN OUT
    conv = subparsers.add_parser("convert", help="Convert between SRT and VTT")
    conv.add_argument("input", type=Path, help="Input subtitle file")
    conv.add_argument("output", type=Path, help="Output subtitle file")

    # shift FILE --ms N -o OUT
    sh = subparsers.add_parser("shift", help="Shift subtitle timing")
    sh.add_argument("input", type=Path, help="Input subtitle file")
    sh.add_argument("--ms", type=int, required=True, help="Offset in milliseconds")
    sh.add_argument("-o", "--output", type=Path, required=True, help="Output subtitle file")

    # retime FILE --factor FACTOR -o OUT
    rt = subparsers.add_parser("retime", help="Retime subtitle timestamps")
    rt.add_argument("input", type=Path, help="Input subtitle file")
    rt.add_argument(
        "--factor", type=str, required=True, help="Rational factor (e.g. 25/24 or 1.001)"
    )
    rt.add_argument("-o", "--output", type=Path, required=True, help="Output subtitle file")

    # check FILE
    chk = subparsers.add_parser("check", help="Check subtitles for quality issues")
    chk.add_argument("input", type=Path, help="Input subtitle file")
    chk.add_argument("--max-line-chars", type=int, default=42, help="Max line characters")
    chk.add_argument("--max-lines", type=int, default=2, help="Max lines per cue")
    chk.add_argument("--max-cps", type=float, default=20.0, help="Max characters per second")

    args = parser.parse_args(argv)

    try:
        if args.command == "convert":
            in_fmt = _detect_format(args.input)
            out_fmt = _detect_format(args.output)
            content = args.input.read_text(encoding="utf-8")
            cues = parse(content, in_fmt)
            rendered = render(cues, out_fmt)
            args.output.write_text(rendered, encoding="utf-8")
            return 0

        if args.command == "shift":
            fmt = _detect_format(args.input)
            out_fmt = _detect_format(args.output)
            content = args.input.read_text(encoding="utf-8")
            cues = parse(content, fmt)
            shifted = shift(cues, args.ms)
            rendered = render(shifted, out_fmt)
            args.output.write_text(rendered, encoding="utf-8")
            return 0

        if args.command == "retime":
            fmt = _detect_format(args.input)
            out_fmt = _detect_format(args.output)
            factor_val = Fraction(args.factor)
            content = args.input.read_text(encoding="utf-8")
            cues = parse(content, fmt)
            retimed = retime(cues, factor_val)
            rendered = render(retimed, out_fmt)
            args.output.write_text(rendered, encoding="utf-8")
            return 0

        if args.command == "check":
            fmt = _detect_format(args.input)
            content = args.input.read_text(encoding="utf-8")
            cues = parse(content, fmt)
            issues = check(
                cues,
                max_line_chars=args.max_line_chars,
                max_lines=args.max_lines,
                max_cps=args.max_cps,
            )
            if issues:
                for issue in issues:
                    sys.stderr.write(f"Cue {issue.cue}: {issue.code}\n")
                return 1
            return 0

    except SubtitleError as err:
        sys.stderr.write(f"Error [{err.code}]: {err}\n")
        return 2
    except Exception as err:
        sys.stderr.write(f"Unexpected error: {err}\n")
        return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
