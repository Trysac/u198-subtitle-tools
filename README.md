# subtitle-tools

Parse, convert and retime SRT and WebVTT subtitles: exact millisecond timing, tag and entity handling, shift and frame-rate retiming, and readability checks.

## Problem
Subtitle files frequently suffer from format drift, incorrect frame rates (e.g., 25 fps source for 23.976 fps display), and incompatible tag/entity formatting when manually edited or processed by low-quality converters. This library provides a unified cue model to parse, retime, and audit subtitles without relying on third-party dependencies.

## Installation

```bash
pip install subtitle-tools
```

## Usage Example

```python
from fractions import Fraction
from subtitle_tools import parse, render, retime

content = "1\n00:00:01,000 --> 00:00:02,000\nHello World\n"
cues = parse(content, "srt")
retimed = retime(cues, Fraction(25, 24))
vtt_output = render(retimed, "vtt")
print(vtt_output)
```

## API Summary

- **Data**: `Cue` (frozen dataclass), `Issue` (auditing result).
- **Functions**: `parse(text, fmt)`, `render(cues, fmt)`, `shift(cues, ms)`, `retime(cues, factor)`, `check(cues)`. 
- **Limits**: `parse` enforces `max_chars` (default 10M) and `max_cues` (default 100k) to prevent memory exhaustion.
- **Errors**: `SubtitleError` (codes: `input_too_large`, `too_many_cues`, `invalid_timestamp`, `missing_header`, `invalid_option`).

## Why not <best-known alternative>
Unlike `pysrt` or `webvtt-py`, `subtitle-tools` enforces a single, unified data model (`Cue`) for both SRT and WebVTT. It performs exact format conversion by handling tags and HTML entities bidirectionally, and uses `fractions.Fraction` for frame-rate retiming to prevent cumulative drift.

For more details, see [docs/SECURITY.md](docs/SECURITY.md).
