"""Abstracción Multi-LLM para ChispaClips (BrainMatic).

ChispaClips es agnóstico del proveedor LLM. La skill soporta:

  - **Gemini** (`google-genai`): multimodal nativo, sube video vía Files API.
  - **Claude** (`anthropic`): requiere extraer frames del video (no procesa
    video nativo) y los envía como array de imágenes.
  - **OpenAI / OpenRouter / OpenCode** (cliente `openai` con `base_url`):
    multimodal nativo (gpt-4o+) o compatible con cualquier API OpenAI-spec.

El proveedor se selecciona con `LLM_PROVIDOR` en `.env`.
"""

from __future__ import annotations

from .base import LLMProvider
from .factory import get_provider, listar_proveedores

__all__ = ["LLMProvider", "get_provider", "listar_proveedores"]
