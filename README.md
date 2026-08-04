# Smart Content Hub - المنصة الذكية لسحب وتحليل المقالات

منصة متقدمة لسحب محتوى المقالات من الويب، تحليلها، وتوفير محرك بحث قوي يعتمد على Elasticsearch.

## 🏗️ المعمارية (Architecture)

```
┌─────────────┐
│   Browser   │  (المتصفح)
└──────┬──────┘
       │ HTTP (Port 80)
       ▼
┌─────────────┐
│   Nginx     │  (خادم عكسي - Reverse Proxy)
└──────┬──────┘
       │
       ├─────────────────────┬─────────────────────┐
       ▼                     ▼                     ▼
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  Frontend    │     │   Backend    │     │ Elasticsearch│
│  (React)     │     │  (FastAPI)   │     │  (Search)    │
└──────────────┘     └──────┬───────┘     └──────────────┘
                            │
                            ▼
                     ┌──────────────┐
                     │   Redis      │  (Message Broker)
                     │   (Broker)   │
                     └──────┬───────┘
                            │
                            ▼
                     ┌──────────────┐
                     │   Worker     │
                     │  (Celery)    │
                     │ (Processing) │
                     └──────┬───────┘
                            │
                            ▼
                     ┌──────────────┐
                     │ PostgreSQL   │
                     │ (Database)   │
                     └──────────────┘
```

## 📦 الخدمات (Services)

| الخدمة | الصورة | المنفذ | الدور |
|--------|--------|--------|------|
| **nginx** | nginx:alpine | 80 | خادم عكسي وموزع الأحمال |
| **backend** | python:3.10 | 8000 | واجهة برمجية (FastAPI) |
| **frontend** | node:18 | 80 (عبر nginx) | واجهة مستخدم (React) |
| **worker** | python:3.10 | N/A | معالج مهام (Celery) |
| **postgres_db** | postgres:15 | 5432 | قاعدة البيانات |
| **redis_broker** | redis:7 | 6379 | وسيط الرسائل |
| **elasticsearch** | elasticsearch:8.7 | 9200 | محرك البحث |

## 🚀 البدء السريع (Quick Start)

### المتطلبات
- Docker
- Docker Compose

### التثبيت والتشغيل

```bash
# نسخ المشروع
cd smart-content-hub

# إنشاء ملف البيئة (إذا لم يكن موجوداً)
cat > .env << EOF
DB_USER=content_admin
DB_PASSWORD=secure_password_123
DB_NAME=smart_hub_db
REDIS_URL=redis://redis_broker:6379/0
ELASTICSEARCH_URL=http://elasticsearch:9200
BACKEND_PORT=8000
EOF

# بناء وتشغيل جميع الخدمات
docker-compose up --build -d

# عرض السجلات
docker-compose logs -f
```

## 🌐 نقاط الوصول (Access Points)

بعد التشغيل، ستتمكن من الوصول إلى:

| النقطة | الرابط | الوصف |
|--------|--------|------|
| الواجهة الأمامية | http://localhost | تطبيق React |
| API الرئيسية | http://localhost/api/ | نقطة دخول API |
| توثيق API | http://localhost/docs | Swagger UI التفاعلي |
| Elasticsearch | http://localhost:9200 | محرك البحث (اختياري) |
| Backend المباشر | http://localhost:8000 (يحتاج تعديل nginx) | FastAPI مباشرة |

## 📡 API Endpoints

### 1️⃣ فحص صحة الخدمة
```bash
GET /api/health
```

**الاستجابة:**
```json
{
    "status": "healthy",
    "service": "Smart Content Hub API",
    "version": "1.0.0"
}
```

---

### 2️⃣ سحب وتحليل مقال
```bash
POST /api/analyze
Content-Type: application/json

{
    "url": "https://example.com/article",
    "article_id": "optional-id"
}
```

**الاستجابة:**
```json
{
    "status": "accepted",
    "task_id": "12345-abcde-67890",
    "message": "تم استلام الرابط بنجاح، جاري سحب وتحليل المقال في الخلفية.",
    "check_status_url": "/api/status/12345-abcde-67890",
    "polling_interval_seconds": 2
}
```

---

### 3️⃣ التحقق من حالة المهمة (Polling)
```bash
GET /api/status/{task_id}
```

**الاستجابة أثناء المعالجة:**
```json
{
    "task_id": "12345-abcde-67890",
    "status": "PENDING",
    "result": null,
    "message": "المهمة قيد الانتظار في الطابور",
    "polling_interval_seconds": 2
}
```

**الاستجابة عند الاكتمال:**
```json
{
    "task_id": "12345-abcde-67890",
    "status": "SUCCESS",
    "result": {
        "status": "success",
        "url": "https://example.com/article",
        "title": "عنوان المقال",
        "content_length": 4500,
        "content_preview": "نص المقال الأول..."
    },
    "message": "اكتملت المهمة بنجاح",
    "is_complete": true
}
```

---

### 4️⃣ البحث عن مقالات
```bash
POST /api/search
Content-Type: application/json

{
    "query": "الذكاء الاصطناعي",
    "limit": 10
}
```

**الاستجابة:**
```json
{
    "status": "processing",
    "message": "جاري البحث عن: الذكاء الاصطناعي",
    "task_id": "search-12345",
    "check_status_url": "/api/status/search-12345",
    "polling_interval_seconds": 2
}
```

## 🔄 دورة حياة المهمة (Task Lifecycle)

```
1. المستخدم يرسل رابط
            ▼
2. Backend يستقبل الرابط ويرسله إلى Redis
            ▼
3. Worker يلتقط المهمة من Redis
            ▼
4. Worker يزور الموقع ويسحب المحتوى
            ▼
5. Worker ينظف النص ويرسله إلى Elasticsearch
            ▼
6. Worker يحفظ النتيجة في Redis
            ▼
7. Frontend يتحقق من الحالة (Polling) حتى تصبح SUCCESS
            ▼
8. Frontend يعرض النتيجة للمستخدم
```

## 🛠️ الأوامر المفيدة

```bash
# عرض جميع الحاويات
docker-compose ps

# عرض سجلات خدمة معينة
docker-compose logs -f backend
docker-compose logs -f worker
docker-compose logs -f nginx

# إيقاف جميع الخدمات
docker-compose down

# إزالة جميع البيانات
docker-compose down -v

# إعادة بناء خدمة معينة
docker-compose up --build backend

# الدخول إلى shell حاوية معينة
docker-compose exec backend bash
docker-compose exec worker python

# عرض استهلاك الموارد
docker stats
```

## 📝 هيكل المشروع

```
smart-content-hub/
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── main.py              # FastAPI application
├── frontend/
│   ├── Dockerfile
│   └── (React files)
├── worker/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── tasks.py             # Celery tasks
├── nginx/
│   ├── Dockerfile
│   └── default.conf         # Reverse proxy config
├── .env
├── .dockerignore
├── docker-compose.yml
└── README.md
```

## 🔐 متغيرات البيئة (.env)

```env
# قاعدة البيانات
DB_USER=content_admin           # اسم مستخدم PostgreSQL
DB_PASSWORD=secure_password_123 # كلمة السر
DB_NAME=smart_hub_db            # اسم قاعدة البيانات

# Redis
REDIS_URL=redis://redis_broker:6379/0

# Elasticsearch
ELASTICSEARCH_URL=http://elasticsearch:9200

# Backend
BACKEND_PORT=8000
```

## 🐛 استكشاف الأخطاء (Troubleshooting)

### المشكلة: اتصال Worker بـ Redis فشل

```bash
# تحقق من حالة Redis
docker-compose exec redis_broker redis-cli ping

# عرض سجلات Worker
docker-compose logs worker
```

### المشكلة: Frontend لا يتحمل بشكل صحيح

```bash
# تحقق من إعدادات Nginx
docker-compose exec nginx nginx -t

# عرض سجلات Nginx
docker-compose logs nginx
```

### المشكلة: Elasticsearch لا يستجيب

```bash
# تحقق من حالة Elasticsearch
curl http://localhost:9200/_cluster/health

# عرض السجلات
docker-compose logs elasticsearch
```

## 📚 المراجع

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Celery Documentation](https://docs.celeryproject.org/)
- [Elasticsearch Documentation](https://www.elastic.co/guide/en/elasticsearch/reference/current/index.html)
- [Docker Compose Documentation](https://docs.docker.com/compose/)

## 📄 الرخصة

هذا المشروع مرخص تحت MIT License

## 👨‍💻 المساهمة

يرحب المشروع بالمساهمات! يرجى فتح Issue أو Pull Request.
