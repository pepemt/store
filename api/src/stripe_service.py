import os
import stripe
from typing import Optional
from dataclasses import dataclass

from .config import setup_logging

logger = setup_logging()


@dataclass
class CheckoutSessionResult:
    """Resultado de crear una sesión de checkout."""
    session_id: str
    checkout_url: str


@dataclass
class SessionStatus:
    """Estado de una sesión de checkout."""
    status: str  # "open", "complete", "expired"
    payment_status: str  # "paid", "unpaid", "no_payment_required"
    payment_intent_id: Optional[str] = None
    customer_email: Optional[str] = None


class StripeService:
    """Servicio para operaciones de Stripe."""

    _initialized: bool = False

    @classmethod
    def initialize(cls) -> None:
        """Inicializa el cliente de Stripe con la API key."""
        api_key = os.getenv("STRIPE_SECRET_KEY")
        if not api_key:
            logger.warning("STRIPE_SECRET_KEY no configurada")
            return

        stripe.api_key = api_key
        cls._initialized = True
        logger.info("Stripe Service inicializado")

    @classmethod
    def is_initialized(cls) -> bool:
        """Verifica si el servicio está inicializado."""
        return cls._initialized

    @classmethod
    def create_checkout_session(
        cls,
        order_id: int,
        line_items: list[dict],
        customer_email: Optional[str] = None,
        success_url: Optional[str] = None,
        cancel_url: Optional[str] = None,
    ) -> CheckoutSessionResult:
        """
        Crea una sesión de Stripe Checkout.

        Args:
            order_id: ID de la orden en nuestra BD
            line_items: Lista de items para Stripe con formato:
                [{"price_data": {"currency": "usd", "unit_amount": 1999, "product_data": {"name": "..."}}, "quantity": 1}]
            customer_email: Email del cliente (opcional)
            success_url: URL de redirección tras pago exitoso
            cancel_url: URL de redirección si cancela

        Returns:
            CheckoutSessionResult con session_id y checkout_url
        """
        if not cls._initialized:
            cls.initialize()

        frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")

        if not success_url:
            success_url = f"{frontend_url}/checkout/success?session_id={{CHECKOUT_SESSION_ID}}"
        if not cancel_url:
            cancel_url = f"{frontend_url}/checkout/cancel"

        session_params = {
            "mode": "payment",
            "line_items": line_items,
            "success_url": success_url,
            "cancel_url": cancel_url,
            "metadata": {
                "order_id": str(order_id),
            },
        }

        if customer_email:
            session_params["customer_email"] = customer_email

        session = stripe.checkout.Session.create(**session_params)

        logger.info(f"Stripe Checkout Session creada: {session.id} para orden {order_id}")

        return CheckoutSessionResult(
            session_id=session.id,
            checkout_url=session.url,
        )

    @classmethod
    def get_session_status(cls, session_id: str) -> SessionStatus:
        """
        Obtiene el estado de una sesión de checkout.

        Args:
            session_id: ID de la sesión de Stripe

        Returns:
            SessionStatus con estado actual
        """
        if not cls._initialized:
            cls.initialize()

        session = stripe.checkout.Session.retrieve(session_id)

        return SessionStatus(
            status=session.status,
            payment_status=session.payment_status,
            payment_intent_id=session.payment_intent,
            customer_email=session.customer_email,
        )

    @classmethod
    def verify_webhook_signature(cls, payload: bytes, signature: str) -> dict:
        """
        Verifica la firma de un webhook de Stripe.

        Args:
            payload: Body raw del request
            signature: Header stripe-signature

        Returns:
            Evento de Stripe verificado

        Raises:
            ValueError: Si la firma es inválida
        """
        webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")
        if not webhook_secret:
            raise ValueError("STRIPE_WEBHOOK_SECRET no configurada")

        try:
            event = stripe.Webhook.construct_event(
                payload, signature, webhook_secret
            )
            return event
        except stripe.error.SignatureVerificationError as e:
            logger.error(f"Error de verificación de firma Stripe: {e}")
            raise ValueError("Firma de webhook inválida")

    @classmethod
    def get_publishable_key(cls) -> Optional[str]:
        """Retorna la publishable key para el frontend."""
        return os.getenv("STRIPE_PUBLISHABLE_KEY")
