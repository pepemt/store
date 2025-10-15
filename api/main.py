from images.lib import process_image_info
from text.lib import format_text_info


def main():
    print("Hello from api!")

    # Ejemplo de uso de la función desde images/lib.py
    image_data = process_image_info("ejemplo.jpg", 1920, 1080)
    print(f"\nInformación de imagen procesada:")
    for key, value in image_data.items():
        print(f"  {key}: {value}")

    # Ejemplo de uso de la función desde text/lib.py
    text_data = format_text_info("Este es un texto de ejemplo para probar la funcion de procesamiento de texto desde el modulo text")
    print(f"\nInformación de texto procesada:")
    for key, value in text_data.items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    main()
