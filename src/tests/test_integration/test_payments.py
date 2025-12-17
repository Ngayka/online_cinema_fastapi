import pytest
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from database import Payment, PaymentStatusEnum, CartItem, Cart, PaymentItem


@pytest.mark.asyncio
async def test_get_all_payments(
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
    payment = Payment(
        user_id=test_user.id,
        order_id=order.id,
        amount=Decimal("9.99"),
        status=PaymentStatusEnum.SUCCESSFUL,
        external_payment_id="test_tx_123"
    )
    db_session.add(payment)
    await db_session.commit()

    response = await client.get("/api/v1/payments/", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["external_payment_id"] == "test_tx_123"
    assert Decimal(data[0]["amount"]) == Decimal("9.99")


@pytest.mark.asyncio
async def test_payment_by_id(
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

    payment = Payment(
        user_id=test_user.id,
        order_id=order.id,
        amount=Decimal("9.99"),
        status=PaymentStatusEnum.SUCCESSFUL,
        external_payment_id="test_tx_123",
        order=order
    )
    db_session.add(payment)
    await db_session.flush()

    payment_item = PaymentItem(
        payment_id=payment.id,
        order_item_id=order.order_items[0].id,
        price_at_payment=order.order_items[0].price_at_order
    )
    db_session.add(payment_item)
    await db_session.commit()

    response = await client.get(f"/api/v1/payments/{payment.id}", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["external_payment_id"] == "test_tx_123"
    assert Decimal(data["amount"]) == Decimal("9.99")
    assert data["order"]["id"] == order.id
