"""Subcomando: `learn` — refresca `learnings/HOT.md` con analíticas reales.

Flujo:
1. Lee `post-history.jsonl`.
2. Filtra por ventana de maduración (`--soak-days` y `--max-age-days`).
3. Para cada clip, consulta `/api/uploadposts/post-analytics/{request_id}`.
4. Calcula score compuesto (0.6·vistas + 0.4·tasa_engagement).
5. Marca top 20% y bottom 20%.
6. Pide al LLM que actualice `HOT.md` con los patrones validados.
7. Guarda auditoría completa en `learnings/runs/learn-YYYY-MM-DD.md`.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime

from ..config import Config
from ..llm import get_provider
from ..prompts import META_PROMPT_APRENDIZAJE
from ..utils.http import sesion_global
from ..utils.logging import log
from .state import (
    append_jsonl,
    comprimir_jsonl_si_grande,
    leer_jsonl_auto,
)

UPLOAD_POST_BASE = "https://api.upload-post.com/api"


def _metricas_post(plataformas: dict) -> dict:
    total_vistas = 0
    total_eng = 0
    por_plataforma: dict[str, dict] = {}
    for plataforma, datos in (plataformas or {}).items():
        m = (datos or {}).get("post_metrics") or {}
        vistas = int(m.get("views") or m.get("impressions") or m.get("reach") or 0)
        likes = int(m.get("likes") or 0)
        comentarios = int(m.get("comments") or 0)
        compartidos = int(m.get("shares") or 0)
        guardados = int(m.get("saves") or 0)
        eng = likes + comentarios + compartidos + guardados
        total_vistas += vistas
        total_eng += eng
        por_plataforma[plataforma] = {
            "views": vistas, "likes": likes, "comments": comentarios,
            "shares": compartidos, "saves": guardados, "engagement": eng,
        }
    tasa = total_eng / total_vistas if total_vistas else 0.0
    return {
        "total_views": total_vistas,
        "total_engagement": total_eng,
        "engagement_rate": tasa,
        "per_platform": por_plataforma,
    }


def _zscore(valores: list[float]) -> list[float]:
    if not valores:
        return []
    n = len(valores)
    media = sum(valores) / n
    var = sum((v - media) ** 2 for v in valores) / n
    sd = var ** 0.5
    if sd == 0:
        return [0.0] * n
    return [(v - media) / sd for v in valores]


def _renderizar_clip(c: dict) -> str:
    m = c["metrics"]
    return json.dumps({
        "hook_text": c.get("hook_text"),
        "duration_s": c.get("duration_s"),
        "viral_score_gemini": c.get("viral_score_gemini"),
        "reason_gemini": c.get("reason_gemini"),
        "platforms": c.get("platforms"),
        "video_source": c.get("video_source"),
        "metrics": {
            "total_views": m["total_views"],
            "total_engagement": m["total_engagement"],
            "engagement_rate": round(m["engagement_rate"], 4),
            "per_platform": m["per_platform"],
        },
        "composite_score": round(c["composite"], 3),
    }, ensure_ascii=False)


def cmd_learn(cfg: Config, args) -> None:  # noqa: ANN001
    if not cfg.upload_post_api_key:
        raise SystemExit("UPLOAD_POST_API_KEY no está configurada en .env")
    if not cfg.llm_api_key:
        raise SystemExit("la API key del proveedor LLM no está configurada en .env")

    historial = leer_jsonl_auto(cfg.post_history)
    if not historial:
        raise SystemExit(
            "post-history.jsonl está vacío. Publica algunos clips antes de ejecutar learn."
        )

    ahora = datetime.now()
    segundos_soak = args.soak_days * 86400
    segundos_max = args.max_age_days * 86400
    elegibles: list[dict] = []
    for h in historial:
        try:
            pub = datetime.fromisoformat(h["published_at"])
        except (KeyError, ValueError):
            continue
        edad = (ahora - pub).total_seconds()
        if segundos_soak <= edad <= segundos_max:
            elegibles.append(h)

    log().info(
        "[aprender] %d clips en ventana de maduración (%d–%d días)",
        len(elegibles), args.soak_days, args.max_age_days,
    )
    if not elegibles:
        raise SystemExit(
            "no hay clips en la ventana de maduración. "
            "Espera más tiempo o usa --soak-days menor."
        )

    sesion = sesion_global()
    enriquecido: list[dict] = []
    for h in elegibles:
        rid = h.get("request_id")
        if not rid:
            continue
        url = f"{UPLOAD_POST_BASE}/uploadposts/post-analytics/{rid}"
        try:
            resp = sesion.get(url, headers={"Authorization": f"Apikey {cfg.upload_post_api_key}"})
        except Exception as exc:  # noqa: BLE001
            log().error("[aprender] %s: error HTTP %s", rid, exc)
            continue
        if resp.status_code >= 400:
            log().warning("[aprender] %s: HTTP %d: %s", rid, resp.status_code, resp.text[:200])
            continue
        cuerpo = resp.json()
        append_jsonl(cfg.metrics_file, {
            "fetched_at": ahora.isoformat(timespec="seconds"),
            "request_id": rid,
            "raw": cuerpo,
        })
        m = _metricas_post(cuerpo.get("platforms") or {})
        enriquecido.append({**h, "metrics": m})

    if len(enriquecido) < 5:
        msg = (
            f"solo {len(enriquecido)} clips tienen analíticas — "
            f"se necesitan ≥5 ganadores + ≥5 perdedores, reintenta más tarde"
        )
        log().warning("[aprender] %s", msg)
        ruta_run = cfg.runs_folder / f"learn-{ahora.strftime('%Y-%m-%d')}.md"
        ruta_run.parent.mkdir(parents=True, exist_ok=True)
        ruta_run.write_text(f"# Learn run — {ahora.date()}\n\n{msg}\n", encoding="utf-8")
        return

    vistas = [c["metrics"]["total_views"] for c in enriquecido]
    engs = [c["metrics"]["engagement_rate"] for c in enriquecido]
    z_vistas = _zscore(vistas)
    z_engs = _zscore(engs)
    for i, c in enumerate(enriquecido):
        c["composite"] = args.weight_views * z_vistas[i] + args.weight_engagement * z_engs[i]

    enriquecido.sort(key=lambda c: c["composite"], reverse=True)
    n = len(enriquecido)
    top_n = max(5, int(n * args.top_pct))
    bot_n = max(5, int(n * args.bottom_pct))
    ganadores = enriquecido[:top_n]
    perdedores = enriquecido[-bot_n:]

    ganadores_txt = "\n".join(_renderizar_clip(c) for c in ganadores)
    perdedores_txt = "\n".join(_renderizar_clip(c) for c in perdedores)
    hot_actual = cfg.hot_file.read_text(encoding="utf-8") if cfg.hot_file.exists() else ""

    prompt = (
        META_PROMPT_APRENDIZAJE
        + "\n\n## HOT.md ACTUAL\n"
        + (hot_actual or "(vacío — primera ejecución)")
        + f"\n\n## GANADORES (top {len(ganadores)} de {n})\n"
        + ganadores_txt
        + f"\n\n## PERDEDORES (bottom {len(perdedores)} de {n})\n"
        + perdedores_txt
    )

    proveedor = get_provider(cfg)
    log().info(
        "[aprender] llamando a %s con %d ganadores + %d perdedores…",
        proveedor.nombre, len(ganadores), len(perdedores),
    )
    nuevo_hot = proveedor.generar_texto(prompt, max_tokens=4096)

    if cfg.hot_file.exists():
        backup = cfg.learnings_folder / f"HOT.{ahora.strftime('%Y%m%d-%H%M%S')}.md.bak"
        backup.write_text(cfg.hot_file.read_text(encoding="utf-8"), encoding="utf-8")
    cfg.learnings_folder.mkdir(parents=True, exist_ok=True)
    cfg.hot_file.write_text(nuevo_hot + "\n", encoding="utf-8")

    ruta_run = cfg.runs_folder / f"learn-{ahora.strftime('%Y-%m-%d')}.md"
    ruta_run.parent.mkdir(parents=True, exist_ok=True)
    auditoria = [
        f"# Learn run — {ahora.isoformat(timespec='seconds')}",
        "",
        f"- proveedor: {proveedor.nombre} ({cfg.llm_model})",
        f"- maduración: {args.soak_days}d / máx edad: {args.max_age_days}d",
        f"- pesos: vistas={args.weight_views} engagement={args.weight_engagement}",
        f"- cohorte: {n} clips con analítica",
        f"- ganadores ({len(ganadores)}):",
    ]
    for w in ganadores:
        auditoria.append(
            f"  - score={w['composite']:.2f}  vistas={w['metrics']['total_views']}  "
            f"tasa_eng={w['metrics']['engagement_rate']:.4f}  hook=\"{w.get('hook_text')}\""
        )
    auditoria.append(f"- perdedores ({len(perdedores)}):")
    for l in perdedores:
        auditoria.append(
            f"  - score={l['composite']:.2f}  vistas={l['metrics']['total_views']}  "
            f"tasa_eng={l['metrics']['engagement_rate']:.4f}  hook=\"{l.get('hook_text')}\""
        )
    auditoria.append("")
    auditoria.append("## Nuevo HOT.md")
    auditoria.append("")
    auditoria.append(nuevo_hot)
    ruta_run.write_text("\n".join(auditoria), encoding="utf-8")
    log().info(
        "[aprender] HOT.md actualizado (%d caracteres), auditoría → %s",
        len(nuevo_hot), ruta_run,
    )

    comprimir_jsonl_si_grande(cfg.metrics_file, umbral_mb=10.0)
    json.dump(
        {"hot_chars": len(nuevo_hot), "audit": str(ruta_run), "winners": len(ganadores), "losers": len(perdedores)},
        sys.stdout, indent=2, ensure_ascii=False,
    )
    sys.stdout.write("\n")


__all__ = ["cmd_learn"]
