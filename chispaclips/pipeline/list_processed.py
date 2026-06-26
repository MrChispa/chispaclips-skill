"""Subcomando: `list-processed` — lista el estado de videos procesados."""

from __future__ import annotations

import json
import sys

from ..config import Config
from .state import cargar_estado


def cmd_list_processed(cfg: Config, args) -> None:  # noqa: ANN001
    estado = cargar_estado(cfg)
    json.dump(estado, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")


__all__ = ["cmd_list_processed"]
