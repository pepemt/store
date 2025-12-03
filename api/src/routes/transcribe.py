"""
Audio transcription routes (OPTIMIZADO).

- POST /transcribe: recibe audio y lo reenvía DIRECTO al backend STT remoto.
  (faster-whisper procesa WebM/Opus directamente, no necesita conversión)
- GET  /transcribe/health: verifica disponibilidad del backend.
"""

import os
import logging
from typing import Optional

import httpx
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, status, Request

logger = logging.getLogger(__name__)
router = APIRouter()

# Cliente HTTP reutilizable para conexiones persistentes
_http_client: Optional[httpx.AsyncClient] = None


def _get_backend_url() -> str:
    """Devuelve la URL del backend STT remoto."""
    url = os.getenv("TRANSCRIBE_BACKEND_URL") or os.getenv("ORACLE_STT_URL")
    if not url:
        raise HTTPException(
            status_code=500,
            detail="Backend STT no configurado. Define TRANSCRIBE_BACKEND_URL u ORACLE_STT_URL en el .env."
        )
    return url.rstrip("/")


async def _get_http_client() -> httpx.AsyncClient:
    """Retorna cliente HTTP con conexión persistente."""
    global _http_client
    if _http_client is None or _http_client.is_closed:
        timeout_ms = int(os.getenv("ORACLE_STT_TIMEOUT_MS", "30000"))  # 30s default
        _http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout_ms / 1000),
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
        )
    return _http_client


async def _proxy_to_backend(
    audio_bytes: bytes,
    filename: str,
    content_type: str,
    model_name: Optional[str],
    language: Optional[str]
) -> str:
    """
    Envía el audio DIRECTO al backend STT remoto (sin conversión).
    faster-whisper procesa WebM/Opus, MP3, WAV, etc. directamente.
    """
    backend_url = _get_backend_url()

    params = {}
    if model_name:
        params["model_name"] = model_name
    if language:
        params["language"] = language

    try:
        client = await _get_http_client()
        files = {"file": (filename, audio_bytes, content_type)}
        resp = await client.post(backend_url, params=params, files=files)

        if resp.status_code >= 400:
            logger.warning("Backend STT %s devolvió %s: %s",
                          backend_url, resp.status_code, resp.text)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Backend STT {resp.status_code}: {resp.text}"
            )

        data = resp.json()
        return data.get("text", "")

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error conectando al backend STT")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Error conectando al backend STT: {e}"
        )


# =========================
# Rutas públicas
# =========================

@router.get("/transcribe/health")
async def transcribe_health():
    """Verifica disponibilidad del backend STT."""
    try:
        backend_url = _get_backend_url()
        client = await _get_http_client()
        # Verificar que el backend responde
        resp = await client.get(f"{backend_url.rsplit('/transcribe', 1)[0]}/health")
        if resp.status_code == 200:
            remote_health = resp.json()
            return {
                "status": "healthy",
                "backend": backend_url,
                "remote": remote_health,
                "optimizations": ["no_ffmpeg_conversion", "persistent_connections"]
            }
        return {
            "status": "degraded",
            "backend": backend_url,
            "remote_status": resp.status_code
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "backend": os.getenv("TRANSCRIBE_BACKEND_URL") or os.getenv("ORACLE_STT_URL") or ""
        }


@router.post("/transcribe")
async def transcribe(
    request: Request,
    file: UploadFile = File(...),
    model_name: Optional[str] = Form(None),
    language: Optional[str] = Form(None),
):
    """
    Recibe audio y lo reenvía DIRECTO al backend STT (sin conversión ffmpeg).
    faster-whisper procesa WebM/Opus, MP3, WAV directamente.
    """
    # Permitir params por query o form-data
    q = request.query_params
    model = model_name or q.get("model_name") or "small"  # Default: small (más rápido)
    lang = language or q.get("language") or "es"

    try:
        # Leer audio directamente en memoria (sin guardar a disco)
        audio_bytes = await file.read()

        # Enviar DIRECTO al backend (sin conversión)
        text = await _proxy_to_backend(
            audio_bytes=audio_bytes,
            filename=file.filename or "audio.webm",
            content_type=file.content_type or "audio/webm",
            model_name=model,
            language=lang
        )

        return {"text": text}

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error procesando transcripción")
        raise HTTPException(status_code=500, detail=f"Error: {e}")
