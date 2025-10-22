#!/usr/bin/env python3
"""
Script simple para probar la conexión con la base de datos PostgreSQL.
"""

import asyncio
import os
import sys
from dotenv import load_dotenv

# Agregar el directorio src al path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from database.lib import Database

async def test_connection():
    """Prueba la conexión con la base de datos."""
    print("🔍 Probando conexión con PostgreSQL...")
    print(f"📍 IP: 100.64.101.26")
    print(f"🗄️  Base de datos: store")
    print(f"👤 Usuario: admin")
    
    try:
        # Cargar variables de entorno
        load_dotenv()
        
        # Obtener URL de conexión
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            # Fallback si DATABASE_URL no está definida
            db_host = os.getenv("DB_HOST", "100.64.101.26")
            db_port = os.getenv("DB_PORT", "5432")
            db_name = os.getenv("DB_NAME", "store")
            db_user = os.getenv("DB_USER", "admin")
            db_password = os.getenv("DB_PASSWORD", "awdrqwer12")
            database_url = f"postgresql+asyncpg://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
        
        # Mostrar URL segura (sin password)
        safe_url = database_url.replace(":awdrqwer12@", ":***@")
        print(f"🔗 URL: {safe_url}")
        
        # Inicializar y probar conexión
        print("⚙️  Inicializando...")
        Database.initialize(database_url)
        
        print("⏳ Conectando...")
        await Database.wait_for_connection()
        print("✅ ¡Conexión exitosa!")
        
        print("📋 Creando tablas...")
        await Database.create_tables()
        print("✅ ¡Tablas creadas!")
        
        print("\n🎉 ¡Todo funcionando perfectamente!")
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False
    
    finally:
        try:
            await Database.cleanup()
            print("🔌 Conexión cerrada")
        except:
            pass

if __name__ == "__main__":
    print("=" * 50)
    print("🧪 PRUEBA DE CONEXIÓN POSTGRESQL")
    print("=" * 50)
    
    success = asyncio.run(test_connection())
    
    print("=" * 50)
    if success:
        print("✅ RESULTADO: ¡Conexión exitosa!")
        sys.exit(0)
    else:
        print("❌ RESULTADO: Error en la conexión")
        sys.exit(1)
