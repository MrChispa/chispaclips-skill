"""Factoría de proveedores LLM para ChispaClips."""

from __future__ import annotations

from ..config import Config
from ..utils.logging import log
from .base import LLMProvider
from .claude import ClaudeProvider
from .gemini import GeminiProvider
from .openai_compat import OpenAICompatProvider


_PROVEEDORES_DISPONIBLES = ("gemini", "claude", "openai")


def listar_proveedores() -> tuple[str, ...]:
    return _PROVEEDORES_DISPONIBLES


def get_provider(cfg: Config) -> LLMProvider:
    """Construye el proveedor adecuado según `cfg.llm_provider`."""
    log().info("inicializando proveedor LLM: %s (%s)", cfg.llm_provider, cfg.llm_model)

    if cfg.llm_provider == "gemini":
        return GeminiProvider(modelo=cfg.gemini_model, api_key=cfg.llm_api_key)

    if cfg.llm_provider == "claude":
        return ClaudeProvider(
            modelo=cfg.claude_model,
            api_key=cfg.llm_api_key,
            n_frames=cfg.claude_video_frames,
        )

    if cfg.llm_provider == "openai":
        return OpenAICompatProvider(
            modelo=cfg.openai_model,
            api_key=cfg.llm_api_key,
            base_url=cfg.openai_base_url,
            n_frames=cfg.claude_video_frames,
        )

    raise ValueError(
        f"proveedor LLM no soportado: {cfg.llm_provider!r}. "
        f"Opciones: {', '.join(_PROVEEDORES_DISPONIBLES)}"
    )


__all__ = ["get_provider", "listar_proveedores"]
