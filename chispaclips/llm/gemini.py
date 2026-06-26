"""Proveedor LLM: Google Gemini (multimodal nativo vía Files API)."""

from __future__ import annotations

import json
import time
from pathlib import Path

from ..utils.logging import log
from .base import LLMProvider

_CACHE_ARCHIVOS: dict[str, str] = {}


class GeminiProvider(LLMProvider):
    nombre = "gemini"

    def __init__(self, modelo: str, api_key: str) -> None:
        super().__init__(modelo=modelo, api_key=api_key)
        from google import genai

        self._cliente = genai.Client(api_key=api_key)

    def subir_archivo(self, ruta: Path) -> str:
        digest = _hash_archivo(ruta)
        if digest in _CACHE_ARCHIVOS:
            cached = _CACHE_ARCHIVOS[digest]
            log().info(
                "[analizar] reutilizando subida cacheada de %s (sha256=%s…)",
                ruta.name, digest[:10],
            )
            return cached

        log().info("[analizar] subiendo %s a Gemini Files API…", ruta.name)
        subido = self._cliente.files.upload(file=str(ruta))

        inicio = time.monotonic()
        while subido.state.name == "PROCESSING":
            if time.monotonic() - inicio > 300:
                raise TimeoutError(
                    f"Gemini Files API tardó más de 300s en procesar {ruta.name}"
                )
            time.sleep(3)
            subido = self._cliente.files.get(name=subido.name)
            log().info("[analizar] estado del archivo: %s", subido.state.name)

        if subido.state.name != "ACTIVE":
            raise RuntimeError(
                f"subida del video a Gemini falló: estado={subido.state.name}"
            )

        _CACHE_ARCHIVOS[digest] = subido.name
        return subido.name

    def esperar_listo(self, id_archivo: str, timeout_s: int = 300) -> None:
        inicio = time.monotonic()
        while True:
            obj = self._cliente.files.get(name=id_archivo)
            if obj.state.name == "ACTIVE":
                return
            if obj.state.name == "FAILED":
                raise RuntimeError(f"archivo Gemini falló: {id_archivo}")
            if time.monotonic() - inicio > timeout_s:
                raise TimeoutError("timeout esperando archivo Gemini")
            time.sleep(3)

    def generar_json(
        self,
        prompt: str,
        *,
        id_archivo: str | None = None,
        max_tokens: int = 8192,
        temperatura: float = 0.7,
    ) -> dict:
        from google.genai import types

        contenido: list = [prompt]
        if id_archivo:
            contenido.insert(0, self._cliente.files.get(name=id_archivo))

        log().info("[analizar] llamando a Gemini %s…", self.modelo)
        resp = self._cliente.models.generate_content(
            model=self.modelo,
            contents=contenido,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                max_output_tokens=max_tokens,
                temperature=temperatura,
            ),
        )
        texto = (resp.text or "").strip()
        try:
            return json.loads(texto)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Gemini devolvió contenido no-JSON: {texto[:200]!r}…"
            ) from exc

    def generar_texto(
        self,
        prompt: str,
        *,
        max_tokens: int = 4096,
        temperatura: float = 0.7,
    ) -> str:
        from google.genai import types

        log().info("[analizar] llamando a Gemini %s (texto)…", self.modelo)
        resp = self._cliente.models.generate_content(
            model=self.modelo,
            contents=[prompt],
            config=types.GenerateContentConfig(
                response_mime_type="text/plain",
                max_output_tokens=max_tokens,
                temperature=temperatura,
            ),
        )
        return (resp.text or "").strip()


def _hash_archivo(ruta: Path) -> str:
    import hashlib

    h = hashlib.sha256()
    with ruta.open("rb") as fh:
        for bloque in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(bloque)
    return h.hexdigest()


__all__ = ["GeminiProvider"]
