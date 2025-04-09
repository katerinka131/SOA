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
from uuid import uuid4, UUID

# Настроим CORS
origins = [
    "http://localhost:8000",
    "http://127.0.0.1:8000" 
]

app = FastAPI(title="User API", description="Handles user management", version="1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SECRET_KEY = "your_secret_key"
ALGORITHM = "HS256"

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

def verify_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return {
            "username": payload.get("username"),
            "user_id": payload.get("sub")
        }
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
        password=hashed_password
        # created_at и updated_at добавятся автоматически
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

    token = jwt.encode({
        "sub": str(db_user.id),  # Используем UUID как основной идентификатор
        "username": db_user.username,  # Сохраняем username для обратной совместимости
        "exp": datetime.utcnow() + timedelta(hours=1)
    }, SECRET_KEY, algorithm=ALGORITHM)

    return {"access_token": token, "token_type": "bearer"}

@app.put("/update-profile")
async def update_profile(user_update: UserUpdate, token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    token_data = verify_token(token)
    user = db.query(User).filter(User.username == token_data["username"]).first()

    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    if user_update.email:
        existing_user = db.query(User).filter(User.email == user_update.email).first()
        if existing_user and existing_user.id != user.id:
            raise HTTPException(status_code=400, detail="Email is already in use")

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

    if any([user_update.first_name, user_update.last_name, user_update.email, user_update.birth_date, user_update.phone]):
        user.updated_at = datetime.utcnow()

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
    token_data = verify_token(token)
    user = db.query(User).filter(User.username == token_data["username"]).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return {
        "username": user.username,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "birth_date": str(user.birth_date) if user.birth_date else None,
        "phone": user.phone
    }

# Изменяем verify_token_endpoint, чтобы возвращал user_id
@app.get("/verify-token")
async def verify_token_endpoint(token: str = Depends(oauth2_scheme)):
    token_data = verify_token(token)
    return {
        "username": token_data["username"],
        "user_id": token_data["user_id"]  # Добавляем возврат user_id
    }

if __name__ == "__main__":
    init_db()
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)