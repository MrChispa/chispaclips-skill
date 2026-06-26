"""Subcomando: `pick` — selecciona el siguiente video a procesar.

Estrategia de ciclo: cada video se procesa como máximo una vez por ciclo.
Cuando todos los videos en `INPUT_FOLDER` han sido procesados en el ciclo
actual, se inicia un nuevo ciclo y todos vuelven a estar disponibles
(generando clips nuevos de fuentes ya procesadas). Dentro de un ciclo,
el siguiente pick es el más nuevo NO procesado (mtime DESC), por lo que
el material recién añadido siempre salta la cola.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

from ..config import Config
from ..utils.ffmpeg import ffprobe_duracion
from ..utils.logging import log
from .state import cargar_estado, guardar_estado, sha256_archivo

EXTENSIONES_VIDEO = frozenset({".mp4", ".mov", ".mkv", ".m4v", ".webm"})


def _listar_candidatos(carpeta: Path) -> list[Path]:
    if not carpeta.exists():
        raise SystemExit(f"INPUT_FOLDER no existe: {carpeta}")
    return [
        p for p in carpeta.iterdir()
        if p.is_file() and p.suffix.lower() in EXTENSIONES_VIDEO
    ]


def _esta_disponible(estado: dict, ruta: Path, inicio_ciclo: str | None) -> bool:
    digest = sha256_archivo(ruta)
    rec = next((r for r in estado["processed"] if r["hash"] == digest), None)
    if rec is None:
        return True
    ultimo = rec.get("last_processed_at")
    if inicio_ciclo is None or ultimo is None:
        return False
    return ultimo < inicio_ciclo


def cmd_pick(cfg: Config, args) -> None:  # noqa: ANN001
    candidatos = _listar_candidatos(cfg.input_folder)
    if not candidatos:
        raise SystemExit(f"no hay videos en {cfg.input_folder}")

    estado = cargar_estado(cfg)
    inicio_ciclo = estado.get("cycle_started_at")
    disponibles = [p for p in candidatos if _esta_disponible(estado, p, inicio_ciclo)]
    nuevo_ciclo = False

    if not disponibles:
        estado["cycle_started_at"] = datetime.now().isoformat(timespec="seconds")
        guardar_estado(cfg, estado)
        inicio_ciclo = estado["cycle_started_at"]
        disponibles = list(candidatos)
        nuevo_ciclo = True

    disponibles.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    elegido = disponibles[0]
    digest = sha256_archivo(elegido)
    rec = next((r for r in estado["processed"] if r["hash"] == digest), None) or {}

    payload = {
        "path": str(elegido),
        "name": elegido.name,
        "size_mb": round(elegido.stat().st_size / 1_000_000, 1),
        "mtime": datetime.fromtimestamp(elegido.stat().st_mtime).isoformat(),
        "duration_s": round(ffprobe_duracion(elegido), 1),
        "previous_cycles_completed": rec.get("cycles_count", 0),
        "remaining_in_cycle": len(disponibles) - 1,
        "cycle_started_at": inicio_ciclo,
        "new_cycle_started": nuevo_ciclo,
    }
    log().info("video elegido: %s (%.1f MB, %.1fs)", elegido.name, payload["size_mb"], payload["duration_s"])
    json.dump(payload, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")


__all__ = ["cmd_pick", "EXTENSIONES_VIDEO"]
