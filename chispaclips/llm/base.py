"""Interfaz abstracta para proveedores LLM multimodales."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


class LLMProvider(ABC):
    """Contrato común para Gemini / Claude / OpenAI-compat.

    El identificador devuelto por `subir_archivo` es opaco (lo gestiona cada
    proveedor internamente) y se reusa en `generar_json` / `generar_texto`.
    """

    nombre: str

    def __init__(self, modelo: str, api_key: str) -> None:
        if not api_key:
            raise ValueError(
                f"API key vacía para proveedor {self.nombre!r}. "
                "Revisa las variables de entorno en `.env`."
            )
        self.modelo = modelo
        self.api_key = api_key

    @abstractmethod
    def subir_archivo(self, ruta: Path) -> str:
        """Sube un archivo (video o imagen) y devuelve un ID interno."""

    @abstractmethod
    def esperar_listo(self, id_archivo: str, timeout_s: int = 300) -> None:
        """Bloquea hasta que el archivo esté listo para ser consultado.

        Para Gemini: poll de PROCESSING → ACTIVE.
        Para Claude / OpenAI: no-op (los frames se suben inline en el prompt).
        """

    @abstractmethod
    def generar_json(
        self,
        prompt: str,
        *,
        id_archivo: str | None = None,
        max_tokens: int = 8192,
        temperatura: float = 0.7,
    ) -> dict:
        """Llama al modelo y parsea la respuesta como JSON (dict)."""

    @abstractmethod
    def generar_texto(
        self,
        prompt: str,
        *,
        max_tokens: int = 4096,
        temperatura: float = 0.7,
    ) -> str:
        """Llama al modelo y devuelve texto plano (para HOT.md / reflect)."""

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} modelo={self.modelo!r}>"


__all__ = ["LLMProvider"]
