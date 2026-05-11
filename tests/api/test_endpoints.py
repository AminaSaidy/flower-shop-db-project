#TO LAUNCH "docker compose exec -e PYTHONPATH=/app api_1 pytest tests/api/test_endpoints.py"

import pytest

# 1. 404 Negative Test (API prefix should return JSON)
def test_api_404_not_found(client):
    response = client.get("/api/non-existent-endpoint")
    assert response.status_code == 404
    assert response.json()["detail"] == "Not Found"

# 2. 404 Negative Test (Frontend route should redirect or return HTML)
def test_frontend_404_redirect(client, allow_redirects=False):
    response = client.get("/random-frontend-page", follow_redirects=False)
    # Based on the previous task, it redirects to /404.html
    assert response.status_code in [302, 303, 307, 404]

# 3. Catalog Positive Test - List Products
def test_get_products_success(client):
    response = client.get("/api/products/")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)
    assert "products" in data

# 4. Catalog Negative Test - Pagination validation (negative limit)
def test_get_products_invalid_pagination(client):
    # Depending on implementation, pass an invalid query param
    response = client.get("/api/products/?limit=-5")
    assert response.status_code == 422

# 5. Catalog Negative Test - Non-existent product ID
def test_get_product_not_found(client):
    response = client.get("/api/products/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404

# 6. Auth Negative Test - Access token without credentials
def test_auth_no_credentials(client):
    response = client.post("/api/auth/login")
    assert response.status_code == 422

# 7. Auth Negative Test - Invalid credentials
def test_auth_invalid_credentials(client):
    response = client.post(
        "/api/auth/login", 
        json={"email": "wronguser@example.com", "password": "wrongpassword"}
    )
    assert response.status_code in [400, 401]

# 8. Cart Negative Test - Access without authentication
def test_cart_unauthorized_access(client):
    response = client.get("/api/cart/")
    assert response.status_code == 401

# 9. Orders Negative Test - Access without authentication
def test_orders_unauthorized_access(client):
    response = client.get("/api/orders/")
    assert response.status_code == 401

# 10. Users Negative Test - Missing fields on registration
def test_user_registration_missing_fields(client):
    response = client.post("/api/auth/register", json={"email": "test@example.com"})
    assert response.status_code == 422 # Missing password, etc.

# 11. WS Negative Test - WebSocket without auth (if applicable)
def test_ws_connection_fail(client):
    with pytest.raises(Exception):
        with client.websocket_connect("/api/ws/orders/1") as websocket:
            pass # Should fail due to unauthorized or no token

# 12. Healthcheck / Ping (If exists, otherwise just extra coverage)
def test_auth_swagger_ui(client):
    # Checking if Swagger docs are accessible
    response = client.get("/api/docs")
    assert response.status_code == 200

# 13. Catalog Positive Test - Filter by category
def test_get_products_by_category(client):
    response = client.get("/api/products/?category=some-slug")
    assert response.status_code in [200, 422]  # Depending on schema validation

# 14. Users Positive/Negative - Method Not Allowed
def test_users_method_not_allowed(client):
    response = client.put("/api/users/")
    assert response.status_code in [404, 405]

# 15. Cart Negative Test - Add item unauthorized
def test_cart_add_item_unauthorized(client):
    response = client.post("/api/cart/add", json={"product_id": "00000000-0000-0000-0000-000000000000", "quantity": 1})
    assert response.status_code == 401
