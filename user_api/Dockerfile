FROM python:3.11

WORKDIR /app

# Сначала копируем только requirements.txt
COPY requirements.txt .

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Затем копируем остальные файлы
COPY . .

CMD ["python", "main.py"]