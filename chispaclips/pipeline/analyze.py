"""Subcomando: `analyze` — análisis multimodal con el LLM seleccionado.

Inyecta:
  1. El prompt de análisis en español (con dialecto detectado).
  2. Los aprendizajes previos (HOT.md) si existen.
  3. La transcripción de Whisper.
  4. El video (Gemini nativo) o los frames均匀 extraídos (Claude / OpenAI).

Escribe `clips.json` con los candidatos detectados.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

from ..config import Config
from ..dialectos import resolver_dialecto
from ..llm import get_provider
from ..prompts import construir_prompt_analisis
from ..utils.logging import log
from .state import append_jsonl, carpeta_salida_video, leer_jsonl


def _leer_transcripcion(ruta: Path) -> tuple[str, str, float]:
    """Devuelve (transcripcion_texto, codigo_idioma, confianza)."""
    data = json.loads(ruta.read_text(encoding="utf-8"))
    texto = json.dumps(data, ensure_ascii=False, indent=2)
    idioma = data.get("language", "")
    confianza = float(data.get("language_probability", 0.0))
    return texto, idioma, confianza


def _leer_priors(ruta: Path) -> str:
    if not ruta.exists():
        return ""
    contenido = ruta.read_text(encoding="utf-8").strip()
    return contenido


def cmd_analyze(cfg: Config, args) -> None:  # noqa: ANN001
    video = Path(args.video).resolve()
    if not video.exists():
        raise SystemExit(f"video no encontrado: {video}")

    out_dir = carpeta_salida_video(cfg, video)
    transcript_path = Path(args.transcript).resolve() if args.transcript else out_dir / "transcript.json"
    out_path = Path(args.output).resolve() if args.output else out_dir / "clips.json"

    if not transcript_path.exists():
        raise SystemExit(f"transcripción no encontrada: {transcript_path}")

    transcripcion, codigo_idioma, confianza = _leer_transcripcion(transcript_path)
    idioma_legible, _instruccion, dialecto_bloque = resolver_dialecto(codigo_idioma, confianza)

    priors = _leer_priors(cfg.hot_file)
    if priors:
        log().info("[analizar] inyectando %d caracteres de aprendizajes previos", len(priors))

    prompt = construir_prompt_analisis(
        dialecto_bloque=dialecto_bloque,
        priors_bloque=priors,
        transcripcion=transcripcion,
    )

    proveedor = get_provider(cfg)
    log().info(
        "[analizar] subiendo video con %s · idioma detectado=%s (%s, %.2f)",
        proveedor.nombre, idioma_legible, codigo_idioma, confianza,
    )
    id_archivo = proveedor.subir_archivo(video)
    proveedor.esperar_listo(id_archivo)

    datos = proveedor.generar_json(prompt, id_archivo=id_archivo)
    out_path.write_text(json.dumps(datos, indent=2, ensure_ascii=False), encoding="utf-8")

    n = len(datos.get("clips", []))
    log().info("[analizar] %d candidatos de clip → %s", n, out_path)

    ahora_iso = datetime.now().isoformat(timespec="seconds")
    for c in datos.get("clips", []):
        append_jsonl(cfg.candidate_history, {
            "video_source": video.name,
            "analyzed_at": ahora_iso,
            "clip_id": c.get("id"),
            "start": c.get("start"),
            "end": c.get("end"),
            "duration_s": (
                (c.get("end", 0) - c.get("start", 0))
                if c.get("end") is not None and c.get("start") is not None
                else None
            ),
            "hook_text": c.get("hook_text"),
            "viral_score_gemini": c.get("viral_score"),
            "reason_gemini": c.get("reason"),
            "language": datos.get("language") or codigo_idioma,
            "had_priors": bool(priors),
            "llm_provider": cfg.llm_provider,
        })

    sys.stdout.write(str(out_path) + "\n")


__all__ = ["cmd_analyze"]
