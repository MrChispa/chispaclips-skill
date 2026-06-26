"""Subcomando: `mark-processed` — marca un video como consumido."""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

from ..config import Config
from ..utils.logging import log
from .state import cargar_estado, guardar_estado, sha256_archivo


def cmd_mark_processed(cfg: Config, args) -> None:  # noqa: ANN001
    video = Path(args.video).resolve()
    if not video.exists():
        raise SystemExit(f"video no encontrado: {video}")

    estado = cargar_estado(cfg)
    digest = sha256_archivo(video)
    ahora = datetime.now().isoformat(timespec="seconds")

    if estado.get("cycle_started_at") is None:
        estado["cycle_started_at"] = ahora

    existente = next((r for r in estado["processed"] if r["hash"] == digest), None)
    if existente:
        existente["last_processed_at"] = ahora
        existente["cycles_count"] = existente.get("cycles_count", 1) + 1
        existente.setdefault("history", []).append({
            "processed_at": ahora,
            "clips_generated": args.clips_generated,
            "clips_published": args.clips_published,
        })
        existente["clips_generated"] = args.clips_generated
        existente["clips_published"] = args.clips_published
        ciclo_n = existente["cycles_count"]
    else:
        rec = {
            "path": str(video),
            "name": video.name,
            "hash": digest,
            "first_processed_at": ahora,
            "last_processed_at": ahora,
            "cycles_count": 1,
            "clips_generated": args.clips_generated,
            "clips_published": args.clips_published,
            "history": [{
                "processed_at": ahora,
                "clips_generated": args.clips_generated,
                "clips_published": args.clips_published,
            }],
        }
        estado["processed"].append(rec)
        ciclo_n = 1

    guardar_estado(cfg, estado)
    log().info("marcado: %s (ciclo #%d, generados=%d, publicados=%d)",
               video.name, ciclo_n, args.clips_generated, args.clips_published)
    sys.stdout.write(json.dumps({"marked": True, "cycle": ciclo_n}, ensure_ascii=False) + "\n")


__all__ = ["cmd_mark_processed"]
