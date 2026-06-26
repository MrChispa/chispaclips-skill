"""Subcomando: `reflect` — extrae patrones cualitativos de aprobación del creador.

Compara candidatos ofrecidos vs. aprobados en una ventana de días. Pide al LLM
que extraiga 3-8 observaciones sobre las preferencias del creador. El output
NO se promueve automáticamente a HOT.md (queda en `runs/` para revisión).
"""

from __future__ import annotations

import json
import sys
from datetime import datetime

from ..config import Config
from ..llm import get_provider
from ..prompts import META_PROMPT_REFLEXION
from ..utils.logging import log
from .state import leer_jsonl


def _recortar(c: dict) -> dict:
    return {
        "hook": c.get("hook_text"),
        "duration_s": c.get("duration_s"),
        "viral_score_gemini": c.get("viral_score_gemini"),
        "reason_gemini": c.get("reason_gemini"),
        "language": c.get("language"),
    }


def cmd_reflect(cfg: Config, args) -> None:  # noqa: ANN001
    if not cfg.llm_api_key:
        raise SystemExit("la API key del proveedor LLM no está configurada en .env")

    candidatos = leer_jsonl(cfg.candidate_history)
    posts = leer_jsonl(cfg.post_history)
    if not candidatos:
        raise SystemExit(
            "candidate-history.jsonl está vacío. Ejecuta `analyze` en al menos un video primero."
        )
    if not posts:
        raise SystemExit(
            "post-history.jsonl está vacío. Publica algunos clips antes de ejecutar reflect."
        )

    corte = datetime.now().timestamp() - args.window_days * 86400
    candidatos_recientes: list[dict] = []
    for c in candidatos:
        try:
            ts = datetime.fromisoformat(c["analyzed_at"]).timestamp()
        except (KeyError, ValueError):
            continue
        if ts >= corte:
            candidatos_recientes.append(c)

    aprobados_claves: set[tuple[str | None, str | None]] = set()
    for p in posts:
        try:
            ts = datetime.fromisoformat(p["published_at"]).timestamp()
        except (KeyError, ValueError):
            continue
        if ts >= corte:
            aprobados_claves.add((p.get("video_source"), p.get("hook_text")))

    aprobados: list[dict] = []
    rechazados: list[dict] = []
    for c in candidatos_recientes:
        clave = (c.get("video_source"), c.get("hook_text"))
        if clave in aprobados_claves:
            aprobados.append(c)
        else:
            rechazados.append(c)

    if not aprobados or not rechazados:
        raise SystemExit(
            f"se necesitan candidatos aprobados y rechazados en la ventana; "
            f"hay {len(aprobados)} aprobados, {len(rechazados)} rechazados."
        )

    prompt = (
        META_PROMPT_REFLEXION
        + "\n\n## OFRECIDOS\n" + json.dumps([_recortar(c) for c in candidatos_recientes], ensure_ascii=False, indent=2)
        + "\n\n## APROBADOS\n" + json.dumps([_recortar(c) for c in aprobados], ensure_ascii=False, indent=2)
        + "\n\n## RECHAZADOS\n" + json.dumps([_recortar(c) for c in rechazados], ensure_ascii=False, indent=2)
    )

    proveedor = get_provider(cfg)
    log().info(
        "[reflexionar] %d aprobados + %d rechazados, llamando a %s…",
        len(aprobados), len(rechazados), proveedor.nombre,
    )
    datos = proveedor.generar_json(prompt, max_tokens=2048)

    ahora = datetime.now()
    ruta_run = cfg.runs_folder / f"reflect-{ahora.strftime('%Y-%m-%d-%H%M')}.md"
    ruta_run.parent.mkdir(parents=True, exist_ok=True)
    lineas = [
        f"# Reflect run — {ahora.isoformat(timespec='seconds')}",
        "",
        f"- ventana: últimos {args.window_days} días",
        f"- aprobados: {len(aprobados)} / rechazados: {len(rechazados)}",
        f"- proveedor: {proveedor.nombre}",
        "",
        "## Observaciones (NO se promueven automáticamente a HOT.md — revisa y curada manualmente)",
        "",
    ]
    for o in datos.get("observations", []):
        lineas.append(f"- **{o.get('rule')}** — {o.get('evidence')}")
    ruta_run.write_text("\n".join(lineas) + "\n", encoding="utf-8")
    log().info(
        "[reflexionar] %d observaciones → %s",
        len(datos.get("observations", [])), ruta_run,
    )
    json.dump(datos, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")


__all__ = ["cmd_reflect"]
