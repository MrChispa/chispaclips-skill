"""Pipeline diario de ChispaClips (BrainMatic).

Cada submódulo implementa UN subcomando CLI y devuelve JSON serializable
a stdout. La skill nunca imprime texto libre a stdout (solo paths/JSON)
para que el agente orquestador pueda parsearlo de forma determinista.
"""

from .state import (
    cargar_estado,
    guardar_estado,
    sha256_archivo,
    slug_video,
    carpeta_salida_video,
    append_jsonl,
    leer_jsonl,
    leer_jsonl_auto,
    comprimir_jsonl_si_grande,
)
from .pick import cmd_pick
from .transcribe import cmd_transcribe
from .analyze import cmd_analyze
from .extract import cmd_extract
from .hook import cmd_hook
from .preview import cmd_preview
from .publish import cmd_publish
from .mark_processed import cmd_mark_processed
from .list_processed import cmd_list_processed
from .learn import cmd_learn
from .reflect import cmd_reflect

__all__ = [
    "cargar_estado",
    "guardar_estado",
    "sha256_archivo",
    "slug_video",
    "carpeta_salida_video",
    "append_jsonl",
    "leer_jsonl",
    "leer_jsonl_auto",
    "comprimir_jsonl_si_grande",
    "cmd_pick",
    "cmd_transcribe",
    "cmd_analyze",
    "cmd_extract",
    "cmd_hook",
    "cmd_preview",
    "cmd_publish",
    "cmd_mark_processed",
    "cmd_list_processed",
    "cmd_learn",
    "cmd_reflect",
]
