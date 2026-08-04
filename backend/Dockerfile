FROM python:3.10-slim

WORKDIR /app

# تثبيت المكتبات الأساسية
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# نسخ ملفات التطبيق
COPY . .

EXPOSE 8000

# تشغيل التطبيق عبر Gunicorn في بيئة الإنتاج
# -w 4: تشغيل 4 عمال (Workers) متزامنين
# -k uvicorn.workers.UvicornWorker: دعم FastAPI و Asynchronous Requests
# --bind 0.0.0.0:8000: استماع على جميع الواجهات
# --access-logfile -: إرسال السجلات إلى stdout
# --error-logfile -: إرسال أخطاء إلى stderr
CMD ["gunicorn", "main:app", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000", "--access-logfile", "-", "--error-logfile", "-", "--timeout", "60"]
