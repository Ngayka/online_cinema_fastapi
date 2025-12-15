import logging
from typing import Dict, Any

import stripe
from fastapi import HTTPException

from config.settings import Settings
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
            self,
            order: "Order",
            payment_data: PaymentRequestSchema,
            user: "UserModel") -> Dict[str, Any]:

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
                    "movie_count": str(len(order.order_items))
                },
                "description": f"Order #{order.id} - {len(order.order_items)} movies",
                "automatic_payment_methods": {
                    "enabled": True,
                    "allow_redirects": "always"
                }
            }
            if user.email:
                payment_intent_data["receipt_email"] = user.email

            payment_intent = stripe.PaymentIntent.create(**payment_intent_data)

            logger.info(f"Stripe PaymentIntent created: {payment_intent.id}, "
                        f"status: {payment_intent.status}")
            return self._handle_payment_intent_response(payment_intent)

        except stripe.error.CardError as e:
            logger.error(f"Stripe CardError: {e.user_message}")
            return self._handle_card_error(e)

        except stripe.error.RateLimitError as e:
            logger.error(f"Stripe RateLimitError: {str(e)}")
            return self._handle_rate_limit_error()

        except stripe.error.InvalidRequestError as e:
            logger.error(f"Stripe InvalidRequestError: {str(e)}")
            return self._handle_invalid_request_error()

        except stripe.error.AuthenticationError as e:
            logger.error(f"Stripe AuthenticationError: {str(e)}")
            return self._handle_authentication_error()

        except stripe.error.StripeError as e:
            logger.error(f"Stripe error: {str(e)}")
            return self._handle_generic_stripe_error()

        except Exception as e:
            logger.error(f"Unexpected error in process_payment: {str(e)}")
            return self._handle_unexpected_error()

    def _handle_payment_intent_response(self, payment_intent) -> Dict[str, Any]:
        """Processing response from Stripe"""
        status = payment_intent.status

        base_response = {
            "transaction_id": payment_intent.id,
            "payment_intent_id": payment_intent.id,
            "client_secret": payment_intent.client_secret,
            "status": status
        }

        if status == "succeeded":
            return {
                **base_response,
                "success": True,
                "requires_action": False,
                "message": "Payment successful"
            }

        elif status == "requires_action":
            return {
                **base_response,
                "success": True,
                "requires_action": True,
                "message": "Additional authentication required",
                "next_action": payment_intent.next_action
            }

        elif status == "processing":
            return {
                **base_response,
                "success": True,
                "requires_action": False,
                "message": "Payment is being processed"
            }

        else:
            error_msg = payment_intent.last_payment_error
            logger.error(f"Stripe payment failed: {status}, error: {error_msg}")
            return {
                **base_response,
                "success": False,
                "error": error_msg,
                "message": f"Payment failed: {status}"
            }

    def _handle_card_error(self, e) -> Dict[str, Any]:
        """Card error handling"""
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

    def _handle_rate_limit_error(self) -> Dict[str, Any]:
        return {
            "success": False,
            "error": "rate_limit",
            "message": "Too many requests. Please try again later."
        }

    def _handle_invalid_request_error(self) -> Dict[str, Any]:
        return {
            "success": False,
            "error": "invalid_request",
            "message": "Invalid payment data"
        }

    def _handle_authentication_error(self) -> Dict[str, Any]:
        return {
            "success": False,
            "error": "authentication",
            "message": "Payment service authentication failed"
        }

    def _handle_generic_stripe_error(self) -> Dict[str, Any]:
        return {
            "success": False,
            "error": "stripe_error",
            "message": "Payment service error"
        }

    def _handle_unexpected_error(self) -> Dict[str, Any]:
        return {
            "success": False,
            "error": "internal_error",
            "message": "Internal server error"
        }

    async def verify_webhook_signature(
            self,
            payload: bytes,
            sig_header: str
    ) -> stripe.Event:
        """Stripe webhook validation"""
        try:
            event = stripe.Webhook.construct_event(
                payload,
                sig_header,
                self.settings.STRIPE_WEBHOOK_SECRET
            )
            return event
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid payload: {str(e)}")
        except stripe.error.SignatureVerificationError as e:
            raise HTTPException(status_code=400, detail=f"Invalid signature: {str(e)}")

    async def handle_webhook_event(self, event: stripe.Event) -> Dict[str, Any]:
        """Webhook event handling"""
        event_type = event.type

        if event_type == "payment_intent.succeeded":
            return await self._process_successful_webhook(event)
        elif event_type == "payment_intent.payment_failed":
            return await self._process_failed_webhook(event)
        elif event_type == "payment_intent.processing":
            return await self._process_processing_webhook(event)

        return {
            "status": "ignored",
            "event_type": event_type,
            "message": f"Event {event_type} received but not processed"
        }

    async def _process_successful_webhook(self, event: stripe.Event) -> Dict[str, Any]:
        """Successful webhook payment handling"""
        payment_intent = event.data.object
        return {
            "status": "success",
            "payment_id": payment_intent.id,
            "order_id": payment_intent.metadata.get("order_id"),
            "user_id": payment_intent.metadata.get("user_id")
        }

    async def _process_failed_webhook(self, event: stripe.Event) -> Dict[str, Any]:
        """Unsuccessful webhook payment handling"""
        payment_intent = event.data.object
        return {
            "status": "failed",
            "payment_id": payment_intent.id,
            "error": payment_intent.get('last_payment_error', {}).get('message', 'Unknown error')
        }

    async def _process_processing_webhook(self, event: stripe.Event) -> Dict[str, Any]:
        """Payment processing in progress"""
        payment_intent = event.data.object
        return {
            "status": "processing",
            "payment_id": payment_intent.id,
            "message": "Payment is being processed"
        }
