# from passlib.context import CryptContext
# from jose import jwt
# import datetime

# SECRET_KEY = "supersecret"
# ALGORITHM = "HS256"
# pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# def hash_password(password):
#     return pwd_context.hash(password)

# def verify_password(plain_password, hashed_password):
#     return pwd_context.verify(plain_password, hashed_password)

# def create_token(user_id: str):
#     expire = datetime.datetime.utcnow() + datetime.timedelta(days=1)
#     return jwt.encode({"sub": user_id, "exp": expire}, SECRET_KEY, algorithm=ALGORITHM)
