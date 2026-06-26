"""Prompt principal de análisis (Paso 3 del pipeline) — ChispaClips / BrainMatic.

Este prompt se inyecta a Gemini / Claude / OpenAI junto con la transcripción
de Whisper y (opcionalmente) el archivo de video o los frames extraídos.

El campo {dialecto_bloque} se sustituye con la salida de
`chispaclips.dialectos.resolver_dialecto(...)`. El campo {priors_bloque}
se sustituye con el contenido de `learnings/HOT.md` (si existe).
"""

PROMPT_ANALISIS = """Eres un editor experto en video corto viral (Shorts / Reels / TikTok) \
especializado en contenido para audiencia hispanohablante.

DATOS QUE RECIBES
1. Un video largo (o, según el proveedor, una muestra de frames均匀 distribuidos del video).
2. Una transcripción con segmentos a nivel de oración y marcas temporales por palabra.
3. (Opcional) Aprendizajes previos derivados de datos reales de engagement del creador.

{dialecto_bloque}

TAREA
Identifica TODOS los momentos viables para Shorts / Reels / TikTok. \
Sé generoso: devuelve cada candidato viable, no limites artificialmente. \
Calidad sobre relleno, pero no te detengas en 3 si hay 8 buenos.

REQUISITOS
- Duración: 20 a 60 segundos.
- Autocontenido: tiene sentido sin contexto previo. Evita momentos que \
referencien algo no visto ("como dije antes", "volviendo a aquello").
- Gancho (hook) potente en los primeros 2 segundos: sorpresa, controversia, \
pico emocional, remate, opinión contraria, consejo accionable o clímax narrativo.
- `start` DEBE coincidir con el `start` de una palabra existente en la \
transcripción; `end` DEBE coincidir con el `end` de una palabra. NO inventes \
marcas temporales. Ancla a límites de palabra.
- Usa señales multimodales del video: risas, gestos, cambios de escena, \
picos de energía, reacciones, gráficos en pantalla, movimientos de cámara.
- Si dos candidatos se solapan, devuelve solo el más fuerte.
- El gancho debe usar el mismo registro y dialecto que el video, no \
traducciones literales del inglés.

ADAPTACIÓN AL DILECTO
- Adapta los ganchos al dialecto indicado arriba. Usa expresiones, muletillas \
y registros naturales de esa variante. Si el dialecto es "neutro", prefiere \
español comprensible en toda Latinoamérica y España, evitando regionalismos \
extremos.
- El texto del gancho en pantalla DEBE ser del mismo idioma que el video, \
con la misma ortografía y acentuación que usan los hablantes del dialecto \
detectado (por ejemplo, "está" en vez de "esta" si aplica en contexto).

PUNTUACIÓN
- viral_score: entero del 1 al 10, donde 10 es un éxito seguro.
- Razona brevemente: ¿por qué este momento funcionará? \
Considera shock value, re-watchability, shareability, claridad del \
mensaje principal.

PARA CADA CLIP DEVUELVE
- id: entero secuencial empezando en 1.
- start: segundos (flotante, anclado al start de una palabra).
- end: segundos (flotante, anclado al end de una palabra).
- hook_text: máximo 8 palabras, atención inmediata, MISMO IDIOMA que el video.
- reason: una frase corta explicando por qué es viral.
- viral_score: entero 1-10.

SALIDA
Devuelve ÚNICAMENTE JSON estricto, sin comentarios ni bloques markdown:
{{"language": "<código iso>", "clips": [{{"id": 1, "start": 12.34, "end": 45.67, \
"hook_text": "...", "reason": "...", "viral_score": 8}}, ...]}}
"""

ENCABEZADO_PRIORS = """

APRENDIZAJES PREVIOS DE CLIPS PUBLICADOS POR ESTE CREADOR
Los patrones de abajo están derivados de datos reales de engagement de clips \
anteriormente publicados por este creador. Aplícalos tanto al SELECCIONAR \
los momentos como al ESCRIBIR los ganchos. Cuando entren en conflicto con las \
recomendaciones genéricas de arriba, los aprendizajes prevalecen.

"""

PIE_PRIORS = "\n\n--- fin de aprendizajes previos ---\n\nTRANSCRIPCIÓN\n"

ENCABEZADO_TRANSCRIPCION = "\nTRANSCRIPCIÓN\n"


def construir_prompt_analisis(
    *,
    dialecto_bloque: str,
    priors_bloque: str = "",
    transcripcion: str = "",
) -> str:
    """Compone el prompt final con el dialecto y los priors inyectados."""
    base = PROMPT_ANALISIS.format(dialecto_bloque=dialecto_bloque)

    if priors_bloque.strip():
        prompt = base + ENCABEZADO_PRIORS + priors_bloque.strip() + PIE_PRIORS + transcripcion
    else:
        prompt = base + ENCABEZADO_TRANSCRIPCION + transcripcion
    return prompt


__all__ = [
    "PROMPT_ANALISIS",
    "ENCABEZADO_PRIORS",
    "PIE_PRIORS",
    "ENCABEZADO_TRANSCRIPCION",
    "construir_prompt_analisis",
]
