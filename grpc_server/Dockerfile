FROM python:3.9-slim

RUN apt-get update && \
    apt-get install -y \
    gcc \
    python3-dev \
    libpq-dev \
    protobuf-compiler \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY ./grpc_server/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем proto-файлы
COPY ./grpc_modules /app/protos

# Генерируем файлы в отдельную папку
RUN mkdir -p /app/protos/generated && \
    python -m grpc_tools.protoc \
    -I/app/protos \
    --python_out=/app/protos/generated \
    --grpc_python_out=/app/protos/generated \
    /app/protos/posts.proto \
    /app/protos/promocodes.proto

# Фиксим импорты в сгенерированных файлах
RUN sed -i 's/^import \(.*\)_pb2 as/from protos.generated import \1_pb2 as/' /app/protos/generated/*_pb2_grpc.py && \
    sed -i 's/^from \(.*\) import \(.*\)_pb2 as/from protos.generated import \2_pb2 as/' /app/protos/generated/*_pb2_grpc.py

# Инициализируем пакет
RUN touch /app/protos/__init__.py && \
    touch /app/protos/generated/__init__.py

# Копируем остальной код
COPY ./grpc_server/ .

ENV PYTHONPATH="${PYTHONPATH}:/app"

CMD ["python", "main.py"]