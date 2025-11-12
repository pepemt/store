import os
import boto3
from botocore.exceptions import NoCredentialsError, ClientError

# Ruta base de la carpeta de imágenes
BASE_IMAGE_FOLDER = "../andrea/h-and-m-personalized-fashion-recommendations/images"

# Credenciales y configuración del Oracle Object Storage
S3_ACCESS_KEY_ID = "1e5d23ffdaef32a3b76ae3277cff40e172a5af20"
S3_SECRET_ACCESS_KEY = "0qCwONjD7GMChWyUIlCeFKzlbKItkd+bFv5R9cy9x1g="
S3_REGION = "us-chicago-1"
S3_ENDPOINT_URL = "https://ax3bzf9323pt.compat.objectstorage.us-chicago-1.oraclecloud.com"
S3_BUCKET = "store"

# Crear cliente S3
s3_client = boto3.client(
    "s3",
    aws_access_key_id=S3_ACCESS_KEY_ID,
    aws_secret_access_key=S3_SECRET_ACCESS_KEY,
    region_name=S3_REGION,
    endpoint_url=S3_ENDPOINT_URL,
)

# Extensiones de archivo permitidas
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".bmp"}

def upload_image_to_s3(file_path, image_key):
    """
    Sube una imagen al Oracle Object Storage usando boto3.

    Args:
        file_path (str): Ruta completa de la imagen a subir.
        image_key (str): Clave de la imagen en el bucket (nombre del archivo).

    Returns:
        bool: True si la imagen se subió correctamente, False en caso contrario.
    """
    try:
        # Subir el archivo usando upload_file
        s3_client.upload_file(file_path, S3_BUCKET, image_key)
        print(f"Imagen subida correctamente: {image_key}")
        return True
    except FileNotFoundError:
        print(f"Archivo no encontrado: {file_path}")
        return False
    except NoCredentialsError:
        print("Credenciales no válidas para S3.")
        return False
    except ClientError as e:
        print(f"Error al subir la imagen {image_key}: {e}")
        return False

def main():
    """
    Recorre la carpeta de imágenes y sube cada imagen al Oracle Object Storage.
    """
    for root, _, files in os.walk(BASE_IMAGE_FOLDER):
        for file_name in files:
            # Ignorar archivos ocultos como .DS_Store
            if file_name.startswith("."):
                continue

            # Verificar si el archivo tiene una extensión permitida
            _, ext = os.path.splitext(file_name)
            if ext.lower() not in ALLOWED_EXTENSIONS:
                print(f"Archivo ignorado (extensión no permitida): {file_name}")
                continue

            # Ruta completa del archivo
            file_path = os.path.join(root, file_name)
            
            # Usar solo el nombre del archivo como clave en el bucket
            image_key = file_name

            print(f"Subiendo imagen: {file_path} con clave: {image_key}")
            success = upload_image_to_s3(file_path, image_key)
            if not success:
                print(f"Fallo al subir la imagen: {file_path}")

if __name__ == "__main__":
    main()