"""Factoría de proveedores de transcripción."""

from __future__ import annotations

from ..config import Config
from ..utils.logging import log
from .base import Transcriber
from .groq import GroqTranscriber
from .whisper_local import WhisperLocalTranscriber


_TRANSCRIDORES_DISPONIBLES = ("whisper", "groq")


def listar_transcridores() -> tuple[str, ...]:
    return _TRANSCRIDORES_DISPONIBLES


def get_transcriber(cfg: Config) -> Transcriber:
    """Construye el proveedor adecuado según `cfg.transcriber_provider`."""
    provider = cfg.transcriber_provider
    modelo_efectivo = (
        cfg.groq_whisper_model if provider == "groq" else cfg.whisper_model
    )
    log().info(
        "inicializando transcriber: %s (modelo=%s, idioma=%s)",
        provider, modelo_efectivo, cfg.whisper_language or "auto",
    )

    if provider == "whisper":
        return WhisperLocalTranscriber(
            modelo=cfg.whisper_model,
            idioma=cfg.whisper_language,
        )

    if provider == "groq":
        return GroqTranscriber(
            modelo=cfg.groq_whisper_model,
            api_key=cfg.groq_api_key,
            idioma=cfg.whisper_language,
        )

    raise ValueError(
        f"proveedor de transcripción no soportado: {provider!r}. "
        f"Opciones: {', '.join(_TRANSCRIDORES_DISPONIBLES)}"
    )


__all__ = ["get_transcriber", "listar_transcridores"]
