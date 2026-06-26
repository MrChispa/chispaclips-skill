"""Subcomando: `extract` — corta un único clip con ffmpeg (frame-accurate)."""

from __future__ import annotations

import sys
from pathlib import Path

from ..config import Config
from ..utils.ffmpeg import ffmpeg_ejecutar


def cmd_extract(cfg: Config, args) -> None:  # noqa: ANN001
    video = Path(args.video).resolve()
    if not video.exists():
        raise SystemExit(f"video no encontrado: {video}")

    inicio = float(args.start)
    fin = float(args.end)
    if fin <= inicio:
        raise SystemExit(f"--end ({fin}) debe ser mayor que --start ({inicio})")

    salida = Path(args.output).resolve()
    salida.parent.mkdir(parents=True, exist_ok=True)

    ffmpeg_ejecutar([
        "-ss", f"{inicio:.3f}",
        "-to", f"{fin:.3f}",
        "-i", str(video),
        "-c:v", "libx264", "-preset", "fast", "-crf", "20",
        "-c:a", "aac", "-b:a", "160k",
        "-movflags", "+faststart",
        str(salida),
    ])
    sys.stdout.write(str(salida) + "\n")


__all__ = ["cmd_extract"]
