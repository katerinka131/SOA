from datetime import datetime
from google.protobuf.timestamp_pb2 import Timestamp
from grpc_modules.generated import promocodes_pb2, promocodes_pb2_grpc
from .database import get_db
from sqlalchemy.orm import Session
from uuid import UUID
import grpc

class PromocodeService(promocodes_pb2_grpc.PromocodeServiceServicer):
    def __init__(self, db: Session): 
        self.db = db

    def _convert_to_proto_time(self, dt: datetime) -> Timestamp:
        if dt is None:
            dt = datetime.utcnow()  # или можно вернуть минимальную дату
        timestamp = Timestamp()
        timestamp.FromDatetime(dt)
        return timestamp
    def CreatePromocode(self, request, context):
        try:
            from .database import Promocode
            
            # Проверка на существующий промокод
            if self.db.query(Promocode).filter(Promocode.code == request.code).first():
                context.abort(grpc.StatusCode.ALREADY_EXISTS, 
                            f"Promocode with code '{request.code}' already exists")
            
            # Создаем промокод с текущим временем
            now = datetime.utcnow()
            promocode = Promocode(
                name=request.name,
                description=request.description,
                discount=request.discount,
                code=request.code,
                creator_id=UUID(request.creator_id),
                created_at=now,
                updated_at=now
            )
            
            self.db.add(promocode)
            self.db.commit()
            self.db.refresh(promocode)
            
            return promocodes_pb2.PromocodeResponse(
                id=str(promocode.id),
                name=promocode.name,
                description=promocode.description,
                creator_id=str(promocode.creator_id),
                discount=promocode.discount,
                code=promocode.code,
                created_at=self._convert_to_proto_time(promocode.created_at),
                updated_at=self._convert_to_proto_time(promocode.updated_at)
            )
        except Exception as e:
            context.abort(grpc.StatusCode.INTERNAL, str(e))

    def GetPromocode(self, request, context):
        try:
            from .database import Promocode
            promocode = self.db.query(Promocode).filter(Promocode.id == UUID(request.id)).first()
            
            if not promocode:
                context.abort(grpc.StatusCode.NOT_FOUND, "Promocode not found")
            
            if str(promocode.creator_id) != request.user_id:
                context.abort(grpc.StatusCode.PERMISSION_DENIED, "Not your promocode")
            
            created_at = self._convert_to_proto_time(promocode.created_at)
            updated_at = self._convert_to_proto_time(promocode.updated_at)
            
            return promocodes_pb2.PromocodeResponse(
                id=str(promocode.id),
                name=promocode.name,
                description=promocode.description,
                creator_id=str(promocode.creator_id),
                discount=promocode.discount,
                code=promocode.code,
                created_at=created_at,
                updated_at=updated_at
            )
        except Exception as e:
            context.abort(grpc.StatusCode.INTERNAL, str(e))

    def UpdatePromocode(self, request, context):
        try:
            from .database import Promocode
            
            # Получаем промокод
            promocode = self.db.query(Promocode).filter(Promocode.id == UUID(request.id)).first()
            if not promocode:
                context.abort(grpc.StatusCode.NOT_FOUND, "Promocode not found")
            
            # Проверяем права пользователя
            if str(promocode.creator_id) != request.user_id:
                context.abort(grpc.StatusCode.PERMISSION_DENIED, "Not your promocode")
            
            # Проверяем, изменился ли код и не дублируется ли он
            if request.code and request.code != promocode.code:
                existing_promo = self.db.query(Promocode).filter(
                    Promocode.code == request.code,
                    Promocode.id != UUID(request.id)  # Исключаем текущий промокод из проверки
                ).first()
                if existing_promo:
                    context.abort(grpc.StatusCode.ALREADY_EXISTS, 
                                f"Promocode with code '{request.code}' already exists")
            
            # Обновляем только те поля, которые были переданы
            if request.name:
                promocode.name = request.name
            if request.description:
                promocode.description = request.description
            if request.discount:
                promocode.discount = request.discount
            if request.code:
                promocode.code = request.code
            
            # Явно устанавливаем updated_at
            promocode.updated_at = datetime.utcnow()
            
            try:
                self.db.commit()
                self.db.refresh(promocode)
            except Exception as e:
                self.db.rollback()  # Важно делать rollback при ошибках
                context.abort(grpc.StatusCode.INTERNAL, f"Database error: {str(e)}")
            
            return promocodes_pb2.PromocodeResponse(
                id=str(promocode.id),
                name=promocode.name,
                description=promocode.description,
                creator_id=str(promocode.creator_id),
                discount=promocode.discount,
                code=promocode.code,
                created_at=self._convert_to_proto_time(promocode.created_at),
                updated_at=self._convert_to_proto_time(promocode.updated_at)
            )
        except Exception as e:
            if hasattr(self, 'db'):
                self.db.rollback()
            context.abort(grpc.StatusCode.INTERNAL, str(e))

    def DeletePromocode(self, request, context):
        try:
            from .database import Promocode
            promocode = self.db.query(Promocode).filter(Promocode.id == UUID(request.id)).first()
            
            if not promocode:
                context.abort(grpc.StatusCode.NOT_FOUND, "Promocode not found")
            
            if str(promocode.creator_id) != request.user_id:
                context.abort(grpc.StatusCode.PERMISSION_DENIED, "Not your promocode")
            
            self.db.delete(promocode)
            self.db.commit()
            
            return promocodes_pb2.EmptyResponse()
        except Exception as e:
            context.abort(grpc.StatusCode.INTERNAL, str(e))

    def ListPromocodes(self, request, context):
        try:
            from .database import Promocode
            query = self.db.query(Promocode)\
                          .filter(Promocode.creator_id == UUID(request.user_id))
            
            # Пагинация
            promocodes = query.offset((request.page - 1) * request.per_page)\
                              .limit(request.per_page)\
                              .all()
            
            total = query.count()
            
            return promocodes_pb2.ListPromocodesResponse(
                promocodes=[promocodes_pb2.PromocodeResponse(
                    id=str(promo.id),
                    name=promo.name,
                    description=promo.description,
                    creator_id=str(promo.creator_id),
                    discount=promo.discount,
                    code=promo.code,
                    created_at=self._convert_to_proto_time(promo.created_at),
                    updated_at=self._convert_to_proto_time(promo.updated_at)
                ) for promo in promocodes],
                total=total
            )
        except Exception as e:
            context.abort(grpc.StatusCode.INTERNAL, str(e))