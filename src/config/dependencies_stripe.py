import stripe
from typing import Optional
from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from config import BaseAppSettings, get_settings
from config.dependencies import get_payment_email_sender
from notifications import EmailSenderInterface
from database import get_db


class StripeWebhookHandler:
    def __init__(self, webhook_secrets: str):
        self.webhook_secrets = webhook_secrets

    async def handle_webhook(self, payload: bytes, sig_header: str):
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, self.webhook_secrets
            )
            return event
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except stripe.error.SignatureVerificationError as e:
            raise HTTPException(status_code=400, detail=str(e))


def get_stripe_webhook_handler(
        settings: BaseAppSettings = Depends(get_settings)
) -> StripeWebhookHandler:
    stripe.api_key = settings.STRIPE_SECRET_KEY
    return StripeWebhookHandler(
        webhook_secrets=settings.STRIPE_WEBHOOK_SECRET
    )

def get_payment_service(
        stripe_handler: StripeWebhookHandler = Depends(get_stripe_webhook_handler),
        email_sender: EmailSenderInterface = Depends(get_payment_email_sender),
        db: AsyncSession = Depends(get_db)
) -> "PaymentService":
    class PaymentService:
        def __init__(self, stripe_handler, email_sender, db):
            self.stripe_handler = stripe_handler,
            self.email_sender = email_sender,
            self.db = db

        async def process_payment_confirmation(
            self,
            payment_intent_id: int,
            customer_email: str,
            amount: float,
            items: list
            ):
            await self.update_payment_status

