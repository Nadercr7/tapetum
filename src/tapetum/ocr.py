"""Optional on-screen text. Arabic and other non-Latin scripts: let the host model read the images."""
from __future__ import annotations

from pathlib import Path

from .common import TapetumError


def read_frames(root: Path, frames: list[dict]) -> dict[str, str]:
    try:
        from rapidocr_onnxruntime import RapidOCR
    except ImportError as exc:
        raise TapetumError("no_ocr", "OCR extra not installed", "pip install 'tapetum[ocr]'") from exc
    eng = RapidOCR()
    out, prev = {}, ""
    for f in frames:
        res, _ = eng(str(root / f["file"]))
        text = "\n".join(r[1] for r in (res or []) if float(r[2]) > 0.6)
        if text and text != prev:  # skip repeats of the same slide
            out[f["file"]] = text
            prev = text
    return out
