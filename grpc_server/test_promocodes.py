import pytest
from unittest.mock import MagicMock, patch, call
from datetime import datetime
from uuid import uuid4, UUID
import grpc
from google.protobuf.timestamp_pb2 import Timestamp
from grpc_modules.generated import promocodes_pb2
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
def mock_promocode(test_uuid, test_time):
    promocode = MagicMock()
    promocode.id = test_uuid
    promocode.name = "Test Promo"
    promocode.description = "Test Description"
    promocode.discount = 10.0
    promocode.code = "TEST123"
    promocode.creator_id = test_uuid
    promocode.created_at = test_time
    promocode.updated_at = test_time
    return promocode

@pytest.fixture
def promocode_service(mock_db):
    with patch('sqlalchemy.orm.declarative_base', return_value=MagicMock()), \
         patch('sqlalchemy.create_engine', return_value=MagicMock()), \
         patch('sqlalchemy.orm.sessionmaker', return_value=MagicMock()):
        from grpc_server.services.promocodes_service import PromocodeService
        return PromocodeService(mock_db)

# Тесты
class TestPromocodeService:
    

    def test_create_promocode_success(self, promocode_service, mock_db, mock_context, test_uuid, test_time):
        """Тест успешного создания промокода"""
        request = promocodes_pb2.CreatePromocodeRequest(
            name="Test Promo",
            description="Test Description",
            discount=10.0,
            code="TEST123",
            creator_id=str(test_uuid)
        )
        
        # Настраиваем mock для нового промокода
        new_promo = MagicMock()
        new_promo.id = test_uuid
        new_promo.name = request.name
        new_promo.description = request.description
        new_promo.discount = request.discount
        new_promo.code = request.code
        new_promo.creator_id = UUID(request.creator_id)
        new_promo.created_at = test_time
        new_promo.updated_at = test_time
        
        # Мокаем запрос к БД на проверку существующего промокода
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        with patch('grpc_server.services.database.Promocode', return_value=new_promo):
            response = promocode_service.CreatePromocode(request, mock_context)
            
            mock_db.add.assert_called_once_with(new_promo)
            mock_db.commit.assert_called_once()
            mock_db.refresh.assert_called_once_with(new_promo)
            
            assert response.name == "Test Promo"
            assert response.code == "TEST123"

    def test_create_promocode_duplicate(self, promocode_service, mock_db, mock_context, test_uuid):
        """Тест создания дубликата промокода"""
        request = promocodes_pb2.CreatePromocodeRequest(
            name="Test Promo",
            code="TEST123",
            creator_id=str(test_uuid)
        )
        
        # Мокаем что промокод уже существует
        mock_db.query.return_value.filter.return_value.first.return_value = MagicMock()
        
        promocode_service.CreatePromocode(request, mock_context)
        
        mock_context.abort.assert_called_once_with(
            grpc.StatusCode.ALREADY_EXISTS,
            "Promocode with code 'TEST123' already exists"
        )

    def test_get_promocode_success(self, promocode_service, mock_db, mock_context, test_uuid, mock_promocode):
        """Тест успешного получения промокода"""
        mock_db.query.return_value.filter.return_value.first.return_value = mock_promocode
        
        request = promocodes_pb2.GetPromocodeRequest(
            id=str(test_uuid),
            user_id=str(test_uuid)
        )
        
        response = promocode_service.GetPromocode(request, mock_context)
        
        assert response.id == str(test_uuid)
        assert response.name == "Test Promo"

    def test_get_promocode_not_found(self, promocode_service, mock_db, mock_context, test_uuid):
        mock_db.query.return_value.filter.return_value.first.return_value = None
    
        request = promocodes_pb2.GetPromocodeRequest(
            id=str(test_uuid),
            user_id=str(test_uuid)
        )
        
        # Сбрасываем счетчик вызовов перед тестом
        mock_context.abort.reset_mock()
        
        # Вызываем тестируемый метод
        promocode_service.GetPromocode(request, mock_context)
        
        assert mock_context.abort.called
        
        calls = mock_context.abort.mock_calls
        
        expected_call = call(grpc.StatusCode.NOT_FOUND, "Promocode not found")
        assert expected_call in calls, f"Expected call {expected_call} not found in {calls}"

    def test_update_promocode_success(self, promocode_service, mock_db, mock_context, 
                                test_uuid, mock_promocode):
        """Тест успешного обновления промокода"""
        mock_db.query.return_value.filter.return_value.first.return_value = mock_promocode
        
        request = promocodes_pb2.UpdatePromocodeRequest(
            id=str(test_uuid),
            user_id=str(test_uuid),
            name="Updated Name",
            description="Updated Description",
            discount=15.0,
            code="NEWCODE"
        )
        
        response = promocode_service.UpdatePromocode(request, mock_context)
        
        assert mock_promocode.name == "Updated Name"
        assert mock_promocode.description == "Updated Description"
        assert mock_promocode.discount == 15.0
        assert mock_promocode.code == "NEWCODE"
        assert response.name == "Updated Name"

    def test_delete_promocode_success(self, promocode_service, mock_db, mock_context, test_uuid, mock_promocode):
        """Тест успешного удаления промокода"""
        mock_db.query.return_value.filter.return_value.first.return_value = mock_promocode
        
        request = promocodes_pb2.DeletePromocodeRequest(
            id=str(test_uuid),
            user_id=str(test_uuid)
        )
        
        response = promocode_service.DeletePromocode(request, mock_context)
        
        mock_db.delete.assert_called_once_with(mock_promocode)
        mock_db.commit.assert_called_once()

    def test_list_promocodes_success(self, promocode_service, mock_db, mock_context, test_uuid, mock_promocode):
        """Тест получения списка промокодов"""
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.offset.return_value.limit.return_value.all.return_value = [mock_promocode]
        mock_query.count.return_value = 1
        mock_db.query.return_value = mock_query
        
        request = promocodes_pb2.ListPromocodesRequest(
            user_id=str(test_uuid),
            page=1,
            per_page=10
        )
        
        response = promocode_service.ListPromocodes(request, mock_context)
        
        assert len(response.promocodes) == 1
        assert response.promocodes[0].name == "Test Promo"
        assert response.total == 1