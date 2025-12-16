import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, patch, MagicMock

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from database import Order, OrderStatusEnum, CartItem, Cart


@pytest.mark.asyncio
async def test_create_order_success(
        client,
        db_session,
        test_cart,
        auth_headers,
        test_movie
):
    """Test successful order creation from cart"""
    test_movie.current_price = Decimal("10.00")
    db_session.add(test_movie)
    await db_session.commit()

    cart_item = CartItem(
        cart_id=test_cart.id,
        movie_id=test_movie.id
    )
    db_session.add(cart_item)
    await db_session.commit()

    response = await client.post("/api/v1/orders/", headers=auth_headers)
    assert response.status_code == 201


async def test_get_all_orders(
        client,
        test_user,
        db_session,
        test_cart,
        auth_headers,
        test_movie,
        test_movie2
):
    test_movie.current_price = Decimal("10.00")
    test_movie2.current_price = Decimal("5.25")
    db_session.add_all([test_movie, test_movie2])
    await db_session.commit()

    cart_item_1 = CartItem(
        cart_id=test_cart.id,
        movie_id=test_movie.id
    )
    cart_item_2 = CartItem(
        cart_id=test_cart.id,
        movie_id=test_movie2.id
    )
    db_session.add_all([cart_item_1, cart_item_2])
    await db_session.commit()

    result = await db_session.execute(
        select(Cart)
        .where(Cart.id == test_cart.id)
        .options(selectinload(Cart.items).selectinload(CartItem.movie))
    )
    test_cart = result.scalars().first()

    from config.order_config import create_order_service

    await create_order_service(db_session, test_cart, user=test_user)

    response = await client.get("/api/v1/orders/me", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data["orders"], list)
    assert len(data["orders"]) == 1


async def test_cancel_order(
        client,
        test_user,
        db_session,
        test_cart,
        auth_headers,
        test_movie
):
    test_movie.current_price = Decimal("5.25")
    db_session.add(test_movie)
    await db_session.commit()

    cart_item = CartItem(
        cart_id=test_cart.id,
        movie_id=test_movie.id
    )
    db_session.add(cart_item)
    await db_session.commit()

    result = await db_session.execute(
        select(Cart)
        .where(Cart.id == test_cart.id)
        .options(selectinload(Cart.items).selectinload(CartItem.movie))
    )
    cart = result.scalar_one()

    from config.order_config import create_order_service

    order = await create_order_service(db_session, cart, user=test_user)
    response = await client.post(f"/api/v1/orders/{order.id}/cancel", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "successfully cancelled" in data["message"]

    await db_session.refresh(order)
    assert order.status == OrderStatusEnum.CANCELED


async def test_pay_order_with_mock(
        client,
        test_user,
        db_session,
        test_cart,
        auth_headers,
        payment_data,
        test_movie
):
    test_user.is_active = True
    db_session.add(test_user)
    await db_session.commit()

    test_movie.current_price = Decimal("5.25")
    db_session.add(test_movie)
    await db_session.commit()

    cart_item = CartItem(
        cart_id=test_cart.id,
        movie_id=test_movie.id
    )
    db_session.add(cart_item)
    await db_session.commit()

    result = await db_session.execute(
        select(Cart)
        .where(Cart.id == test_cart.id)
        .options(selectinload(Cart.items).selectinload(CartItem.movie))
    )
    cart = result.scalar_one()

    from config.order_config import create_order_service

    order = await create_order_service(db_session, cart, user=test_user)

    assert order.order_items
    assert order.order_items[0].price_at_order is not None

    from routes.orders import get_payment_service
    from main import app

    class FakePaymentService:
        async def process_payment(self, order, payment_data, user):
            return {
                "success": True,
                "transaction_id": "mock_tx_123",
                "message": "Payment successful",
                "requires_action": False,
            }

    app.dependency_overrides[get_payment_service] = lambda: FakePaymentService()

    try:

        response = await client.post(
            f"/api/v1/orders/{order.id}/pay",
            json=payment_data.model_dump(),
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        assert data["id"] == order.id
        assert float(data["total_amount"]) == float(order.total_amount)

    finally:
        app.dependency_overrides.clear()
