from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
import httpx
import re
import grpc
from datetime import datetime
from typing import List, Optional

__all__ = ("app",)
from grpc_modules.generated import posts_pb2, posts_pb2_grpc, promocodes_pb2, promocodes_pb2_grpc

app = FastAPI(
    title="System API",
    description="Proxy for User API and gRPC services for posts and promocodes",
    version="1.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

# Настроим OAuth2
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="http://localhost:8001/login")
GRPC_SERVER = "grpc_server:50051"
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
    


# Pydantic модели для постов
class PostCreate(BaseModel):
    title: str
    description: str
    is_private: bool = False
    tags: List[str] = []

class PostUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    is_private: Optional[bool] = None
    tags: Optional[List[str]] = None

class PostResponse(BaseModel):
    id: str
    title: str
    description: str
    creator_id: str
    created_at: datetime
    updated_at: datetime
    is_private: bool
    tags: List[str]

class PostListResponse(BaseModel):
    posts: List[PostResponse]
    total: int
    page: int
    per_page: int

# Pydantic модели для промокодов
class PromocodeCreate(BaseModel):
    name: str
    description: str
    discount: float
    code: str

class PromocodeUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    discount: Optional[float] = None
    code: Optional[str] = None

class PromocodeResponse(BaseModel):
    id: str
    name: str
    description: str
    creator_id: str
    discount: float
    code: str
    created_at: datetime
    updated_at: datetime

class PromocodeListResponse(BaseModel):
    promocodes: List[PromocodeResponse]
    total: int
    page: int
    per_page: int

# Функция для проверки аутентификации
async def get_current_user_id(token: str = Depends(oauth2_scheme)) -> str:
    async with httpx.AsyncClient() as client:
        verify_response = await client.get(
            "http://user_api:8001/verify-token",
            headers={"Authorization": f"Bearer {token}"}
        )
        if verify_response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token"
            )
        data = verify_response.json()
        user_id = data.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User ID not found in token"
            )
        return user_id

# gRPC клиент для постов
def get_posts_grpc_client():
    channel = grpc.insecure_channel(GRPC_SERVER)
    return posts_pb2_grpc.PostServiceStub(channel)

# gRPC клиент для промокодов
def get_promocodes_grpc_client():
    channel = grpc.insecure_channel(GRPC_SERVER)
    return promocodes_pb2_grpc.PromocodeServiceStub(channel)

# Эндпоинты для постов
@app.post("/posts", response_model=PostResponse)
async def create_post(
    post: PostCreate,
    user_id: str = Depends(get_current_user_id)  # Получаем user_id из токена
):
    try:
        print(f"Creating post with user_id: {user_id}")
        grpc_client = get_posts_grpc_client()
        response = grpc_client.CreatePost(
            posts_pb2.CreatePostRequest(
                title=post.title,
                description=post.description,
                creator_id=user_id,  # Используем user_id из аутентификации
                is_private=post.is_private,
                tags=post.tags
            )
        )
        return PostResponse(
            id=response.id,
            title=response.title,
            description=response.description,
            creator_id=response.creator_id,
            created_at=datetime.fromtimestamp(response.created_at.seconds),
            updated_at=datetime.fromtimestamp(response.updated_at.seconds),
            is_private=response.is_private,
            tags=list(response.tags)
        )
    except grpc.RpcError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.details()
        )

@app.get("/posts/{post_id}", response_model=PostResponse)
async def get_post(
    post_id: str,
    user_id: str = Depends(get_current_user_id)
):
    try:
        grpc_client = get_posts_grpc_client()
        response = grpc_client.GetPost(
            posts_pb2.GetPostRequest(id=post_id, user_id=user_id)
        )
        return PostResponse(**{
            "id": response.id,
            "title": response.title,
            "description": response.description,
            "creator_id": response.creator_id,
            "created_at": datetime.fromtimestamp(response.created_at.seconds),
            "updated_at": datetime.fromtimestamp(response.updated_at.seconds),
            "is_private": response.is_private,
            "tags": list(response.tags)
        })
    except grpc.RpcError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND if e.code() == grpc.StatusCode.NOT_FOUND else status.HTTP_400_BAD_REQUEST,
            detail=e.details()
        )

@app.put("/posts/{post_id}", response_model=PostResponse)
async def update_post(
    post_id: str,
    post: PostUpdate,
    user_id: str = Depends(get_current_user_id)
):
    try:
        grpc_client = get_posts_grpc_client()
        response = grpc_client.UpdatePost(
            posts_pb2.UpdatePostRequest(
                id=post_id,
                user_id=user_id,
                title=post.title if post.title else "",
                description=post.description if post.description else "",
                is_private=post.is_private if post.is_private is not None else None,
                tags=post.tags if post.tags else []
            )
        )
        return PostResponse(**{
            "id": response.id,
            "title": response.title,
            "description": response.description,
            "creator_id": response.creator_id,
            "created_at": datetime.fromtimestamp(response.created_at.seconds),
            "updated_at": datetime.fromtimestamp(response.updated_at.seconds),
            "is_private": response.is_private,
            "tags": list(response.tags)
        })
    except grpc.RpcError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND if e.code() == grpc.StatusCode.NOT_FOUND else status.HTTP_400_BAD_REQUEST,
            detail=e.details()
        )

@app.delete("/posts/{post_id}")
async def delete_post(
    post_id: str,
    user_id: str = Depends(get_current_user_id)
):
    try:
        grpc_client = get_posts_grpc_client()
        grpc_client.DeletePost(
            posts_pb2.DeletePostRequest(id=post_id, user_id=user_id)
        )
        return {"message": "Post deleted successfully"}
    except grpc.RpcError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND if e.code() == grpc.StatusCode.NOT_FOUND else status.HTTP_400_BAD_REQUEST,
            detail=e.details()
        )

@app.get("/posts", response_model=PostListResponse)
async def list_posts(
    page: int = 1,
    per_page: int = 10,
    user_id: str = Depends(get_current_user_id)
):
    try:
        grpc_client = get_posts_grpc_client()
        response = grpc_client.ListPosts(
            posts_pb2.ListPostsRequest(
                user_id=user_id,
                page=page,
                per_page=per_page
            )
        )
        return PostListResponse(
            posts=[PostResponse(**{
                "id": post.id,
                "title": post.title,
                "description": post.description,
                "creator_id": post.creator_id,
                "created_at": datetime.fromtimestamp(post.created_at.seconds),
                "updated_at": datetime.fromtimestamp(post.updated_at.seconds),
                "is_private": post.is_private,
                "tags": list(post.tags)
            }) for post in response.posts],
            total=response.total,
            page=page,
            per_page=per_page
        )
    except grpc.RpcError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.details()
        )

# Эндпоинты для промокодов (аналогично постам)
@app.post("/promocodes", response_model=PromocodeResponse)
async def create_promocode(
    promocode: PromocodeCreate,
    user_id: str = Depends(get_current_user_id)  # Получаем user_id после проверки токена
):
    try:
        # Логирование для отладки
        print(f"Creating promocode for user {user_id}")
        
        grpc_client = get_promocodes_grpc_client()
        response = grpc_client.CreatePromocode(
            promocodes_pb2.CreatePromocodeRequest(
                name=promocode.name,
                description=promocode.description,
                discount=promocode.discount,
                code=promocode.code,
                creator_id=user_id  # Передаём проверенный user_id
            )
        )
        return PromocodeResponse(
            id=response.id,
            name=response.name,
            description=response.description,
            creator_id=response.creator_id,
            discount=response.discount,
            code=response.code,
            created_at=datetime.fromtimestamp(response.created_at.seconds),
            updated_at=datetime.fromtimestamp(response.updated_at.seconds)
        )
    except grpc.RpcError as e:
        print(f"gRPC error: {e.code()}: {e.details()}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.details()
        )

@app.get("/promocodes/{promocode_id}", response_model=PromocodeResponse)
async def get_promocode(
    promocode_id: str,
    user_id: str = Depends(get_current_user_id)
):
    try:
        grpc_client = get_promocodes_grpc_client()
        response = grpc_client.GetPromocode(
            promocodes_pb2.GetPromocodeRequest(id=promocode_id, user_id=user_id)
        )
        return PromocodeResponse(**{
            "id": response.id,
            "name": response.name,
            "description": response.description,
            "creator_id": response.creator_id,
            "discount": response.discount,
            "code": response.code,
            "created_at": datetime.fromtimestamp(response.created_at.seconds),
            "updated_at": datetime.fromtimestamp(response.updated_at.seconds)
        })
    except grpc.RpcError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND if e.code() == grpc.StatusCode.NOT_FOUND else status.HTTP_400_BAD_REQUEST,
            detail=e.details()
        )

@app.put("/promocodes/{promocode_id}", response_model=PromocodeResponse)
async def update_promocode(
    promocode_id: str,
    promocode: PromocodeUpdate,
    user_id: str = Depends(get_current_user_id)
):
    try:
        grpc_client = get_promocodes_grpc_client()
        response = grpc_client.UpdatePromocode(
            promocodes_pb2.UpdatePromocodeRequest(
                id=promocode_id,
                user_id=user_id,
                name=promocode.name if promocode.name else "",
                description=promocode.description if promocode.description else "",
                discount=promocode.discount if promocode.discount else 0.0,
                code=promocode.code if promocode.code else ""
            )
        )
        return PromocodeResponse(**{
            "id": response.id,
            "name": response.name,
            "description": response.description,
            "creator_id": response.creator_id,
            "discount": response.discount,
            "code": response.code,
            "created_at": datetime.fromtimestamp(response.created_at.seconds),
            "updated_at": datetime.fromtimestamp(response.updated_at.seconds)
        })
    except grpc.RpcError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND if e.code() == grpc.StatusCode.NOT_FOUND else status.HTTP_400_BAD_REQUEST,
            detail=e.details()
        )

@app.delete("/promocodes/{promocode_id}")
async def delete_promocode(
    promocode_id: str,
    user_id: str = Depends(get_current_user_id)
):
    try:
        grpc_client = get_promocodes_grpc_client()
        grpc_client.DeletePromocode(
            promocodes_pb2.DeletePromocodeRequest(id=promocode_id, user_id=user_id)
        )
        return {"message": "Promocode deleted successfully"}
    except grpc.RpcError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND if e.code() == grpc.StatusCode.NOT_FOUND else status.HTTP_400_BAD_REQUEST,
            detail=e.details()
        )

@app.get("/promocodes", response_model=PromocodeListResponse)
async def list_promocodes(
    page: int = 1,
    per_page: int = 10,
    user_id: str = Depends(get_current_user_id)
):
    try:
        grpc_client = get_promocodes_grpc_client()
        response = grpc_client.ListPromocodes(
            promocodes_pb2.ListPromocodesRequest(
                user_id=user_id,
                page=page,
                per_page=per_page
            )
        )
        return PromocodeListResponse(
            promocodes=[PromocodeResponse(**{
                "id": promocode.id,
                "name": promocode.name,
                "description": promocode.description,
                "creator_id": promocode.creator_id,
                "discount": promocode.discount,
                "code": promocode.code,
                "created_at": datetime.fromtimestamp(promocode.created_at.seconds),
                "updated_at": datetime.fromtimestamp(promocode.updated_at.seconds)
            }) for promocode in response.promocodes],
            total=response.total,
            page=page,
            per_page=per_page
        )
    except grpc.RpcError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.details()
        )


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
async def login(user: UserLogin):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://user_api:8001/login",
            data={"username": user.username, "password": user.password}  # Используем форму для передачи данных
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
