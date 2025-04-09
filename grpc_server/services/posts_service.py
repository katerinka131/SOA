from datetime import datetime
from google.protobuf.timestamp_pb2 import Timestamp
from sqlalchemy.orm import Session
from uuid import UUID
import grpc
import logging
from concurrent import futures
from sqlalchemy.exc import SQLAlchemyError

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Импорт сгенерированных gRPC модулей
from grpc_modules.generated import posts_pb2, posts_pb2_grpc
from .database import get_db, Base, engine, SessionLocal

class PostService(posts_pb2_grpc.PostServiceServicer):
    def __init__(self, db: Session):
        self.db = db

    def _convert_to_proto_time(self, dt: datetime) -> Timestamp:
        """Конвертирует datetime в protobuf Timestamp с гарантией не-None значения"""
        try:
            if dt is None:
                logger.warning("Received None datetime, using current time")
                dt = datetime.utcnow()
            
            timestamp = Timestamp()
            timestamp.FromDatetime(dt)
            return timestamp
        except Exception as e:
            logger.error(f"Error converting datetime: {e}")
            raise ValueError("Invalid datetime format")

    def _validate_post_request(self, request):
        """Валидация входящего запроса"""
        if not request.title or not request.description:
            raise ValueError("Title and description are required")
        
        try:
            UUID(request.creator_id)
        except ValueError:
            raise ValueError("Invalid creator_id format")

    def CreatePost(self, request, context):
        """Создание нового поста с гарантией установки временных меток"""
        try:
            from .database import Post
            
            # Валидация запроса
            self._validate_post_request(request)
            
            # Создаем пост с явным указанием времени
            current_time = datetime.utcnow()
            post = Post(
                title=request.title,
                description=request.description,
                creator_id=UUID(request.creator_id),
                is_private=request.is_private if request.is_private else False,
                tags=list(request.tags) if request.tags else [],
                created_at=current_time,
                updated_at=current_time
            )
            
            self.db.add(post)
            self.db.commit()
            self.db.refresh(post)
            
            # Двойная проверка временных меток
            if post.created_at is None or post.updated_at is None:
                logger.error("Database didn't set timestamps, using fallback")
                post.created_at = post.created_at or current_time
                post.updated_at = post.updated_at or current_time
            
            return posts_pb2.PostResponse(
                id=str(post.id),
                title=post.title,
                description=post.description,
                creator_id=str(post.creator_id),
                created_at=self._convert_to_proto_time(post.created_at),
                updated_at=self._convert_to_proto_time(post.updated_at),
                is_private=post.is_private,
                tags=post.tags
            )
            
        except ValueError as e:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, str(e))
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Database error: {str(e)}")
            context.abort(grpc.StatusCode.INTERNAL, "Database operation failed")
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}", exc_info=True)
            context.abort(grpc.StatusCode.INTERNAL, "Internal server error")

    def GetPost(self, request, context):
        try:
            from .database import Post
            post = self.db.query(Post).filter(Post.id == UUID(request.id)).first()
            
            if not post:
                context.abort(grpc.StatusCode.NOT_FOUND, "Post not found")
            
            if post.is_private and str(post.creator_id) != request.user_id:
                context.abort(grpc.StatusCode.PERMISSION_DENIED, "Private post")
                
            created_at = self._convert_to_proto_time(post.created_at)
            updated_at = self._convert_to_proto_time(post.updated_at)
            
            return posts_pb2.PostResponse(
                id=str(post.id),
                title=post.title,
                description=post.description,
                creator_id=str(post.creator_id),
                created_at=created_at,
                updated_at=updated_at,
                is_private=post.is_private,
                tags=post.tags
            )
        except Exception as e:
            context.abort(grpc.StatusCode.INTERNAL, str(e))

    def UpdatePost(self, request, context):
        try:
            from .database import Post
            post = self.db.query(Post).filter(Post.id == UUID(request.id)).first()
            
            if not post:
                context.abort(grpc.StatusCode.NOT_FOUND, "Post not found")
            
            if str(post.creator_id) != request.user_id:
                context.abort(grpc.StatusCode.PERMISSION_DENIED, "Not your post")
            
            if request.title:
                post.title = request.title
            if request.description:
                post.description = request.description
            if request.is_private is not None:
                post.is_private = request.is_private
            if request.tags:
                post.tags = request.tags
                
            self.db.commit()
            self.db.refresh(post)
            
            created_at = self._convert_to_proto_time(post.created_at)
            updated_at = self._convert_to_proto_time(post.updated_at)
            
            return posts_pb2.PostResponse(
                id=str(post.id),
                title=post.title,
                description=post.description,
                creator_id=str(post.creator_id),
                created_at=created_at,
                updated_at=updated_at,
                is_private=post.is_private,
                tags=post.tags
            )
        except Exception as e:
            context.abort(grpc.StatusCode.INTERNAL, str(e))

    def DeletePost(self, request, context):
        try:
            from .database import Post
            post = self.db.query(Post).filter(Post.id == UUID(request.id)).first()
            
            if not post:
                context.abort(grpc.StatusCode.NOT_FOUND, "Post not found")
            
            if str(post.creator_id) != request.user_id:
                context.abort(grpc.StatusCode.PERMISSION_DENIED, "Not your post")
            
            self.db.delete(post)
            self.db.commit()
            
            return posts_pb2.EmptyResponse()
        except Exception as e:
            context.abort(grpc.StatusCode.INTERNAL, str(e))

    def ListPosts(self, request, context):
        try:
            from .database import Post
            query = self.db.query(Post)
            
            # Фильтр по пользователю для приватных постов
            query = query.filter(
                (Post.creator_id == UUID(request.user_id)) |
                (Post.is_private == False)
            )
            
            # Пагинация
            posts = query.offset((request.page - 1) * request.per_page)\
                        .limit(request.per_page)\
                        .all()
            
            total = query.count()
            
            return posts_pb2.ListPostsResponse(
                posts=[posts_pb2.PostResponse(
                    id=str(post.id),
                    title=post.title,
                    description=post.description,
                    creator_id=str(post.creator_id),
                    created_at=self._convert_to_proto_time(post.created_at),
                    updated_at=self._convert_to_proto_time(post.updated_at),
                    is_private=post.is_private,
                    tags=post.tags
                ) for post in posts],
                total=total
            )
        except Exception as e:
            context.abort(grpc.StatusCode.INTERNAL, str(e))