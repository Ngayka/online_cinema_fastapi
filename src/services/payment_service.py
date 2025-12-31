import asyncio
import logging
from typing import Any

import stripe

from config.settings import Settings
from database import Order, UserModel
from schemas import PaymentRequestSchema

logger = logging.getLogger(__name__)


class MockPaymentProcessor:
    """Basic mockups for dev"""

    async def create_payment_intent(self, amount, email):
        return {"success": True, "transaction_id": "dev_mock_123"}


class PaymentService:
    def __init__(self, settings: Settings):
        self.settings = settings
        stripe.api_key = settings.STRIPE_SECRET_KEY
        self.currency = settings.STRIPE_CURRENCY
        self.success_url = settings.STRIPE_SUCCESS_URL

    async def process_payment(
        self, order: "Order", payment_data: PaymentRequestSchema, user: "UserModel"
    ) -> dict[str, Any]:

        try:
            amount_in_cents = int(order.total_amount * 100)
            payment_intent_data = {
                "amount": amount_in_cents,
                "currency": self.currency,
                "payment_method": payment_data.payment_method_id,
                "confirm": True,
                "confirmation_method": "automatic",
                "return_url": self.success_url,
                "metadata": {
                    "order_id": str(order.id),
                    "user_id": str(user.id),
                    "user_email": user.email,
                    "movie_count": str(len(order.order_items)),
                },
                "description": f"Order #{order.id} - {len(order.order_items)} movies",
                "automatic_payment_methods": {
                    "enabled": True,
                    "allow_redirects": "always",
                },
            }
            if user.email:
                payment_intent_data["receipt_email"] = user.email

            payment_intent = await asyncio.to_thread(
                stripe.PaymentIntent.create, **payment_intent_data
            )

            return self._handle_payment_intent_response(payment_intent)

        except stripe.error.StripeError as e:
            logger.error(f"Stripe Error: {str(e)}")
            return {"success": False, "error": str(e), "message": "Payment failed"}

        except Exception as e:
            logger.error(f"Unexpected error in process_payment: {str(e)}")

            return {
                "success": False,
                "error": "internal_error",
                "message": "Internal server error",
            }

    def _handle_payment_intent_response(self, payment_intent) -> dict[str, Any]:
        status = payment_intent.status
        base_response = {
            "transaction_id": payment_intent.id,
            "payment_intent_id": payment_intent.id,
            "client_secret": getattr(payment_intent, "client_secret", None),
            "status": status,
        }

        if status == "succeeded":
            return {
                **base_response,
                "success": True,
                "requires_action": False,
                "message": "Payment successful",
            }
        elif status == "requires_action":
            return {
                **base_response,
                "success": True,
                "requires_action": True,
                "message": "Additional authentication required",
                "next_action": getattr(payment_intent, "next_action", None),
            }
        elif status == "processing":
            return {
                **base_response,
                "success": True,
                "requires_action": False,
                "message": "Payment is being processed",
            }
        else:
            error_msg = getattr(payment_intent, "last_payment_error", None)
            return {
                **base_response,
                "success": False,
                "error": error_msg,
                "message": f"Payment failed: {status}",
            }
