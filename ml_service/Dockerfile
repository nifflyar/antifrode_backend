FROM python:3.12-slim

WORKDIR /app

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    sed \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Fix potential Windows CRLF issues
RUN find . -name "*.sh" -exec sed -i 's/\r$//' {} +

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
