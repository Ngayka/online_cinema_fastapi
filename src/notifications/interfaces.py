from abc import ABC, abstractmethod
from decimal import Decimal


class EmailSenderInterface(ABC):

    @abstractmethod
    async def send_activation_email(self, email: str, activation_link: str) -> None:
        """
        Asynchronously send an account activation email.

        Args:
            email (str): The recipient's email address.
            activation_link (str): The activation link to include in the email.
        """
        pass

    @abstractmethod
    async def send_activation_complete_email(self, email: str, login_link: str) -> None:
        """
        Asynchronously send an email confirming that the account has been activated.

        Args:
            email (str): The recipient's email address.
            login_link (str): The login link to include in the email.
        """
        pass

    @abstractmethod
    async def send_password_reset_email(self, email: str, reset_link: str) -> None:
        """
        Asynchronously send a password reset request email.

        Args:
            email (str): The recipient's email address.
            reset_link (str): The password reset link to include in the email.
        """
        pass

    @abstractmethod
    async def send_password_reset_complete_email(
        self, email: str, login_link: str
    ) -> None:
        """
        Asynchronously send an email confirming that the password has been reset.

        Args:
            email (str): The recipient's email address.
            login_link (str): The login link to include in the email.
        """
        pass

    @abstractmethod
    async def send_payment_confirmation_email(
        self,
        email: str,
        order_id: int,
        amount: Decimal,
        transaction_id: str,
    ) -> None:
        """
        Asynchronously send a payment confirmation email.

        Args:
            email (str): The recipient's email address.
            order_id (int): The order ID.
            amount (Decimal): The payment amount.
            transaction_id (str): The transaction reference ID.

        Raises:
            BaseEmailError: If sending the email fails.
        """
        pass
