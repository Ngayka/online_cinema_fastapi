class TestPaymentProcessor:
    """Advanced mockup for tests with flexible behavior"""

    def __init__(self):
        self.responses = []
        self.calls = []

    def set_response(self, response):
        self.responses.append(response)

    async def create_payment_intent(self, amount, email):
        self.calls.append({"amount": amount, "email": email})
        if self.responses:
            return self.responses.pop(0)
        return {"success": True, "transaction_id": "test_123"}
