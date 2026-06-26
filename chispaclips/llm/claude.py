"""Proveedor LLM: Anthropic Claude (multimodal vía frames extraídos).

Claude no procesa video nativo. Para analizar un video, primero extraemos
N frames均匀 distribuidos con ffmpeg y los enviamos como array de
imágenes junto al prompt. `subir_archivo` aquí hace el trabajo de extracción
y devuelve la lista de paths como un identificador serializado.
"""

from __future__ import annotations

import base64
import json
import re
from pathlib import Path

from ..utils.ffmpeg import extraer_frames
from ..utils.logging import log
from .base import LLMProvider

_SEPARADOR = "::"


class ClaudeProvider(LLMProvider):
    nombre = "claude"

    def __init__(self, modelo: str, api_key: str, n_frames: int = 12) -> None:
        super().__init__(modelo=modelo, api_key=api_key)
        try:
            from anthropic import Anthropic
        except ImportError as exc:
            raise ImportError(
                "El proveedor Claude requiere `pip install anthropic`."
            ) from exc
        self._cliente = Anthropic(api_key=api_key)
        self.n_frames = n_frames

    def subir_archivo(self, ruta: Path) -> str:
        carpeta_frames = ruta.parent / f"frames_{ruta.stem}"
        frames = extraer_frames(
            ruta, carpeta_frames, n_frames=self.n_frames, prefijo="frame"
        )
        if not frames:
            raise RuntimeError(
                f"no se pudieron extraer frames de {ruta} para Claude"
            )
        return _SEPARADOR.join(str(f) for f in frames)

    def esperar_listo(self, id_archivo: str, timeout_s: int = 300) -> None:
        return None

    def _imagenes_a_bloques(self, id_archivo: str) -> list[dict]:
        paths = [Path(p) for p in id_archivo.split(_SEPARADOR) if p]
        bloques: list[dict] = []
        for p in paths:
            data = base64.standard_b64encode(p.read_bytes()).decode("ascii")
            bloques.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/jpeg",
                    "data": data,
                },
            })
        return bloques

    def _llamar(
        self,
        prompt: str,
        *,
        id_archivo: str | None,
        max_tokens: int,
        temperatura: float,
    ) -> str:
        contenido: list[dict] = []
        if id_archivo:
            contenido.extend(self._imagenes_a_bloques(id_archivo))
        contenido.append({"type": "text", "text": prompt})

        log().info("[analizar] llamando a Claude %s…", self.modelo)
        resp = self._cliente.messages.create(
            model=self.modelo,
            max_tokens=max_tokens,
            temperature=temperatura,
            messages=[{"role": "user", "content": contenido}],
        )
        partes = [b.text for b in resp.content if getattr(b, "type", None) == "text"]
        return "\n".join(partes).strip()

    def _extraer_json(self, texto: str) -> dict:
        texto = texto.strip()
        try:
            return json.loads(texto)
        except json.JSONDecodeError:
            match = re.search(r"\{[\s\S]*\}", texto)
            if not match:
                raise ValueError(
                    f"Claude no devolvió JSON parseable: {texto[:200]!r}…"
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
        )


__all__ = ["ClaudeProvider"]
