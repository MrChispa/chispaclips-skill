"""Carga de configuración desde variables de entorno (`.env`)."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

from . import __version__

PAQUETE_ROOT = Path(__file__).resolve().parent.parent
CARPETA_RUNTIME = PAQUETE_ROOT / ".chispaclips"

LLM_PROVEEDORES_VALIDOS = frozenset({"gemini", "claude", "openai"})
TRANSCRIBER_PROVEEDORES_VALIDOS = frozenset({"whisper", "groq"})


def cargar_env(archivo: Path | None = None) -> None:
    """Carga `.env` desde la raíz del repositorio. Idempotente."""
    candidato = archivo or (PAQUETE_ROOT / ".env")
    if candidato.exists():
        load_dotenv(candidato, override=False)


@dataclass(slots=True)
class Config:
    """Configuración consolidada de ChispaClips.

    Todos los campos tienen valores por defecto sensatos. Los secretos
    (`*_API_KEY`) deben establecerse en el archivo `.env`.
    """

    llm_provider: str = "gemini"
    llm_model: str = "gemini-3-flash-preview"
    llm_api_key: str = ""

    upload_post_api_key: str = ""
    upload_post_profile: str = ""

    input_folder: Path = field(default_factory=lambda: CARPETA_RUNTIME / "input")
    output_folder: Path = field(default_factory=lambda: CARPETA_RUNTIME / "output")
    state_folder: Path = field(default_factory=lambda: CARPETA_RUNTIME / "state")
    learnings_folder: Path = field(default_factory=lambda: CARPETA_RUNTIME / "learnings")

    whisper_model: str = "medium"
    whisper_language: str = ""

    transcriber_provider: str = "whisper"
    groq_api_key: str = ""
    groq_whisper_model: str = "whisper-large-v3"

    timezone: str = "America/Bogota"

    claude_video_frames: int = 12

    openai_base_url: str = "https://api.openai.com/v1"

    @property
    def state_file(self) -> Path:
        return self.state_folder / "processed.json"

    @property
    def hot_file(self) -> Path:
        return self.learnings_folder / "HOT.md"

    @property
    def post_history(self) -> Path:
        return self.learnings_folder / "post-history.jsonl"

    @property
    def candidate_history(self) -> Path:
        return self.learnings_folder / "candidate-history.jsonl"

    @property
    def metrics_file(self) -> Path:
        return self.learnings_folder / "metrics.jsonl"

    @property
    def runs_folder(self) -> Path:
        return self.learnings_folder / "runs"

    @property
    def insights_folder(self) -> Path:
        return self.learnings_folder / "insights"

    @property
    def openai_model(self) -> str:
        return self.llm_model

    @property
    def claude_model(self) -> str:
        return self.llm_model

    @property
    def gemini_model(self) -> str:
        return self.llm_model


def cargar_config() -> Config:
    """Lee `.env` y devuelve una instancia inmutable-lógica de `Config`."""
    cargar_env()

    provider = (os.getenv("LLM_PROVIDER", "gemini") or "gemini").strip().lower()
    if provider not in LLM_PROVEEDORES_VALIDOS:
        raise SystemExit(
            f"LLM_PROVIDOR inválido: {provider!r}. "
            f"Opciones válidas: {', '.join(sorted(LLM_PROVEEDORES_VALIDOS))}."
        )

    transcriber = (os.getenv("TRANSCRIBER_PROVIDER", "whisper") or "whisper").strip().lower()
    if transcriber not in TRANSCRIBER_PROVEEDORES_VALIDOS:
        raise SystemExit(
            f"TRANSCRIBER_PROVIDER inválido: {transcriber!r}. "
            f"Opciones válidas: {', '.join(sorted(TRANSCRIBER_PROVEEDORES_VALIDOS))}."
        )

    api_key = ""
    if provider == "gemini":
        api_key = os.getenv("GEMINI_API_KEY", "").strip()
        model = os.getenv("GEMINI_MODEL", "gemini-3-flash-preview").strip()
    elif provider == "claude":
        api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
        model = os.getenv("CLAUDE_MODEL", "claude-3-5-sonnet-latest").strip()
    else:  # openai
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip()

    def _path(var: str, default: Path) -> Path:
        raw = os.getenv(var, "").strip()
        if not raw:
            return default
        return Path(raw).expanduser()

    return Config(
        llm_provider=provider,
        llm_model=model,
        llm_api_key=api_key,
        upload_post_api_key=os.getenv("UPLOAD_POST_API_KEY", "").strip(),
        upload_post_profile=os.getenv("UPLOAD_POST_PROFILE", "").strip(),
        input_folder=_path("INPUT_FOLDER", CARPETA_RUNTIME / "input"),
        output_folder=_path("OUTPUT_FOLDER", CARPETA_RUNTIME / "output"),
        state_folder=_path("STATE_FOLDER", CARPETA_RUNTIME / "state"),
        learnings_folder=_path("LEARNINGS_FOLDER", CARPETA_RUNTIME / "learnings"),
        whisper_model=os.getenv("WHISPER_MODEL", "medium").strip() or "medium",
        whisper_language=os.getenv("WHISPER_LANGUAGE", "").strip(),
        transcriber_provider=transcriber,
        groq_api_key=os.getenv("GROQ_API_KEY", "").strip(),
        groq_whisper_model=(
            os.getenv("GROQ_WHISPER_MODEL", "whisper-large-v3").strip()
            or "whisper-large-v3"
        ),
        timezone=os.getenv("TIMEZONE", "America/Bogota").strip() or "America/Bogota",
        claude_video_frames=int(os.getenv("CLAUDE_VIDEO_FRAMES", "12") or "12"),
        openai_base_url=(
            os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").strip()
            or "https://api.openai.com/v1"
        ),
    )


def validar_para_pipeline(cfg: Config) -> list[str]:
    """Devuelve la lista de claves faltantes o vacías (no aborta).

    El agente puede usar esta lista para pedirle al usuario solo lo que falta,
    sin tener que conocer todos los campos.
    """
    faltan: list[str] = []
    if not cfg.llm_api_key:
        faltan.append(f"API key del proveedor LLM ({cfg.llm_provider.upper()})")
    if cfg.transcriber_provider == "groq" and not cfg.groq_api_key:
        faltan.append("GROQ_API_KEY (transcriber configurado como 'groq')")
    if not cfg.upload_post_api_key:
        faltan.append("UPLOAD_POST_API_KEY")
    if not cfg.upload_post_profile:
        faltan.append("UPLOAD_POST_PROFILE")
    return faltan


def info_version() -> str:
    return f"ChispaClips v{__version__} · BrainMatic"
