"""Logger en español para ChispaClips (BrainMatic).

Todos los mensajes van a stderr (los paths legibles a stdout), así el agente
orquestador (Hermes / Odysseus / Claude Code) puede parsearlos fácil.
"""

from __future__ import annotations

import logging
import sys
from typing import Final

_FORMATO: Final[str] = "[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s"
_FECHA: Final[str] = "%Y-%m-%d %H:%M:%S"

_LOGGER_RAIZ: logging.Logger | None = None


class _FiltroChispa(logging.Filter):
    """Limpia prefijos duplicados y normaliza niveles al español."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = record.msg.strip()
        return True


def configurar_logging(nivel: int = logging.INFO) -> logging.Logger:
    """Configura el logger raíz una sola vez. Llamadas adicionales son no-op."""
    global _LOGGER_RAIZ
    if _LOGGER_RAIZ is not None:
        return _LOGGER_RAIZ

    handler = logging.StreamHandler(stream=sys.stderr)
    handler.setFormatter(logging.Formatter(_FORMATO, datefmt=_FECHA))
    handler.addFilter(_FiltroChispa())

    raiz = logging.getLogger("chispaclips")
    raiz.setLevel(nivel)
    raiz.handlers.clear()
    raiz.addHandler(handler)
    raiz.propagate = False

    _LOGGER_RAIZ = raiz
    return raiz


def log() -> logging.Logger:
    """Devuelve el logger de ChispaClips (lo crea si no existe)."""
    if _LOGGER_RAIZ is None:
        return configurar_logging()
    return _LOGGER_RAIZ


__all__ = ["configurar_logging", "log"]
