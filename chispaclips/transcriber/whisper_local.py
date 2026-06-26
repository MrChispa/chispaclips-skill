"""Proveedor de transcripción: Whisper local con `faster-whisper`.

Corre en CPU con cuantización `int8`. La primera ejecución descarga
el modelo seleccionado (medium ≈ 1.5 GB). Después se cachea en
`~/.cache/huggingface/`.
"""

from __future__ import annotations

import json
from pathlib import Path

from ..utils.logging import log
from .base import Transcriber


class WhisperLocalTranscriber(Transcriber):
    nombre = "whisper"

    def transcribir(self, ruta_video: Path) -> dict:
        from faster_whisper import WhisperModel

        log().info(
            "[transcribir] cargando Whisper local (modelo=%s)…",
            self.modelo,
        )
        modelo = WhisperModel(self.modelo, device="cpu", compute_type="int8")

        log().info("[transcribir] procesando %s…", ruta_video.name)
        segmentos_iter, info = modelo.transcribe(
            str(ruta_video),
            word_timestamps=True,
            vad_filter=True,
            language=self.idioma or None,
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

        return {
            "video": ruta_video.name,
            "language": info.language,
            "language_probability": round(info.language_probability, 3),
            "duration": round(info.duration, 3),
            "segments": segmentos,
        }


__all__ = ["WhisperLocalTranscriber"]
