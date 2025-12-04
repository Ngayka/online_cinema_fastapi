import pytest
from decimal import Decimal


@pytest.mark.asyncio
async def test_payment_success(mock_payment_processor):

    mock_payment_processor.set_response({
        "success": True,
        "transaction_id": "test_success_123"
    })

    response = await client.post("/payments", json={"amount": "9.99"})
    assert response.status_code == 200
    assert response.json()["transaction_id"] == "test_success_123"


@pytest.mark.asyncio
async def test_payment_failure(mock_payment_processor):

    mock_payment_processor.set_response({
        "success": False,
        "error": "Card declined"
    })

    response = await client.post("/payments", json={"amount": "9.99"})
    assert response.status_code == 402
