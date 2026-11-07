# Project record

## Objective
Parse, convert and retime SRT and WebVTT subtitles: exact millisecond timing, tag and entity handling, shift and frame-rate retiming, and readability checks.

## Scope
- Public API documented in the README, implemented with strict typing, and verified by unit tests.
- Parsing and serialization of SRT and WebVTT formats.
- Transformation logic (shifting by ms, retiming by rational factor).
- Auditing logic (reading speed, overlaps, line limits).

## Out-of-scope
- Subtitle formats other than SRT and WebVTT (e.g., ASS/SSA, TTML).
- Burning subtitles into video files.
- Speech alignment.
- Translation logic.

## Timeline

| Date | Event |
|---|---|
| 2026 | Repository created from the factory utility template. |

## Effort metrics

| Metric | Value |
|---|---|
| Tokens (input / output) | 1626779 / 18525 |
| Hours (human) | pending measurement |
| Cost (USD) | 0.2936 |

## Factory run u198 (measured from API usage)

| Phase | Model | Batch | Input | Output | Cache write | Cache read | Cost (USD) |
|---|---|---|---|---|---|---|---|
| generation | gemini-3.8-flash | yes | 4772 | 12886 | 0 | 0 | 0.0260 |
| fix-1 | gemini-3.8-flash | no | 19756 | 371 | 0 | 33828 | 0.0187 |
| fix-2 | gemini-3.8-flash | no | 103401 | 3712 | 0 | 1068167 | 0.1716 |
| fix-3 | gemini-3.8-flash | no | 19906 | 111 | 0 | 26653 | 0.0173 |
| audit | gemini-3.1-flash-lite | no | 55235 | 217 | 0 | 132327 | 0.0174 |
| docs | gemini-3.1-flash-lite | no | 162734 | 1228 | 0 | 0 | 0.0425 |

Total: $0.2936. Prices: Anthropic list prices.
