FROM python:3.10-slim

WORKDIR /app

# تثبيت المكتبات الأساسية لسحب البيانات وتحليلها
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# تشغيل Celery Worker
CMD ["celery", "-A", "tasks", "worker", "--loglevel=info"]
