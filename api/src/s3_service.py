"""
Servicio para manejar operaciones con S3/MinIO.
"""
import os
import logging
from typing import Optional
from urllib.parse import urlparse
import boto3
from botocore.client import Config
from botocore.exceptions import ClientError, NoCredentialsError

logger = logging.getLogger(__name__)


class S3Service:
    """Servicio para interactuar con S3/MinIO."""
    
    _client = None
    _bucket_name = None
    _endpoint_url = None
    
    @classmethod
    def initialize(cls):
        """Inicializa el cliente de S3/MinIO."""
        try:
            s3_url = os.getenv("S3_URL", "")
            if not s3_url:
                logger.warning("S3_URL no está configurada en las variables de entorno")
                return
            
            # Parsear la URL de S3
            # Formato esperado: s3://host:port o s3://host:port/bucket
            parsed = urlparse(s3_url)
            
            # Extraer host y puerto
            host = parsed.hostname or "100.64.101.26"
            port = parsed.port or 9000
            
            # Construir endpoint URL (MinIO usa HTTP)
            cls._endpoint_url = f"http://{host}:{port}"
            
            # Extraer bucket si está en el path
            if parsed.path and parsed.path != "/":
                cls._bucket_name = parsed.path.strip("/")
            else:
                # Usar bucket por defecto si no está en la URL
                cls._bucket_name = os.getenv("S3_BUCKET", "store")
            
            # Credenciales de S3/MinIO
            access_key = os.getenv("S3_ACCESS_KEY", os.getenv("MINIO_ROOT_USER", "minioadmin"))
            secret_key = os.getenv("S3_SECRET_KEY", os.getenv("MINIO_ROOT_PASSWORD", "minioadmin"))
            
            # Crear cliente de S3
            cls._client = boto3.client(
                's3',
                endpoint_url=cls._endpoint_url,
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
                config=Config(signature_version='s3v4'),
                use_ssl=False,
                verify=False
            )
            
            logger.info(f"✅ S3 Service inicializado: {cls._endpoint_url}, bucket: {cls._bucket_name}")
            
        except Exception as e:
            logger.error(f"❌ Error al inicializar S3 Service: {e}")
            raise
    
    @classmethod
    def get_client(cls):
        """Obtiene el cliente de S3."""
        if cls._client is None:
            cls.initialize()
        return cls._client
    
    @classmethod
    def get_bucket_name(cls):
        """Obtiene el nombre del bucket."""
        if cls._bucket_name is None:
            cls.initialize()
        return cls._bucket_name
    
    @classmethod
    def get_image_url(cls, image_key: str, expires_in: int = 3600) -> Optional[str]:
        """
        Genera una URL presignada para acceder a una imagen.
        
        Args:
            image_key: Clave de la imagen en S3 (ej: 'products/product1.jpg')
            expires_in: Tiempo de expiración en segundos (default: 1 hora)
        
        Returns:
            URL presignada o None si hay error
        """
        try:
            client = cls.get_client()
            bucket = cls.get_bucket_name()
            
            # Generar URL presignada
            url = client.generate_presigned_url(
                'get_object',
                Params={'Bucket': bucket, 'Key': image_key},
                ExpiresIn=expires_in
            )
            
            return url
            
        except ClientError as e:
            logger.error(f"Error al generar URL presignada para {image_key}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error inesperado al generar URL: {e}")
            return None
    
    @classmethod
    def get_image_object(cls, image_key: str) -> Optional[bytes]:
        """
        Obtiene el contenido de una imagen desde S3.
        
        Args:
            image_key: Clave de la imagen en S3
        
        Returns:
            Contenido de la imagen en bytes o None si hay error
        """
        try:
            client = cls.get_client()
            bucket = cls.get_bucket_name()
            
            response = client.get_object(Bucket=bucket, Key=image_key)
            return response['Body'].read()
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            if error_code == 'NoSuchKey':
                logger.warning(f"Imagen no encontrada: {image_key}")
            elif error_code == 'NoSuchBucket':
                logger.error(f"Bucket '{bucket}' no existe en S3")
            else:
                logger.error(f"Error al obtener imagen {image_key}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error inesperado al obtener imagen: {e}")
            return None
    
    @classmethod
    def list_images(cls, prefix: str = "", max_keys: int = 1000) -> list:
        """
        Lista todas las imágenes en un prefijo.
        
        Args:
            prefix: Prefijo para filtrar (ej: 'products/')
            max_keys: Número máximo de objetos a retornar
        
        Returns:
            Lista de claves de imágenes
        """
        try:
            client = cls.get_client()
            bucket = cls.get_bucket_name()
            
            response = client.list_objects_v2(
                Bucket=bucket,
                Prefix=prefix,
                MaxKeys=max_keys
            )
            
            if 'Contents' in response:
                return [obj['Key'] for obj in response['Contents']]
            return []
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            if error_code == 'NoSuchBucket':
                logger.error(f"Bucket '{bucket}' no existe en S3")
                raise  # Re-raise para que el endpoint pueda manejar el error apropiadamente
            logger.error(f"Error al listar imágenes: {e}")
            return []
        except Exception as e:
            logger.error(f"Error inesperado al listar imágenes: {e}")
            return []
    
    @classmethod
    def image_exists(cls, image_key: str) -> bool:
        """
        Verifica si una imagen existe en S3.
        
        Args:
            image_key: Clave de la imagen en S3
        
        Returns:
            True si existe, False en caso contrario
        """
        try:
            client = cls.get_client()
            bucket = cls.get_bucket_name()
            
            client.head_object(Bucket=bucket, Key=image_key)
            return True
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            if error_code in ['404', 'NoSuchKey']:
                return False
            elif error_code == 'NoSuchBucket':
                logger.error(f"Bucket '{bucket}' no existe en S3")
                return False
            logger.error(f"Error al verificar existencia de imagen: {e}")
            return False
        except Exception as e:
            logger.error(f"Error inesperado al verificar imagen: {e}")
            return False
    
    @classmethod
    def bucket_exists(cls) -> bool:
        """
        Verifica si el bucket existe en S3.
        
        Returns:
            True si existe, False en caso contrario
        """
        try:
            client = cls.get_client()
            bucket = cls.get_bucket_name()
            
            client.head_bucket(Bucket=bucket)
            return True
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            if error_code in ['404', 'NoSuchBucket']:
                return False
            logger.error(f"Error al verificar existencia del bucket: {e}")
            return False
        except Exception as e:
            logger.error(f"Error inesperado al verificar bucket: {e}")
            return False
    
    @classmethod
    def create_bucket(cls) -> bool:
        """
        Crea el bucket si no existe.
        
        Returns:
            True si se creó o ya existía, False si hay error
        """
        try:
            client = cls.get_client()
            bucket = cls.get_bucket_name()
            
            # Verificar si ya existe
            if cls.bucket_exists():
                logger.info(f"Bucket '{bucket}' ya existe")
                return True
            
            # Crear el bucket
            client.create_bucket(Bucket=bucket)
            logger.info(f"✅ Bucket '{bucket}' creado exitosamente")
            return True
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            if error_code == 'BucketAlreadyExists':
                logger.info(f"Bucket '{bucket}' ya existe")
                return True
            logger.error(f"Error al crear bucket: {e}")
            return False
        except Exception as e:
            logger.error(f"Error inesperado al crear bucket: {e}")
            return False
    
    @classmethod
    def list_buckets(cls) -> list:
        """
        Lista todos los buckets disponibles en S3/MinIO.
        
        Returns:
            Lista de nombres de buckets
        """
        try:
            client = cls.get_client()
            
            response = client.list_buckets()
            
            if 'Buckets' in response:
                return [bucket['Name'] for bucket in response['Buckets']]
            return []
            
        except ClientError as e:
            logger.error(f"Error al listar buckets: {e}")
            return []
        except Exception as e:
            logger.error(f"Error inesperado al listar buckets: {e}")
            return []
    
    @classmethod
    def upload_image(cls, image_key: str, image_data: bytes, content_type: str = "image/jpeg") -> bool:
        """
        Sube una imagen a S3/MinIO.
        
        Args:
            image_key: Clave de la imagen en S3 (ej: 'products/product1.jpg')
            image_data: Contenido de la imagen en bytes
            content_type: Tipo de contenido de la imagen (default: image/jpeg)
        
        Returns:
            True si se subió exitosamente, False si hay error
        """
        try:
            client = cls.get_client()
            bucket = cls.get_bucket_name()
            
            # Verificar que el bucket existe
            if not cls.bucket_exists():
                logger.error(f"Bucket '{bucket}' no existe")
                return False
            
            # Subir la imagen
            client.put_object(
                Bucket=bucket,
                Key=image_key,
                Body=image_data,
                ContentType=content_type
            )
            
            logger.info(f"✅ Imagen subida exitosamente: {image_key}")
            return True
            
        except ClientError as e:
            logger.error(f"Error al subir imagen {image_key}: {e}")
            return False
        except Exception as e:
            logger.error(f"Error inesperado al subir imagen: {e}")
            return False

