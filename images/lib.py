def process_image_info(image_name: str, width: int, height: int) -> dict:
    """
    Procesa informacion de una imagen y retorna un diccionario con detalles.

    Args:
        image_name: Nombre de la imagen
        width: Ancho en pixeles
        height: Alto en pixeles

    Returns:
        dict: Diccionario con informacion procesada de la imagen
    """
    aspect_ratio = width / height if height != 0 else 0
    total_pixels = width * height

    return {
        "name": image_name,
        "dimensions": f"{width}x{height}",
        "aspect_ratio": round(aspect_ratio, 2),
        "total_pixels": total_pixels,
        "megapixels": round(total_pixels / 1_000_000, 2)
    }
