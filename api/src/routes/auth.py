from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr
from typing import Optional
import logging

from ..auth import AuthService

logger = logging.getLogger(__name__)

router = APIRouter()

# Modelos Pydantic para validación
class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class SignupNewUserRequest(BaseModel):
    name: str
    email: EmailStr
    password: str
    age: Optional[int] = None
    postal_code: str = "00000"

class SignupLinkUserRequest(BaseModel):
    customer_id: str
    name: str
    email: EmailStr
    password: str

class AuthResponse(BaseModel):
    success: bool
    message: str
    customer_id: Optional[str] = None
    name: Optional[str] = None
    email: Optional[str] = None
    error: Optional[str] = None

@router.post("/login", response_model=AuthResponse)
async def login(request: LoginRequest):
    """
    Autentica un usuario con email y contraseña.
    """
    try:
        result = await AuthService.authenticate_user(request.email, request.password)

        if result["success"]:
            return AuthResponse(
                success=True,
                message=result["message"],
                customer_id=result["customer_id"],
                name=result["name"],
                email=result["email"]
            )
        else:
            raise HTTPException(status_code=401, detail=result["error"])

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en login: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@router.post("/signup/new", response_model=AuthResponse)
async def signup_new_user(request: SignupNewUserRequest):
    """
    Crea un nuevo usuario completamente nuevo.
    """
    try:
        result = await AuthService.create_new_user(
            name=request.name,
            email=request.email,
            password=request.password,
            age=request.age,
            postal_code=request.postal_code
        )

        if result["success"]:
            return AuthResponse(
                success=True,
                message=result["message"],
                customer_id=result["customer_id"]
            )
        else:
            raise HTTPException(status_code=400, detail=result["error"])

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en signup nuevo: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@router.post("/signup/link", response_model=AuthResponse)
async def signup_link_user(request: SignupLinkUserRequest):
    """
    Vincula credenciales a un usuario existente de Kaggle.
    """
    try:
        result = await AuthService.link_existing_user(
            customer_id=request.customer_id,
            name=request.name,
            email=request.email,
            password=request.password
        )

        if result["success"]:
            return AuthResponse(
                success=True,
                message=result["message"],
                customer_id=result["customer_id"]
            )
        else:
            raise HTTPException(status_code=400, detail=result["error"])

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en signup vinculado: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@router.get("/user/{customer_id}")
async def get_user_info(customer_id: str):
    """
    Obtiene información de un usuario por su ID.
    """
    try:
        user_info = await AuthService.get_user_by_id(customer_id)

        if user_info:
            return {
                "success": True,
                "user": user_info
            }
        else:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al obtener usuario: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@router.get("/customers/unlinked")
async def get_unlinked_customers(limit: int = 10, offset: int = 0):
    """
    Obtiene una lista de usuarios de Kaggle que no tienen credenciales vinculadas.
    Útil para el signup vinculado.
    """
    try:
        from database.lib import Database
        from database.models import Customer
        from sqlalchemy import select

        async with Database.get_session() as session:
            result = await session.execute(
                select(Customer)
                .where(Customer.is_authenticated == False)
                .limit(limit)
                .offset(offset)
            )
            customers = result.scalars().all()

            return {
                "success": True,
                "customers": [
                    {
                        "customer_id": customer.customer_id,
                        "club_member_status": customer.club_member_status,
                        "age": customer.age,
                        "postal_code": customer.postal_code
                    }
                    for customer in customers
                ]
            }

    except Exception as e:
        logger.error(f"Error al obtener usuarios no vinculados: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")
