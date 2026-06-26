"""CLI principal de ChispaClips (BrainMatic).

Se invoca como:

    python -m chispaclips <subcomando> [args]
    chispaclips <subcomando> [args]            (tras `pip install -e .`)
    python chispaclips.py <subcomando> [args]  (shim retrocompatible)

Subcomandos: pick, transcribe, analyze, extract, hook, preview, publish,
mark-processed, list-processed, learn, reflect.
"""

from __future__ import annotations

import argparse
import sys

from . import __version__
from .config import cargar_config
from .pipeline import (
    cmd_analyze,
    cmd_extract,
    cmd_hook,
    cmd_learn,
    cmd_list_processed,
    cmd_mark_processed,
    cmd_pick,
    cmd_preview,
    cmd_publish,
    cmd_reflect,
    cmd_transcribe,
)
from .utils.logging import configurar_logging


def _construir_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="chispaclips",
        description="ChispaClips — pipeline diario de clips virales (BrainMatic).",
    )
    parser.add_argument(
        "--version", action="version",
        version=f"ChispaClips v{__version__} · BrainMatic",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="activa logging a nivel DEBUG",
    )
    sub = parser.add_subparsers(dest="cmd", required=True, metavar="<subcomando>")

    sub.add_parser("pick", help="elige el siguiente video a procesar (ciclo más reciente)").set_defaults(func=cmd_pick)

    t = sub.add_parser("transcribe", help="transcribe un video con Whisper (palabra por palabra)")
    t.add_argument("video", help="ruta absoluta al video largo")
    t.add_argument("--model", default=None, help="modelo Whisper (override de WHISPER_MODEL)")
    t.add_argument("--output", default=None, help="ruta de salida del transcript.json")
    t.set_defaults(func=cmd_transcribe)

    a = sub.add_parser("analyze", help="analiza el video con el LLM configurado y escribe clips.json")
    a.add_argument("video", help="ruta absoluta al video largo")
    a.add_argument("--transcript", default=None, help="ruta al transcript.json (default: <salida>/transcript.json)")
    a.add_argument("--output", default=None, help="ruta de salida del clips.json")
    a.set_defaults(func=cmd_analyze)

    e = sub.add_parser("extract", help="corta un clip con ffmpeg (frame-accurate)")
    e.add_argument("video")
    e.add_argument("--start", required=True, help="segundos de inicio")
    e.add_argument("--end", required=True, help="segundos de fin")
    e.add_argument("--output", required=True, help="ruta del clip resultante")
    e.set_defaults(func=cmd_extract)

    h = sub.add_parser("hook", help="superpone el texto gancho sobre un clip")
    h.add_argument("video", help="ruta al clip cortado")
    h.add_argument("--text", required=True, help="texto del gancho (en el dialecto del video)")
    h.add_argument("--duration", default="3", help="segundos que el gancho permanece en pantalla")
    h.add_argument("--font", default=None, help="ruta a la fuente TTF (opcional)")
    h.add_argument("--output", required=True, help="ruta del clip final con gancho")
    h.set_defaults(func=cmd_hook)

    pv = sub.add_parser("preview", help="extrae un frame para QA visual del gancho")
    pv.add_argument("video", help="ruta al clip_<ID>_final.mp4")
    pv.add_argument("--at-time", type=float, default=1.0, help="timestamp dentro de la ventana del gancho")
    pv.add_argument("--output", default=None, help="ruta del PNG resultante")
    pv.set_defaults(func=cmd_preview)

    pub = sub.add_parser("publish", help="publica un clip en TikTok / Instagram / YouTube via Upload-Post")
    pub.add_argument("video")
    pub.add_argument("--platforms", required=True, help="separadas por coma: tiktok,instagram,youtube")
    pub.add_argument("--title", default="")
    pub.add_argument("--description", default="")
    pub.add_argument("--tiktok-title", default=None)
    pub.add_argument("--instagram-title", default=None)
    pub.add_argument("--youtube-title", default=None)
    pub.add_argument("--schedule", default=None, help="ISO-8601, ej. 2026-06-01T10:00:00")
    pub.add_argument("--timezone", default=None, help="default: TIMEZONE en .env")
    pub.add_argument("--add-to-queue", action="store_true")
    pub.add_argument("--tiktok-mode", choices=["draft", "direct"], default="draft")
    pub.add_argument("--tiktok-privacy", default="PUBLIC_TO_EVERYONE")
    pub.add_argument("--dry-run", action="store_true")
    pub.add_argument("--clip-id", type=int, default=None, help="para el loop de aprendizaje")
    pub.add_argument("--hook-text", default=None, help="para el loop de aprendizaje")
    pub.add_argument("--viral-score", type=int, default=None, help="para el loop de aprendizaje")
    pub.add_argument("--reason", default=None, help="para el loop de aprendizaje")
    pub.add_argument("--video-source", default=None, help="nombre del video original (para aprendizaje)")
    pub.set_defaults(func=cmd_publish)

    m = sub.add_parser("mark-processed", help="marca un video como consumido (lo salta el próximo pick)")
    m.add_argument("video")
    m.add_argument("--clips-generated", type=int, default=0)
    m.add_argument("--clips-published", type=int, default=0)
    m.set_defaults(func=cmd_mark_processed)

    sub.add_parser("list-processed", help="lista el estado de videos procesados").set_defaults(func=cmd_list_processed)

    lrn = sub.add_parser("learn", help="semanal: refresca HOT.md con analíticas reales")
    lrn.add_argument("--soak-days", type=int, default=7, help="ignorar clips más jóvenes que esto")
    lrn.add_argument("--max-age-days", type=int, default=90, help="ignorar clips más viejos que esto")
    lrn.add_argument("--top-pct", type=float, default=0.20)
    lrn.add_argument("--bottom-pct", type=float, default=0.20)
    lrn.add_argument("--weight-views", type=float, default=0.6)
    lrn.add_argument("--weight-engagement", type=float, default=0.4)
    lrn.set_defaults(func=cmd_learn)

    ref = sub.add_parser("reflect", help="opcional: extrae patrones cualitativos de aprobación del creador")
    ref.add_argument("--window-days", type=int, default=30, help="ventana de búsqueda hacia atrás")
    ref.set_defaults(func=cmd_reflect)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _construir_parser()
    args = parser.parse_args(argv)
    configurar_logging()

    cfg = cargar_config()
    args.func(cfg, args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
