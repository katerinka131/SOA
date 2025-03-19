from fastapi import FastAPI, HTTPException, Depends, Form
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
import httpx
import re

__all__ = ("app",)


app = FastAPI(title="System API", description="Proxy for User API", version="1.0")



# Настроим OAuth2
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="http://localhost:8001/login")


# Pydantic модели
class UserRegister(BaseModel):
    username: str
    email: str
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

EMAIL_REGEX = r"(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)"
class UserUpdate(BaseModel):
    first_name: str
    last_name: str
    birth_date: str
    phone: str
    email: str
    
# Регистрация пользователя
@app.post("/register")
async def register(user: UserRegister):
    async with httpx.AsyncClient() as client:
        response = await client.post("http://user_api:8001/register", json=user.dict())
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=response.json().get("detail", "Registration failed"))
        return response.json()

# Логин пользователя
@app.post("/login")
async def login(
    username: str = Form(None), 
    password: str = Form(None), 
    user: UserLogin | None = None  # Принимаем JSON, если он пришел
):
    # Если пришел JSON, используем его данные
    if user:
        username = user.username
        password = user.password
    
    # Если данных нет, ошибка
    if not username or not password:
        raise HTTPException(status_code=400, detail="Username and password required")

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://user_api:8001/login",
            data={"username": username, "password": password}  # Отправляем форму
        )
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail="Invalid credentials")
        return response.json()

# Обновление профиля пользователя
@app.put("/update-profile")
async def update_profile(user_update: UserUpdate, token: str = Depends(oauth2_scheme)):
    # Проверка валидности email
    if user_update.email and not re.match(EMAIL_REGEX, user_update.email):
        raise HTTPException(status_code=400, detail="Invalid email format")

    async with httpx.AsyncClient() as client:
        verify_response = await client.get("http://user_api:8001/verify-token", headers={"Authorization": f"Bearer {token}"})
        
        if verify_response.status_code != 200:
            raise HTTPException(status_code=verify_response.status_code, detail="Invalid or expired token")

        response = await client.put(
            "http://user_api:8001/update-profile", 
            json=user_update.dict(),
            headers={"Authorization": f"Bearer {token}"}
        )

        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail="Failed to update profile")
        
        return response.json()

# Получение данных профиля пользователя
@app.get("/profile")
async def get_profile(token: str = Depends(oauth2_scheme)):
    async with httpx.AsyncClient() as client:
        verify_response = await client.get("http://user_api:8001/verify-token", headers={"Authorization": f"Bearer {token}"})

        if verify_response.status_code != 200:
            raise HTTPException(status_code=verify_response.status_code, detail="Invalid or expired token")

        response = await client.get("http://user_api:8001/profile", headers={"Authorization": f"Bearer {token}"})

        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail="Failed to fetch profile")

        return response.json()

# Защищённый ресурс, доступный только для авторизованных пользователей
@app.get("/protected-resource")
async def protected_resource(token: str = Depends(oauth2_scheme)):
    async with httpx.AsyncClient() as client:
        verify_response = await client.get("http://user_api:8001/verify-token", headers={"Authorization": f"Bearer {token}"})

        if verify_response.status_code != 200:
            raise HTTPException(status_code=verify_response.status_code, detail="Invalid or expired token")

        response = await client.get("http://user_api:8001/protected-resource", headers={"Authorization": f"Bearer {token}"})

        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail="Unauthorized access")

        return response.json()

@app.get("/")
async def read_root():
    return {"message": "Welcome to the System API"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
