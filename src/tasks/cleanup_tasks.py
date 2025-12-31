from datetime import datetime, timezone
from celery import shared_task
from sqlalchemy import delete

from database import ActivationTokenModel, PasswordResetTokenModel
from database.session_postgresql import AsyncPostgresqlSessionLocal


@shared_task
def cleanup_expired_tokens():
    """
    Celery task to delete expired activation and password reset tokens.
    NOTE: This is a synchronous Celery task, but it runs async SQLAlchemy under the hood.
    """

    async def _cleanup():
        async with AsyncPostgresqlSessionLocal() as session:
            now = datetime.now(timezone.utc)
            await session.execute(
                delete(ActivationTokenModel).where(
                    ActivationTokenModel.expires_at < now
                )
            )

            await session.execute(
                delete(PasswordResetTokenModel).where(
                    PasswordResetTokenModel.expires_at < now
                )
            )
            await session.comit()

        import asyncio

        asyncio.run(_cleanup())

        return "Expired tokens deleted"
