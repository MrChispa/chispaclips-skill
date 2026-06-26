"""Subcomando: `hook` — superpone el texto gancho sobre el clip.

Renderiza el texto a un PNG transparente con Pillow (auto word-wrap + pildora
negra estilo TikTok) y lo compone con ffmpeg `overlay`. Se coloca en la parte
superior durante los primeros N segundos. El PNG temporal se borra al final.
"""

from __future__ import annotations

import sys
from pathlib import Path

from ..config import Config
from ..utils.ffmpeg import ffmpeg_ejecutar, ffprobe_dimensiones

FUENTE_POR_DEFECTO = "/System/Library/Fonts/Supplemental/Impact.ttf"
FUENTES_FALLBACK = (
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
)


def _resolver_fuente(ruta: str | None) -> str:
    if ruta and Path(ruta).exists():
        return ruta
    for candidata in FUENTES_FALLBACK:
        if Path(candidata).exists():
            return candidata
    return ruta or FUENTE_POR_DEFECTO


def _renderizar_hook_png(
    texto: str,
    ruta_png: Path,
    ancho_video: int,
    ruta_fuente: str,
    tamano_fuente: int = 72,
    max_ratio: float = 0.85,
) -> None:
    from PIL import Image, ImageDraw, ImageFont

    fuente = ImageFont.truetype(ruta_fuente, tamano_fuente)
    max_w = int(ancho_video * max_ratio)

    pad_x = 26
    pad_y = 10
    separacion = 10
    max_w_texto = max_w - pad_x * 2

    palabras = texto.split()
    lineas: list[str] = []
    actual: list[str] = []
    for p in palabras:
        candidata = " ".join(actual + [p])
        bbox = fuente.getbbox(candidata)
        if (bbox[2] - bbox[0]) > max_w_texto and actual:
            lineas.append(" ".join(actual))
            actual = [p]
        else:
            actual.append(p)
    if actual:
        lineas.append(" ".join(actual))

    ascent, descent = fuente.getmetrics()
    alto_linea = ascent + descent
    alto_pildora = alto_linea + pad_y * 2
    margen_externo = 12
    alto_total = alto_pildora * len(lineas) + separacion * (len(lineas) - 1) + margen_externo * 2

    img = Image.new("RGBA", (ancho_video, alto_total), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    color_pildora = (0, 0, 0, 200)

    for i, linea in enumerate(lineas):
        bbox = fuente.getbbox(linea)
        ancho_linea = bbox[2] - bbox[0]

        x_texto = (ancho_video - ancho_linea) // 2
        top_pildora = margen_externo + i * (alto_pildora + separacion)
        y_texto = top_pildora + pad_y

        x0 = x_texto - pad_x
        y0 = top_pildora
        x1 = x_texto + ancho_linea + pad_x
        y1 = top_pildora + alto_pildora
        radio = min(24, alto_pildora // 3)
        draw.rounded_rectangle((x0, y0, x1, y1), radius=radio, fill=color_pildora)

        draw.text(
            (x_texto, y_texto), linea, font=fuente,
            fill=(255, 255, 255, 255),
            stroke_width=3, stroke_fill=(0, 0, 0, 255),
        )

    img.save(ruta_png, "PNG")


def cmd_hook(cfg: Config, args) -> None:  # noqa: ANN001
    video = Path(args.video).resolve()
    if not video.exists():
        raise SystemExit(f"video no encontrado: {video}")

    salida = Path(args.output).resolve()
    salida.parent.mkdir(parents=True, exist_ok=True)

    fuente = _resolver_fuente(args.font)
    if not Path(fuente).exists():
        raise SystemExit(
            f"fuente no encontrada: {fuente}. "
            "Instala DejaVu Sans o pasa --font con una ruta válida."
        )

    duracion = float(args.duration)
    ancho, _alto = ffprobe_dimensiones(video)
    png = salida.with_suffix(".hook.png")

    _renderizar_hook_png(args.text, png, ancho, fuente)

    filtro = f"[0:v][1:v]overlay=0:H*0.08:enable='lte(t,{duracion})'"
    ffmpeg_ejecutar([
        "-i", str(video),
        "-i", str(png),
        "-filter_complex", filtro,
        "-c:v", "libx264", "-preset", "fast", "-crf", "20",
        "-c:a", "copy",
        "-movflags", "+faststart",
        str(salida),
    ])
    png.unlink(missing_ok=True)
    sys.stdout.write(str(salida) + "\n")


__all__ = ["cmd_hook", "FUENTE_POR_DEFECTO"]
