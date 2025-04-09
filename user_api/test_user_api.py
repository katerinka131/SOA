import pytest
from fastapi.testclient import TestClient
from user_api.main import app
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from user_api.database import Base, User

# Создаем тестовую базу данных
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="module")
def test_db():
    # Настроим таблицы
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def client():
    # Инициализация клиента FastAPI
    with TestClient(app) as client:
        yield client



def test_get_profile_no_token(client):
    response = client.get("/profile")
    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"


def test_verify_token_invalid(client):
    response = client.get("/verify-token", headers={"Authorization": "Bearer invalidtoken"})
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid token"


