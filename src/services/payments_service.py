from typing import Dict, Any

from database import Order, UserModel

from config import get_settings
from schemas import PaymentRequestSchema

app_settings = get_settings()


class MockPaymentProcessor:
    """Basic mockups for dev"""

    async def create_payment_intent(self, amount, email):
        return {"success": True, "transaction_id": "dev_mock_123"}


class StripePaymentService:
    def __init__(self):
        if app_settings.MOCK_PAYMENTS:
            self.processor = MockPaymentProcessor()
        else:
            import stripe
            stripe.api_key = app_settings.STRIPE_SECRET_KEY
            self.stripe = stripe
            self.currency = app_settings.STRIPE_CURRENCY
    async def process_payment(
            self,
            order: Order,
            payment_data: PaymentRequestSchema,
            user: UserModel
    ) -> Dict[str, Any]:
        try:

