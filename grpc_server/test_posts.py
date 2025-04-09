import pytest
from unittest.mock import MagicMock, patch, call
from datetime import datetime
from uuid import uuid4, UUID
import grpc
from google.protobuf.timestamp_pb2 import Timestamp
from grpc_modules.generated import posts_pb2
from sqlalchemy.exc import SQLAlchemyError

# Фикстуры
@pytest.fixture
def mock_db():
    return MagicMock()

@pytest.fixture
def mock_context():
    return MagicMock()

@pytest.fixture
def test_uuid():
    return uuid4()

@pytest.fixture
def test_time():
    return datetime.utcnow()

@pytest.fixture
def test_timestamp(test_time):
    timestamp = Timestamp()
    timestamp.FromDatetime(test_time)
    return timestamp

@pytest.fixture
def mock_post(test_uuid, test_time):
    post = MagicMock()
    post.id = test_uuid
    post.title = "Test Post"
    post.description = "Test Description"
    post.creator_id = test_uuid
    post.created_at = test_time
    post.updated_at = test_time
    post.is_private = False
    post.tags = ["tag1", "tag2"]
    return post

@pytest.fixture
def post_service(mock_db):
    with patch('sqlalchemy.orm.declarative_base', return_value=MagicMock()), \
         patch('sqlalchemy.create_engine', return_value=MagicMock()), \
         patch('sqlalchemy.orm.sessionmaker', return_value=MagicMock()):
        from grpc_server.services.posts_service import PostService
        return PostService(mock_db)

# Тесты
class TestPostService:
    def test_validate_post_request_valid(self, post_service, test_uuid):
        """Тест валидации корректного запроса"""
        request = MagicMock()
        request.title = "Valid Title"
        request.description = "Valid Description"
        request.creator_id = str(test_uuid)
        
        # Должен пройти без исключений
        post_service._validate_post_request(request)

    def test_validate_post_request_invalid(self, post_service):
        """Тест валидации некорректного запроса"""
        request = MagicMock()
        request.title = ""
        request.description = ""
        request.creator_id = "invalid-uuid"
        
        with pytest.raises(ValueError):
            post_service._validate_post_request(request)

    def test_create_post_success(self, post_service, mock_db, mock_context, 
                               test_uuid, test_time, mock_post):
        """Тест успешного создания поста"""
        request = posts_pb2.CreatePostRequest(
            title="Test Post",
            description="Test Description",
            creator_id=str(test_uuid),
            is_private=False,
            tags=["tag1", "tag2"]
        )
        
        new_post = MagicMock()
        new_post.id = test_uuid
        new_post.title = request.title
        new_post.description = request.description
        new_post.creator_id = UUID(request.creator_id)
        new_post.is_private = request.is_private
        new_post.tags = request.tags
        new_post.created_at = test_time
        new_post.updated_at = test_time
        
        with patch('grpc_server.services.database.Post', return_value=new_post):
            response = post_service.CreatePost(request, mock_context)
            
            mock_db.add.assert_called_once_with(new_post)
            mock_db.commit.assert_called_once()
            mock_db.refresh.assert_called_once_with(new_post)
            
            assert response.title == "Test Post"
            assert response.description == "Test Description"

    def test_create_post_db_error(self, post_service, mock_db, mock_context, test_uuid):
        """Тест ошибки БД при создании поста"""
        request = posts_pb2.CreatePostRequest(
            title="Test Post",
            description="Test Description",
            creator_id=str(test_uuid)
        )
        
        mock_db.commit.side_effect = SQLAlchemyError("DB error")
        
        post_service.CreatePost(request, mock_context)
        
        mock_context.abort.assert_called_once_with(
            grpc.StatusCode.INTERNAL, 
            "Database operation failed"
        )
        mock_db.rollback.assert_called_once()

    def test_get_post_found(self, post_service, mock_db, mock_context, 
                          test_uuid, mock_post):
        """Тест успешного получения поста"""
        mock_db.query.return_value.filter.return_value.first.return_value = mock_post
        
        request = posts_pb2.GetPostRequest(
            id=str(test_uuid),
            user_id=str(test_uuid)
        )
        
        response = post_service.GetPost(request, mock_context)
        
        assert response.id == str(test_uuid)
        assert response.title == "Test Post"

    def test_get_post_not_found(self, post_service, mock_db, mock_context, test_uuid):
        """Тест случая, когда пост не найден"""
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        request = posts_pb2.GetPostRequest(
            id=str(test_uuid),
            user_id=str(test_uuid)
        )
        
        mock_context.abort.reset_mock()
        post_service.GetPost(request, mock_context)
        
        assert mock_context.abort.called
        expected_call = call(grpc.StatusCode.NOT_FOUND, "Post not found")
        assert expected_call in mock_context.abort.mock_calls

    def test_update_post_success(self, post_service, mock_db, mock_context, 
                               test_uuid, mock_post):
        """Тест успешного обновления поста"""
        mock_db.query.return_value.filter.return_value.first.return_value = mock_post
        
        request = posts_pb2.UpdatePostRequest(
            id=str(test_uuid),
            user_id=str(test_uuid),
            title="Updated Title",
            description="Updated Description",
            is_private=True,
            tags=["new_tag"]
        )
        
        response = post_service.UpdatePost(request, mock_context)
        
        assert mock_post.title == "Updated Title"
        assert mock_post.description == "Updated Description"
        assert mock_post.is_private is True
        assert mock_post.tags == ["new_tag"]
        assert response.title == "Updated Title"

    def test_delete_post_success(self, post_service, mock_db, mock_context, 
                               test_uuid, mock_post):
        """Тест успешного удаления поста"""
        mock_db.query.return_value.filter.return_value.first.return_value = mock_post
        
        request = posts_pb2.DeletePostRequest(
            id=str(test_uuid),
            user_id=str(test_uuid)
        )
        
        response = post_service.DeletePost(request, mock_context)
        
        mock_db.delete.assert_called_once_with(mock_post)
        mock_db.commit.assert_called_once()

    def test_list_posts_success(self, post_service, mock_db, mock_context, 
                              test_uuid, mock_post):
        """Тест получения списка постов"""
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.offset.return_value.limit.return_value.all.return_value = [mock_post]
        mock_query.count.return_value = 1
        mock_db.query.return_value = mock_query
        
        request = posts_pb2.ListPostsRequest(
            user_id=str(test_uuid),
            page=1,
            per_page=10
        )
        
        response = post_service.ListPosts(request, mock_context)
        
        assert len(response.posts) == 1
        assert response.posts[0].title == "Test Post"
        assert response.total == 1