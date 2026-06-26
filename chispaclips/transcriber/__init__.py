"""Abstracción de proveedores de transcripción (Whisper local / Groq API).

ChispaClips soporta dos formas de transcribir un video:

  - **Whisper local** (`faster-whisper`): corre en tu CPU, sin enviar audio
    a la nube. La primera vez descarga el modelo (~1.5 GB para `medium`).
    Ideal para: privacidad, trabajo offline, costos cero.

  - **Groq API** (`whisper-large-v3` en sus servidores): transcripción en
    la nube extremadamente rápida (un video de 10 min en ~10 segundos vs
    ~5 min de Whisper local). Requiere `GROQ_API_KEY` (tier gratuito
    generoso: https://console.groq.com/). Límite de 25 MB por archivo
    (se extrae el audio a MP3 antes de enviar).

Ambos transcridores devuelven el mismo formato estándar de ChispaClips
para `transcript.json` (segmentos con marcas por palabra), así el resto
del pipeline no nota la diferencia.
"""

from .base import Transcriber
from .factory import get_transcriber, listar_transcridores

__all__ = ["Transcriber", "get_transcriber", "listar_transcridores"]
