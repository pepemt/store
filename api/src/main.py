import os
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from .config import setup_logging
from .auth_routes import router as auth_router
from .cart_routes import router as cart_router
from .product_routes import router as product_router
from .chat_routes import router as chat_router
from .image_routes import router as image_router

from database.lib import Database
from images.lib import process_image_info
from text.lib import format_text_info
from .s3_service import S3Service

load_dotenv()
logger = setup_logging()

app = FastAPI(title="La Tiendita de la Esquina API", version="0.1.0")

# CORS (en dev dejamos * para evitar bloqueos; en prod lista dominios)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # en prod: ["http://localhost:5173", "https://tu-dominio"]
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth_router,    prefix="/api/v1/auth",     tags=["authentication"])
app.include_router(cart_router,    prefix="/api/v1/cart",     tags=["cart"])
app.include_router(product_router, prefix="/api/v1/products", tags=["products"])
app.include_router(chat_router,    prefix="/api/v1/chat",     tags=["chat"])
app.include_router(image_router,   prefix="/api/v1/images",   tags=["images"])


def get_database_url() -> str:
    """Obtiene la URL de conexión a PostgreSQL desde las variables de entorno."""
    database_url = os.getenv("STORE_DATABASE_URL")
    return database_url


@app.on_event("startup")
async def startup_event():
    """Inicializa la conexión con la base de datos al arrancar la aplicación."""
    try:
        database_url = get_database_url()
        logger.info(
            f"Conectando a la base de datos: "
            f"{database_url.split('@')[1] if '@' in database_url else database_url}"
        )

        # DB
        Database.initialize(database_url, echo=False)
        await Database.wait_for_connection()
        await Database.create_tables()
        logger.info("✅ Base de datos inicializada correctamente")

        # S3 (opcional)
        try:
            S3Service.initialize()
            logger.info("✅ Servicio S3 inicializado correctamente")
        except Exception as e:
            logger.warning(f"⚠️  Error al inicializar S3 Service (puede continuar sin S3): {e}")

        # Log de rutas (útil para confirmar que /api/v1/cart/add existe)
        try:
            for r in app.router.routes:
                if hasattr(r, "methods") and hasattr(r, "path"):
                    logger.info(f"Route: {sorted(list(r.methods))} {r.path}")
        except Exception:
            pass

    except Exception as e:
        logger.error(f"❌ Error al inicializar la base de datos: {e}")
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Cierra la conexión con la base de datos al cerrar la aplicación."""
    try:
        await Database.cleanup()
        logger.info("🔌 Conexión con la base de datos cerrada")
    except Exception as e:
        logger.error(f"❌ Error al cerrar la conexión con la base de datos: {e}")


@app.get("/")
async def hello():
    return {"message": "¡Bienvenido a La Tiendita de la Esquina API!", "status": "running"}


@app.get("/health")
async def health_check():
    """Endpoint para verificar el estado de la API y la base de datos."""
    try:
        await Database.wait_for_connection()
        return {"status": "healthy", "database": "connected", "message": "OK"}
    except Exception as e:
        return {"status": "unhealthy", "database": "disconnected", "error": str(e)}


def main():
    # Demos (logs)
    image_data = process_image_info("example.jpg", 1920, 1080)
    logger.info("Image processed:")
    for k, v in image_data.items():
        logger.info(f"  {k}: {v}")

    text_data = format_text_info("Example Text", 5)
    logger.info("Text processed:")
    for k, v in text_data.items():
        logger.info(f"  {k}: {v}")

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
