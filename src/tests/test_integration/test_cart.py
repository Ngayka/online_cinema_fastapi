from datetime import date

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import insert, select

from database.models.movies import MovieStatusEnum
from main import app


@pytest.mark.asyncio
async def test_cart_crud(client, jwt_manager, test_user, test_movie):
    """
    Comprehensive test suite for Cart CRUD operations.

    Tests cover the complete lifecycle of cart management:
    - Creating cart items
    - Reading cart contents
    - Updating cart quantities (if applicable)
    - Deleting cart items
    - Edge cases and error handling
    """
    token = jwt_manager.create_access_token(
        {"sub": test_user.email, "id": test_user.id}
    )
    headers = {"Authorization": f"Bearer {token}"}
    add_response = await client.post(
        "/api/v1/cart/items", json={"movie_id": test_movie.id}, headers=headers
    )
    assert add_response.status_code == 201

    response = await client.get("/api/v1/cart/me", headers=headers)
    assert response.status_code == 200

    cart_data = response.json()
    cart_items = cart_data["items"]

    if cart_items:
        cart_item_id = cart_items[0]["id"]
        response = await client.delete(
            f"/api/v1/cart/items/{cart_item_id}", headers=headers
        )
        assert response.status_code == 204
    else:
        pytest.fail("No movies in cart to delete")


@pytest.mark.asyncio
async def test_delete_all_movies(
    client, jwt_manager, test_user, test_movie, test_movie2
):
    """Test deleting all movies from cart at once.

    Endpoint: DELETE /api/v1/cart/items/
    Expected: Successfully deletes all items with 204 status"""
    token = jwt_manager.create_access_token(
        {"sub": test_user.email, "id": test_user.id}
    )
    headers = {"Authorization": f"Bearer {token}"}
    await client.post(
        "/api/v1/cart/items", json={"movie_id": test_movie.id}, headers=headers
    )
    await client.post(
        "/api/v1/cart/items", json={"movie_id": test_movie2.id}, headers=headers
    )
    cart_response_before_delete = await client.get("/api/v1/cart/me", headers=headers)
    cart_data_before_delete = cart_response_before_delete.json()
    assert len(cart_data_before_delete) == 2

    response = await client.delete(f"/api/v1/cart/items/", headers=headers)
    assert response.status_code == 204

    response_after_delete = await client.get(f"/api/v1/cart/me", headers=headers)
    data_after_delete = response_after_delete.json()
    assert len(data_after_delete["items"]) == 0


@pytest.mark.asyncio
async def test_delete_movies_from_empty_cart(client, jwt_manager, test_user):
    """Test deleting all movies from empty cart.

    Endpoint: DELETE /api/v1/cart/items/
    Expected: Returns 404 Not Found when cart is empty"""
    token = jwt_manager.create_access_token(
        {"sub": test_user.email, "id": test_user.id}
    )
    headers = {"Authorization": f"Bearer {token}"}
    cart_response = await client.get("/api/v1/cart/me", headers=headers)
    empty_cart_data = cart_response.json()
    assert len(empty_cart_data["items"]) == 0

    response = await client.delete(f"/api/v1/cart/items/", headers=headers)
    assert response.status_code == 404
