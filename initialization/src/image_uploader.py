"""
Módulo para subir imágenes de productos a Oracle Object Storage (S3-compatible).
Procesa las imágenes locales y las sube en batch para ser accesibles por el backend.
"""
import os
import sys
import logging
from pathlib import Path
from typing import List, Tuple, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
import time

# Agregar el directorio api/src al path para importar S3Service
api_src_path = Path(__file__).resolve().parent.parent.parent / "api" / "src"
sys.path.insert(0, str(api_src_path))

from s3_service import S3Service

logger = logging.getLogger(__name__)


@dataclass
class UploadStats:
    """Estadísticas de la operación de upload."""
    total: int = 0
    uploaded: int = 0
    skipped: int = 0
    failed: int = 0
    start_time: float = 0
    end_time: float = 0

    @property
    def duration(self) -> float:
        """Duración total en segundos."""
        return self.end_time - self.start_time if self.end_time > 0 else 0

    @property
    def success_rate(self) -> float:
        """Tasa de éxito (0-100)."""
        return (self.uploaded / self.total * 100) if self.total > 0 else 0


class ImageUploader:
    """
    Manejador de subida de imágenes a S3.
    Procesa imágenes locales y las sube en batch con manejo de errores.
    """

    def __init__(
        self,
        base_image_folder: str = ".data/raw/images",
        s3_prefix: str = "products",
        allowed_extensions: Optional[List[str]] = None,
        max_workers: int = 10,
        check_existing: bool = True
    ):
        """
        Inicializa el uploader de imágenes.

        Args:
            base_image_folder: Carpeta base con las imágenes locales
            s3_prefix: Prefijo para organizar imágenes en S3 (ej: 'products')
            allowed_extensions: Extensiones permitidas (default: ['.jpg'])
            max_workers: Número de workers para upload paralelo
            check_existing: Si verificar si la imagen ya existe antes de subir
        """
        self.base_image_folder = Path(base_image_folder)
        self.s3_prefix = s3_prefix
        self.allowed_extensions = allowed_extensions or ['.jpg']
        self.max_workers = max_workers
        self.check_existing = check_existing
        self.stats = UploadStats()

    def find_images(self) -> List[Path]:
        """
        Encuentra todas las imágenes .jpg en la carpeta base.
        Ignora carpetas y solo procesa archivos.

        Returns:
            Lista de rutas de archivos de imagen
        """
        logger.info(f"Buscando imágenes en: {self.base_image_folder}")
        images = []

        if not self.base_image_folder.exists():
            logger.error(f"La carpeta de imágenes no existe: {self.base_image_folder}")
            return images

        # Recorrer recursivamente la carpeta
        for file_path in self.base_image_folder.rglob("*"):
            # Saltar si es directorio
            if file_path.is_dir():
                continue

            # Ignorar archivos ocultos (.DS_Store, etc.)
            if file_path.name.startswith("."):
                continue

            # Verificar extensión
            if file_path.suffix.lower() in self.allowed_extensions:
                images.append(file_path)

        logger.info(f"Encontradas {len(images)} imágenes para procesar")
        return images

    def get_s3_key(self, image_path: Path) -> str:
        """
        Genera la clave S3 para una imagen.
        Usa solo el nombre del archivo (ID del producto) con el prefijo.

        Args:
            image_path: Ruta local de la imagen

        Returns:
            Clave para S3 (ej: 'products/0249136006.jpg')
        """
        filename = image_path.name
        if self.s3_prefix:
            return f"{self.s3_prefix}/{filename}"
        return filename

    def upload_single_image(self, image_path: Path) -> Tuple[bool, str]:
        """
        Sube una sola imagen a S3.

        Args:
            image_path: Ruta local de la imagen

        Returns:
            Tupla (éxito, mensaje)
        """
        try:
            s3_key = self.get_s3_key(image_path)

            # Verificar si ya existe (opcional)
            if self.check_existing and S3Service.image_exists(s3_key):
                return True, f"Ya existe: {s3_key}"

            # Leer el archivo
            with open(image_path, 'rb') as f:
                image_data = f.read()

            # Determinar tipo de contenido
            content_type = "image/jpeg"
            if image_path.suffix.lower() in ['.png']:
                content_type = "image/png"
            elif image_path.suffix.lower() in ['.gif']:
                content_type = "image/gif"

            # Subir a S3
            success = S3Service.upload_image(s3_key, image_data, content_type)

            if success:
                return True, f"Subida: {s3_key}"
            else:
                return False, f"Error al subir: {s3_key}"

        except FileNotFoundError:
            return False, f"Archivo no encontrado: {image_path}"
        except Exception as e:
            return False, f"Error con {image_path.name}: {str(e)}"

    def upload_batch(
        self,
        images: List[Path],
        show_progress: bool = True,
        progress_interval: int = 100
    ) -> UploadStats:
        """
        Sube un lote de imágenes en paralelo.

        Args:
            images: Lista de rutas de imágenes a subir
            show_progress: Si mostrar progreso durante la subida
            progress_interval: Cada cuántas imágenes mostrar progreso

        Returns:
            Estadísticas de la operación
        """
        self.stats = UploadStats()
        self.stats.total = len(images)
        self.stats.start_time = time.time()

        if self.stats.total == 0:
            logger.warning("No hay imágenes para subir")
            return self.stats

        logger.info(f"Iniciando upload de {self.stats.total} imágenes...")
        logger.info(f"Workers: {self.max_workers}, Prefijo S3: {self.s3_prefix}")

        # Inicializar S3Service si no está inicializado
        try:
            S3Service.initialize()
        except Exception as e:
            logger.error(f"Error al inicializar S3Service: {e}")
            self.stats.failed = self.stats.total
            self.stats.end_time = time.time()
            return self.stats

        # Upload paralelo
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Enviar todas las tareas
            future_to_image = {
                executor.submit(self.upload_single_image, img): img
                for img in images
            }

            # Procesar resultados conforme terminan
            for future in as_completed(future_to_image):
                image_path = future_to_image[future]

                try:
                    success, message = future.result()

                    if success:
                        if "Ya existe" in message:
                            self.stats.skipped += 1
                        else:
                            self.stats.uploaded += 1
                    else:
                        self.stats.failed += 1
                        logger.error(message)

                    # Mostrar progreso
                    if show_progress:
                        processed = self.stats.uploaded + self.stats.skipped + self.stats.failed
                        if processed % progress_interval == 0 or processed == self.stats.total:
                            progress_pct = (processed / self.stats.total) * 100
                            logger.info(
                                f"Progreso: {processed}/{self.stats.total} "
                                f"({progress_pct:.1f}%) - "
                                f"Subidas: {self.stats.uploaded}, "
                                f"Omitidas: {self.stats.skipped}, "
                                f"Fallidas: {self.stats.failed}"
                            )

                except Exception as e:
                    self.stats.failed += 1
                    logger.error(f"Error procesando {image_path.name}: {e}")

        self.stats.end_time = time.time()
        return self.stats

    def print_summary(self):
        """Imprime un resumen de las estadísticas de upload."""
        logger.info("\n" + "=" * 70)
        logger.info("RESUMEN DE UPLOAD DE IMÁGENES")
        logger.info("=" * 70)
        logger.info(f"Total de imágenes procesadas: {self.stats.total}")
        logger.info(f"  ✅ Subidas exitosamente:    {self.stats.uploaded}")
        logger.info(f"  ⏭️  Omitidas (ya existían):  {self.stats.skipped}")
        logger.info(f"  ❌ Fallidas:                {self.stats.failed}")
        logger.info(f"\nTasa de éxito: {self.stats.success_rate:.2f}%")
        logger.info(f"Tiempo total: {self.stats.duration:.2f} segundos")

        if self.stats.duration > 0:
            rate = self.stats.total / self.stats.duration
            logger.info(f"Velocidad: {rate:.2f} imágenes/segundo")

        logger.info("=" * 70 + "\n")


def upload_images_to_s3(
    base_image_folder: str = ".data/raw/images",
    s3_prefix: str = "products",
    max_workers: int = 10,
    check_existing: bool = True
) -> UploadStats:
    """
    Función helper para subir imágenes a S3.

    Args:
        base_image_folder: Carpeta base con las imágenes
        s3_prefix: Prefijo en S3 (ej: 'products')
        max_workers: Workers para upload paralelo
        check_existing: Si verificar imágenes existentes

    Returns:
        Estadísticas de la operación
    """
    uploader = ImageUploader(
        base_image_folder=base_image_folder,
        s3_prefix=s3_prefix,
        max_workers=max_workers,
        check_existing=check_existing
    )

    # Buscar imágenes
    images = uploader.find_images()

    if not images:
        logger.warning("No se encontraron imágenes para subir")
        return UploadStats()

    # Subir en batch
    stats = uploader.upload_batch(images)

    # Mostrar resumen
    uploader.print_summary()

    return stats


if __name__ == "__main__":
    # Configurar logging para ejecución directa
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Ejecutar upload
    upload_images_to_s3()
