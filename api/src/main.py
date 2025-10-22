import os
import uvicorn
from fastapi import FastAPI
from dotenv import load_dotenv
from .config import setup_logging
from .auth_routes import router as auth_router
from database.lib import Database
from images.lib import process_image_info
from text.lib import format_text_info

load_dotenv()
logger = setup_logging()

app = FastAPI(title="La Tiendita de la Esquina API", version="0.1.0")

# Incluir las rutas de autenticación
app.include_router(auth_router, prefix="/api/v1/auth", tags=["authentication"])

def get_database_url() -> str:
    """Obtiene la URL de conexión a PostgreSQL desde las variables de entorno."""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        # Fallback a variables individuales si DATABASE_URL no está definida
        db_host = os.getenv("DB_HOST", "100.64.101.26")
        db_port = os.getenv("DB_PORT", "5432")
        db_name = os.getenv("DB_NAME", "store")
        db_user = os.getenv("DB_USER", "admin")
        db_password = os.getenv("DB_PASSWORD", "awdrqwer12")
        database_url = f"postgresql+asyncpg://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    
    return database_url

@app.on_event("startup")
async def startup_event():
    """Inicializa la conexión con la base de datos al arrancar la aplicación."""
    try:
        database_url = get_database_url()
        logger.info(f"Conectando a la base de datos: {database_url.split('@')[1] if '@' in database_url else 'localhost'}")
        
        # Inicializar la base de datos usando la clase existente
        Database.initialize(database_url)
        
        # Esperar a que la conexión esté lista
        await Database.wait_for_connection()
        
        # Crear las tablas si no existen
        await Database.create_tables()
        
        logger.info("✅ Base de datos inicializada correctamente")
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
        # Verificar conexión con la base de datos
        await Database.wait_for_connection()
        return {
            "status": "healthy",
            "database": "connected",
            "message": "API y base de datos funcionando correctamente"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(e)
        }

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
