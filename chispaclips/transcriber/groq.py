"""Proveedor de transcripción: Groq API (Whisper large-v3 en la nube).

Groq ofrece una API compatible con el formato de OpenAI para
`/audio/transcriptions`. Es **extremadamente rápida** (un video de
10 minutos se transcribe en ~10 segundos vs ~5 minutos de Whisper
local en CPU).

Trade-offs:
  - El audio se envía a los servidores de Groq (no es privado).
  - Límite de 25 MB por archivo — extraemos el audio a MP3 mono
    64 kbps antes de enviar, lo que típicamente reduce el tamaño
    50-100× vs el video.
  - Tier gratuito generoso en https://console.groq.com/.

API: https://console.groq.com/docs/speech-text
"""

from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path

from ..utils.ffmpeg import ffmpeg_ejecutar
from ..utils.http import sesion_global
from ..utils.logging import log
from .base import Transcriber

URL_GROQ_TRANSCRIPTIONS = "https://api.groq.com/openai/v1/audio/transcriptions"
_TAMANO_MAXIMO_BYTES = 25 * 1024 * 1024  # 25 MB


class GroqTranscriber(Transcriber):
    nombre = "groq"

    def __init__(self, modelo: str, api_key: str, idioma: str = "") -> None:
        super().__init__(modelo=modelo, idioma=idioma)
        if not api_key:
            raise ValueError(
                "GROQ_API_KEY está vacía. Consigue una gratis en "
                "https://console.groq.com/ y añádela a `.env`."
            )
        self.api_key = api_key

    def _extraer_audio_comprimido(self, ruta_video: Path) -> Path:
        """Extrae la pista de audio a MP3 mono 64 kbps en un archivo temporal.

        Típicamente reduce 50-100× el tamaño del video original, manteniendo
        calidad suficiente para Whisper large-v3.
        """
        tmp = Path(tempfile.mkstemp(suffix=".mp3", prefix="chispaclips_audio_")[1])
        log().debug("[transcribir] extrayendo audio a MP3 temporal: %s", tmp.name)
        ffmpeg_ejecutar([
            "-i", str(ruta_video),
            "-vn",
            "-ac", "1",
            "-ar", "16000",
            "-b:a", "64k",
            "-f", "mp3",
            str(tmp),
        ])
        return tmp

    def transcribir(self, ruta_video: Path) -> dict:
        archivo_a_enviar = ruta_video
        tmp_audio: Path | None = None

        if ruta_video.stat().st_size > _TAMANO_MAXIMO_BYTES:
            log().info(
                "[transcribir] video > 25 MB, extrayendo audio comprimido para Groq…"
            )
            tmp_audio = self._extraer_audio_comprimido(ruta_video)
            archivo_a_enviar = tmp_audio
            log().info(
                "[transcribir] audio extraído: %.2f MB (de %.2f MB)",
                tmp_audio.stat().st_size / 1_000_000,
                ruta_video.stat().st_size / 1_000_000,
            )

        try:
            log().info(
                "[transcribir] Groq API · modelo=%s · idioma=%s",
                self.modelo, self.idioma or "auto",
            )
            with archivo_a_enviar.open("rb") as fh:
                archivos = {
                    "file": (archivo_a_enviar.name, fh, "audio/mpeg"),
                }
                datos: dict = {
                    "model": self.modelo,
                    "response_format": "verbose_json",
                    "timestamp_granularities[]": "segment",
                    "timestamp_granularities[]": "word",
                }
                if self.idioma:
                    datos["language"] = self.idioma

                resp = sesion_global().post(
                    URL_GROQ_TRANSCRIPTIONS,
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    files=archivos,
                    data=datos,
                    timeout=600,
                )

            if resp.status_code >= 400:
                raise RuntimeError(
                    f"Groq devolvió HTTP {resp.status_code}: {resp.text[:300]}"
                )

            cuerpo = resp.json()
        finally:
            if tmp_audio is not None:
                try:
                    tmp_audio.unlink()
                except OSError:
                    pass

        return _normalizar_respuesta_groq(cuerpo, ruta_video)


def _normalizar_respuesta_groq(cuerpo: dict, ruta_video: Path) -> dict:
    """Convierte la respuesta JSON de Groq al formato estándar ChispaClips."""
    language = cuerpo.get("language", "es")
    language_probability = float(cuerpo.get("language_probability", 0.0) or 0.0)
    duration = float(cuerpo.get("duration", 0.0) or 0.0)

    segmentos_raw = cuerpo.get("segments") or []
    palabras_por_segmento: dict[int, list[dict]] = {}
    for w in cuerpo.get("words") or []:
        idx = int(w.get("segment_id", 0))
        palabras_por_segmento.setdefault(idx, []).append({
            "s": round(float(w.get("start", 0.0)), 3),
            "e": round(float(w.get("end", 0.0)), 3),
            "t": str(w.get("word", "")).strip(),
        })

    segmentos: list[dict] = []
    for i, seg in enumerate(segmentos_raw):
        texto = str(seg.get("text", "")).strip()
        if not texto and i not in palabras_por_segmento:
            continue
        segmentos.append({
            "start": round(float(seg.get("start", 0.0)), 3),
            "end": round(float(seg.get("end", 0.0)), 3),
            "text": texto,
            "words": palabras_por_segmento.get(i, []),
        })

    return {
        "video": ruta_video.name,
        "language": language,
        "language_probability": round(language_probability, 3),
        "duration": round(duration, 3),
        "segments": segmentos,
    }


__all__ = ["GroqTranscriber", "URL_GROQ_TRANSCRIPTIONS"]
