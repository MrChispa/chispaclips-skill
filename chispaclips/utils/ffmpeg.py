"""Helpers para invocar `ffmpeg` y `ffprobe` desde ChispaClips.

Centraliza el patrón de subprocess + captura de errores. Si ffmpeg no está
instalado, los errores se reportan en español claro.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

from .logging import log

ARGS_BASE_FFMPEG = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error"]


def ffmpeg_disponible() -> bool:
    return shutil.which("ffmpeg") is not None


def ffprobe_disponible() -> bool:
    return shutil.which("ffprobe") is not None


def ffmpeg_ejecutar(args: list[str]) -> None:
    """Ejecuta ffmpeg con argumentos extra (sin el binario). Aborta si falla."""
    if not ffmpeg_disponible():
        raise SystemExit(
            "ffmpeg no está instalado. Instálalo con `brew install ffmpeg` "
            "(macOS) o `apt install ffmpeg` (Linux)."
        )
    cmd = [*ARGS_BASE_FFMPEG, *args]
    log().debug("ffmpeg: %s", " ".join(cmd))
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        sys.stderr.write(res.stderr)
        log().error("ffmpeg falló (código %d): %s", res.returncode, " ".join(cmd))
        raise SystemExit(f"ffmpeg falló: {' '.join(cmd)}")


def ffprobe_duracion(video: Path) -> float:
    """Devuelve la duración en segundos del video."""
    if not ffprobe_disponible():
        raise SystemExit("ffprobe no está instalado.")
    res = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(video),
        ],
        capture_output=True, text=True, check=True,
    )
    return float(res.stdout.strip())


def ffprobe_dimensiones(video: Path) -> tuple[int, int]:
    """Devuelve (ancho, alto) del primer stream de video."""
    if not ffprobe_disponible():
        raise SystemExit("ffprobe no está instalado.")
    res = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=width,height",
            "-of", "csv=p=0:s=x",
            str(video),
        ],
        capture_output=True, text=True, check=True,
    )
    w, h = res.stdout.strip().split("x")
    return int(w), int(h)


def extraer_frames(
    video: Path,
    carpeta_destino: Path,
    n_frames: int = 12,
    prefijo: str = "frame",
    extension: str = "jpg",
    calidad: int = 2,
) -> list[Path]:
    """Extrae N frames均匀 distribuidos del video usando `select=not(mod(n\\,K))`.

    Útil para análisis multimodal con Claude (que no procesa video nativo)
    y como respaldo para OpenAI / Gemini si el upload del video falla.

    Returns: lista de paths a los frames generados, ordenados cronológicamente.
    """
    carpeta_destino.mkdir(parents=True, exist_ok=True)
    duracion = ffprobe_duracion(video)
    if duracion <= 0:
        raise ValueError(f"el video {video} tiene duración {duracion}s, no se puede extraer frames")

    filtro = f"select='not(mod(n\\,max(1\\,floor(N)))')',setpts=N/(TB*FR)"
    plantilla = carpeta_destino / f"{prefijo}_%03d.{extension}"

    ffmpeg_ejecutar([
        "-i", str(video),
        "-vf", f"fps={n_frames}/{duracion:.3f},scale=720:-1",
        "-frames:v", str(n_frames),
        "-q:v", str(calidad),
        str(plantilla),
    ])

    frames = sorted(carpeta_destino.glob(f"{prefijo}_*.{extension}"))
    log().info(
        "se extrajeron %d/%d frames de %s a %s",
        len(frames), n_frames, video.name, carpeta_destino.name,
    )
    return frames


__all__ = [
    "ffmpeg_ejecutar",
    "ffmpeg_disponible",
    "ffprobe_disponible",
    "ffprobe_duracion",
    "ffprobe_dimensiones",
    "extraer_frames",
]
