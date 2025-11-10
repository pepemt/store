"""
Rutas de la API para obtener imágenes desde OCI Object Storage (S3-compatible).
"""
from typing import Optional
from fastapi import APIRouter, HTTPException, Query, status, UploadFile, File, Form
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
import logging
from io import BytesIO

from .s3_service import S3Service

logger = logging.getLogger(__name__)

router = APIRouter()


class ImageURLResponse(BaseModel):
    """Modelo de respuesta para URL de imagen."""
    url: str
    image_key: str
    expires_in: int


class ImageListResponse(BaseModel):
    """Modelo de respuesta para lista de imágenes."""
    images: list[str]
    total: int
    prefix: str


class BucketListResponse(BaseModel):
    """Modelo de respuesta para lista de buckets."""
    buckets: list[str]
    total: int


class UploadImageResponse(BaseModel):
    """Modelo de respuesta para subida de imagen."""
    success: bool
    message: str
    image_key: Optional[str] = None
    url: Optional[str] = None


@router.get("/buckets", response_model=BucketListResponse)
async def list_buckets():
    """
    Lista todos los buckets disponibles en OCI Object Storage.

    Returns:
        Lista de nombres de buckets
    """
    try:
        buckets = S3Service.list_buckets()
        
        return BucketListResponse(
            buckets=buckets,
            total=len(buckets)
        )
        
    except Exception as e:
        logger.error(f"Error al listar buckets: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al listar buckets: {str(e)}"
        )


@router.post("/upload", response_model=UploadImageResponse)
async def upload_image(
    file: UploadFile = File(..., description="Archivo de imagen a subir"),
    image_key: Optional[str] = Form(None, description="Clave de la imagen en S3 (ej: 'products/product1.jpg'). Si no se proporciona, se usa el nombre del archivo")
):
    """
    Sube una imagen a OCI Object Storage.

    Args:
        file: Archivo de imagen a subir
        image_key: Clave opcional para la imagen en S3. Si no se proporciona, se usa el nombre del archivo
    
    Returns:
        Información sobre la subida de la imagen
    """
    try:
        # Verificar que el bucket existe
        bucket_exists = S3Service.bucket_exists()
        if not bucket_exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Bucket '{S3Service.get_bucket_name()}' no existe en S3. Por favor crea el bucket primero."
            )
        
        # Determinar el image_key (usar el nombre del archivo si no se proporciona)
        if not image_key:
            image_key = file.filename
        
        if not image_key:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Debes proporcionar un nombre de archivo o una clave de imagen"
            )
        
        # Leer el contenido del archivo
        image_data = await file.read()
        
        # Determinar content type
        content_type = file.content_type or "image/jpeg"
        if not content_type.startswith("image/"):
            # Intentar determinar el tipo basado en la extensión
            if image_key.lower().endswith('.png'):
                content_type = "image/png"
            elif image_key.lower().endswith('.gif'):
                content_type = "image/gif"
            elif image_key.lower().endswith('.webp'):
                content_type = "image/webp"
            elif image_key.lower().endswith('.jpg') or image_key.lower().endswith('.jpeg'):
                content_type = "image/jpeg"
            else:
                content_type = "image/jpeg"  # Default
        
        # Subir la imagen
        success = S3Service.upload_image(image_key, image_data, content_type)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error al subir la imagen: {image_key}"
            )
        
        # Generar URL presignada para la imagen subida
        url = S3Service.get_image_url(image_key, expires_in=3600)
        
        return UploadImageResponse(
            success=True,
            message=f"Imagen subida exitosamente: {image_key}",
            image_key=image_key,
            url=url
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al subir imagen: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al subir imagen: {str(e)}"
        )


@router.get("/list/all", response_model=ImageListResponse)
async def list_images(
    prefix: Optional[str] = Query("", description="Prefijo para filtrar imágenes (ej: 'products/')"),
    max_keys: int = Query(1000, ge=1, le=10000, description="Número máximo de imágenes a retornar")
):
    """
    Lista todas las imágenes disponibles en S3.
    
    Args:
        prefix: Prefijo para filtrar (ej: 'products/' para solo productos)
        max_keys: Número máximo de imágenes a retornar
    
    Returns:
        Lista de claves de imágenes
    """
    try:
        # Verificar que el bucket existe
        bucket_exists = S3Service.bucket_exists()
        if not bucket_exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Bucket '{S3Service.get_bucket_name()}' no existe en S3. Por favor crea el bucket primero."
            )
        
        images = S3Service.list_images(prefix=prefix, max_keys=max_keys)
        
        return ImageListResponse(
            images=images,
            total=len(images),
            prefix=prefix or ""
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al listar imágenes: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al listar imágenes: {str(e)}"
        )


@router.get("/url/{image_key:path}", response_model=ImageURLResponse)
async def get_image_url(
    image_key: str,
    expires_in: int = Query(3600, ge=60, le=604800, description="Tiempo de expiración en segundos (60-604800)")
):
    """
    Obtiene una URL presignada para acceder a una imagen desde S3.
    
    Args:
        image_key: Clave de la imagen en S3 (ej: 'products/product1.jpg')
        expires_in: Tiempo de expiración en segundos (default: 1 hora, max: 7 días)
    
    Returns:
        URL presignada para acceder a la imagen
    """
    try:
        # Verificar que el bucket existe
        bucket_exists = S3Service.bucket_exists()
        if not bucket_exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Bucket '{S3Service.get_bucket_name()}' no existe en S3. Por favor crea el bucket primero."
            )
        
        # Verificar que la imagen existe
        if not S3Service.image_exists(image_key):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Imagen no encontrada: {image_key}"
            )
        
        # Generar URL presignada
        url = S3Service.get_image_url(image_key, expires_in)
        
        if not url:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error al generar URL presignada"
            )
        
        return ImageURLResponse(
            url=url,
            image_key=image_key,
            expires_in=expires_in
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al obtener URL de imagen: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener URL de imagen: {str(e)}"
        )


@router.get("/{image_key:path}")
async def get_image(
    image_key: str,
    download: bool = Query(False, description="Forzar descarga en lugar de mostrar")
):
    """
    Obtiene una imagen directamente desde S3 y la sirve como respuesta.
    
    Args:
        image_key: Clave de la imagen en S3 (ej: 'products/product1.jpg')
        download: Si es True, fuerza la descarga del archivo
    
    Returns:
        Imagen como StreamingResponse
    """
    try:
        # Verificar que el bucket existe
        bucket_exists = S3Service.bucket_exists()
        if not bucket_exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Bucket '{S3Service.get_bucket_name()}' no existe en S3. Por favor crea el bucket primero."
            )
        
        # Obtener imagen desde S3
        image_data = S3Service.get_image_object(image_key)
        
        if not image_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Imagen no encontrada: {image_key}"
            )
        
        # Determinar content type basado en la extensión
        content_type = "image/jpeg"  # Default
        if image_key.lower().endswith('.png'):
            content_type = "image/png"
        elif image_key.lower().endswith('.gif'):
            content_type = "image/gif"
        elif image_key.lower().endswith('.webp'):
            content_type = "image/webp"
        
        # Preparar headers
        headers = {}
        if download:
            filename = image_key.split('/')[-1]
            headers["Content-Disposition"] = f'attachment; filename="{filename}"'
        
        return StreamingResponse(
            BytesIO(image_data),
            media_type=content_type,
            headers=headers
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al obtener imagen: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener imagen: {str(e)}"
        )


@router.head("/{image_key:path}")
async def check_image_exists(image_key: str):
    """
    Verifica si una imagen existe en S3 sin descargarla.
    
    Args:
        image_key: Clave de la imagen en S3
    
    Returns:
        Status 200 si existe, 404 si no existe
    """
    try:
        # Verificar que el bucket existe
        bucket_exists = S3Service.bucket_exists()
        if not bucket_exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Bucket '{S3Service.get_bucket_name()}' no existe en S3. Por favor crea el bucket primero."
            )
        
        exists = S3Service.image_exists(image_key)
        
        if exists:
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={"exists": True, "image_key": image_key}
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Imagen no encontrada: {image_key}"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al verificar imagen: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al verificar imagen: {str(e)}"
        )

