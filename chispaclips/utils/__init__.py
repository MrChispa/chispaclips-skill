"""Utilidades transversales de ChispaClips (BrainMatic)."""

from .logging import configurar_logging, log
from .http import SesionHTTP, sesion_global
from .ffmpeg import (
    ffmpeg_ejecutar,
    ffprobe_duracion,
    ffprobe_dimensiones,
    extraer_frames,
)

__all__ = [
    "configurar_logging",
    "log",
    "SesionHTTP",
    "sesion_global",
    "ffmpeg_ejecutar",
    "ffprobe_duracion",
    "ffprobe_dimensiones",
    "extraer_frames",
]
