# ✨ ميزة التحليل الذكي وجلب المقالات المرتبطة

## 📋 النظرة العامة

تمت إضافة **ميزة تحليل متقدمة** إلى منصة Smart Content Hub تتيح:
- ✅ تحليل ذكي للمقالات
- ✅ استخراج الكلمات المفتاحية تلقائياً
- ✅ جلب 10 مقالات مرتبطة من مصادر مختلفة
- ✅ حفظ النتائج في قاعدة البيانات و Elasticsearch
- ✅ معالجة في الخلفية (Background Task)

---

## 🔧 الملفات المضافة/المحدثة

### 1. Backend Router
```
✅ backend/routers/analysis.py (جديد)
   - POST /api/content/analyze
   - GET /api/content/analysis-status/{task_id}
   - GET /api/content/latest-analyses
```

### 2. Worker Tasks
```
✅ worker/analysis_tasks.py (جديد)
   - analyze_and_fetch_related_task (مهمة التحليل الرئيسية)
   - extract_keywords (استخراج الكلمات المفتاحية)
   - fetch_related_articles_from_web (جلب المقالات المرتبطة)
   - search_in_analysis_results (البحث في النتائج)
```

### 3. Database Model
```
✅ backend/database.py (محدث)
   - نموذج ArticleAnalysis الجديد
     - original_url
     - title
     - summary
     - keywords (JSON)
     - related_articles_data (JSON)
     - analysis_status
     - celery_task_id
```

---

## 🚀 طريقة الاستخدام

### 1. تحليل مقال جديد

```bash
curl -X POST http://localhost/api/content/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com/article",
    "include_summary": true,
    "max_related_articles": 10
  }'
```

**الاستجابة:**
```json
{
  "status": "processing",
  "task_id": "abc123def456",
  "message": "تم بدء عملية التحليل والبحث عن مقالات مرتبطة...",
  "check_status_url": "/api/status/abc123def456"
}
```

### 2. التحقق من حالة التحليل

```bash
curl http://localhost/api/status/{task_id}
```

**الاستجابة عند الاكتمال:**
```json
{
  "task_id": "abc123def456",
  "status": "SUCCESS",
  "result": {
    "status": "success",
    "analysis_id": 1,
    "original_url": "https://example.com/article",
    "title": "عنوان المقال",
    "summary": "ملخص المقال...",
    "keywords": ["keyword1", "keyword2", ...],
    "related_articles_count": 10,
    "related_articles": [
      {
        "title": "مقال مرتبط 1",
        "source_site": "techcrunch.com",
        "url": "https://techcrunch.com/...",
        "match_score": 0.95
      },
      ...
    ]
  }
}
```

### 3. جلب آخر التحليلات

```bash
curl http://localhost/api/content/latest-analyses?limit=10
```

---

## 📊 كيفية العمل

```
┌─────────────────────────────────────────────────────────┐
│ 1. المستخدم يرسل طلب تحليل                             │
│    POST /api/content/analyze                           │
└────────────────┬────────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────────┐
│ 2. Backend يستقبل الطلب ويرسله لـ Celery              │
│    (فوراً يعيد task_id للمستخدم)                      │
└────────────────┬────────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────────┐
│ 3. Worker يبدأ معالجة الطلب في الخلفية:              │
│    أ) جلب محتوى المقال                               │
│    ب) استخراج الكلمات المفتاحية                      │
│    ج) البحث عن 10 مقالات مرتبطة                      │
│    د) حفظ النتائج في قاعدة البيانات                 │
│    هـ) فهرسة في Elasticsearch                        │
└────────────────┬────────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────────┐
│ 4. النتائج جاهزة في قاعدة البيانات و Elasticsearch  │
│    المستخدم يستطيع جلبها بـ:                          │
│    GET /api/status/{task_id}                          │
└─────────────────────────────────────────────────────────┘
```

---

## 💾 قاعدة البيانات - الجدول الجديد

```sql
CREATE TABLE article_analyses (
    id SERIAL PRIMARY KEY,
    original_url VARCHAR(2048) UNIQUE NOT NULL,
    title VARCHAR(500) NOT NULL,
    summary TEXT,
    keywords TEXT,  -- JSON array
    related_articles_count INTEGER DEFAULT 0,
    related_articles_data TEXT,  -- JSON
    analysis_status VARCHAR(50) DEFAULT 'pending',
    celery_task_id VARCHAR(200),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_analyses_url ON article_analyses(original_url);
CREATE INDEX idx_analyses_created_at ON article_analyses(created_at);
CREATE INDEX idx_analyses_status ON article_analyses(analysis_status);
```

---

## 🔑 الكلمات المفتاحية - آلية الاستخراج

الخوارزمية الحالية:
1. تنظيف النص (lowercase, remove special chars)
2. تصفية Stop Words (كلمات عادية مثل "و", "أو", etc.)
3. حساب تكرار الكلمات
4. إرجاع أكثر 10 كلمات تكراراً

**يمكن تحسينها باستخدام:**
- NLP libraries (NLTK, spaCy)
- TF-IDF algorithm
- Machine Learning models
- Arabic language processing

---

## 🌐 مصادر جلب المقالات المرتبطة

المصادر الحالية (Mock Data):
- techcrunch.com
- medium.com
- dev.to
- reddit.com
- news.ycombinator.com
- wikipedia.org
- quora.com
- twitter.com
- linkedin.com
- github.com

**يمكن تحسينها باستخدام:**
- Google News API
- NewsAPI.org
- RSS Feeds
- Elasticsearch من قاعدة البيانات الخاصة
- Web scraping من مصادر محددة
- APIs خارجية

---

## 📈 Elasticsearch Indexing

```json
{
  "index": "article_analyses",
  "document": {
    "article_id": 1,
    "original_url": "https://example.com/article",
    "title": "عنوان المقال",
    "summary": "ملخص المقال",
    "keywords": ["keyword1", "keyword2"],
    "related_articles_count": 10,
    "analysis_date": "2026-08-05T...",
    "related_titles": ["عنوان 1", "عنوان 2", ...]
  }
}
```

**البحث في النتائج:**
```bash
POST /api/search
{
  "query": "اسم الموضوع",
  "limit": 10
}
```

---

## ⚙️ التعديلات المطلوبة في main.py

```python
# أضف هذا في أعلى main.py
from routers.analysis import router as analysis_router

# ثم أضف هذا بعد Instrumentator
if analysis_router:
    app.include_router(analysis_router)
```

---

## ✅ التحقق من التثبيت

```bash
# 1. تحقق من وجود المهام الجديدة
curl http://localhost/api/health

# 2. جرب التحليل
curl -X POST http://localhost/api/content/analyze \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}'

# 3. اعرض الحالة
curl http://localhost/api/content/latest-analyses
```

---

## 🎯 المميزات الإضافية المقترحة

- [ ] تحسين استخراج الكلمات المفتاحية بـ NLP
- [ ] API خارجية حقيقية لجلب المقالات
- [ ] التصنيف التلقائي للمقالات
- [ ] تحليل العاطفة (Sentiment Analysis)
- [ ] إنشاء ملخص تلقائي (Summarization)
- [ ] الترجمة التلقائية
- [ ] الكشف عن اللغة
- [ ] تجميع المقالات حسب الموضوع

---

**آخر تحديث:** 2026-08-05  
**الحالة:** ✅ **FEATURE COMPLETE**
