FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_ENV=production \
    PORT=8080

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# No ejecutar como root dentro del contenedor
RUN useradd --create-home appuser && chown -R appuser /app
USER appuser

# --preload: la app (y la creación de tablas) se carga una sola vez antes de crear los workers
CMD exec gunicorn --bind :$PORT --workers 2 --threads 4 --timeout 60 --preload app:app
