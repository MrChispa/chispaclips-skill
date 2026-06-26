"""Mapeo de dialectos detectado por Whisper → instrucción para el LLM.

Whisper normalmente devuelve solo códigos ISO-639-1 (`es`, `en`, `pt`...).
Algunos modelos extendidos (WhisperX, whisper-cpp con `--language` o
`whisper-large-v3` ajustado) pueden devolver variantes regionales
(`es-MX`, `es-AR`, `es-CO`, etc.). Esta tabla normaliza ambos casos.

Si Whisper devuelve algo fuera de la tabla, caemos en "español neutro"
o el idioma más cercano.
"""

from __future__ import annotations

DIALECTOS: dict[str, tuple[str, str]] = {
    # código_whisper -> (idioma_legible, instrucción_dialecto)
    "es": (
        "español",
        "español neutro, comprensible en toda Latinoamérica y España. "
        "Evita regionalismos extremos; prefiere frases universales.",
    ),
    "es-ES": (
        "español de España",
        "español de España: usa 'vosotros', 'vale', 'tío/tía', "
        "registro coloquial peninsular.",
    ),
    "es-MX": (
        "español mexicano",
        "español mexicano: usa 'güey', 'neta', 'chido', '¡qué padre!'. "
        "Tuteo estándar. Registro relajado y directo.",
    ),
    "es-AR": (
        "español rioplatense",
        "español rioplatense: usa 'che', 'boludo/a', 're copado', 'flashero'. "
        "Voseo ('vos tenés', 'vos hacés').",
    ),
    "es-CO": (
        "español colombiano",
        "español colombiano: usa 'parce', 'chimba', 'bacano', '¡qué nota!'. "
        "Tuteo estándar. Tono cálido.",
    ),
    "es-CL": (
        "español chileno",
        "español chileno: usa 'cachai', 'po', 'weón/wea', 'lucas'. "
        "Voseo. Registro muy coloquial.",
    ),
    "es-PE": (
        "español peruano",
        "español peruano: usa 'pata', 'chamba', 'habla', '¡ya pues!'. "
        "Tuteo estándar.",
    ),
    "es-VE": (
        "español venezolano",
        "español venezolano: usa 'pana', 'chevere', 'arrecho (bueno)', "
        "'¡qué loco!'. Tuteo estándar.",
    ),
    "es-EC": (
        "español ecuatoriano",
        "español ecuatoriano: usa 'ñaño/ñaña', 'chulla', '¡bacán!'. "
        "Voseo en la sierra.",
    ),
    "es-UY": (
        "español uruguayo",
        "español uruguayo: similar al rioplatense. 'Che', 'bo', 'ta'. "
        "Voseo.",
    ),
    "en": (
        "inglés",
        "inglés estándar, comprensible globalmente.",
    ),
    "en-US": (
        "inglés americano",
        "inglés americano: registro directo, contracciones coloquiales.",
    ),
    "en-GB": (
        "inglés británico",
        "inglés británico: registro algo más formal, 'mate', 'bloody'.",
    ),
    "pt": (
        "portugués",
        "portugués neutro, comprensible en Brasil y Portugal.",
    ),
    "pt-BR": (
        "portugués brasileño",
        "portugués brasileño: registro coloquial, 'mano', 'tipo', 'véi'.",
    ),
    "pt-PT": (
        "portugués europeo",
        "portugués europeo: registro más formal, 'fixe', 'giro'.",
    ),
    "fr": (
        "francés",
        "francés estándar.",
    ),
    "it": (
        "italiano",
        "italiano estándar.",
    ),
    "de": (
        "alemán",
        "alemán estándar.",
    ),
}


def resolver_dialecto(
    codigo_whisper: str,
    confianza: float = 0.0,
) -> tuple[str, str, str]:
    """Devuelve (idioma_legible, instrucción_dialecto, fragmento_prompt).

    Si el código no está mapeado, intenta con los 2 primeros caracteres
    (ej. `es-AR-XX` → `es-AR`). Si tampoco, usa español neutro.
    """
    codigo = (codigo_whisper or "").strip()
    if not codigo:
        return (
            "español",
            DIALECTOS["es"][1],
            "Idioma: español (no detectado). Adapta al español neutro.",
        )

    if codigo in DIALECTOS:
        idioma, inst = DIALECTOS[codigo]
    elif codigo[:2] in DIALECTOS:
        idioma, inst = DIALECTOS[codigo[:2]]
    else:
        idioma = codigo
        inst = f"idioma detectado: {codigo}. Adapta los ganchos a esa variante."

    fragmento = (
        f"Idioma detectado: {idioma} "
        f"(código Whisper: {codigo}, confianza: {confianza:.2f}).\n"
        f"Dialecto objetivo: {inst}\n"
        f"Audiencia principal: hispanohablantes (o el idioma detectado).\n"
    )
    return idioma, inst, fragmento


__all__ = ["DIALECTOS", "resolver_dialecto"]
