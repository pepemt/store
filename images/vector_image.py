import chromadb
from transformers import CLIPProcessor, CLIPModel
from PIL import Image
import os
import torch

# Cargar el modelo CLIP desde la ruta local
clip_model = CLIPModel.from_pretrained("./models/clip-vit-base-patch32")
clip_processor = CLIPProcessor.from_pretrained("./models/clip-vit-base-patch32")

# Crear cliente de ChromaDB
client = chromadb.Client()

# Verificar si la colección ya existe
collection_name = 'multimodal_collection'
if collection_name in [col.name for col in client.list_collections()]:
    collection = client.get_collection(name=collection_name)
else:
    collection = client.create_collection(name=collection_name)

# Función para generar embeddings visuales con CLIP
def generate_image_embedding(image_path):
    image = Image.open(image_path).convert("RGB")  # Asegurarse de que la imagen esté en formato RGB
    inputs = clip_processor(images=image, return_tensors="pt")
    with torch.no_grad():
        image_embeds = clip_model.get_image_features(**inputs)
    # Normalizar los embeddings
    image_embeds = image_embeds / image_embeds.norm(p=2, dim=-1, keepdim=True)
    return image_embeds.squeeze(0).tolist()  # Convertir a lista para almacenar en la base de datos

# Función para cargar imágenes en la colección
def load_images_to_collection(image_folder):
    image_files = []
    for root, _, files in os.walk(image_folder):  # Recorrer todas las subcarpetas
        for file in files:
            if file.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif')):
                image_files.append(os.path.join(root, file))  # Agregar la ruta completa de la imagen

    for image_path in image_files:
        try:
            image_embedding = generate_image_embedding(image_path)
            collection.add(
                documents=["Embedding de imagen"],  # Texto genérico, ya que estamos almacenando embeddings
                metadatas=[{"filename": os.path.basename(image_path), "path": image_path}],
                ids=[os.path.relpath(image_path, image_folder)],  # Relativizar la ruta
                embeddings=[image_embedding]  # Agregar los embeddings generados por CLIP
            )
        except Exception as e:
            print(f"Error procesando la imagen {image_path}: {e}")

    print(f"Se han agregado {len(image_files)} imágenes a la colección.")

# Función para realizar consultas
def query_images(query_text):
    inputs = clip_processor(text=[query_text], return_tensors="pt", padding=True)
    with torch.no_grad():
        query_embedding = clip_model.get_text_features(**inputs)
    query_embedding = query_embedding / query_embedding.norm(p=2, dim=-1, keepdim=True)
    query_embedding = query_embedding.squeeze(0).tolist()

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=5
    )
    return results

# Cargar imágenes en la colección
image_folder = os.path.join(os.getcwd(), "clothes")  # Ruta a la carpeta principal
load_images_to_collection(image_folder)

# Entrada de consulta
while True:
    query = input("\nIntroduce tu consulta (o escribe 'salir' para terminar): ")
    if query.lower() in ["salir", "exit", "q"]:
        break

    results = query_images(query)

    # Mostrar los resultados en la terminal
    print("\nResultados de la consulta:")
    if not results["metadatas"]:
        print("No se encontraron resultados para la consulta.")
    else:
        for metadata in results["metadatas"]:
            if isinstance(metadata, list):  # Si hay múltiples resultados
                for item in metadata:
                    print(f"Imagen relacionada: {item['filename']}")
            else:
                print(f"Imagen relacionada: {metadata['filename']}")