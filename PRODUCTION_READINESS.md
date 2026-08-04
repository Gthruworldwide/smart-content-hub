# 🚀 Production Readiness Guide - Smart Content Hub

## 📋 اعتبارات الإنتاج (Production Considerations)

هذا الدليل يغطي كيفية تحضير منصة Smart Content Hub للعمل في بيئة الإنتاج الحقيقية.

---

## 1️⃣ تحسينات الأداء (Performance Optimization)

### 1.1 Gunicorn Workers Configuration

```bash
# عدد Workers = (2 × CPU Cores) + 1
# للـ 4-core machine: (2 × 4) + 1 = 9 workers
docker-compose exec backend bash
# داخل الحاوية:
ps aux | grep gunicorn  # للتحقق من عدد Workers
```

**الإعدادات الحالية:**
```dockerfile
CMD ["gunicorn", "main:app", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", ...]
```

**للماكينات الأقوى:**
```dockerfile
CMD ["gunicorn", "main:app", "-w", "16", "-k", "uvicorn.workers.UvicornWorker", ...]
```

### 1.2 Connection Pooling

```python
# backend/database.py - تحديث موجود
engine = create_engine(
    DATABASE_URL,
    pool_size=20,           # عدد الاتصالات الدائمة
    max_overflow=40,        # اتصالات إضافية مؤقتة
    pool_recycle=3600,      # إعادة تدوير كل ساعة
    pool_pre_ping=True      # التحقق قبل الاستخدام
)
```

### 1.3 Celery Worker Concurrency

```yaml
# docker-compose.yml
worker:
  command: celery -A tasks worker --loglevel=info --concurrency=8 -Ofair
```

**خيارات:**
- `--concurrency=8`: عدد المهام المتزامنة
- `-Ofair`: توزيع عادل للمهام
- `--prefetch-multiplier=1`: قلل استهلاك الذاكرة

---

## 2️⃣ المراقبة والتنبيهات (Monitoring & Alerts)

### 2.1 الوصول إلى لوحة المراقبة

```
Prometheus: http://localhost:9090
Grafana: http://localhost:3000 (admin/admin)
API Metrics: http://localhost:8000/metrics
```

### 2.2 المقاييس المهمة للمراقبة

| المقياس | الحد الأخضر | الحد الأحمر | الإجراء |
|---------|----------|----------|--------|
| CPU Usage | <50% | >80% | زيادة Workers |
| Memory Usage | <2GB | >3.5GB | تقليل Concurrency |
| API Response Time | <100ms | >500ms | Scale Up |
| DB Connections | <10 | >40 | زيادة Pool Size |
| Queue Depth | <50 | >500 | زيادة Workers |
| Error Rate | <0.1% | >1% | تحقق من السجلات |

### 2.3 إنشاء تنبيهات Prometheus

```yaml
# monitoring/alerts.yml
groups:
  - name: api_alerts
    rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.01
        for: 5m
        annotations:
          summary: "High error rate detected"
          
      - alert: SlowAPI
        expr: histogram_quantile(0.95, http_request_duration_seconds) > 1
        for: 10m
        annotations:
          summary: "API response time is high"
```

---

## 3️⃣ الأمان (Security Hardening)

### 3.1 متغيرات البيئة الحساسة

```bash
# .env - لا تُخزن في Git
DB_USER=prod_user
DB_PASSWORD=<strong-password-here>
ELASTICSEARCH_USER=elastic
ELASTICSEARCH_PASSWORD=<strong-password-here>
```

### 3.2 HTTPS/TLS Configuration

```nginx
# nginx/default.conf
server {
    listen 443 ssl http2;
    ssl_certificate /etc/nginx/certs/cert.pem;
    ssl_certificate_key /etc/nginx/certs/key.pem;
    
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    
    location / {
        proxy_pass http://frontend:80;
    }
}

# إعادة التوجيه HTTP → HTTPS
server {
    listen 80;
    server_name _;
    return 301 https://$host$request_uri;
}
```

### 3.3 API Rate Limiting

```python
# backend/main.py - إضافة Rate Limiting
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.post("/api/analyze")
@limiter.limit("10/minute")
async def analyze_article(request: ArticleRequest):
    # ... code ...
```

---

## 4️⃣ النسخ الاحتياطية والكوارث (Backup & DR)

### 4.1 النسخ الاحتياطية من PostgreSQL

```bash
# يومي
0 2 * * * docker-compose exec postgres_db pg_dump -U app_user smart_hub_db > /backups/db_$(date +\%Y\%m\%d).sql

# استعادة من نسخة احتياطية
docker-compose exec postgres_db psql -U app_user smart_hub_db < /backups/db_20260804.sql
```

### 4.2 نسخ احتياطية من Elasticsearch

```bash
# إنشاء Snapshot
curl -X PUT "localhost:9200/_snapshot/my_backup" -H 'Content-Type: application/json' -d '{
  "type": "fs",
  "settings": {"location": "/backup/elasticsearch"}
}'

# النسخ الاحتياطية الدورية
curl -X PUT "localhost:9200/_snapshot/my_backup/snapshot_1"
```

### 4.3 استراتيجية الاسترجاع (Recovery)

```
RTO (Recovery Time Objective): 1 ساعة
RPO (Recovery Point Objective): 15 دقيقة

Plan:
1. قاعدة البيانات الأساسية: 99.99% SLA
2. Elasticsearch: Snapshot يومي
3. Redis: عدم الحرجة (يمكن إعادة البناء)
```

---

## 5️⃣ التوسع (Scaling Strategy)

### 5.1 التوسع الرأسي (Vertical)

```yaml
# زيادة موارد الحاوية
services:
  backend:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
        reservations:
          cpus: '1'
          memory: 2G
```

### 5.2 التوسع الأفقي (Horizontal)

```bash
# تشغيل عمال إضافيين
docker-compose up --scale worker=5

# أو في Kubernetes
kubectl scale deployment worker-deployment --replicas=5
```

### 5.3 Load Balancing

```nginx
# nginx/default.conf - Backend Load Balancing
upstream backend {
    server backend1:8000;
    server backend2:8000;
    server backend3:8000;
}

server {
    location /api/ {
        proxy_pass http://backend;
    }
}
```

---

## 6️⃣ التطوير المستمر (CI/CD)

### 6.1 GitHub Actions Pipeline

```yaml
name: Deploy to Production

on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run Tests
        run: docker-compose up --abort-on-container-exit
      
  deploy:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Deploy to Server
        run: |
          ssh production-server 'cd smart-content-hub && git pull && docker-compose up -d'
```

---

## 7️⃣ السجلات والتصحيح (Logging & Debugging)

### 7.1 مراقبة السجلات

```bash
# جميع الخدمات
docker-compose logs -f

# خدمة محددة
docker-compose logs -f backend

# آخر 100 سطر
docker-compose logs -f --tail=100 worker

# بتصفية التاريخ
docker-compose logs --since 2h backend
```

### 7.2 تكوين الفرز المركزي (Centralized Logging)

```yaml
# إضافة ELK Stack
elasticsearch:
  # موجود بالفعل

logstash:
  image: docker.elastic.co/logstash/logstash:8.7.0
  volumes:
    - ./monitoring/logstash.conf:/usr/share/logstash/pipeline/logstash.conf

kibana:
  image: docker.elastic.co/kibana/kibana:8.7.0
  ports:
    - "5601:5601"
```

---

## 8️⃣ قائمة التحقق قبل الإطلاق

- [ ] تم تحديث جميع بيانات المعايير الإنتاجية
- [ ] تم تفعيل HTTPS/TLS
- [ ] تم إعداد النسخ الاحتياطية
- [ ] تم اختبار فشل الخدمات وتعافيها
- [ ] تم تكوين المراقبة والتنبيهات
- [ ] تم توثيق الإجراءات الطوارئ
- [ ] تم اختبار حمل شامل (Load Testing)
- [ ] تم مراجعة الأمان (Security Audit)
- [ ] تم التدريب على العمليات
- [ ] تم توثيق جميع العمليات

---

## 9️⃣ العمليات الروتينية

### 9.1 الفحص الأسبوعي

```bash
# تحقق من استخدام الموارد
docker stats --no-stream

# تحقق من حالة الخدمات
docker-compose ps

# حجم قاعدة البيانات
docker-compose exec postgres_db du -sh /var/lib/postgresql/data

# حجم Elasticsearch
curl localhost:9200/_cat/indices?v
```

### 9.2 الصيانة الشهرية

```bash
# تنظيف الحاويات غير المستخدمة
docker system prune -a --volumes

# تحديث الصور
docker-compose pull
docker-compose up -d

# فحص السجلات للأخطاء
grep ERROR docker-compose.logs

# تحقق من النسخ الاحتياطية
ls -lh /backups/
```

---

## 🔟 الدعم والمساعدة

### المشاكل الشائعة

**المشكلة:** ارتفاع استهلاك الذاكرة
```bash
# الحل: قلل Celery Concurrency
docker-compose exec worker celery -A tasks inspect active
# أو قلل pool_size في database.py
```

**المشكلة:** بطء في استجابة API
```bash
# تحقق من السجلات
docker-compose logs backend

# تحقق من اتصالات قاعدة البيانات
docker-compose exec postgres_db ps aux | grep postgres

# زيادة عدد Gunicorn Workers
```

**المشكلة:** فشل المهام في الطابور
```bash
# عرض مهام Celery
docker-compose exec worker celery -A tasks inspect active

# تنظيف الطابور
docker-compose exec worker celery -A tasks purge
```

---

**نسخة الدليل:** 1.0  
**آخر تحديث:** 2026-08-04  
**الحالة:** ✅ **PRODUCTION READY**
