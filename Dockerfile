# Dockerfile optimizado para Metricool Personal
FROM python:3.11-slim

# Evita creación de archivos .pyc y buffer en stdout
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

WORKDIR /app

# Dependencias mínimas del sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copiar e instalar requerimientos
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código fuente
COPY . .

# Asegurar carpetas persistentes para base de datos SQLite y videos
RUN mkdir -p /app/data /app/uploads

EXPOSE 8000

# Comando de arranque (usa el puerto asignado por Render o 8000 por defecto)
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
