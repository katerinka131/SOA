import os
import sys
from concurrent import futures
import grpc
import logging
from sqlalchemy.orm import Session

# Добавляем путь к модулям
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Импорт сервисов
from services.posts_service import PostService
from services.promocodes_service import PromocodeService
from services.database import get_db, Base, engine

# Импорт сгенерированных файлов
from grpc_modules.generated import posts_pb2_grpc, promocodes_pb2_grpc

def serve():
    # Создаем таблицы при запуске
    Base.metadata.create_all(bind=engine)
    
    # Создаем сессию для всех сервисов
    db = next(get_db())
    
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    
    # Передаем сессию в сервисы
    posts_pb2_grpc.add_PostServiceServicer_to_server(PostService(db), server)
    promocodes_pb2_grpc.add_PromocodeServiceServicer_to_server(PromocodeService(db), server)
    
    server.add_insecure_port('[::]:50051')
    server.start()
    logging.info("gRPC server started on port 50051")
    server.wait_for_termination()

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    serve()