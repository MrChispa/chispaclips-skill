"""Proveedor LLM: OpenAI / OpenRouter / OpenCode (API OpenAI-compatible).

Soporta cualquier endpoint compatible con la spec de OpenAI:

  - OpenAI nativo: `https://api.openai.com/v1`
  - OpenRouter:    `https://openrouter.ai/api/v1` (acceso a 200+ modelos)
  - OpenCode:      `http://localhost:8080/v1` (proxy local)
  - Cualquier proxy que implemente `/chat/completions` con multimodal

Para video, este proveedor:
  1. Si el modelo es gpt-4o / gpt-4o-mini / vision-capable → sube el video
     directamente como `video_url` (en `input` con detalle) o como URI base64.
  2. Como fallback robusto → extrae frames均匀 con ffmpeg y los envía como
     array de imágenes.
"""

from __future__ import annotations

import base64
import json
import re
from pathlib import Path

from ..config import Config
from ..utils.ffmpeg import extraer_frames, ffprobe_duracion
from ..utils.logging import log
from .base import LLMProvider

_SEPARADOR = "::"
_TAMANO_MAXIMO_VIDEO_BYTES = 20 * 1024 * 1024  # 20 MB para subida inline


class OpenAICompatProvider(LLMProvider):
    nombre = "openai"

    def __init__(self, modelo: str, api_key: str, base_url: str, n_frames: int = 12) -> None:
        super().__init__(modelo=modelo, api_key=api_key)
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise ImportError(
                "El proveedor OpenAI requiere `pip install openai`."
            ) from exc
        self._cliente = OpenAI(api_key=api_key, base_url=base_url)
        self.base_url = base_url
        self.n_frames = n_frames

    def subir_archivo(self, ruta: Path) -> str:
        if ruta.stat().st_size <= _TAMANO_MAXIMO_VIDEO_BYTES and self._soporta_video_url():
            return f"video::{ruta}"
        carpeta_frames = ruta.parent / f"frames_{ruta.stem}"
        frames = extraer_frames(
            ruta, carpeta_frames, n_frames=self.n_frames, prefijo="frame"
        )
        if not frames:
            raise RuntimeError(
                f"no se pudieron extraer frames de {ruta} para {self.nombre}"
            )
        return _SEPARADOR.join(str(f) for f in frames)

    def esperar_listo(self, id_archivo: str, timeout_s: int = 300) -> None:
        return None

    def _soporta_video_url(self) -> bool:
        modelo_lc = self.modelo.lower()
        return any(
            token in modelo_lc
            for token in ("gpt-4o", "gpt-4-vision", "o1", "gemini", "claude", "qwen-vl")
        )

    def _contenido_desde_id(self, id_archivo: str) -> list[dict]:
        if id_archivo.startswith("video::"):
            ruta = Path(id_archivo.removeprefix("video::"))
            data = base64.standard_b64encode(ruta.read_bytes()).decode("ascii")
            mime = "video/mp4" if ruta.suffix.lower() == ".mp4" else "video/webm"
            return [{
                "type": "video_url",
                "video_url": {"url": f"data:{mime};base64,{data}"},
            }]
        paths = [Path(p) for p in id_archivo.split(_SEPARADOR) if p]
        bloques: list[dict] = []
        for p in paths:
            data = base64.standard_b64encode(p.read_bytes()).decode("ascii")
            bloques.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{data}"},
            })
        return bloques

    def _llamar(
        self,
        prompt: str,
        *,
        id_archivo: str | None,
        max_tokens: int,
        temperatura: float,
        json_mode: bool,
    ) -> str:
        contenido: list[dict] = []
        if id_archivo:
            contenido.extend(self._contenido_desde_id(id_archivo))
        contenido.append({"type": "text", "text": prompt})

        kwargs: dict = {
            "model": self.modelo,
            "messages": [{"role": "user", "content": contenido}],
            "max_tokens": max_tokens,
            "temperature": temperatura,
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        log().info("[analizar] llamando a %s %s…", self.nombre, self.modelo)
        resp = self._cliente.chat.completions.create(**kwargs)
        return (resp.choices[0].message.content or "").strip()

    def _extraer_json(self, texto: str) -> dict:
        texto = texto.strip()
        try:
            return json.loads(texto)
        except json.JSONDecodeError:
            match = re.search(r"\{[\s\S]*\}", texto)
            if not match:
                raise ValueError(
                    f"{self.nombre} no devolvió JSON parseable: {texto[:200]!r}…"
                )
            return json.loads(match.group(0))

    def generar_json(
        self,
        prompt: str,
        *,
        id_archivo: str | None = None,
        max_tokens: int = 8192,
        temperatura: float = 0.7,
    ) -> dict:
        prompt_con_formato = (
            prompt.rstrip()
            + "\n\nDevuelve ÚNICAMENTE JSON válido. Sin texto antes ni después. "
            "Sin bloques de markdown. Solo el objeto JSON crudo."
        )
        texto = self._llamar(
            prompt_con_formato,
            id_archivo=id_archivo,
            max_tokens=max_tokens,
            temperatura=temperatura,
            json_mode=True,
        )
        return self._extraer_json(texto)

    def generar_texto(
        self,
        prompt: str,
        *,
        max_tokens: int = 4096,
        temperatura: float = 0.7,
    ) -> str:
        return self._llamar(
            prompt,
            id_archivo=None,
            max_tokens=max_tokens,
            temperatura=temperatura,
            json_mode=False,
        )


__all__ = ["OpenAICompatProvider"]
