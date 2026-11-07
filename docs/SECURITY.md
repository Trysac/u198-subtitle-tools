# Security notes

## Threat model

`subtitle-tools` is a library without I/O or network dependencies.

- **Defended**: The parser validates input size (`max_chars`) and total cue count (`max_cues`) before processing, mitigating memory exhaustion from malicious or malformed files. All timestamps are validated against format constraints, and `SubtitleError` exceptions are raised for malformed data rather than propagating parser failure.
- **Not Defended**: The library performs no sandboxing. If the caller passes untrusted, malicious input into `parse`, the library assumes the caller has already performed necessary I/O security checks. It does not perform arbitrary code execution; it strictly handles string processing of subtitle text.
