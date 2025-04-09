import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from datetime import datetime
from google.protobuf.timestamp_pb2 import Timestamp
import grpc
from grpc import StatusCode
from fastapi import HTTPException

from main import app, get_current_user_id
from grpc_modules.generated import posts_pb2, promocodes_pb2

client = TestClient(app)

# Mock данные для тестов
TEST_USER_ID = "test_user_id"
TEST_TOKEN = "test_token"
TEST_POST_ID = "test_post_id"
TEST_PROMOCODE_ID = "test_promocode_id"

# Фикстуры для моков
@pytest.fixture
def mock_verify_token():
    async def mock_get_current_user(*args, **kwargs):
        return TEST_USER_ID
    
    with patch("main.get_current_user_id", new=mock_get_current_user):
        yield

def create_timestamp():
    ts = Timestamp()
    ts.FromDatetime(datetime.now())
    return ts

@pytest.fixture
def mock_grpc_posts():
    with patch("grpc.insecure_channel") as mock_channel:
        mock_stub = MagicMock()
        mock_channel.return_value = MagicMock()

        # Создаем правильные protobuf объекты
        post_response = posts_pb2.PostResponse(
            id=TEST_POST_ID,
            title="Test Post",
            description="Test Description",
            creator_id=TEST_USER_ID,
            created_at=create_timestamp(),
            updated_at=create_timestamp(),
            is_private=False,
            tags=["test"]
        )

        list_response = posts_pb2.ListPostsResponse()
        list_response.posts.extend([post_response])
        list_response.total = 1

        mock_stub.CreatePost.return_value = post_response
        mock_stub.GetPost.return_value = post_response
        mock_stub.ListPosts.return_value = list_response
        mock_stub.UpdatePost.return_value = post_response
        mock_stub.DeletePost.return_value = MagicMock()

        with patch("main.posts_pb2_grpc.PostServiceStub", return_value=mock_stub):
            yield mock_stub

@pytest.fixture
def mock_grpc_promocodes():
    with patch("grpc.insecure_channel") as mock_channel:
        mock_stub = MagicMock()
        mock_channel.return_value = MagicMock()

        promocode_response = promocodes_pb2.PromocodeResponse(
            id=TEST_PROMOCODE_ID,
            name="Test Promo",
            description="Test Description",
            creator_id=TEST_USER_ID,
            discount=10.0,
            code="TESTCODE",
            created_at=create_timestamp(),
            updated_at=create_timestamp()
        )

        list_response = promocodes_pb2.ListPromocodesResponse()
        list_response.promocodes.extend([promocode_response])
        list_response.total = 1

        mock_stub.CreatePromocode.return_value = promocode_response
        mock_stub.GetPromocode.return_value = promocode_response
        mock_stub.ListPromocodes.return_value = list_response
        mock_stub.UpdatePromocode.return_value = promocode_response
        mock_stub.DeletePromocode.return_value = MagicMock()

        with patch("main.promocodes_pb2_grpc.PromocodeServiceStub", return_value=mock_stub):
            yield mock_stub

# Тесты для аутентификации
@pytest.mark.asyncio
async def test_get_current_user_id_success():
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {"user_id": TEST_USER_ID}
        )
        result = await get_current_user_id(TEST_TOKEN)
        assert result == TEST_USER_ID

@pytest.mark.asyncio
async def test_get_current_user_id_failure():
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_get.return_value = MagicMock(
            status_code=401,
            json=lambda: {"detail": "Invalid token"}
        )
        with pytest.raises(HTTPException):
            await get_current_user_id("invalid_token")

# Тесты для постов
def test_create_post(mock_verify_token, mock_grpc_posts):
    post_data = {
        "title": "Test Post",
        "description": "Test Description",
        "is_private": False,
        "tags": ["test"]
    }
    response = client.post(
        "/posts",
        json=post_data,
        headers={"Authorization": f"Bearer {TEST_TOKEN}"}
    )
    assert response.status_code == 200
    assert response.json()["id"] == TEST_POST_ID

def test_get_post(mock_verify_token, mock_grpc_posts):
    response = client.get(
        f"/posts/{TEST_POST_ID}",
        headers={"Authorization": f"Bearer {TEST_TOKEN}"}
    )
    assert response.status_code == 200
    assert response.json()["id"] == TEST_POST_ID

def test_list_posts(mock_verify_token, mock_grpc_posts):
    response = client.get(
        "/posts",
        headers={"Authorization": f"Bearer {TEST_TOKEN}"},
        params={"page": 1, "per_page": 10}
    )
    assert response.status_code == 200
    assert len(response.json()["posts"]) == 1
    assert response.json()["total"] == 1

def test_update_post(mock_verify_token, mock_grpc_posts):
    update_data = {
        "title": "Updated Post",
        "description": "Updated Description"
    }
    response = client.put(
        f"/posts/{TEST_POST_ID}",
        json=update_data,
        headers={"Authorization": f"Bearer {TEST_TOKEN}"}
    )
    assert response.status_code == 200
    assert response.json()["id"] == TEST_POST_ID

def test_delete_post(mock_verify_token, mock_grpc_posts):
    response = client.delete(
        f"/posts/{TEST_POST_ID}",
        headers={"Authorization": f"Bearer {TEST_TOKEN}"}
    )
    assert response.status_code == 200
    assert response.json()["message"] == "Post deleted successfully"

# Тесты для промокодов
def test_create_promocode(mock_verify_token, mock_grpc_promocodes):
    promocode_data = {
        "name": "Test Promo",
        "description": "Test Description",
        "discount": 10.0,
        "code": "TESTCODE"
    }
    response = client.post(
        "/promocodes",
        json=promocode_data,
        headers={"Authorization": f"Bearer {TEST_TOKEN}"}
    )
    assert response.status_code == 200
    assert response.json()["id"] == TEST_PROMOCODE_ID

def test_get_promocode(mock_verify_token, mock_grpc_promocodes):
    response = client.get(
        f"/promocodes/{TEST_PROMOCODE_ID}",
        headers={"Authorization": f"Bearer {TEST_TOKEN}"}
    )
    assert response.status_code == 200
    assert response.json()["id"] == TEST_PROMOCODE_ID

def test_list_promocodes(mock_verify_token, mock_grpc_promocodes):
    response = client.get(
        "/promocodes",
        headers={"Authorization": f"Bearer {TEST_TOKEN}"},
        params={"page": 1, "per_page": 10}
    )
    assert response.status_code == 200
    assert len(response.json()["promocodes"]) == 1
    assert response.json()["total"] == 1

def test_update_promocode(mock_verify_token, mock_grpc_promocodes):
    update_data = {
        "name": "Updated Promo",
        "description": "Updated Description"
    }
    response = client.put(
        f"/promocodes/{TEST_PROMOCODE_ID}",
        json=update_data,
        headers={"Authorization": f"Bearer {TEST_TOKEN}"}
    )
    assert response.status_code == 200
    assert response.json()["id"] == TEST_PROMOCODE_ID

def test_delete_promocode(mock_verify_token, mock_grpc_promocodes):
    response = client.delete(
        f"/promocodes/{TEST_PROMOCODE_ID}",
        headers={"Authorization": f"Bearer {TEST_TOKEN}"}
    )
    assert response.status_code == 200
    assert response.json()["message"] == "Promocode deleted successfully"

# Тесты на ошибки
def test_unauthorized_access():
    response = client.post("/posts", json={})
    assert response.status_code == 401

def test_post_not_found(mock_verify_token, mock_grpc_posts):
    error = grpc.RpcError()
    error.code = lambda: StatusCode.NOT_FOUND
    error.details = lambda: "Post not found"
    mock_grpc_posts.GetPost.side_effect = error
    
    response = client.get(
        "/posts/non_existent_id",
        headers={"Authorization": f"Bearer {TEST_TOKEN}"}
    )
    assert response.status_code == 404