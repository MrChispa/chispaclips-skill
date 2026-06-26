"""Prompts del LLM en español para ChispaClips (BrainMatic)."""

from .analisis_es import (
    PROMPT_ANALISIS,
    ENCABEZADO_PRIORS,
    PIE_PRIORS,
    ENCABEZADO_TRANSCRIPCION,
    construir_prompt_analisis,
)
from .aprendizaje_es import META_PROMPT_APRENDIZAJE
from .reflexion_es import META_PROMPT_REFLEXION

__all__ = [
    "PROMPT_ANALISIS",
    "ENCABEZADO_PRIORS",
    "PIE_PRIORS",
    "ENCABEZADO_TRANSCRIPCION",
    "construir_prompt_analisis",
    "META_PROMPT_APRENDIZAJE",
    "META_PROMPT_REFLEXION",
]
