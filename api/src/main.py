import os
import uvicorn
from fastapi import FastAPI
from dotenv import load_dotenv
from .config import setup_logging
from images.lib import process_image_info
from text.lib import format_text_info

load_dotenv()
logger = setup_logging()

app = FastAPI(title="Server", version="0.1.0")

@app.get("/")
async def hello():
    return "Hello, World!"

def main():
    # Example of using the function from images/lib.py
    image_data = process_image_info("example.jpg", 1920, 1080)
    logger.info(f"\nImage processed:")
    for key, value in image_data.items():
        logger.info(f"  {key}: {value}")

    # Example of using the function from text/lib.py
    text_data = format_text_info("Example Text", 5)
    logger.info(f"\nText processed:")
    for key, value in text_data.items():
        logger.info(f"  {key}: {value}")

    # Start the FastAPI server
    host = os.getenv("FASTAPI_HOST", "0.0.0.0")
    port = int(os.getenv("FASTAPI_PORT", "8000"))
    debug = os.getenv("FASTAPI_DEBUG", "true").lower() == "true"

    uvicorn.run(
        "api.main:app",
        host=host,
        port=port,
        reload=debug,
        log_level="info" if not debug else "debug",
    )


if __name__ == "__main__":
    main()
