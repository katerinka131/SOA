import pytest
from fastapi.testclient import TestClient
from ..user_api.user_api.main import app
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from ..user_api.user_api.database import Base

# Создаем тестовую базу данных в памяти
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Фикстура для тестовой базы данных
@pytest.fixture(scope="module")
def test_db():
    # Настроим таблицы (создание схемы базы данных)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()  # Создаем сессию
    try:
        yield db  # Возвращаем сессию для использования в тестах
    finally:
        db.close()  # Закрываем сессию после тестов
        Base.metadata.drop_all(bind=engine)  # Удаляем таблицы после завершения тестов

# Фикстура для клиента FastAPI
@pytest.fixture
def client(test_db):
    # Заменяем сессию в приложении на тестовую
    app.dependency_overrides[SessionLocal] = lambda: test_db
    with TestClient(app) as client:
        yield client

# Пример теста: Проверка получения профиля без токена
def test_get_profile_no_token(client):
    response = client.get("/profile")
    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"

# Пример теста: Проверка недействительного токена
def test_verify_token_invalid(client):
    response = client.get("/verify-token", headers={"Authorization": "Bearer invalidtoken"})
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid token"

# Пример теста: Проверка защищенного ресурса без токена
def test_protected_resource_no_token(client):
    response = client.get("/protected-resource")
    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"
