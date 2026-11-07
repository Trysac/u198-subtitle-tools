"""Behavior tests for the public API of subtitle_tools."""

from __future__ import annotations

import pytest

import subtitle_tools


def test_normalize_trims_and_lowercases() -> None:
    assert subtitle_tools.normalize("  Hello World ") == "hello world"


@pytest.mark.parametrize("value", ["", "   ", "\t\n"])
def test_normalize_rejects_blank_input(value: str) -> None:
    with pytest.raises(ValueError, match="must not be empty"):
        subtitle_tools.normalize(value)


def test_version_is_semver() -> None:
    parts = subtitle_tools.__version__.split(".")
    assert len(parts) == 3
    assert all(part.isdigit() for part in parts)
