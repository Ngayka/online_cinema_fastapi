import stripe
from typing import Dict, Any

from database import Order, UserModel
from schemas import PaymentRequestSchema


async def process_payment(
        order: Order,
        payment_data: PaymentRequestSchema,
        user: UserModel
) -> Dict[str, Any]:
    stripe.api_key = app