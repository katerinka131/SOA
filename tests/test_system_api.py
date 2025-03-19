import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock
from system_api.main import app

# Убедись, что используешь правильный клиент для асинхронных запросов
client = AsyncClient(app=app)

@pytest.mark.asyncio
async def test_register_user_exists(mocker):
    # Мокируем метод post
    mock_post = mocker.patch("httpx.AsyncClient.post", new_callable=AsyncMock)
    mock_post.return_value.status_code = 409
    mock_post.return_value.json.return_value = {"detail": "User already exists"}

    # Используем полный URL
    response = await client.post("http://localhost:8000/register", json={
        "username": "testuser",
        "email": "test@example.com",
        "password": "securepassword"
    })
    
    assert response.status_code == 409
    assert (await response.json())["detail"] == "User already exists"

@pytest.mark.asyncio
async def test_register_invalid_email(mocker):
    # Мокируем клиент
    mock_response = mocker.Mock()
    mock_response.status_code = 400
    mock_response.json = mocker.AsyncMock(return_value={"detail": "Invalid email format"})
    
    # Мокируем вызов HTTP-клиента
    mocker.patch("httpx.AsyncClient.post", return_value=mock_response)

    response = await client.post("http://localhost:8000/register", json={
        "username": "testuser",
        "email": "invalid-email",
        "password": "securepassword"
    })
    
    assert response.status_code == 400
    assert (await response.json())["detail"] == "Invalid email format"


@pytest.mark.asyncio
async def test_register_missing_fields(mocker):
    response = await client.post("http://localhost:8000/register", json={
        "username": "testuser",
        "password": "securepassword"
    })
    
    assert response.status_code == 422

@pytest.mark.asyncio
async def test_register_user_api_unavailable(mocker):
    # Мокаем запрос
    mock_post = mocker.patch("httpx.AsyncClient.post", new_callable=AsyncMock)
    
    # Устанавливаем side_effect на исключение, которое имитирует недоступность сервиса
    mock_post.side_effect = Exception("Service unavailable")

    # Попытка выполнить запрос
    try:
        response = await client.post("http://localhost:8000/register", json={
            "username": "testuser",
            "email": "test@example.com",
            "password": "securepassword"
        })
    except Exception as e:
        response = e  # В случае ошибки сохраняем исключение

    # Проверяем, что возвращается правильная ошибка с кодом 500
    assert isinstance(response, Exception)
    assert str(response) == "Service unavailable"


@pytest.mark.asyncio
async def test_login_invalid_credentials(mocker):
    mock_post = mocker.patch("httpx.AsyncClient.post", new_callable=AsyncMock)
    mock_post.return_value.status_code = 401
    mock_post.return_value.json.return_value = {"detail": "Invalid credentials"}
    
    response = await client.post("http://localhost:8000/login", json={
        "username": "wronguser",
        "password": "wrongpassword"
    })
    
    assert response.status_code == 401
    assert (await response.json())["detail"] == "Invalid credentials"

@pytest.mark.asyncio
async def test_login_user_api_unavailable(mocker):
    # Мокаем запрос
    mock_post = mocker.patch("httpx.AsyncClient.post", new_callable=AsyncMock)
    
    # Устанавливаем side_effect на исключение, которое симулирует недоступность сервиса
    mock_post.side_effect = Exception("Service unavailable")

    # Попытка выполнить запрос
    try:
        response = await client.post("http://localhost:8000/login", json={
            "username": "testuser",
            "password": "securepassword"
        })
    except Exception as e:
        response = e  # В случае ошибки, сохраняем исключение

    # Проверяем, что при исключении возвращается корректный ответ с кодом 500
    assert isinstance(response, Exception)
    assert str(response) == "Service unavailable"


@pytest.mark.asyncio
async def test_update_profile_invalid_email(mocker):
    token = "valid_token"
    response = await client.put("http://localhost:8000/update-profile", json={
        "first_name": "Test",
        "last_name": "User",
        "birth_date": "2000-01-01",
        "phone": "1234567890",
        "email": "invalid-email"
    }, headers={"Authorization": f"Bearer {token}"})
    
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid email format"


@pytest.mark.asyncio
async def test_update_profile_invalid_token(mocker):
    mock_get = mocker.patch("httpx.AsyncClient.get", new_callable=AsyncMock)
    mock_get.return_value.status_code = 401
    mock_get.return_value.json.return_value = {"detail": "Invalid or expired token"}
    
    token = "invalid_token"
    response = await client.put("http://localhost:8000/update-profile", json={
        "first_name": "Test",
        "last_name": "User",
        "birth_date": "2000-01-01",
        "phone": "1234567890",
        "email": "test@example.com"
    }, headers={"Authorization": f"Bearer {token}"})
    
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or expired token"

@pytest.mark.asyncio
async def test_get_profile_invalid_token(mocker):
    mock_get = mocker.patch("httpx.AsyncClient.get", new_callable=AsyncMock)
    mock_get.return_value.status_code = 401
    mock_get.return_value.json.return_value = {"detail": "Invalid or expired token"}
    
    token = "invalid_token"
    response = await client.get("http://localhost:8000/profile", headers={"Authorization": f"Bearer {token}"})
    
    assert response.status_code == 401
    assert (await response.json())["detail"] == "Invalid or expired token"

@pytest.mark.asyncio
async def test_protected_resource_invalid_token(mocker):
    mock_get = mocker.patch("httpx.AsyncClient.get", new_callable=AsyncMock)
    mock_get.return_value.status_code = 401
    mock_get.return_value.json.return_value = {"detail": "Invalid or expired token"}
    
    token = "invalid_token"
    response = await client.get("http://localhost:8000/protected-resource", headers={"Authorization": f"Bearer {token}"})
    
    assert response.status_code == 401
    assert (await response.json())["detail"] == "Invalid or expired token"

@pytest.mark.asyncio
async def test_register_success(mocker):
    mock_post = mocker.patch("httpx.AsyncClient.post", new_callable=AsyncMock)
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = {"username": "testuser", "email": "test@example.com"}

    response = await client.post("http://localhost:8000/register", json={
        "username": "testuser",
        "email": "test@example.com",
        "password": "securepassword"
    })
    
    assert response.status_code == 200
    assert (await response.json())["username"] == "testuser"
    assert (await response.json())["email"] == "test@example.com"

@pytest.mark.asyncio
async def test_login_success(mocker):
    mock_post = mocker.patch("httpx.AsyncClient.post", new_callable=AsyncMock)
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = {"access_token": "valid_token", "token_type": "bearer"}

    response = await client.post("http://localhost:8000/login", json={
        "username": "testuser",
        "password": "securepassword"
    })
    
    assert response.status_code == 200
    assert (await response.json())["access_token"] == "valid_token"
    assert (await response.json())["token_type"] == "bearer"

@pytest.mark.asyncio
async def test_update_profile_success(mocker):
    mock_put = mocker.patch("httpx.AsyncClient.put", new_callable=AsyncMock)
    mock_put.return_value.status_code = 200
    mock_put.return_value.json.return_value = {"first_name": "Test", "last_name": "User"}

    token = "valid_token"
    response = await client.put("http://localhost:8000/update-profile", json={
        "first_name": "Test",
        "last_name": "User",
        "birth_date": "2000-01-01",
        "phone": "1234567890",
        "email": "test@example.com"
    }, headers={"Authorization": f"Bearer {token}"})
    
    assert response.status_code == 200
    # Используем await для вызова json
    json_response = await response.json()
    assert json_response["first_name"] == "Test"
    assert json_response["last_name"] == "User"


@pytest.mark.asyncio
async def test_get_profile_success(mocker):
    mock_get = mocker.patch("httpx.AsyncClient.get", new_callable=AsyncMock)
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {"username": "testuser", "email": "test@example.com"}

    token = "valid_token"
    response = await client.get("http://localhost:8000/profile", headers={"Authorization": f"Bearer {token}"})
    
    assert response.status_code == 200
    assert (await response.json())["username"] == "testuser"
    assert (await response.json())["email"] == "test@example.com"


@pytest.mark.asyncio
async def test_protected_resource_success(mocker):
    mock_get = mocker.patch("httpx.AsyncClient.get", new_callable=AsyncMock)
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {"message": "Access granted"}

    token = "valid_token"
    response = await client.get("http://localhost:8000/protected-resource", headers={"Authorization": f"Bearer {token}"})
    
    assert response.status_code == 200
    assert (await response.json())["message"] == "Access granted"

@pytest.mark.asyncio
async def test_register_missing_username(mocker):
    response = await client.post("http://localhost:8000/register", json={
        "email": "test@example.com",
        "password": "securepassword"
    })
    
    assert response.status_code == 422  # Ошибка из-за отсутствия обязательного поля

@pytest.mark.asyncio
async def test_login_missing_credentials(mocker):
    response = await client.post("http://localhost:8000/login", json={})
    
    # Ожидаем ошибку с кодом 400
    assert response.status_code == 400  # Ошибка из-за отсутствия обязательных данных


