"""
Audio transcription routes.

- POST /transcribe: recibe audio (multipart "file"), convierte a WAV 16k mono con ffmpeg
  y lo reenvía al backend STT remoto vía túnel/URL configurada.
- GET  /transcribe/health: verifica disponibilidad de ffmpeg y muestra el backend configurado.
"""

import os
import uuid
import shutil
import logging
import tempfile
import subprocess
from typing import Optional

import httpx
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, status, Request

logger = logging.getLogger(__name__)
router = APIRouter()

# =========================
# Helpers de configuración
# =========================

def _get_ffmpeg_path() -> str:
    """
    Devuelve la ruta/comando ffmpeg desde FFMPEG_PATH (env) o 'ffmpeg' por defecto.
    """
    return os.getenv("FFMPEG_PATH") or "ffmpeg"


def _get_backend_url() -> str:
    """
    Devuelve la URL del backend STT remoto (vía túnel o IP directa).
    Prioriza TRANSCRIBE_BACKEND_URL y luego ORACLE_STT_URL.
    """
    url = os.getenv("TRANSCRIBE_BACKEND_URL") or os.getenv("ORACLE_STT_URL")
    if not url:
        raise HTTPException(
            status_code=500,
            detail="Backend STT no configurado. Define TRANSCRIBE_BACKEND_URL u ORACLE_STT_URL en el .env."
        )
    return url.rstrip("/")


def _to_wav_16k_mono(src_path: str) -> str:
    """
    Convierte el archivo de entrada a WAV PCM mono 16 kHz usando ffmpeg.
    Retorna la ruta del archivo WAV generado.
    """
    ffmpeg = _get_ffmpeg_path()

    # Archivo de salida temporal .wav
    out_path = os.path.join(
        tempfile.gettempdir(),
        f"stt_{uuid.uuid4().hex}.wav"
    )

    # Comando ffmpeg:
    # -y: overwrite
    # -i INPUT
    # -ac 1: mono
    # -ar 16000: 16 kHz
    # -f wav: formato WAV
    cmd = [
        ffmpeg,
        "-y",
        "-i", src_path,
        "-ac", "1",
        "-ar", "16000",
        "-f", "wav",
        out_path,
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            logger.error("ffmpeg stderr: %s", result.stderr)
            raise HTTPException(
                status_code=500,
                detail=f"No se pudo convertir el audio a WAV 16k mono. Verifica ffmpeg. (code={result.returncode})"
            )
        return out_path
    except FileNotFoundError:
        raise HTTPException(
            status_code=500,
            detail=f"ffmpeg no disponible ({ffmpeg}): asegúrate de que FFMPEG_PATH esté bien configurado."
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error ejecutando ffmpeg: {e}"
        )


async def _proxy_to_oracle(wav_path: str, model_name: Optional[str], language: Optional[str]) -> str:
    """
    Envía el WAV al backend STT remoto (vía túnel/URL).
    - Campo del archivo: "file"
    - Query params: model_name (opcional), language (opcional)
    Devuelve el texto transcrito.
    """
    backend_url = _get_backend_url()
    timeout_ms = int(os.getenv("ORACLE_STT_TIMEOUT_MS", "60000"))
    timeout = httpx.Timeout(timeout_ms / 1000)

    params = {}
    if model_name:
        params["model_name"] = model_name
    if language:
        params["language"] = language

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            with open(wav_path, "rb") as f:
                files = {
                    "file": ("audio.wav", f, "audio/wav")
                }
                resp = await client.post(backend_url, params=params, files=files)

        if resp.status_code >= 400:
            # Propagamos el mensaje del backend para depurar
            logger.warning("Backend STT %s devolvió %s: %s",
                           backend_url, resp.status_code, resp.text)
            # 502 Bad Gateway hacia el front para indicar fallo del backend
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Backend STT {resp.status_code}: {resp.text}"
            )

        data = resp.json()
        text = data.get("text", "")
        return text

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
    """
    Verifica si ffmpeg está disponible y muestra el backend configurado.
    """
    ffmpeg = _get_ffmpeg_path()
    try:
        out = subprocess.run(
            [ffmpeg, "-version"],
            capture_output=True,
            text=True
        )
        if out.returncode != 0:
            return {
                "status": "unhealthy",
                "error": f"ffmpeg ejecutó pero retornó código {out.returncode}",
                "backend": _get_backend_url()
            }
    except FileNotFoundError:
        return {
            "status": "unhealthy",
            "error": f"ffmpeg no disponible ({ffmpeg})",
            "backend": os.getenv("TRANSCRIBE_BACKEND_URL") or os.getenv("ORACLE_STT_URL") or ""
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "backend": os.getenv("TRANSCRIBE_BACKEND_URL") or os.getenv("ORACLE_STT_URL") or ""
        }

    return {
        "status": "healthy",
        "ffmpeg": ffmpeg,
        "backend": _get_backend_url()
    }


@router.post("/transcribe")
async def transcribe(
    request: Request,
    file: UploadFile = File(...),
    model_name: Optional[str] = Form(None),
    language: Optional[str] = Form(None),
):
    """
    Recibe un audio, lo convierte a WAV 16k mono y lo envía al backend STT remoto.
    Acepta model_name y language ya sea por query (?model_name=medium&language=es) o por form-data.
    """
    # Permitir también por query (fallback si no viene por form)
    q = request.query_params
    model = model_name or q.get("model_name")
    lang = language or q.get("language")

    # 1) Guardar el archivo subido a un temporal en disco
    tmp_in_path = os.path.join(
        tempfile.gettempdir(),
        f"upload_{uuid.uuid4().hex}_{file.filename or 'audio'}"
    )

    try:
        with open(tmp_in_path, "wb") as out_f:
            shutil.copyfileobj(file.file, out_f)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"No se pudo leer/subir el archivo: {e}")

    out_wav = None
    try:
        # 2) Convertir a WAV 16k mono con ffmpeg
        out_wav = _to_wav_16k_mono(tmp_in_path)

        # 3) Enviar al backend STT
        text = await _proxy_to_oracle(out_wav, model_name=model, language=lang)

        # 4) Responder al cliente
        return {"text": text}

    finally:
        # Limpieza de temporales
        try:
            if os.path.exists(tmp_in_path):
                os.remove(tmp_in_path)
        except Exception:
            pass
        try:
            if out_wav and os.path.exists(out_wav):
                os.remove(out_wav)
        except Exception:
            pass
