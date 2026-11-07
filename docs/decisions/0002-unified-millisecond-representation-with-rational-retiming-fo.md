# Unified millisecond representation with rational retiming for SRT and WebVTT

Status: accepted (generated, pending human review)

## Context

Converting subtitles between SRT and WebVTT often suffers from precision loss, mangled markup tags, and timing drift across framerate conversions. Existing Python libraries either specialize in one format or introduce heavy dependencies.

## Decision

Implement a zero-dependency Python library with an immutable Cue model storing integer milliseconds, exact rational retiming via fractions.Fraction, strict parser limits, and bidirectional tag/entity translation.

## Consequences

Timings remain exact across multiple retiming steps; WebVTT and SRT formats can be converted without timing drift or mangled HTML tags. External dependencies remain empty.
