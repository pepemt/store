def format_text_info(text: str, max_length: int = 50) -> dict:
    """
    Procesa informacion de texto y retorna detalles.

    Args:
        text: El texto a procesar
        max_length: Longitud maxima para el preview

    Returns:
        dict: Diccionario con informacion del texto
    """
    words = text.split()
    preview = text[:max_length] + "..." if len(text) > max_length else text

    return {
        "length": len(text),
        "word_count": len(words),
        "preview": preview,
        "is_long": len(text) > max_length
    }
