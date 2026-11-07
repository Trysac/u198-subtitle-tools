# Testing

## Tests Coverage

The tests are located in `tests/test_subtitle_tools.py`. They cover:
- Parsing: Validation of SRT/VTT parsing logic, including BOM removal, line ending normalization, and handling of blank lines/comments.
- Conversion: Ensuring tags and HTML entities are correctly converted and escaped between SRT and VTT formats.
- Timing: Accuracy of `shift` and `retime` using rational arithmetic to handle frame-rate conversions without rounding errors.
- Validation: `check` function verification for overlaps, duration, character-per-second (CPS) speed, and line length constraints.
- Error Handling: Verifying that `SubtitleError` is raised with appropriate codes for input size limits, timing errors, and format mismatches.
