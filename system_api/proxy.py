# import httpx
# from config import USER_API_URL

# async def register_user(data):
#     async with httpx.AsyncClient() as client:
#         try:
#             response = await client.post(f"{USER_API_URL}/register", json=data)
#             response.raise_for_status()  # Проверка на успешность запроса
#             return response.json()
#         except httpx.HTTPStatusError as e:
#             return {"error": f"HTTP error occurred: {e.response.status_code}"}
#         except Exception as e:
#             return {"error": str(e)}


# async def authenticate_user(data):
#     async with httpx.AsyncClient() as client:
#         response = await client.post(f"{USER_API_URL}/login", json=data)
#     return response.json()
