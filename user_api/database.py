from sqlalchemy import create_engine, Column, String, DateTime, Date, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import datetime
from config import DATABASE_URL
from sqlalchemy.dialects.postgresql import UUID
import uuid

Base = declarative_base()
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

class User(Base):
    __tablename__ = "users"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    password = Column(String)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    
    # Изменил тип на Date
    birth_date = Column(Date, nullable=True)
    phone = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

def init_db():
    
    Base.metadata.create_all(bind=engine)
