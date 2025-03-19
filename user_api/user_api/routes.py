# from fastapi import FastAPI, Depends, HTTPException
# from sqlalchemy.orm import Session
# from database import SessionLocal, User, init_db
# from auth import hash_password, verify_password, create_token

# app = FastAPI(title="User API", description="Handles user authentication", version="1.0")

# def get_db():
#     db = SessionLocal()
#     try:
#         yield db
#     finally:
#         db.close()

# @app.post("/register")
# async def register(username: str, email: str, password: str, db: Session = Depends(get_db)):
#     # Хеширование пароля
#     hashed_pw = hash_password(password)
    
#     # Создание нового пользователя
#     user = User(username=username, email=email, password=hashed_pw)
    
#     # Добавление пользователя в базу данных
#     db.add(user)
#     db.commit()
    
#     # Возвращаем ID пользователя после регистрации
#     return {"message": "User registered", "user_id": user.id}

# @app.post("/login")
# async def login(username: str, password: str, db: Session = Depends(get_db)):
#     # Поиск пользователя по имени
#     user = db.query(User).filter(User.username == username).first()
    
#     # Проверка наличия пользователя и пароля
#     if not user or not verify_password(password, user.password):
#         raise HTTPException(status_code=401, detail="Invalid credentials")
    
#     # Создание токена для пользователя
#     token = create_token(user.id)
    
#     # Возвращаем токен и ID пользователя
#     return {"access_token": token, "user_id": user.id}

# @app.get("/profile")
# async def profile(username: str, db: Session = Depends(get_db)):
#     # Поиск пользователя по имени
#     user = db.query(User).filter(User.username == username).first()
    
#     # Если пользователь не найден, генерируем ошибку
#     if not user:
#         raise HTTPException(status_code=404, detail="User not found")
    
#     # Возвращаем все данные о пользователе
#     return user
