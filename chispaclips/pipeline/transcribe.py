"""Subcomando: `transcribe` — transcribe un video con el proveedor configurado.

Selecciona entre Whisper local (`faster-whisper`) o Groq API según
`TRANSCRIBER_PROVIDER` en `.env`. Ambos devuelven el mismo formato
estándar de `transcript.json` (segmentos con marcas por palabra).

Para override puntual: `python -m chispaclips transcribe video.mp4 --provider groq`
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from ..config import Config
from ..transcriber import get_transcriber
from ..utils.logging import log
from .state import carpeta_salida_video


def cmd_transcribe(cfg: Config, args) -> None:  # noqa: ANN001
    video = Path(args.video).resolve()
    if not video.exists():
        raise SystemExit(f"video no encontrado: {video}")

    out_dir = carpeta_salida_video(cfg, video)
    out_path = Path(args.output).resolve() if args.output else out_dir / "transcript.json"

    provider_override = getattr(args, "provider", None)
    if provider_override:
        from dataclasses import replace

        if provider_override not in ("whisper", "groq"):
            raise SystemExit(
                f"--provider inválido: {provider_override!r}. "
                "Opciones: whisper | groq."
            )
        log().info("[transcribir] override puntual: %s (config dice %s)",
                   provider_override, cfg.transcriber_provider)
        cfg = replace(cfg, transcriber_provider=provider_override)

    transcriber = get_transcriber(cfg)
    datos = transcriber.transcribir(video)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(datos, indent=2, ensure_ascii=False), encoding="utf-8")
    n_seg = len(datos.get("segments", []))
    log().info(
        "[transcribir] %d segmentos · idioma=%s (%.2f) · %s · → %s",
        n_seg,
        datos.get("language", "?"),
        datos.get("language_probability", 0.0),
        transcriber.nombre,
        out_path,
    )
    sys.stdout.write(str(out_path) + "\n")


__all__ = ["cmd_transcribe"]
