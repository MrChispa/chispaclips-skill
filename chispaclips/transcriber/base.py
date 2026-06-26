"""Interfaz abstracta para proveedores de transcripción."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


class Transcriber(ABC):
    """Contrato común para Whisper local / Groq API.

    El método `transcribir` devuelve un dict con el formato estándar de
    `transcript.json` que el resto del pipeline de ChispaClips espera:

        {
            "video": str,
            "language": str,             # ej. "es", "es-MX"
            "language_probability": float,
            "duration": float,           # segundos
            "segments": [
                {
                    "start": float,
                    "end": float,
                    "text": str,
                    "words": [{"s": float, "e": float, "t": str}, ...]
                }
            ]
        }
    """

    nombre: str

    def __init__(self, modelo: str, idioma: str = "") -> None:
        self.modelo = modelo
        self.idioma = idioma.strip() if idioma else ""

    @abstractmethod
    def transcribir(self, ruta_video: Path) -> dict:
        """Transcribe `ruta_video` y devuelve el dict estándar."""

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} modelo={self.modelo!r} idioma={self.idioma!r}>"


__all__ = ["Transcriber"]
