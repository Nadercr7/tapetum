"""Pick frames that matter: dense sample, drop near-duplicates, cap at a budget."""
from __future__ import annotations

import shutil
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from .common import fmt_ts, run_ffmpeg

SIG_W, SIG_H = 96, 54


def _sig(path: Path) -> np.ndarray:
    with Image.open(path) as im:
        return np.asarray(im.convert("L").resize((SIG_W, SIG_H), Image.BILINEAR), dtype=np.float32) / 255.0


def sample_candidates(video: Path, duration: float | None, out: Path, cap: int = 600) -> tuple[list[Path], float]:
    """Dense, cheap sampling. Returns (files, fps). Avoids -vsync, which newer ffmpeg removed."""
    out.mkdir(parents=True, exist_ok=True)
    fps = 1.0 if not duration else min(1.0, cap / max(duration, 1.0))
    # round=up puts output frame i at i/fps; the default rounding makes every label half a step late
    run_ffmpeg(["-i", str(video), "-vf", f"fps={fps:.5f}:round=up,scale=640:-2", "-q:v", "4", str(out / "c_%05d.jpg")])
    files = sorted(out.glob("c_*.jpg"))
    if len(files) > cap:  # duration was unknown: thin out afterwards so long files stay bounded
        step = len(files) / cap
        files = [files[int(i * step)] for i in range(cap)]
        fps = fps / step
    return files, fps


def select_frames(files: list[Path], fps: float, budget: int, max_gap: float = 45.0, sensitivity: float = 0.006):
    """Keep a frame when enough pixels changed (so slides that differ only in text survive),
    or when `max_gap` seconds passed. Then trim to `budget` by keeping the biggest changes per time bin."""
    if not files:
        return []
    if budget <= 1:
        return [(files[0], 0.0, 1.0)]
    times = [i / fps for i in range(len(files))]
    kept = [(0, 1.0)]  # (index, change score); first frame is always kept
    last = _sig(files[0])
    last_t = times[0]
    for i in range(1, len(files)):
        cur = _sig(files[i])
        score = float((np.abs(cur - last) > 0.12).mean())
        if score >= sensitivity or times[i] - last_t >= max_gap:
            kept.append((i, max(score, 0.0001)))
            last, last_t = cur, times[i]
    # A transition (zoom, fade, scroll) fires several frames in a row. Keep only the last, settled one.
    # Continuous motion (handheld, panning) fires constantly, so a burst is capped at `burst_cap`
    # seconds, which leaves one frame every few seconds instead of collapsing the whole clip.
    settle, burst_cap = 2.5, 5.0
    merged = [kept[0]]
    cluster_start = times[kept[0][0]]
    for idx, sc in kept[1:]:
        t = times[idx]
        if len(merged) > 1 and t - times[merged[-1][0]] < settle and t - cluster_start < burst_cap:
            merged[-1] = (idx, max(sc, merged[-1][1]))
        else:
            merged.append((idx, sc))
            cluster_start = t
    kept = merged
    if len(kept) > budget:
        # keep the first, then the strongest change inside each of (budget-1) equal time bins
        total = times[-1] + 1e-6
        bins: dict[int, tuple[int, float]] = {}
        for idx, sc in kept[1:]:
            b = min(budget - 2, int(times[idx] / total * (budget - 1))) if budget > 1 else 0
            if b not in bins or sc > bins[b][1]:
                bins[b] = (idx, sc)
        kept = [kept[0]] + sorted(bins.values())
    return [(files[i], times[i], s) for i, s in kept]


def save_frames(selected, frames_dir: Path) -> list[dict]:
    frames_dir.mkdir(parents=True, exist_ok=True)
    out = []
    for n, (src, t, score) in enumerate(selected):
        name = f"f{n:03d}_{fmt_ts(t).replace(':', '-')}.jpg"
        shutil.copyfile(src, frames_dir / name)
        out.append({"t": round(t, 1), "ts": fmt_ts(t), "file": f"frames/{name}", "change": round(score, 4)})
    return out


def _font(size: int):
    try:
        return ImageFont.load_default(size=size)
    except TypeError:  # old Pillow
        return ImageFont.load_default()


def contact_sheets(frames: list[dict], root: Path, per_sheet: int = 9, cell_w: int = 480) -> list[str]:
    paths = []
    font = _font(22)
    for s in range(0, len(frames), per_sheet):
        chunk = frames[s : s + per_sheet]
        ims = []
        for f in chunk:
            with Image.open(root / f["file"]) as im:
                ims.append(im.convert("RGB"))
        cell_h = int(cell_w * ims[0].height / ims[0].width)
        cols = 3
        rows = (len(ims) + cols - 1) // cols
        sheet = Image.new("RGB", (cols * cell_w, rows * cell_h), "black")
        d = ImageDraw.Draw(sheet)
        for i, (im, f) in enumerate(zip(ims, chunk)):
            x, y = (i % cols) * cell_w, (i // cols) * cell_h
            sheet.paste(im.resize((cell_w, cell_h)), (x, y))
            w = int(d.textlength(f["ts"], font=font)) + 14
            d.rectangle([x, y, x + w, y + 30], fill="black")
            d.text((x + 6, y + 3), f["ts"], fill="yellow", font=font)
        name = f"sheet_{s // per_sheet + 1:02d}.jpg"
        sheet.save(root / name, quality=82)
        paths.append(name)
    return paths


def grab_around(video: Path, out: Path, count: int, step: float, offset: float = 0.0) -> list[dict]:
    """Full-resolution frames from a short clip, for `--at` zoom. `offset` is the clip's start time."""
    out.mkdir(parents=True, exist_ok=True)
    run_ffmpeg(["-i", str(video), "-vf", f"fps={1.0 / step:.5f}:round=up", "-frames:v", str(count), "-q:v", "2",
                str(out / "z_%02d.jpg")])
    return [{"file": f"zoom/{p.name}", "ts": fmt_ts(offset + i * step)}
            for i, p in enumerate(sorted(out.glob("z_*.jpg")))]
