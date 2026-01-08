import asyncio
from celery import shared_task

from config.dependencies import get_settings
from notifications.emails import EmailSender


@shared_task(name="tasks.send_activation_email")
def send_activation_email_task(email: str, activation_link: str) -> None:
    """
    Celery task to send activation email.
    """

    async def _send():
        settings = get_settings()

        sender = EmailSender(
            hostname=settings.SMTP_HOST,
            port=settings.SMTP_PORT,
            email=settings.SMTP_EMAIL,
            password=settings.SMTP_PASSWORD,
            use_tls=settings.SMTP_USE_TLS,
            template_dir=settings.EMAIL_TEMPLATE_DIR,
            activation_email_template_name=settings.ACTIVATION_EMAIL_TEMPLATE,
            activation_complete_email_template_name=settings.ACTIVATION_COMPLETE_TEMPLATE,
            password_email_template_name=settings.PASSWORD_RESET_TEMPLATE,
            password_complete_email_template_name=settings.PASSWORD_RESET_COMPLETE_TEMPLATE,
        )

        await sender.send_activation_email(email, activation_link)

    asyncio.run(_send())
