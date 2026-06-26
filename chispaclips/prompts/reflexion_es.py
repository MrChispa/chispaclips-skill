"""Meta-prompt para `reflect` (patrones cualitativos de aprobación) — ChispaClips.

Diferencia con `learn`: aquí no hay métricas de engagement. Solo comparamos
qué ofreció el LLM vs. qué aprobó el humano. Sirve para descubrir
preferencias de estilo del creador (ej: "aprueba ganchos con números,
rechaza los que son preguntas").
"""

META_PROMPT_REFLEXION = """Estás observando cómo un creador filtra manualmente \
los candidatos de clips cortos generados por IA, ANTES de que existan datos \
de engagement.

Verás:
1. Los candidatos que el sistema OFRECIÓ (gancho + duración + viral_score \
de Gemini + razón).
2. Los candidatos que el creador APROBÓ (subconjunto que terminó publicado).
3. Los candidatos que el creador RECHAZÓ (ofrecidos pero no publicados).

TU TRABAJO
Identifica patrones cualitativos que expliquen el filtro del creador. \
Ejemplos: "aprueba ganchos que contienen un número", "rechaza ganchos en \
forma de pregunta", "aprueba clips de menos de 30 s", "rechaza temas sobre X".

RESTRICCIONES
- Devuelve entre 3 y 8 observaciones cortas.
- Cada observación: regla + evidencia \
("aprobó 4 de 5 ganchos con números, rechazó 0 de 3 ganchos pregunta").
- No extrapoles a engagement: no tienes métricas. Esto es puramente \
preferencia del creador.
- Escribe en el idioma dominante de los ganchos candidatos.

SALIDA
Devuelve JSON estricto (sin markdown, sin comentarios):
{{"observations": [{{"rule": "...", "evidence": "..."}}, ...]}}
"""


__all__ = ["META_PROMPT_REFLEXION"]
