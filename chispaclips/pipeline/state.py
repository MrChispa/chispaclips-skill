"""Estado y utilidades de archivos compartidas — ChispaClips (BrainMatic)."""

from __future__ import annotations

import gzip
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

from ..config import Config
from ..utils.logging import log


def sha256_archivo(ruta: Path) -> str:
    h = hashlib.sha256()
    with ruta.open("rb") as fh:
        for bloque in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(bloque)
    return h.hexdigest()


def cargar_estado(cfg: Config) -> dict[str, Any]:
    """Carga `state/processed.json`. Backfill de campos faltantes."""
    ruta = cfg.state_file
    if not ruta.exists():
        return {"cycle_started_at": None, "processed": []}
    estado = json.loads(ruta.read_text(encoding="utf-8"))
    estado.setdefault("cycle_started_at", None)
    estado.setdefault("processed", [])
    for rec in estado["processed"]:
        rec.setdefault("last_processed_at", rec.get("processed_at"))
        rec.setdefault("first_processed_at", rec.get("processed_at"))
        rec.setdefault("cycles_count", 1)
        rec.setdefault("clips_generated", 0)
        rec.setdefault("clips_published", 0)
    return estado


def guardar_estado(cfg: Config, estado: dict[str, Any]) -> None:
    cfg.state_folder.mkdir(parents=True, exist_ok=True)
    cfg.state_file.write_text(
        json.dumps(estado, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    log().debug("estado guardado: %d videos procesados", len(estado["processed"]))


def slug_video(video: Path) -> str:
    return video.stem.replace(" ", "_")


def carpeta_salida_video(cfg: Config, video: Path) -> Path:
    d = cfg.output_folder / slug_video(video)
    d.mkdir(parents=True, exist_ok=True)
    return d


def append_jsonl(ruta: Path, registro: dict[str, Any]) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with ruta.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(registro, ensure_ascii=False) + "\n")


def leer_jsonl(ruta: Path) -> list[dict[str, Any]]:
    if not ruta.exists():
        return []
    salida: list[dict[str, Any]] = []
    with ruta.open(encoding="utf-8") as fh:
        for linea in fh:
            linea = linea.strip()
            if linea:
                salida.append(json.loads(linea))
    return salida


def comprimir_jsonl_si_grande(ruta: Path, umbral_mb: float = 10.0) -> None:
    """Comprime `ruta` con gzip si supera el umbral y la versión `.gz` no existe.

    Se llama desde `learn` para no acumular MB históricos.
    """
    if not ruta.exists():
        return
    if ruta.with_suffix(ruta.suffix + ".gz").exists():
        return
    tamano_mb = ruta.stat().st_size / (1024 * 1024)
    if tamano_mb < umbral_mb:
        return
    destino = ruta.with_suffix(ruta.suffix + ".gz")
    with ruta.open("rb") as origen, gzip.open(destino, "wb") as salida:
        shutil.copyfileobj(origen, salida)
    ruta.unlink()
    log().info("comprimido: %s → %s (%.1f MB)", ruta.name, destino.name, tamano_mb)


def leer_jsonl_auto(ruta: Path) -> list[dict[str, Any]]:
    """Lee un .jsonl aunque esté gzip-comprimido (sufijo `.gz`)."""
    if not ruta.exists():
        return []
    if ruta.suffix == ".gz":
        with gzip.open(ruta, "rt", encoding="utf-8") as fh:
            return [json.loads(linea) for linea in fh if linea.strip()]
    return leer_jsonl(ruta)


__all__ = [
    "sha256_archivo",
    "cargar_estado",
    "guardar_estado",
    "slug_video",
    "carpeta_salida_video",
    "append_jsonl",
    "leer_jsonl",
    "leer_jsonl_auto",
    "comprimir_jsonl_si_grande",
]
