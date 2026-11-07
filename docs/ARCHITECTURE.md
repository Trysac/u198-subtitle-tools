# Architecture

`trysac-subtitle-tools` provides a unified engine for parsing, converting, retiming, and auditing subtitle files in SubRip (`.srt`) and WebVTT (`.vtt`) formats.

## Core Components

1. **Data Model (`Cue`, `Issue`)**:
   - `Cue`: Immutable (frozen) dataclass representing individual subtitle blocks with integer millisecond timestamps (`start_ms`, `end_ms`), raw text, optional cue identifier, and optional WebVTT cue settings.
   - `Issue`: Represents auditing findings such as `overlap`, `non_positive_duration`, `line_too_long`, `too_many_lines`, and `reading_speed`.

2. **Parsers (`parse`)**:
   - Handles UTF-8 BOM removal and line ending normalization (`\r\n`, `\r` -> `\n`).
   - Enforces configurable limits (`max_chars`, `max_cues`) to prevent denial-of-service.
   - SRT parser accepts lenient timestamp variations (dot or comma separators, 1-2+ digit hours).
   - WebVTT parser validates header lines (`WEBVTT`), skips comment blocks (`NOTE`), styling blocks (`STYLE`), and region definitions (`REGION`), and preserves cue settings.

3. **Renderer & Tag Conversion (`render`)**:
   - Bidirectional tag conversions preserve standard tags `<b>`, `<i>`, and `<u>`.
   - Escapes XML/HTML sensitive characters and arrows (`-->`) when converting SRT to WebVTT.
   - Strips non-standard formatting (e.g., `<font>` tags) and decodes standard entities and numeric character references when converting WebVTT to SRT.

4. **Timing Transformations (`shift`, `retime`)**:
   - `shift`: Offsets cue times in milliseconds. Automatically prunes cues whose end becomes `<= 0`.
   - `retime`: Uses exact rational arithmetic (`Fraction`) with round-half-up rounding `int(Fraction(t) * factor + Fraction(1, 2))`.

5. **Auditor (`check`)**:
   - Computes characters per second (CPS) ignoring formatting tags and linebreaks.
   - Detects timestamp inversions, overlaps between sequential cues, and line length violations.
