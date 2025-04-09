import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import Column, String, Text, Boolean, DateTime, Float, ForeignKey, ARRAY
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID
import uuid

# Используем переменную окружения или fallback с правильными credentials
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg2://postgres:postgres@post_db:5432/posts_promocodes")

engine = create_engine(DATABASE_URL, pool_pre_ping=True)  # Добавлен pool_pre_ping для устойчивости подключения
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class Post(Base):
    __tablename__ = "posts"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    creator_id = Column(UUID(as_uuid=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    is_private = Column(Boolean, default=False)
    tags = Column(ARRAY(String(50)))

class Promocode(Base):
    __tablename__ = "promocodes"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    creator_id = Column(UUID(as_uuid=True), nullable=False)
    discount = Column(Float, nullable=False)
    code = Column(String(50), unique=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

# Добавим задержку перед созданием таблиц для гарантии готовности БД
import time
time.sleep(5)  # Даем PostgreSQL время на запуск
Base.metadata.create_all(bind=engine)