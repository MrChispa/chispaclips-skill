"""Subcomando: `preview` — extrae un frame para QA visual del hook.

El agente (Claude / openclaw / Hermes) revisa la imagen con su visión
multimodal nativa. NO se llama al LLM en este paso (lo hace el agente).
"""

from __future__ import annotations

import sys
from pathlib import Path

from ..config import Config
from ..utils.ffmpeg import ffmpeg_ejecutar


def cmd_preview(cfg: Config, args) -> None:  # noqa: ANN001
    clip = Path(args.video).resolve()
    if not clip.exists():
        raise SystemExit(f"clip no encontrado: {clip}")

    if args.output:
        salida = Path(args.output).resolve()
    else:
        salida = clip.with_name(f"preview_{clip.stem}.png")
    salida.parent.mkdir(parents=True, exist_ok=True)

    ffmpeg_ejecutar([
        "-ss", f"{args.at_time:.3f}",
        "-i", str(clip),
        "-frames:v", "1",
        "-q:v", "2",
        str(salida),
    ])
    sys.stdout.write(str(salida) + "\n")


__all__ = ["cmd_preview"]
