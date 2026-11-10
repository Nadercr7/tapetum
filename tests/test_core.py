from pathlib import Path

import numpy as np
from PIL import Image

from tapetum import frames, timeline
from tapetum.common import fmt_ts, parse_source, parse_ts
from tapetum.transcript import Transcript, parse_vtt


def test_fmt_and_parse_ts():
    assert fmt_ts(75) == "01:15"
    assert fmt_ts(3725) == "1:02:05"
    assert parse_ts("3:12") == 192
    assert parse_ts("01:03:12") == 3792
    assert parse_ts("192s") == 192


def test_parse_source_youtube_variants():
    for raw in (
        "https://www.youtube.com/watch?v=jNQXAC9IVRw&t=5s",
        "https://youtu.be/jNQXAC9IVRw?si=abc",
        "https://www.youtube.com/shorts/jNQXAC9IVRw",
        "https://m.youtube.com/embed/jNQXAC9IVRw",
        "jNQXAC9IVRw",
    ):
        s = parse_source(raw)
        assert (s.kind, s.id) == ("youtube", "jNQXAC9IVRw"), raw


def test_parse_source_other_platforms():
    assert parse_source("https://www.tiktok.com/@u/video/7301234567890123456").kind == "tiktok"
    assert parse_source("https://x.com/u/status/1234567890").kind == "x"
    assert parse_source("https://example.com/a.mp4").kind == "web"


def test_vtt_dedupes_rolling_captions(tmp_path: Path):
    vtt = tmp_path / "a.vtt"
    vtt.write_text(
        "WEBVTT\n\n00:00:01.000 --> 00:00:02.000\nhello world\n\n"
        "00:00:02.000 --> 00:00:03.000\nhello world\n\n"
        "00:00:03.000 --> 00:00:04.000\n<c>second</c> line\n",
        encoding="utf-8",
    )
    segs = parse_vtt(vtt)
    assert [s["text"] for s in segs] == ["hello world", "second line"]


def _img(path: Path, color, box=None):
    im = Image.new("RGB", (640, 360), color)
    if box:
        im.paste((255, 255, 255), box)
    im.save(path)


def test_select_keeps_slide_with_small_text_change(tmp_path: Path):
    a, b, c = tmp_path / "a.jpg", tmp_path / "b.jpg", tmp_path / "c.jpg"
    _img(a, (20, 20, 60))
    _img(b, (20, 20, 60))  # identical: dropped
    _img(c, (20, 20, 60), box=(100, 150, 400, 170))  # a new line of text: kept
    sel = frames.select_frames([a, b, c], fps=1.0, budget=10, max_gap=999)
    assert [round(t) for _, t, _ in sel] == [0, 2]


def test_select_respects_budget(tmp_path: Path):
    files = []
    for i in range(30):
        p = tmp_path / f"{i:02d}.jpg"
        _img(p, (i * 8 % 255, 40, 90), box=(0, 0, 40 + i * 15, 360))
        files.append(p)
    sel = frames.select_frames(files, fps=1.0, budget=6, max_gap=999)
    assert len(sel) <= 6 and sel[0][1] == 0


def test_timeline_groups_speech_under_frames():
    t = Transcript(
        [{"start": 1, "end": 2, "text": "one"}, {"start": 12, "end": 13, "text": "two"}],
        "test", "en", "manual",
    )
    md = timeline.build({"title": "T", "duration": 20}, t,
                        [{"t": 0, "ts": "00:00", "file": "frames/a.jpg"}, {"t": 10, "ts": "00:10", "file": "frames/b.jpg"}],
                        [], "https://x")
    assert "### 00:00 – 00:10" in md and "> one" in md and "> two" in md
    assert md.index("> one") < md.index("### 00:10") < md.index("> two")


def test_transition_burst_keeps_only_settled_frame(tmp_path: Path):
    files = []
    for i, w in enumerate([0, 0, 80, 160, 240, 240, 240]):  # content slides across for 3 frames
        p = tmp_path / f"{i}.jpg"
        _img(p, (20, 20, 60), box=(0, 0, 40 + w, 360))
        files.append(p)
    sel = frames.select_frames(files, fps=1.0, budget=10, max_gap=999)
    assert [round(t) for _, t, _ in sel] == [0, 4]


def test_continuous_motion_is_not_collapsed(tmp_path: Path):
    files = []
    for i in range(20):  # something moves every second for 20 s
        p = tmp_path / f"{i:02d}.jpg"
        _img(p, (20, 20, 60), box=(i * 25, 100, i * 25 + 60, 200))
        files.append(p)
    sel = frames.select_frames(files, fps=1.0, budget=24, max_gap=999)
    assert len(sel) >= 4


# ---- regressions from the code review ----------------------------------

import json

import pytest

from tapetum import pipeline
from tapetum.common import TapetumError
from tapetum.transcript import choose_track
from tapetum.view import safe_json


def test_rolling_auto_captions_are_not_doubled(tmp_path: Path):
    vtt = tmp_path / "r.vtt"
    vtt.write_text(
        "WEBVTT\n\n"
        "00:00:00.000 --> 00:00:02.000\nhello world\n\n"
        "00:00:02.000 --> 00:00:02.010\nhello world\n\n"
        "00:00:02.010 --> 00:00:04.000\nhello world\nthis is new\n\n"
        "00:00:04.000 --> 00:00:06.000\nthis is new\nand more\n",
        encoding="utf-8",
    )
    assert [s["text"] for s in parse_vtt(vtt)] == ["hello world", "this is new", "and more"]


def test_choose_track_prefers_original_over_translation():
    # Arabic video, no human captions, YouTube offers auto Arabic plus machine translations
    assert choose_track([], ["ar-orig", "ar", "en", "fr"], [], "ar") == ("ar-orig", "auto")
    # user asked for English: a human English track wins
    assert choose_track(["en-US", "ar"], ["ar-orig"], ["en"], "ar") == ("en-US", "manual")
    # only a translation matches the request: it is flagged, and the original still wins
    assert choose_track([], ["ar-orig", "en"], ["en"], "ar") == ("ar-orig", "auto")
    assert choose_track([], ["en"], ["en"], None) == ("en", "translated")
    assert choose_track([], [], ["en"], "en") is None


def test_viewer_json_cannot_close_the_script_tag():
    blob = safe_json({"title": "</script><img src=x onerror=alert(1)>"})
    assert "</script" not in blob and "<" not in blob


def test_playlist_and_channel_links_are_rejected():
    for url in ("https://www.youtube.com/playlist?list=PL123", "https://www.youtube.com/@somechannel"):
        with pytest.raises(TapetumError) as e:
            parse_source(url)
        assert e.value.code == "playlist_url"


def test_local_files_with_same_name_get_different_keys(tmp_path: Path):
    (tmp_path / "a").mkdir(); (tmp_path / "b").mkdir()
    (tmp_path / "a" / "v.mp4").write_bytes(b"1"); (tmp_path / "b" / "v.mp4").write_bytes(b"22")
    assert parse_source(str(tmp_path / "a" / "v.mp4")).key != parse_source(str(tmp_path / "b" / "v.mp4")).key
    arabic = tmp_path / "فيديو.mp4"; arabic.write_bytes(b"x")
    assert parse_source(str(arabic)).key.startswith("local-file-")


def test_clearing_outputs_never_touches_other_files(tmp_path: Path):
    (tmp_path / "my-notes.txt").write_text("keep me")
    (tmp_path / "frames").mkdir(); (tmp_path / "frames" / "f000_00-00.jpg").write_bytes(b"x")
    (tmp_path / "sheet_01.jpg").write_bytes(b"x"); (tmp_path / "result.json").write_text("{}")
    pipeline._clear_outputs(tmp_path)
    assert sorted(p.name for p in tmp_path.iterdir()) == ["my-notes.txt"]


def test_failed_runs_are_not_cached():
    assert not pipeline._cacheable({"error": {"code": "no_transcript"}, "steps": []})
    assert not pipeline._cacheable({"steps": [{"step": "x", "ok": False, "code": "bot_blocked"}, {"step": "y", "ok": True}]})
    assert pipeline._cacheable({"steps": [{"step": "x", "ok": False, "code": "no_captions"}, {"step": "y", "ok": True}]})


def test_budget_below_six_is_respected(tmp_path: Path):
    files = []
    for i in range(40):
        p = tmp_path / f"{i:02d}.jpg"
        _img(p, (i * 6 % 255, 30, 90), box=(0, 0, 20 + i * 15, 360))
        files.append(p)
    assert len(frames.select_frames(files, fps=0.2, budget=3, max_gap=999)) <= 3
    assert len(frames.select_frames(files, fps=0.2, budget=1)) == 1


def test_unknown_original_language_prefers_english_human_track():
    assert choose_track(["de", "en", "es"], [], ["fr"], None) == ("en", "manual")


def test_hls_segments_cover_only_the_window():
    from tapetum.media import hls_segments

    pl = "\n".join(["#EXTM3U", '#EXT-X-MAP:URI="init.mp4"'] + [f"#EXTINF:5.0,\nseg{i}.m4s" for i in range(10)])
    init, segs, first = hls_segments(pl, 12.0, 20.0)
    assert init == "init.mp4"
    assert segs == ["seg2.m4s", "seg3.m4s"]
    assert first == 10.0
    assert hls_segments(pl, 60.0, 70.0)[1] == []
