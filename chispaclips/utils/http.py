"""Cliente HTTP con reintentos y backoff exponencial.

ChispaClips hace dos tipos de llamadas:
  1. Upload-Post (REST clásica): 5–10% de fallos en producción por rate-limit.
  2. Gemini Files API / OpenAI / Claude: pueden devolver 429 transitorios.

Este módulo centraliza la lógica de reintentos para evitar copiar/pegar
`for i in range(3): try/except` por todo el código.
"""

from __future__ import annotations

import threading
import time
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .logging import log

_TIMEOUT_POR_DEFECTO = 600
_REINTENTOS_TOTALES = 5
_STATUS_FORZAR_REINTENTO = (429, 500, 502, 503, 504)
_STATUS_NO_REINTENTAR = (400, 401, 403, 404, 422)


class SesionHTTP:
    """Wrapper ligero sobre `requests.Session` con reintentos automáticos."""

    def __init__(
        self,
        *,
        reintentos: int = _REINTENTOS_TOTALES,
        backoff: float = 0.6,
        timeout: int = _TIMEOUT_POR_DEFECTO,
        cabeceras_extras: dict[str, str] | None = None,
    ) -> None:
        self._timeout = timeout
        self._sesion = requests.Session()
        retry = Retry(
            total=reintentos,
            connect=reintentos,
            read=reintentos,
            status=reintentos,
            backoff_factor=backoff,
            backoff_jitter=0.3,
            status_forcelist=list(_STATUS_FORZAR_REINTENTO),
            allowed_methods=frozenset(["GET", "POST", "PUT", "DELETE", "PATCH"]),
            raise_on_status=False,
            respect_retry_after_header=True,
        )
        adapter = HTTPAdapter(max_retries=retry, pool_connections=10, pool_maxsize=10)
        self._sesion.mount("https://", adapter)
        self._sesion.mount("http://", adapter)
        if cabeceras_extras:
            self._sesion.headers.update(cabeceras_extras)

    @property
    def sesion(self) -> requests.Session:
        return self._sesion

    def get(self, url: str, **kwargs: Any) -> requests.Response:
        return self._solicitar("GET", url, **kwargs)

    def post(self, url: str, **kwargs: Any) -> requests.Response:
        return self._solicitar("POST", url, **kwargs)

    def request(self, metodo: str, url: str, **kwargs: Any) -> requests.Response:
        return self._solicitar(metodo, url, **kwargs)

    def _solicitar(self, metodo: str, url: str, **kwargs: Any) -> requests.Response:
        kwargs.setdefault("timeout", self._timeout)
        inicio = time.monotonic()
        log().debug("HTTP %s %s", metodo, url)
        try:
            resp = self._sesion.request(metodo, url, **kwargs)
        except requests.RequestException as exc:
            duracion = time.monotonic() - inicio
            log().error("HTTP %s %s falló en %.1fs: %s", metodo, url, duracion, exc)
            raise

        duracion = time.monotonic() - inicio
        if resp.status_code in _STATUS_NO_REINTENTAR:
            log().warning(
                "HTTP %s %s → %d (no reintentable) en %.2fs",
                metodo, url, resp.status_code, duracion,
            )
        else:
            log().debug("HTTP %s %s → %d en %.2fs", metodo, url, resp.status_code, duracion)
        return resp


_sesion_global_lock = threading.Lock()
_sesion_global_instancia: SesionHTTP | None = None


def sesion_global() -> SesionHTTP:
    """Devuelve una `SesionHTTP` singleton (reutilizable entre llamadas)."""
    global _sesion_global_instancia
    with _sesion_global_lock:
        if _sesion_global_instancia is None:
            _sesion_global_instancia = SesionHTTP()
        return _sesion_global_instancia


__all__ = ["SesionHTTP", "sesion_global"]
