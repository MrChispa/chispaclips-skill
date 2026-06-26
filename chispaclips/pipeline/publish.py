"""Subcomando: `publish` — publica un clip en TikTok / Instagram / YouTube.

Sube el video a Upload-Post con los textos por plataforma. Registra el
publicación en `post-history.jsonl` para que `learn` pueda correlacionar
métricas con el contexto del clip (gancho, score, video fuente).
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

from ..config import Config
from ..utils.ffmpeg import ffprobe_duracion
from ..utils.http import sesion_global
from ..utils.logging import log
from .state import append_jsonl

UPLOAD_POST_BASE = "https://api.upload-post.com/api"


def _datos_publicacion(args) -> list[tuple[str, str]]:  # noqa: ANN001
    plataformas = [p.strip() for p in args.platforms.split(",") if p.strip()]
    campos: list[tuple[str, str]] = [
        ("user", args.upload_post_profile or ""),
        ("title", args.title or ""),
        ("description", args.description or ""),
    ]
    for p in plataformas:
        campos.append(("platform[]", p))
    if args.tiktok_title:
        campos.append(("tiktok_title", args.tiktok_title))
    if args.instagram_title:
        campos.append(("instagram_title", args.instagram_title))
    if args.youtube_title:
        campos.append(("youtube_title", args.youtube_title))
    if "tiktok" in plataformas:
        post_mode = "MEDIA_UPLOAD" if args.tiktok_mode == "draft" else "DIRECT_POST"
        campos.append(("post_mode", post_mode))
        if args.tiktok_privacy:
            campos.append(("privacy_level", args.tiktok_privacy))
    if args.schedule:
        campos.append(("scheduled_date", args.schedule))
        campos.append(("timezone", args.timezone or "America/Bogota"))
    elif args.add_to_queue:
        campos.append(("add_to_queue", "true"))
    return campos


def cmd_publish(cfg: Config, args) -> None:  # noqa: ANN001
    api_key = cfg.upload_post_api_key
    profile = cfg.upload_post_profile
    if not api_key or not profile:
        raise SystemExit(
            "UPLOAD_POST_API_KEY o UPLOAD_POST_PROFILE faltan en .env. "
            "Consíguelas en https://app.upload-post.com"
        )

    video = Path(args.video).resolve()
    if not video.exists():
        raise SystemExit(f"video no encontrado: {video}")

    plataformas = [p.strip() for p in args.platforms.split(",") if p.strip()]
    campos = _datos_publicacion(args)
    args.upload_post_profile = profile  # para que _datos_publicacion use el de .env

    if args.dry_run:
        json.dump({
            "DRY_RUN": True,
            "endpoint": f"{UPLOAD_POST_BASE}/upload",
            "video": str(video),
            "fields": campos,
        }, sys.stdout, indent=2, ensure_ascii=False)
        sys.stdout.write("\n")
        return

    log().info("[publicar] subiendo %s a %d plataforma(s)…", video.name, len(plataformas))
    sesion = sesion_global()
    with video.open("rb") as fh:
        archivos = {"video": (video.name, fh, "video/mp4")}
        resp = sesion.post(
            f"{UPLOAD_POST_BASE}/upload",
            headers={"Authorization": f"Apikey {api_key}"},
            data=campos,
            files=archivos,
        )

    if resp.status_code >= 400:
        sys.stderr.write(resp.text + "\n")
        log().error("Upload-Post devolvió HTTP %d", resp.status_code)
        raise SystemExit(f"upload-post HTTP {resp.status_code}")

    cuerpo = resp.json()
    request_id = cuerpo.get("request_id")
    if request_id:
        append_jsonl(cfg.post_history, {
            "request_id": request_id,
            "job_id": cuerpo.get("job_id"),
            "video_source": args.video_source,
            "clip_id": args.clip_id,
            "hook_text": args.hook_text,
            "viral_score_gemini": args.viral_score,
            "reason_gemini": args.reason,
            "duration_s": ffprobe_duracion(video) if video.exists() else None,
            "platforms": plataformas,
            "tiktok_title": args.tiktok_title,
            "instagram_title": args.instagram_title,
            "youtube_title": args.youtube_title,
            "general_title": args.title,
            "tiktok_mode": args.tiktok_mode if "tiktok" in plataformas else None,
            "scheduled_date": args.schedule,
            "published_at": datetime.now().isoformat(timespec="seconds"),
            "clip_file": str(video),
            "llm_provider": cfg.llm_provider,
        })
        log().info("[publicar] OK · request_id=%s", request_id)
    else:
        log().warning("[publicar] respuesta sin request_id: %s", json.dumps(cuerpo)[:200])

    json.dump(cuerpo, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")


__all__ = ["cmd_publish", "UPLOAD_POST_BASE"]
