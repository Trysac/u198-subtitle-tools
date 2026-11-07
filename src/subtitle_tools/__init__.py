"""Parse, convert and retime SRT and WebVTT subtitles."""

from __future__ import annotations

import logging
import re
from collections.abc import Sequence
from dataclasses import dataclass
from fractions import Fraction
from typing import Literal

__all__ = [
    "Cue",
    "Issue",
    "SubtitleError",
    "__version__",
    "check",
    "parse",
    "render",
    "retime",
    "shift",
]

__version__ = "0.1.0"

logging.getLogger(__name__).addHandler(logging.NullHandler())

ErrorCode = Literal[
    "input_too_large",
    "too_many_cues",
    "invalid_timestamp",
    "missing_header",
    "invalid_option",
]
IssueCode = Literal[
    "overlap",
    "non_positive_duration",
    "line_too_long",
    "too_many_lines",
    "reading_speed",
]
FormatType = Literal["srt", "vtt"]


class SubtitleError(ValueError):
    """Base exception for all subtitle_tools errors."""

    def __init__(self, code: ErrorCode, message: str) -> None:
        truncated = message[:200]
        super().__init__(truncated)
        self.code: ErrorCode = code
        self.message: str = truncated


@dataclass(frozen=True)
class Cue:
    """Represents a single subtitle cue with timing in milliseconds."""

    start_ms: int
    end_ms: int
    text: str
    identifier: str | None = None
    settings: str | None = None


@dataclass(frozen=True)
class Issue:
    """Represents a quality or readability issue found in cues."""

    code: IssueCode
    cue: int  # 1-based index


# Private helper functions for timing and conversion

# SRT timestamp regex: lenient on '.' separator, 1-2+ digit hours, min 00-59, sec 00-59, ms 3 digits
_SRT_TIMING_RE = re.compile(
    r"^(\d+):([0-5]\d):([0-5]\d)[,.]([0-9]{3})\s+-->\s+(\d+):([0-5]\d):([0-5]\d)[,.]([0-9]{3})(?:\s+.*)?$"
)

# VTT timestamp regex: optional hours (2+ digits), min 00-59, sec 00-59, ms 3 digits
_VTT_TIMING_RE = re.compile(
    r"^(?:(\d{2,}):)?([0-5]\d):([0-5]\d)\.([0-9]{3})\s+-->\s+(?:(\d{2,}):)?([0-5]\d):([0-5]\d)\.([0-9]{3})(?:\s+(.*))?$"
)

_HTML_ENTITIES = {
    "&amp;": "&",
    "&lt;": "<",
    "&gt;": ">",
    "&nbsp;": "\u00a0",
    "&lrm;": "\u200e",
    "&rlm;": "\u200f",
}


def _parse_srt_timestamp(h: str, m: str, s: str, ms: str) -> int:
    return int(h) * 3600_000 + int(m) * 60_000 + int(s) * 1000 + int(ms)


def _format_srt_timestamp(ms: int) -> str:
    if ms < 0:
        ms = 0
    total_seconds, milliseconds = divmod(ms, 1000)
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"


def _format_vtt_timestamp(ms: int) -> str:
    if ms < 0:
        ms = 0
    total_seconds, milliseconds = divmod(ms, 1000)
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{milliseconds:03d}"


def _convert_vtt_text_to_srt(text: str) -> str:
    # 1. Remove voice / class annotations and tags except <b>, <i>, <u> (and closing)
    # Example: <v Bob> -> "", </v> -> "", <c.red> -> ""
    # Also timestamp tags: <00:19.000>
    def tag_replacer(match: re.Match[str]) -> str:
        content = match.group(1).strip()
        lower = content.lower()
        if lower in ("b", "i", "u", "/b", "/i", "/u"):
            return f"<{lower}>"
        # All other tags (e.g. voice <v Bob>, class <c.yellow>,
        # timestamps <00:01.000>, </v>, etc.) are dropped
        return ""

    cleaned = re.sub(r"<([^>]+)>", tag_replacer, text)

    # 2. Decode entities: &amp;, &lt;, &gt;, &nbsp;, &lrm;, &rlm; and numeric character references
    def entity_replacer(match: re.Match[str]) -> str:
        ent = match.group(0)
        if ent in _HTML_ENTITIES:
            return _HTML_ENTITIES[ent]
        if ent.startswith("&#x") or ent.startswith("&#X"):
            try:
                return chr(int(ent[3:-1], 16))
            except (ValueError, OverflowError):
                return ent
        if ent.startswith("&#"):
            try:
                return chr(int(ent[2:-1], 10))
            except (ValueError, OverflowError):
                return ent
        return ent

    return re.sub(r"&(?:[a-zA-Z]+|#[0-9]+|#[xX][0-9a-fA-F]+);", entity_replacer, cleaned)


def _convert_srt_text_to_vtt(text: str) -> str:
    # 1. Drop font tags keeping their inner text: <font ...> and </font>
    cleaned = re.sub(r"</?font(?:\s+[^>]*)?>", "", text, flags=re.IGNORECASE)

    # 2. Escape '&' and '<' outside <b>, <i>, <u>, </b>, </i>, </u> tags
    # Also replace '-->' with '--&gt;'
    tokens = re.split(r"(</?[biuBIU]\s*>)", cleaned)
    result: list[str] = []
    for part in tokens:
        if re.fullmatch(r"</?[biuBIU]\s*>", part):
            result.append(part.lower())
        else:
            # Escape '&' not part of already escaped sequences or raw text
            escaped = part.replace("&", "&amp;").replace("<", "&lt;")
            escaped = escaped.replace("-->", "--&gt;")
            result.append(escaped)

    return "".join(result)


def _strip_tags_for_cps(text: str) -> str:
    # Exclude tags and newlines for reading speed check
    no_tags = re.sub(r"<[^>]+>", "", text)
    no_newlines = no_tags.replace("\n", "").replace("\r", "")
    return no_newlines


def parse(
    text: str,
    fmt: FormatType,
    *,
    max_chars: int = 10_000_000,
    max_cues: int = 100_000,
) -> list[Cue]:
    """Parse subtitle text into a list of Cue objects."""
    if fmt not in ("srt", "vtt"):
        raise SubtitleError("invalid_option", f"Unsupported format: {fmt}")

    if len(text) > max_chars:
        raise SubtitleError(
            "input_too_large",
            f"Input size {len(text)} exceeds limit of {max_chars} characters",
        )

    # Strip BOM and normalize line breaks
    cleaned = text.lstrip("\ufeff").replace("\r\n", "\n").replace("\r", "\n")

    if fmt == "srt":
        return _parse_srt(cleaned, max_cues)
    return _parse_vtt(cleaned, max_cues)


def _parse_srt(text: str, max_cues: int) -> list[Cue]:
    lines = text.split("\n")
    cues: list[Cue] = []
    i = 0
    n = len(lines)

    while i < n:
        # Skip leading empty lines
        while i < n and not lines[i].strip():
            i += 1
        if i >= n:
            break

        cue_line_num = i + 1
        line = lines[i].strip()

        # Check if current line is index or timing line
        identifier: str | None = None
        timing_match = _SRT_TIMING_RE.match(line)

        if not timing_match:
            # Could be an index
            if line.isdigit():
                identifier = line
                i += 1
                if i < n:
                    timing_line = lines[i].strip()
                    timing_match = _SRT_TIMING_RE.match(timing_line)
                    if not timing_match:
                        # Check if it looks like a broken arrow or malformed timing
                        raise SubtitleError(
                            "invalid_timestamp",
                            f"Invalid timing format at line {i + 1}: {timing_line}",
                        )
                else:
                    raise SubtitleError(
                        "invalid_timestamp",
                        f"Unexpected end of file at line {cue_line_num}",
                    )
            else:
                # If not digit and not timing, it's an invalid line
                raise SubtitleError(
                    "invalid_timestamp",
                    f"Invalid timing format at line {cue_line_num}: {line}",
                )

        if not timing_match:
            raise SubtitleError(
                "invalid_timestamp",
                f"Missing timing at line {cue_line_num}: {lines[i]}",
            )

        h1, m1, s1, ms1, h2, m2, s2, ms2 = timing_match.groups()[:8]
        start_ms = _parse_srt_timestamp(h1, m1, s1, ms1)
        end_ms = _parse_srt_timestamp(h2, m2, s2, ms2)

        i += 1
        # Collect text lines until blank line
        cue_text_lines: list[str] = []
        while i < n and lines[i].strip() != "":
            cue_text_lines.append(lines[i])
            i += 1

        cue_text = "\n".join(cue_text_lines)
        cues.append(Cue(start_ms=start_ms, end_ms=end_ms, text=cue_text, identifier=identifier))
        if len(cues) > max_cues:
            raise SubtitleError("too_many_cues", f"Cue count exceeded maximum of {max_cues}")

    return cues


def _parse_vtt(text: str, max_cues: int) -> list[Cue]:
    lines = text.split("\n")
    if not lines or not (lines[0] == "WEBVTT" or lines[0].startswith(("WEBVTT ", "WEBVTT\t"))):
        raise SubtitleError("missing_header", "VTT text missing required WEBVTT header")

    cues: list[Cue] = []
    n = len(lines)
    i = 1

    while i < n:
        # Skip blank lines
        while i < n and not lines[i].strip():
            i += 1
        if i >= n:
            break

        line = lines[i].strip()

        # Skip NOTE, STYLE, REGION blocks
        if line == "NOTE" or line.startswith(("NOTE ", "NOTE\t")):
            i += 1
            while i < n and lines[i].strip() != "":
                i += 1
            continue
        if line == "STYLE" or line == "REGION":
            i += 1
            while i < n and lines[i].strip() != "":
                i += 1
            continue

        # Cue identifier or timing line
        cue_line_num = i + 1
        identifier: str | None = None
        timing_match = _VTT_TIMING_RE.match(line)

        if not timing_match:
            # Line is potentially an identifier
            identifier = lines[i]  # keep raw formatting if needed
            i += 1
            if i < n:
                line = lines[i].strip()
                timing_match = _VTT_TIMING_RE.match(line)
                if not timing_match:
                    raise SubtitleError(
                        "invalid_timestamp",
                        f"Invalid timing format at line {i + 1}: {line}",
                    )
            else:
                raise SubtitleError(
                    "invalid_timestamp",
                    f"Unexpected end of file at line {cue_line_num}",
                )

        if not timing_match:
            raise SubtitleError(
                "invalid_timestamp",
                f"Invalid timing format at line {cue_line_num}: {line}",
            )

        h1, m1, s1, ms1, h2, m2, s2, ms2, settings = timing_match.groups()
        start_hours = int(h1) if h1 is not None else 0
        start_ms = start_hours * 3600_000 + int(m1) * 60_000 + int(s1) * 1000 + int(ms1)

        end_hours = int(h2) if h2 is not None else 0
        end_ms = end_hours * 3600_000 + int(m2) * 60_000 + int(s2) * 1000 + int(ms2)

        i += 1
        # Cue text
        cue_text_lines: list[str] = []
        while i < n and lines[i].strip() != "":
            cue_text_lines.append(lines[i])
            i += 1

        cue_text = "\n".join(cue_text_lines)
        cues.append(
            Cue(
                start_ms=start_ms,
                end_ms=end_ms,
                text=cue_text,
                identifier=identifier,
                settings=settings if settings else None,
            )
        )
        if len(cues) > max_cues:
            raise SubtitleError("too_many_cues", f"Cue count exceeded maximum of {max_cues}")

    return cues


def render(cues: Sequence[Cue], fmt: FormatType) -> str:
    """Render a sequence of Cue objects into SRT or WebVTT format."""
    if fmt not in ("srt", "vtt"):
        raise SubtitleError("invalid_option", f"Unsupported format: {fmt}")

    if fmt == "srt":
        blocks: list[str] = []
        for idx, cue in enumerate(cues, start=1):
            timing = (
                f"{_format_srt_timestamp(cue.start_ms)} --> {_format_srt_timestamp(cue.end_ms)}"
            )
            converted_text = _convert_vtt_text_to_srt(cue.text)
            blocks.append(f"{idx}\n{timing}\n{converted_text}")
        if not blocks:
            return ""
        return "\n\n".join(blocks) + "\n"

    # WebVTT
    header = "WEBVTT"
    if not cues:
        return f"{header}\n\n"

    blocks = []
    for cue in cues:
        block_lines: list[str] = []
        if cue.identifier is not None:
            block_lines.append(cue.identifier)
        timing_line = (
            f"{_format_vtt_timestamp(cue.start_ms)} --> {_format_vtt_timestamp(cue.end_ms)}"
        )
        if cue.settings:
            timing_line += f" {cue.settings}"
        block_lines.append(timing_line)
        converted_text = _convert_srt_text_to_vtt(cue.text)
        block_lines.append(converted_text)
        blocks.append("\n".join(block_lines))

    return f"{header}\n\n" + "\n\n".join(blocks) + "\n"


def shift(cues: Sequence[Cue], offset_ms: int) -> list[Cue]:
    """Shift cue timings by an offset in milliseconds."""
    result: list[Cue] = []
    for cue in cues:
        new_end = cue.end_ms + offset_ms
        if new_end <= 0:
            continue
        new_start = max(0, cue.start_ms + offset_ms)
        result.append(
            Cue(
                start_ms=new_start,
                end_ms=new_end,
                text=cue.text,
                identifier=cue.identifier,
                settings=cue.settings,
            )
        )
    return result


def retime(cues: Sequence[Cue], factor: Fraction | int) -> list[Cue]:
    """Retime cues by a rational factor using round-half-up."""
    if factor <= 0:
        raise SubtitleError("invalid_option", "Retime factor must be positive")

    frac_factor = Fraction(factor)
    half = Fraction(1, 2)

    def scale_time(t: int) -> int:
        return int(Fraction(t) * frac_factor + half)

    result: list[Cue] = []
    for cue in cues:
        result.append(
            Cue(
                start_ms=scale_time(cue.start_ms),
                end_ms=scale_time(cue.end_ms),
                text=cue.text,
                identifier=cue.identifier,
                settings=cue.settings,
            )
        )
    return result


def check(
    cues: Sequence[Cue],
    *,
    max_line_chars: int = 42,
    max_lines: int = 2,
    max_cps: float = 20.0,
) -> list[Issue]:
    """Validate cues against timing and readability constraints."""
    issues: list[Issue] = []
    prev_end: int | None = None

    for idx, cue in enumerate(cues, start=1):
        # Duration check
        if cue.end_ms <= cue.start_ms:
            issues.append(Issue(code="non_positive_duration", cue=idx))

        # Overlap check
        if prev_end is not None and cue.start_ms < prev_end:
            issues.append(Issue(code="overlap", cue=idx))
        prev_end = cue.end_ms

        # Line checks
        lines = cue.text.split("\n")
        if len(lines) > max_lines:
            issues.append(Issue(code="too_many_lines", cue=idx))

        for line in lines:
            if len(line) > max_line_chars:
                issues.append(Issue(code="line_too_long", cue=idx))
                break

        # Reading speed check (characters per second)
        duration_ms = cue.end_ms - cue.start_ms
        if duration_ms > 0:
            vis_chars = _strip_tags_for_cps(cue.text)
            cps = len(vis_chars) / (duration_ms / 1000.0)
            if cps > max_cps:
                issues.append(Issue(code="reading_speed", cue=idx))

    return issues
