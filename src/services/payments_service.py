import logging
from typing import Dict, Any

import stripe

from database import Order, UserModel

from config import get_settings
from schemas import PaymentRequestSchema

app_settings = get_settings()
logger = logging.GetLogger(__name__)


class MockPaymentProcessor:
    """Basic mockups for dev"""

    async def create_payment_intent(self, amount, email):
        return {"success": True, "transaction_id": "dev_mock_123"}


async def process_payment(
        order: Order,
        payment_data: PaymentRequestSchema,
        user: UserModel) -> Dict[str, Any]:
    stripe.apy_key = app_settings.STRIPE_SECRET_KEY

    try:
        amount_in_cents = int(order.total_amount * 100)
        payment_intent = stripe.PaymentIntent.create(
            amount=amount_in_cents,
            currency=app_settings.STRIPE_CURRENCY.lower(),
            payment_method=payment_data.payment_method_id,
            confirm=True,
            confirmation_method="automatic",
            return_url = app_settings.STRIPE_SUCCESS_URL,
            metadata={
                "order_id": str(order.id),
                "user_id": str(user.id),
                "user_email": user.email,
                "movie_count": str(len(order.order_items))
            },
            description=f"Order #{order.id} - {len(order.order_items)} movies",
            receipt_email=str(user.email if user.email else None),
            automatic_payment_methods={
                "enabled": True,
                "allow_redirects": "always"
            }
        )
        logger.info(f"Stripe PaymentIntent created: {payment_intent.id}, status: {payment_intent.status}")
        if payment_intent.status == "succeeded":
            return{
                "success": True,
                "transaction_id": payment_intent.id,
                "payment_intent_id": payment_intent.id,
                "status": "succeeded",
                "client_secret": payment_intent.client_secret,
                "requires_action": False,
                "message": "Payment successful"
            }
        elif payment_intent.status == "requires_action":
            return {
                "success": True,
                "transaction_id": payment_intent.id,
                "payment_intent_id": payment_intent.id,
                "status": "requires_action",
                "client_secret": payment_intent.client_secret,
                "requires_action": True,
                "message": "Additional authentication required",
                "next_action": payment_intent.next_action
            }
        elif payment_intent.status == "processing":
            return {
                "success": True,
                "transaction_id": payment_intent.id,
                "status": "processing",
                "requires_action": False,
                "message": "Payment is being processed"
            }
        else:
            error_msg = payment_intent.last_payment_error
            logger.error(f"Stripe payment failed: {payment_intent.status}, error: {error_msg}")
            return {
                "success": False,
                "transaction_id": payment_intent.id,
                "status": payment_intent.status,
                "error": error_msg,
                "message": f"Payment failed: {payment_intent.status}"
            }
    except stripe.error.CardError as e:
        logger.error(f"Stripe CardError: {e.user_message}")
        return {
            "success": False,
            "error": {
                "type": "card_error",
                "code": e.code,
                "message": e.user_message
            },
            "message": e.user_message,
            "suggestion": "Try a different payment method" if e.code == "card_declined" else None
        }
    except stripe.error.RateLimitError as e:
        logger.error(f"Stripe RateLimitError: {str(e)}")
        return {
            "success": False,
            "error": "rate_limit",
            "message": "Too many requests. Please try again later."
        }
    except stripe.error.InvalidRequestError as e:
        logger.error(f"Stripe InvalidRequestError: {str(e)}")
        return {
            "success": False,
            "error": "invalid_request",
            "message": "Invalid payment data"
        }
    except stripe.error.AuthenticationError as e:
        logger.error(f"Stripe AuthenticationError: {str(e)}")
        return {
            "success": False,
            "error": "authentication",
            "message": "Payment service authentication failed"
        }

    except stripe.error.StripeError as e:
        logger.error(f"Stripe error: {str(e)}")
        return {
            "success": False,
            "error": "stripe_error",
            "message": "Payment service error"
        }
    except Exception as e:
        logger.error(f"Unexpected error in process_payment: {str(e)}")
        return {
            "success": False,
            "error": "internal_error",
            "message": "Internal server error"
        }