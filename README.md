# subtitle-tools

[![PyPI version](https://img.shields.io/pypi/v/trysac-subtitle-tools)](https://pypi.org/project/trysac-subtitle-tools/)
[![License: MIT](https://img.shields.io/pypi/l/trysac-subtitle-tools)](LICENSE)
[![CI](https://github.com/Trysac/u198-subtitle-tools/actions/workflows/ci.yml/badge.svg)](https://github.com/Trysac/u198-subtitle-tools/actions/workflows/ci.yml)

Parse, convert and retime SRT and WebVTT subtitles: exact millisecond timing, tag and entity handling, shift and frame-rate retiming, and readability checks

## Problem

Describe in two or three sentences the concrete problem this utility solves, who hits it, and what
they do today without it. Replace this paragraph when the first real feature lands.

## Install

```sh
pip install trysac-subtitle-tools
# or
uv add trysac-subtitle-tools
```

Requires Python 3.10 or newer. No runtime dependencies.

## Usage

```python
import subtitle_tools

# normalize() trims surrounding whitespace and lower-cases the text.
print(subtitle_tools.normalize("  Hello World "))  # -> "hello world"

# Blank input is rejected explicitly instead of returning an empty string.
try:
    subtitle_tools.normalize("   ")
except ValueError as exc:
    print(f"rejected: {exc}")
```

## Documentation

- [Architecture](docs/ARCHITECTURE.md) and [decisions](docs/decisions/)
- [Testing](docs/TESTING.md) and [security](docs/SECURITY.md)
- [Project record](docs/PROJECT.md) and [stack](docs/STACK.md)
- [Changelog](CHANGELOG.md) and [contributing guide](CONTRIBUTING.md)

## License

[MIT](LICENSE) (c) 2026 Miguel Gomez
