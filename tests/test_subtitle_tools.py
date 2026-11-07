"""Comprehensive tests for trysac-subtitle-tools."""

from __future__ import annotations

from fractions import Fraction
from pathlib import Path

import pytest

from subtitle_tools import (
    Cue,
    Issue,
    SubtitleError,
    check,
    parse,
    render,
    retime,
    shift,
)
from subtitle_tools.__main__ import main


def test_acceptance_item_1() -> None:
    s = "1\n00:00:01,000 --> 00:00:02,500\nHello\n\n2\n00:00:03,000 --> 00:00:04,000\nWorld\nagain\n"
    expected = [
        Cue(1000, 2500, "Hello", "1", None),
        Cue(3000, 4000, "World\nagain", "2", None),
    ]
    assert parse(s, "srt") == expected

    s_bom_crlf = "\ufeff" + s.replace("\n", "\r\n")
    assert parse(s_bom_crlf, "srt") == expected


def test_acceptance_item_2() -> None:
    cues = [
        Cue(1000, 2500, "Hello", "1", None),
        Cue(3000, 4000, "World\nagain", "2", None),
    ]
    expected_vtt = "WEBVTT\n\n1\n00:00:01.000 --> 00:00:02.500\nHello\n\n2\n00:00:03.000 --> 00:00:04.000\nWorld\nagain\n"
    assert render(cues, "vtt") == expected_vtt

    s = "1\n00:00:01,000 --> 00:00:02,500\nHello\n\n2\n00:00:03,000 --> 00:00:04,000\nWorld\nagain\n"
    assert render(parse(s, "srt"), "srt") == s


def test_acceptance_item_3() -> None:
    vtt_text = "WEBVTT - title\n\nNOTE hi\n\nSTYLE\n::cue { color: red }\n\n00:01.000 --> 00:02.000 align:start\n<v Bob>Hi &amp; bye</v>\n"
    parsed = parse(vtt_text, "vtt")
    assert parsed == [Cue(1000, 2000, "<v Bob>Hi &amp; bye</v>", None, "align:start")]
    assert render(parsed, "srt") == "1\n00:00:01,000 --> 00:00:02,000\nHi & bye\n"


def test_acceptance_item_4() -> None:
    # An SRT cue text 'a < b & c --> d' renders in VTT as 'a &lt; b &amp; c --&gt; d', and '<i>x</i>' is kept as '<i>x</i>' in both formats
    srt_cue = [Cue(1000, 2000, "a < b & c --> d")]
    rendered_vtt = render(srt_cue, "vtt")
    assert "a &lt; b &amp; c --&gt; d" in rendered_vtt

    formatting_cue = [Cue(1000, 2000, "<i>x</i>")]
    rendered_vtt_fmt = render(formatting_cue, "vtt")
    assert "<i>x</i>" in rendered_vtt_fmt
    rendered_srt_fmt = render(formatting_cue, "srt")
    assert "<i>x</i>" in rendered_srt_fmt


def test_acceptance_item_5() -> None:
    cues = [Cue(1000, 2500, "First"), Cue(3000, 4000, "Second")]
    shifted = shift(cues, -1500)
    assert shifted == [Cue(0, 1000, "First"), Cue(1500, 2500, "Second")]

    # Cue whose end becomes <= 0 is dropped
    dropped = shift([Cue(500, 1000, "Gone")], -1000)
    assert dropped == []
    dropped_more = shift([Cue(500, 1000, "Gone")], -1200)
    assert dropped_more == []


def test_acceptance_item_6() -> None:
    cues = [Cue(1000, 2500, "A")]
    retimed = retime(cues, Fraction(25, 24))
    assert retimed[0].start_ms == 1042
    assert retimed[0].end_ms == 2604

    with pytest.raises(SubtitleError) as exc_info:
        retime(cues, 0)
    assert exc_info.value.code == "invalid_option"

    with pytest.raises(SubtitleError) as exc_info2:
        retime(cues, Fraction(-1, 2))
    assert exc_info2.value.code == "invalid_option"


def test_acceptance_item_7() -> None:
    # check(cues) reports Issue('overlap', 2) when cue 2 starts before cue 1 ends
    overlap_cues = [Cue(0, 2000, "1"), Cue(1500, 3000, "2")]
    issues = check(overlap_cues)
    assert Issue("overlap", 2) in issues

    # 'line_too_long' for a 43-character line but not for 42
    cues_42 = [Cue(0, 10000, "a" * 42)]
    assert Issue("line_too_long", 1) not in check(cues_42)
    cues_43 = [Cue(0, 10000, "a" * 43)]
    assert Issue("line_too_long", 1) in check(cues_43)

    # 'reading_speed' for 21 visible characters in 1000 ms but not 20
    cues_20 = [Cue(0, 1000, "x" * 20)]
    assert Issue("reading_speed", 1) not in check(cues_20)
    cues_21 = [Cue(0, 1000, "x" * 21)]
    assert Issue("reading_speed", 1) in check(cues_21)

    # 'non_positive_duration' for start == end
    cues_zero_dur = [Cue(1000, 1000, "Hello")]
    assert Issue("non_positive_duration", 1) in check(cues_zero_dur)

    cues_neg_dur = [Cue(2000, 1000, "Hello")]
    assert Issue("non_positive_duration", 1) in check(cues_neg_dur)

    # 'too_many_lines'
    cues_three_lines = [Cue(0, 10000, "line1\nline2\nline3")]
    assert Issue("too_many_lines", 1) in check(cues_three_lines)


def test_acceptance_item_8(tmp_path: Path) -> None:
    # '00:00:01,000 -> 00:00:02,000' raises SubtitleError with code 'invalid_timestamp' and a message containing 'line 2'
    bad_timing = "1\n00:00:01,000 -> 00:00:02,000\nTest\n"
    with pytest.raises(SubtitleError) as exc_info:
        parse(bad_timing, "srt")
    assert exc_info.value.code == "invalid_timestamp"
    assert "line 2" in str(exc_info.value)

    # VTT text without 'WEBVTT' raises code 'missing_header'
    with pytest.raises(SubtitleError) as exc_info_vtt:
        parse("00:00.000 --> 00:01.000\nHi\n", "vtt")
    assert exc_info_vtt.value.code == "missing_header"

    # 10_000_001 characters raise code 'input_too_large'
    with pytest.raises(SubtitleError) as exc_info_large:
        parse("a" * 10_000_001, "srt")
    assert exc_info_large.value.code == "input_too_large"

    # CLI main(['convert', 'in.srt', 'out.vtt']) returns 0 and returns 2 on errors
    in_srt = tmp_path / "in.srt"
    out_vtt = tmp_path / "out.vtt"
    in_srt.write_text("1\n00:00:01,000 --> 00:00:02,000\nCLI test\n", encoding="utf-8")
    res = main(["convert", str(in_srt), str(out_vtt)])
    assert res == 0
    assert out_vtt.exists()
    assert "WEBVTT" in out_vtt.read_text(encoding="utf-8")

    # CLI returns 2 on error
    res_err = main(["convert", str(tmp_path / "nonexistent.srt"), str(tmp_path / "out2.vtt")])
    assert res_err == 2


def test_parse_limits_and_formats() -> None:
    with pytest.raises(SubtitleError) as exc:
        parse(
            "WEBVTT\n",
            "invalid",  # type: ignore[arg-type]
        )
    assert exc.value.code == "invalid_option"

    # Cue limit exceeded
    srt_many = "1\n00:00:01,000 --> 00:00:02,000\nA\n\n2\n00:00:03,000 --> 00:00:04,000\nB\n"
    with pytest.raises(SubtitleError) as exc:
        parse(srt_many, "srt", max_cues=1)
    assert exc.value.code == "too_many_cues"

    vtt_many = "WEBVTT\n\n00:01.000 --> 00:02.000\nA\n\n00:03.000 --> 00:04.000\nB\n"
    with pytest.raises(SubtitleError) as exc:
        parse(vtt_many, "vtt", max_cues=1)
    assert exc.value.code == "too_many_cues"


def test_vtt_entities_and_numeric_references() -> None:
    vtt = "WEBVTT\n\n00:01.000 --> 00:02.000\n&lt;Hello&gt; &nbsp; &lrm; &rlm; &#65; &#x42;\n"
    cues = parse(vtt, "vtt")
    rendered_srt = render(cues, "srt")
    assert "<Hello> \u00a0 \u200e \u200f A B" in rendered_srt


def test_vtt_and_srt_tag_transformations() -> None:
    # Font tag removal in SRT -> VTT
    srt_with_font = '1\n00:00:01,000 --> 00:00:02,000\n<font color="red">Red text</font>\n'
    cues = parse(srt_with_font, "srt")
    rendered_vtt = render(cues, "vtt")
    assert "Red text" in rendered_vtt
    assert "<font" not in rendered_vtt
    assert "</font>" not in rendered_vtt

    # Bold, italic, underline preservation
    mixed_srt = "1\n00:00:01,000 --> 00:00:02,000\n<b>Bold</b> <u>Underline</u> <i>Italic</i>\n"
    cues_mixed = parse(mixed_srt, "srt")
    rendered_vtt_mixed = render(cues_mixed, "vtt")
    assert "<b>bold</b>" in rendered_vtt_mixed or "<b>Bold</b>" in rendered_vtt_mixed
    assert "<u>underline</u>" in rendered_vtt_mixed or "<u>Underline</u>" in rendered_vtt_mixed


def test_empty_render() -> None:
    assert render([], "srt") == ""
    assert render([], "vtt") == "WEBVTT\n\n"
    with pytest.raises(SubtitleError) as exc:
        render(
            [],
            "xyz",  # type: ignore[arg-type]
        )
    assert exc.value.code == "invalid_option"


def test_srt_parsing_edge_cases() -> None:
    # No index, just timing line
    srt = "00:00:01,000 --> 00:00:02,000\nNo index cue\n"
    cues = parse(srt, "srt")
    assert len(cues) == 1
    assert cues[0].identifier is None
    assert cues[0].text == "No index cue"

    # Malformed non-digit first line
    srt_bad = "NOT_AN_INDEX\n00:00:01,000 --> 00:00:02,000\nBad\n"
    with pytest.raises(SubtitleError) as exc:
        parse(srt_bad, "srt")
    assert exc.value.code == "invalid_timestamp"


def test_vtt_parsing_edge_cases() -> None:
    # REGION block and identifier in VTT
    vtt = "WEBVTT\n\nREGION\nid=fred\n\nid-1\n100:00:01.000 --> 100:00:02.000 line:0\nCue content\n"
    cues = parse(vtt, "vtt")
    assert len(cues) == 1
    assert cues[0].identifier == "id-1"
    assert cues[0].start_ms == 360001000
    assert cues[0].settings == "line:0"

    # Bad timing line after identifier
    bad_vtt = "WEBVTT\n\nid-1\nbad-timing\nText\n"
    with pytest.raises(SubtitleError) as exc:
        parse(bad_vtt, "vtt")
    assert exc.value.code == "invalid_timestamp"

    # Bad timing without identifier
    bad_vtt2 = "WEBVTT\n\n00:01.000 -> 00:02.000\nText\n"
    with pytest.raises(SubtitleError) as exc2:
        parse(bad_vtt2, "vtt")
    assert exc2.value.code == "invalid_timestamp"


def test_cli_subcommands(tmp_path: Path) -> None:
    # shift CLI
    srt_in = tmp_path / "shift_in.srt"
    srt_out = tmp_path / "shift_out.srt"
    srt_in.write_text("1\n00:00:01,000 --> 00:00:03,000\nShift me\n", encoding="utf-8")
    ret = main(["shift", str(srt_in), "--ms", "500", "-o", str(srt_out)])
    assert ret == 0
    content = srt_out.read_text(encoding="utf-8")
    assert "00:00:01,500 --> 00:00:03,500" in content

    # retime CLI
    rt_out = tmp_path / "retime_out.srt"
    ret = main(["retime", str(srt_in), "--factor", "2", "-o", str(rt_out)])
    assert ret == 0
    content_rt = rt_out.read_text(encoding="utf-8")
    assert "00:00:02,000 --> 00:00:06,000" in content_rt

    # check CLI passing
    ret_chk_ok = main(["check", str(srt_in)])
    assert ret_chk_ok == 0

    # check CLI failing
    bad_srt = tmp_path / "bad.srt"
    bad_srt.write_text("1\n00:00:01,000 --> 00:00:00,500\nNegative dur\n", encoding="utf-8")
    ret_chk_fail = main(["check", str(bad_srt)])
    assert ret_chk_fail == 1


def test_cli_errors(tmp_path: Path) -> None:
    # Unknown file format
    unknown_file = tmp_path / "subs.unknown"
    unknown_file.write_text("hello", encoding="utf-8")
    assert main(["convert", str(unknown_file), str(tmp_path / "out.srt")]) == 2
    assert main(["shift", str(unknown_file), "--ms", "100", "-o", str(tmp_path / "out.srt")]) == 2
    assert (
        main(["retime", str(unknown_file), "--factor", "1", "-o", str(tmp_path / "out.srt")]) == 2
    )
    assert main(["check", str(unknown_file)]) == 2

    # Unexpected exception branch (e.g. invalid factor syntax)
    srt_file = tmp_path / "valid.srt"
    srt_file.write_text("1\n00:00:01,000 --> 00:00:02,000\nHi\n", encoding="utf-8")
    assert (
        main(
            ["retime", str(srt_file), "--factor", "not-a-fraction", "-o", str(tmp_path / "out.srt")]
        )
        == 2
    )


def test_vtt_parsing_details() -> None:
    # Test vtt timing without hours
    vtt = "WEBVTT\n\n01:23.456 --> 01:25.789\nShort timing\n"
    cues = parse(vtt, "vtt")
    assert len(cues) == 1
    assert cues[0].start_ms == 83456
    assert cues[0].end_ms == 85789

    # Unexpected end of file after identifier in VTT
    with pytest.raises(SubtitleError) as exc:
        parse("WEBVTT\n\nidentifier-only", "vtt")
    assert exc.value.code == "invalid_timestamp"

    # Unexpected end of file after identifier in SRT
    with pytest.raises(SubtitleError) as exc:
        parse("1", "srt")
    assert exc.value.code == "invalid_timestamp"


def test_tag_and_entity_edge_cases() -> None:
    # Malformed entity reference should stay unchanged
    vtt = "WEBVTT\n\n00:01.000 --> 00:02.000\n&unknown; &#999999999999999999999999999999999; &#x999999999999999999999999999999999;\n"
    cues = parse(vtt, "vtt")
    srt_text = render(cues, "srt")
    assert "&unknown;" in srt_text

    # SRT with nested or diverse tags: font tags with attributes, b/i/u tags with spacing
    srt = "1\n00:00:01,000 --> 00:00:02,000\n<FONT SIZE=2>Hello</FONT> <B>World</B>\n"
    cues_srt = parse(srt, "srt")
    vtt_text = render(cues_srt, "vtt")
    assert "<b>world</b>" in vtt_text.lower()
    assert "font" not in vtt_text.lower()


def test_shift_and_check_coverage() -> None:
    # Shift with start < 0 clamps start to 0
    cues = [Cue(500, 1500, "Near zero")]
    shifted = shift(cues, -800)
    assert len(shifted) == 1
    assert shifted[0].start_ms == 0
    assert shifted[0].end_ms == 700

    # Retime integer factor
    cues2 = [Cue(1000, 2000, "Double")]
    retimed = retime(cues2, 2)
    assert retimed[0].start_ms == 2000
    assert retimed[0].end_ms == 4000
