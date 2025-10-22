import hashlib
import secrets
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database.lib import Database
from database.models import Customer

logger = logging.getLogger(__name__)

class AuthService:
    """Servicio para manejar autenticación de usuarios."""
    
    @staticmethod
    def hash_password(password: str) -> str:
        """Hashea una contraseña usando SHA-256 con salt."""
        salt = secrets.token_hex(16)
        password_hash = hashlib.sha256((password + salt).encode()).hexdigest()
        return f"{salt}:{password_hash}"
    
    @staticmethod
    def verify_password(password: str, password_hash: str) -> bool:
        """Verifica si una contraseña coincide con el hash."""
        try:
            salt, stored_hash = password_hash.split(':')
            password_hash_to_check = hashlib.sha256((password + salt).encode()).hexdigest()
            return password_hash_to_check == stored_hash
        except ValueError:
            return False
    
    @staticmethod
    async def create_new_user(
        name: str, 
        email: str, 
        password: str,
        age: Optional[int] = None,
        postal_code: str = "00000"
    ) -> Dict[str, Any]:
        """Crea un nuevo usuario completamente nuevo."""
        try:
            async with Database.get_session() as session:
                # Verificar si el email ya existe
                result = await session.execute(
                    select(Customer).where(Customer.email == email)
                )
                if result.scalar_one_or_none():
                    return {"success": False, "error": "El email ya está registrado"}
                
                # Generar un nuevo customer_id único
                customer_id = f"NEW_{secrets.token_hex(8)}"
                
                # Crear el nuevo usuario
                new_customer = Customer(
                    customer_id=customer_id,
                    name=name,
                    email=email,
                    password_hash=AuthService.hash_password(password),
                    is_authenticated=True,
                    created_at=datetime.now(),
                    club_member_status="ACTIVE",
                    fashion_news_frequency="Regularly",
                    age=age,
                    postal_code=postal_code,
                    fn=1.0,
                    active=1.0
                )
                
                session.add(new_customer)
                await session.commit()
                
                logger.info(f"Nuevo usuario creado: {email}")
                return {
                    "success": True,
                    "customer_id": customer_id,
                    "message": "Usuario creado exitosamente"
                }
                
        except Exception as e:
            logger.error(f"Error al crear nuevo usuario: {e}")
            return {"success": False, "error": "Error interno del servidor"}
    
    @staticmethod
    async def link_existing_user(
        customer_id: str,
        name: str,
        email: str,
        password: str
    ) -> Dict[str, Any]:
        """Vincula credenciales a un usuario existente de la BD."""
        try:
            async with Database.get_session() as session:
                # Buscar el usuario existente
                result = await session.execute(
                    select(Customer).where(Customer.customer_id == customer_id)
                )
                customer = result.scalar_one_or_none()
                
                if not customer:
                    return {"success": False, "error": "Usuario no encontrado"}
                
                if customer.is_authenticated:
                    return {"success": False, "error": "Este usuario ya tiene credenciales"}
                
                # Verificar si el email ya está en uso
                email_result = await session.execute(
                    select(Customer).where(Customer.email == email)
                )
                if email_result.scalar_one_or_none():
                    return {"success": False, "error": "El email ya está registrado"}
                
                # Actualizar el usuario existente
                customer.name = name
                customer.email = email
                customer.password_hash = AuthService.hash_password(password)
                customer.is_authenticated = True
                customer.created_at = datetime.now()
                
                await session.commit()
                
                logger.info(f"Usuario existente vinculado: {customer_id} -> {email}")
                return {
                    "success": True,
                    "customer_id": customer_id,
                    "message": "Usuario vinculado exitosamente"
                }
                
        except Exception as e:
            logger.error(f"Error al vincular usuario: {e}")
            return {"success": False, "error": "Error interno del servidor"}
    
    @staticmethod
    async def authenticate_user(email: str, password: str) -> Dict[str, Any]:
        """Autentica un usuario con email y contraseña."""
        try:
            async with Database.get_session() as session:
                # Buscar usuario por email
                result = await session.execute(
                    select(Customer).where(Customer.email == email)
                )
                customer = result.scalar_one_or_none()
                
                if not customer or not customer.is_authenticated:
                    return {"success": False, "error": "Credenciales inválidas"}
                
                # Verificar contraseña
                if not AuthService.verify_password(password, customer.password_hash):
                    return {"success": False, "error": "Credenciales inválidas"}
                
                logger.info(f"Usuario autenticado: {email}")
                return {
                    "success": True,
                    "customer_id": customer.customer_id,
                    "name": customer.name,
                    "email": customer.email,
                    "message": "Autenticación exitosa"
                }
                
        except Exception as e:
            logger.error(f"Error al autenticar usuario: {e}")
            return {"success": False, "error": "Error interno del servidor"}
    
    @staticmethod
    async def get_user_by_id(customer_id: str) -> Optional[Dict[str, Any]]:
        """Obtiene información de un usuario por su ID."""
        try:
            async with Database.get_session() as session:
                result = await session.execute(
                    select(Customer).where(Customer.customer_id == customer_id)
                )
                customer = result.scalar_one_or_none()
                
                if not customer:
                    return None
                
                return {
                    "customer_id": customer.customer_id,
                    "name": customer.name,
                    "email": customer.email,
                    "age": customer.age,
                    "club_member_status": customer.club_member_status,
                    "is_authenticated": customer.is_authenticated,
                    "created_at": customer.created_at.isoformat() if customer.created_at else None
                }
                
        except Exception as e:
            logger.error(f"Error al obtener usuario: {e}")
            return None
