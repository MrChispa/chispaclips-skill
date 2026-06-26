"""Subcomando: `transcribe` — transcripción con Whisper y marcas por palabra."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from ..config import Config
from ..utils.logging import log
from .state import carpeta_salida_video


def cmd_transcribe(cfg: Config, args) -> None:  # noqa: ANN001
    from faster_whisper import WhisperModel

    video = Path(args.video).resolve()
    if not video.exists():
        raise SystemExit(f"video no encontrado: {video}")

    out_dir = carpeta_salida_video(cfg, video)
    out_path = Path(args.output).resolve() if args.output else out_dir / "transcript.json"

    modelo_nombre = args.model or cfg.whisper_model
    log().info("[transcribir] cargando whisper %s…", modelo_nombre)
    modelo = WhisperModel(modelo_nombre, device="cpu", compute_type="int8")

    log().info("[transcribir] procesando %s…", video.name)
    segmentos_iter, info = modelo.transcribe(
        str(video),
        word_timestamps=True,
        vad_filter=True,
        language=cfg.whisper_language or None,
    )

    segmentos: list[dict] = []
    for seg in segmentos_iter:
        palabras: list[dict] = []
        for w in (seg.words or []):
            palabras.append({
                "s": round(w.start, 3),
                "e": round(w.end, 3),
                "t": w.word.strip(),
            })
        segmentos.append({
            "start": round(seg.start, 3),
            "end": round(seg.end, 3),
            "text": seg.text.strip(),
            "words": palabras,
        })

    payload = {
        "video": video.name,
        "language": info.language,
        "language_probability": round(info.language_probability, 3),
        "duration": round(info.duration, 3),
        "segments": segmentos,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    log().info(
        "[transcribir] %d segmentos · idioma=%s (%.2f) → %s",
        len(segmentos), info.language, info.language_probability, out_path,
    )
    sys.stdout.write(str(out_path) + "\n")


__all__ = ["cmd_transcribe"]
