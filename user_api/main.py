from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from pydantic import BaseModel
import datetime
import jwt
from typing import Optional
from database import init_db, User, SessionLocal
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from fastapi.responses import JSONResponse
from datetime import date
from datetime import datetime, timedelta

# Настроим CORS
origins = [
    "http://localhost:8000",  # Разрешаем запросы с system_api
    # Можно добавить другие домены, если нужно
]

app = FastAPI(title="User API", description="Handles user management", version="1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # список доменов, которым разрешены запросы
    allow_credentials=True,
    allow_methods=["*"],  # Разрешаем все HTTP методы (GET, POST, и т.д.)
    allow_headers=["*"],  # Разрешаем все заголовки
)

SECRET_KEY = "your_secret_key"
ALGORITHM = "HS256"

# Настроим OAuth2
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Pydantic модели
class UserLogin(BaseModel):
    username: str
    password: str

class UserRegister(BaseModel):
    username: str
    email: str
    password: str

class UserUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    birth_date: Optional[date] = None
    phone: Optional[str] = None


def verify_token(token: str) -> Optional[str]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get("sub")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

@app.post("/register")
async def register(user: UserRegister, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter((User.username == user.username) | (User.email == user.email)).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username or Email already registered")

    hashed_password = pwd_context.hash(user.password)
    db_user = User(
        username=user.username,
        email=user.email,
        password=hashed_password,
        created_at=datetime.datetime.utcnow(),
        updated_at=datetime.datetime.utcnow()
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    return {"message": "User registered successfully!", "user": {"username": db_user.username, "email": db_user.email}}

@app.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.username == form_data.username).first()
    if not db_user or not pwd_context.verify(form_data.password, db_user.password):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    token = jwt.encode({"sub": db_user.username, "exp": datetime.utcnow() + timedelta(hours=1)}, SECRET_KEY, algorithm=ALGORITHM)

    return {"access_token": token, "token_type": "bearer"}

from datetime import datetime

@app.put("/update-profile")
async def update_profile(user_update: UserUpdate, token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    username = verify_token(token)
    user = db.query(User).filter(User.username == username).first()

    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    # Проверка уникальности email
    if user_update.email:
        existing_user = db.query(User).filter(User.email == user_update.email).first()
        if existing_user and existing_user.id != user.id:
            raise HTTPException(status_code=400, detail="Email is already in use")

    # Обновляем только те поля, которые были переданы
    if user_update.first_name:
        user.first_name = user_update.first_name
    if user_update.last_name:
        user.last_name = user_update.last_name
    if user_update.email:
        user.email = user_update.email
    if user_update.birth_date:
        if isinstance(user_update.birth_date, str):
            user_update.birth_date = datetime.strptime(user_update.birth_date, "%Y-%m-%d").date()
        user.birth_date = user_update.birth_date
    if user_update.phone:
        user.phone = user_update.phone

    db.commit()
    db.refresh(user)

    if user_update.first_name or user_update.last_name or user_update.email or user_update.birth_date or user_update.phone:
        user.updated_at = datetime.utcnow()  # Обновляем поле updated_at

    return {"message": "Profile updated successfully", "user": {
        "username": user.username,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "birth_date": user.birth_date,
        "phone": user.phone
    }}

@app.get("/profile")
async def get_profile(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    username = verify_token(token)
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    user_data = {
        "username": user.username,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "birth_date": str(user.birth_date) if user.birth_date else None,
        "phone": user.phone
    }

    return user_data

@app.get("/protected-resource")
async def protected_resource(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    username = verify_token(token)
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")

    user_data = {
        "username": user.username,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "birth_date": str(user.birth_date) if user.birth_date else None,
        "phone": user.phone
    }

    filtered_data = {key: value for key, value in user_data.items() if value is not None}

    return JSONResponse(content=filtered_data)

@app.get("/verify-token")
async def verify_token_endpoint(token: str = Depends(oauth2_scheme)):
    username = verify_token(token)
    return {"username": username}

if __name__ == "__main__":
    init_db()
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
