# 🚀 Smart Content Hub - دليل النشر والاستخدام الشامل

## 📋 فهرس المحتويات

1. [البدء السريع](#البدء-السريع)
2. [المعمارية](#المعمارية)
3. [الخدمات](#الخدمات)
4. [API Endpoints](#api-endpoints)
5. [أمثلة عملية](#أمثلة-عملية)
6. [استكشاف الأخطاء](#استكشاف-الأخطاء)
7. [النصائح الإنتاجية](#النصائح-الإنتاجية)

---

## 🚀 البدء السريع

### المتطلبات
- Docker و Docker Compose
- 4GB RAM متاح على الأقل
- 20GB مساحة تخزين فارغة

### التثبيت والتشغيل

```bash
# 1. الانتقال إلى مجلد المشروع
cd smart-content-hub

# 2. بناء وتشغيل جميع الخدمات
docker-compose up --build -d

# 3. التحقق من حالة الخدمات
docker-compose ps

# 4. عرض السجلات
docker-compose logs -f
```

**المدة المتوقعة للبدء الأول:** 2-3 دقائق

---

## 🏗️ المعمارية

```
┌─────────────────────────────────────────────────────────────┐
│                      المتصفح (Client)                       │
│                    يدخل http://localhost                    │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTP Request (Port 80)
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                  Nginx (Reverse Proxy)                      │
│   - يوجه طلبات "/" للـ Frontend                            │
│   - يوجه طلبات "/api/" للـ Backend                         │
│   - يوجه طلبات "/search/" لـ Elasticsearch (اختياري)      │
└──┬─────────────────────────────────────────────────────────┘
   │
   ├─────────────────┬────────────────────┬──────────────────┐
   ▼                 ▼                    ▼                  ▼
┌─────────┐    ┌──────────┐        ┌──────────┐      ┌────────┐
│Frontend │    │ Backend  │        │Elasticsearch│    │pgAdmin │
│ (React) │    │(FastAPI) │        │  (Search)  │    │(UI)    │
└─────────┘    └──────┬───┘        └──────┬─────┘    └────────┘
                      │                   │
                      └────────┬──────────┘
                               ▼
                      ┌──────────────────┐
                      │     Redis        │
                      │  (Message Broker)│
                      └────────┬─────────┘
                               │
                      ┌────────▼─────────┐
                      │     Worker       │
                      │    (Celery)      │
                      │ - Scrape         │
                      │ - Index          │
                      │ - Search         │
                      └────────┬─────────┘
                               │
                ┌──────────────┴──────────────┐
                ▼                            ▼
        ┌─────────────────┐        ┌──────────────────┐
        │   PostgreSQL    │        │  Elasticsearch   │
        │   (Persistent)  │        │  (Full-Text)     │
        └─────────────────┘        └──────────────────┘
```

---

## 📦 الخدمات

### 1. Nginx (خادم عكسي)
```yaml
الصورة: nginx:alpine
المنفذ: 80
الدور: توجيه الطلبات، موازنة الأحمال
```

### 2. Frontend (واجهة مستخدم)
```yaml
الصورة: node:18-alpine (build) + nginx:alpine (runtime)
المنفذ: 80 (عبر Nginx)
الدور: عرض المقالات، إدارة البيانات من المستخدم
اللغة: JavaScript/React
```

### 3. Backend (واجهة برمجية)
```yaml
الصورة: python:3.10-slim
المنفذ: 8000
الدور: معالجة الطلبات، تنسيق المهام
الإطار: FastAPI
```

### 4. Worker (معالج المهام)
```yaml
الصورة: python:3.10-slim
المنفذ: N/A (بدون واجهة مستخدم)
الدور: سحب المقالات، تنظيفها، فهرستها
المجدول: Celery
```

### 5. PostgreSQL (قاعدة البيانات)
```yaml
الصورة: postgres:15-alpine
المنفذ: 5432 (داخلي فقط)
الدور: تخزين دائم للبيانات
البيانات المحفوظة: articles, search_logs
```

### 6. Redis (وسيط الرسائل)
```yaml
الصورة: redis:7-alpine
المنفذ: 6379 (داخلي فقط)
الدور: وسيط اتصال بين Backend و Worker
```

### 7. Elasticsearch (محرك البحث)
```yaml
الصورة: docker.elastic.co/elasticsearch/elasticsearch:8.7.0
المنفذ: 9200 (داخلي + اختياري للوصول المباشر)
الدور: فهرسة وبحث سريع في النصوص
```

---

## 🔌 API Endpoints

### أساسية

#### 1. فحص الصحة
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

### جلب المقالات

#### 2. قائمة المقالات (مع Pagination)
```bash
GET /api/articles?skip=0&limit=10
```

**Parameters:**
- `skip`: عدد المقالات المراد تخطيها (افتراضي: 0)
- `limit`: عدد المقالات المراد جلبها (افتراضي: 10، الحد الأقصى: 100)

**الاستجابة:**
```json
{
  "items": [
    {
      "id": 1,
      "url": "https://example.com/article1",
      "title": "عنوان المقال",
      "content_preview": "نص المقال الأول...",
      "content_length": 5000,
      "created_at": "2026-08-04T12:00:00"
    }
  ],
  "total": 42,
  "skip": 0,
  "limit": 10,
  "has_more": true
}
```

---

#### 3. مقال واحد
```bash
GET /api/articles/{article_id}
```

**الاستجابة:**
```json
{
  "id": 1,
  "url": "https://example.com/article1",
  "title": "عنوان المقال",
  "content": "نص المقال الكامل...",
  "content_preview": "نص المقال الأول...",
  "content_length": 5000,
  "created_at": "2026-08-04T12:00:00",
  "updated_at": "2026-08-04T12:00:00"
}
```

---

#### 4. حذف مقال
```bash
DELETE /api/articles/{article_id}
```

**الاستجابة:**
```json
{
  "message": "تم حذف المقال بنجاح",
  "article_id": 1
}
```

---

### سحب وتحليل

#### 5. إضافة مقال جديد (سحب وتحليل)
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
  "message": "تم استلام الرابط بنجاح، جاري سحب وتحليل المقال.",
  "check_status_url": "/api/status/12345-abcde-67890"
}
```

---

#### 6. التحقق من حالة المهمة (Polling)
```bash
GET /api/status/{task_id}
```

**الاستجابة عند الانتظار:**
```json
{
  "task_id": "12345-abcde-67890",
  "status": "PENDING",
  "result": null,
  "message": "المهمة قيد الانتظار في الطابور"
}
```

**الاستجابة عند الاكتمال:**
```json
{
  "task_id": "12345-abcde-67890",
  "status": "SUCCESS",
  "result": {
    "status": "success",
    "article_id": 1,
    "title": "عنوان المقال",
    "url": "https://example.com/article",
    "content_length": 5000,
    "content_preview": "نص المقال..."
  },
  "message": "اكتملت المهمة بنجاح"
}
```

---

### البحث

#### 7. البحث عن مقالات
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
  "check_status_url": "/api/status/search-12345"
}
```

---

#### 8. سجل البحث
```bash
GET /api/search-logs?limit=10
```

---

### الإحصائيات

#### 9. إحصائيات عامة
```bash
GET /api/stats
```

**الاستجابة:**
```json
{
  "total_articles": 42,
  "total_searches": 15,
  "recent_articles": [...],
  "popular_searches": [...]
}
```

---

## 💡 أمثلة عملية

### مثال 1: إضافة مقال جديد والانتظار حتى ينتهي

```bash
# الخطوة 1: إرسال الرابط
curl -X POST http://localhost/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com/article"}'

# سيرد الخادم:
# {
#   "task_id": "abc123def456"
# }

# الخطوة 2: الاستعلام عن الحالة كل ثانيتين
for i in {1..30}; do
  curl http://localhost/api/status/abc123def456
  sleep 2
done

# عندما يصبح status = "SUCCESS"، المقال جاهز!
```

---

### مثال 2: البحث عن مقالات

```bash
# إرسال استعلام بحث
curl -X POST http://localhost/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "Docker", "limit": 5}'

# التحقق من النتائج
curl http://localhost/api/status/search-xyz789
```

---

### مثال 3: الحصول على جميع المقالات مع Pagination

```bash
# الصفحة الأولى
curl http://localhost/api/articles?skip=0&limit=10

# الصفحة الثانية
curl http://localhost/api/articles?skip=10&limit=10

# الصفحة الثالثة
curl http://localhost/api/articles?skip=20&limit=10
```

---

## 🔧 استكشاف الأخطاء

### المشكلة: Worker لا يستجيب

```bash
# تحقق من حالة Worker
docker-compose logs worker

# تحقق من اتصال Redis
docker-compose exec redis_broker redis-cli ping

# أعد تشغيل Worker
docker-compose restart worker
```

---

### المشكلة: Elasticsearch لا يستجيب

```bash
# تحقق من حالة Elasticsearch
curl http://localhost:9200/_cluster/health

# عرض السجلات
docker-compose logs elasticsearch

# تحقق من الموارد المتاحة
docker stats hub_elastic
```

---

### المشكلة: قاعدة البيانات لا تستقبل الاتصالات

```bash
# تحقق من PostgreSQL
docker-compose logs postgres_db

# تحقق من التوفر
docker-compose exec postgres_db pg_isready -U content_admin

# إعادة تشغيل
docker-compose restart postgres_db
```

---

## 📊 النصائح الإنتاجية

### 1. رصد الأداء

```bash
# عرض استهلاك الموارد
docker stats

# عرض حجم قاعدة البيانات
docker-compose exec postgres_db psql -U content_admin -d smart_hub_db \
  -c "SELECT pg_size_pretty(pg_database_size('smart_hub_db'));"
```

### 2. النسخ الاحتياطية

```bash
# نسخة احتياطية من PostgreSQL
docker-compose exec postgres_db pg_dump -U content_admin smart_hub_db > backup.sql

# استعادة النسخة الاحتياطية
docker-compose exec -T postgres_db psql -U content_admin smart_hub_db < backup.sql
```

### 3. تنظيف البيانات

```bash
# حذف جميع المقالات (احذر!)
docker-compose exec postgres_db psql -U content_admin smart_hub_db \
  -c "DELETE FROM articles;"

# حذف فهرس Elasticsearch
curl -X DELETE http://localhost:9200/articles
```

### 4. الأداء والتحسينات

- **قاعدة البيانات:** استخدم `LIMIT` و `OFFSET` دائماً (Pagination)
- **البحث:** Elasticsearch يتعامل مع آلاف المقالات بكفاءة
- **Worker:** يمكنك تشغيل عدة نسخ من Worker للمعالجة المتزامنة:

```yaml
worker1:
  build: ./worker
  # ... الإعدادات ...

worker2:
  build: ./worker
  # ... الإعدادات ...

worker3:
  build: ./worker
  # ... الإعدادات ...
```

---

## 🔐 الأمان

### تغيير كلمات المرور

عدّل ملف `.env`:

```env
DB_USER=admin_جديد
DB_PASSWORD=كلمة_سر_قوية_جداً
```

### تعطيل Elasticsearch من الخارج

في `nginx/default.conf`:

```nginx
# احذف أو علّق هذا الجزء
# location /search/ {
#     proxy_pass http://elasticsearch:9200/;
# }
```

---

## 📚 الموارد الإضافية

- [FastAPI Docs](https://fastapi.tiangolo.com/)
- [Celery Docs](https://docs.celeryproject.org/)
- [Elasticsearch Docs](https://www.elastic.co/guide/en/elasticsearch/reference/)
- [PostgreSQL Docs](https://www.postgresql.org/docs/)
- [React Docs](https://react.dev/)

---

## 📞 الدعم والمساهمة

هذا المشروع مفتوح المصدر. يرحب بالمساهمات والتحسينات!

**آخر تحديث:** 2026-08-04
