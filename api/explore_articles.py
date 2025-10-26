#!/usr/bin/env python3
"""
Script para explorar los datos de la tabla articles y ver qué campos contiene.
"""

import asyncio
import os
import sys
from pathlib import Path

# Agregar el directorio raíz del proyecto al path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
from database.lib import Database
from sqlalchemy import select, text
from database.models import Article

async def explore_articles():
    """Explora la estructura y contenido de la tabla articles."""
    
    # Cargar variables de entorno
    env_path = Path(__file__).parent / ".env"
    load_dotenv(env_path)
    
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ Error: No se encontró DATABASE_URL")
        return
    
    try:
        # Inicializar base de datos
        Database.initialize(database_url)
        await Database.wait_for_connection()
        
        print("🔍 Explorando la tabla articles...\n")
        
        # Obtener información de las columnas
        async with Database.get_session() as session:
            # Contar total de artículos
            from sqlalchemy import func
            count_result = await session.execute(select(func.count(Article.article_id)))
            total_articles = count_result.scalar()
            print(f"📊 Total de artículos en la base de datos: {total_articles}")
            
            # Obtener una muestra de artículos
            result = await session.execute(
                select(Article).limit(3)
            )
            articles = result.scalars().all()
            
            print("\n📋 Muestra de 3 artículos:")
            print("=" * 80)
            
            for i, article in enumerate(articles, 1):
                print(f"\n🏷️  ARTÍCULO {i}:")
                print(f"   • ID: {article.article_id}")
                print(f"   • Código: {article.product_code}")
                print(f"   • Nombre: {article.prod_name}")
                print(f"   • Tipo: {article.product_type_name}")
                print(f"   • Grupo: {article.product_group_name}")
                print(f"   • Departamento: {article.department_name}")
                print(f"   • Color: {article.colour_group_name}")
                print(f"   • Apariencia: {article.graphical_appearance_name}")
                if article.detail_desc:
                    print(f"   • Descripción: {article.detail_desc[:100]}...")
                print("-" * 50)
            
            # Verificar si hay campos relacionados con imágenes
            print("\n🖼️  ANÁLISIS DE CAMPOS RELACIONADOS CON IMÁGENES:")
            
            # Buscar si hay algún campo que pueda contener URLs o referencias a imágenes
            image_related_fields = []
            sample_article = articles[0] if articles else None
            
            if sample_article:
                # Verificar todos los atributos del artículo
                for attr_name in dir(sample_article):
                    if not attr_name.startswith('_') and not callable(getattr(sample_article, attr_name)):
                        attr_value = getattr(sample_article, attr_name)
                        if isinstance(attr_value, str) and ('http' in attr_value.lower() or 'image' in attr_value.lower() or 'photo' in attr_value.lower()):
                            image_related_fields.append(attr_name)
            
            if image_related_fields:
                print(f"   ✅ Campos con posibles URLs de imágenes: {image_related_fields}")
            else:
                print("   ❌ No se encontraron campos con URLs de imágenes")
                print("   💡 La tabla articles no contiene imágenes directamente")
            
            # Obtener categorías/departamentos únicos
            dept_result = await session.execute(
                select(Article.department_name).distinct().limit(10)
            )
            departments = [row[0] for row in dept_result.fetchall()]
            
            print(f"\n🏬 Departamentos disponibles (muestra):")
            for dept in departments:
                print(f"   • {dept}")
            
            # Verificar si hay transacciones asociadas (para precios)
            from database.models import Transaction
            trans_result = await session.execute(
                select(Transaction).limit(1)
            )
            sample_transaction = trans_result.scalar_one_or_none()
            
            if sample_transaction:
                print(f"\n💰 INFORMACIÓN DE PRECIOS:")
                print(f"   ✅ Hay transacciones con precios reales")
                print(f"   • Precio de ejemplo: ${sample_transaction.price}")
                print("   💡 Los precios se pueden obtener de la tabla transactions")
            else:
                print(f"\n💰 INFORMACIÓN DE PRECIOS:")
                print("   ❌ No se encontraron transacciones con precios")
        
        print("\n" + "=" * 80)
        print("📝 RESUMEN:")
        print("   • La tabla articles contiene información detallada de productos")
        print("   • NO hay campo directo para imágenes")
        print("   • Los precios están en la tabla transactions")
        print("   • Tenemos categorías (departamentos) y descripciones")
        print("\n💡 RECOMENDACIÓN:")
        print("   • Usar imágenes generadas dinámicamente basadas en el nombre del producto")
        print("   • O agregar un campo image_url a la tabla articles")
        
    except Exception as e:
        print(f"❌ Error al explorar: {e}")
    finally:
        await Database.cleanup()

if __name__ == "__main__":
    asyncio.run(explore_articles())