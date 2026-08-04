import os
import requests
from bs4 import BeautifulSoup
from celery import Celery
from elasticsearch import Elasticsearch
from datetime import datetime
import logging

from database import SessionLocal, Article, SearchLog

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============= Initialize Services =============

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
ELASTICSEARCH_URL = os.getenv("ELASTICSEARCH_URL", "http://elasticsearch:9200")

# Initialize Celery
app = Celery('content_worker', broker=REDIS_URL, backend=REDIS_URL)

# Initialize Elasticsearch
try:
    es = Elasticsearch([ELASTICSEARCH_URL])
    # Test connection
    if es.ping():
        logger.info("✅ Connected to Elasticsearch successfully")
    else:
        logger.warning("⚠️ Elasticsearch connection test failed")
except Exception as e:
    logger.error(f"❌ Failed to connect to Elasticsearch: {str(e)}")
    es = None

# ============= Celery Tasks =============

@app.task(name="scrape_article")
def scrape_article(url, article_id=None):
    """
    سحب محتوى المقال من الرابط وحفظه في PostgreSQL و Elasticsearch
    """
    db = SessionLocal()
    
    try:
        # إضافة User-Agent
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        logger.info(f"🌐 جاري جلب الرابط: {url}")
        
        # جلب محتوى الصفحة
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        # تحليل HTML
        soup = BeautifulSoup(response.content, 'html.parser')

        # استخراج العنوان
        h1_tag = soup.find('h1')
        title = h1_tag.get_text(strip=True) if h1_tag else (
            soup.title.string if soup.title else "بدون عنوان"
        )

        # استخراج المحتوى
        paragraphs = soup.find_all('p')
        cleaned_text = " ".join([
            p.get_text(strip=True) for p in paragraphs 
            if len(p.get_text(strip=True)) > 30
        ])

        if not cleaned_text:
            cleaned_text = soup.get_text(strip=True)[:500]

        logger.info(f"✅ تم سحب المقال: {title}")

        # ============= Step 1: Save to PostgreSQL =============

        existing_article = db.query(Article).filter(Article.url == url).first()
        
        if existing_article:
            logger.info(f"📝 المقال موجود مسبقاً برقم: {existing_article.id}")
            saved_article_id = existing_article.id
        else:
            # Create preview
            content_preview = cleaned_text[:200] if len(cleaned_text) > 200 else cleaned_text
            
            new_article = Article(
                url=url,
                title=title,
                content=cleaned_text,
                content_preview=content_preview,
                content_length=len(cleaned_text)
            )
            db.add(new_article)
            db.commit()
            db.refresh(new_article)
            saved_article_id = new_article.id
            logger.info(f"💾 تم حفظ المقال في PostgreSQL برقم: {saved_article_id}")

        # ============= Step 2: Index to Elasticsearch =============

        if es:
            try:
                # تجهيز المستند للفهرسة
                document = {
                    "article_id": saved_article_id,
                    "title": title,
                    "content": cleaned_text,
                    "content_preview": cleaned_text[:200],
                    "url": url,
                    "created_at": datetime.utcnow().isoformat()
                }

                # فهرسة المقال في Elasticsearch
                es.index(
                    index="articles",
                    id=str(saved_article_id),
                    document=document
                )
                logger.info(f"🔍 تمت فهرسة المقال في Elasticsearch برقم: {saved_article_id}")
                
            except Exception as es_error:
                logger.warning(f"⚠️ فشل حفظ في Elasticsearch: {str(es_error)}")

        # ============= Return Result =============

        return {
            "status": "success",
            "article_id": saved_article_id,
            "title": title,
            "url": url,
            "content_length": len(cleaned_text),
            "content_preview": cleaned_text[:200]
        }

    except requests.exceptions.Timeout:
        error_msg = f"انتهت المهلة الزمنية عند محاولة الوصول إلى {url}"
        logger.error(f"❌ {error_msg}")
        return {"status": "failed", "error": error_msg}

    except requests.exceptions.ConnectionError:
        error_msg = f"خطأ في الاتصال بـ {url}"
        logger.error(f"❌ {error_msg}")
        return {"status": "failed", "error": error_msg}

    except requests.exceptions.HTTPError as e:
        error_msg = f"خطأ HTTP {e.response.status_code}: {url}"
        logger.error(f"❌ {error_msg}")
        return {"status": "failed", "error": error_msg}

    except Exception as e:
        db.rollback()
        error_msg = f"خطأ: {str(e)}"
        logger.error(f"❌ {error_msg}")
        return {"status": "failed", "error": error_msg}

    finally:
        db.close()


@app.task(name="search_articles")
def search_articles(query, limit=10):
    """
    البحث عن مقالات باستخدام Elasticsearch
    يوفر بحث نصي سريع وقوي بفضل Elasticsearch
    """
    db = SessionLocal()
    
    try:
        if not es:
            logger.warning("⚠️ Elasticsearch غير متصل")
            return {
                "status": "failed",
                "error": "خادم البحث غير متوفر حالياً"
            }

        # بناء استعلام Elasticsearch
        search_body = {
            "query": {
                "multi_match": {
                    "query": query,
                    "fields": [
                        "title^3",      # البحث في العنوان بأولوية أعلى
                        "content^1",    # البحث في المحتوى
                        "content_preview"
                    ],
                    "fuzziness": "AUTO"  # السماح بأخطاء الكتابة
                }
            },
            "size": min(limit, 100),  # الحد الأقصى 100 نتيجة
            "highlight": {
                "fields": {
                    "content": {"number_of_fragments": 1}
                }
            }
        }

        logger.info(f"🔍 جاري البحث عن: {query}")

        # تنفيذ البحث
        results = es.search(index="articles", body=search_body)

        # معالجة النتائج
        articles = []
        for hit in results['hits']['hits']:
            article_data = hit['_source']
            articles.append({
                "score": round(hit['_score'], 2),
                "article_id": article_data.get('article_id'),
                "title": article_data.get('title'),
                "content_preview": article_data.get('content_preview'),
                "url": article_data.get('url'),
                "created_at": article_data.get('created_at')
            })

        # تسجيل البحث في قاعدة البيانات
        try:
            search_log = SearchLog(
                query=query,
                results_count=len(articles)
            )
            db.add(search_log)
            db.commit()
            logger.info(f"📊 تم تسجيل البحث: {query} ({len(articles)} نتائج)")
        except Exception as log_error:
            logger.warning(f"⚠️ فشل تسجيل البحث: {str(log_error)}")
            db.rollback()

        return {
            "status": "success",
            "query": query,
            "total_results": len(articles),
            "results": articles
        }

    except Exception as e:
        error_msg = f"خطأ في البحث: {str(e)}"
        logger.error(f"❌ {error_msg}")
        return {
            "status": "failed",
            "error": error_msg
        }

    finally:
        db.close()


@app.task(name="bulk_index_articles")
def bulk_index_articles():
    """
    مهمة لفهرسة جميع المقالات الموجودة في PostgreSQL إلى Elasticsearch
    مفيدة عند الحاجة لإعادة بناء الفهرس
    """
    db = SessionLocal()
    
    try:
        if not es:
            logger.warning("⚠️ Elasticsearch غير متصل")
            return {"status": "failed", "error": "Elasticsearch غير متاح"}

        # جلب جميع المقالات
        articles = db.query(Article).all()
        logger.info(f"📑 جاري فهرسة {len(articles)} مقالات...")

        indexed_count = 0
        failed_count = 0

        for article in articles:
            try:
                document = {
                    "article_id": article.id,
                    "title": article.title,
                    "content": article.content,
                    "content_preview": article.content_preview,
                    "url": article.url,
                    "created_at": article.created_at.isoformat()
                }

                es.index(
                    index="articles",
                    id=str(article.id),
                    document=document
                )
                indexed_count += 1

            except Exception as article_error:
                logger.error(f"❌ فشل فهرسة المقال {article.id}: {str(article_error)}")
                failed_count += 1

        logger.info(f"✅ تمت الفهرسة: {indexed_count} نجح، {failed_count} فشل")

        return {
            "status": "success",
            "indexed_count": indexed_count,
            "failed_count": failed_count,
            "total": len(articles)
        }

    except Exception as e:
        logger.error(f"❌ خطأ في الفهرسة الجماعية: {str(e)}")
        return {"status": "failed", "error": str(e)}

    finally:
        db.close()


@app.task(name="clear_search_index")
def clear_search_index():
    """
    حذف فهرس Elasticsearch بالكامل (استخدم بحذر!)
    """
    try:
        if not es:
            return {"status": "failed", "error": "Elasticsearch غير متاح"}

        es.indices.delete(index="articles", ignore_unavailable=True)
        logger.info("🗑️ تم حذف فهرس البحث بالكامل")

        return {"status": "success", "message": "تم حذف الفهرس"}

    except Exception as e:
        logger.error(f"❌ خطأ في حذف الفهرس: {str(e)}")
        return {"status": "failed", "error": str(e)}


@app.task(name="get_search_stats")
def get_search_stats():
    """الحصول على إحصائيات فهرس البحث"""
    try:
        if not es:
            return {"status": "failed", "error": "Elasticsearch غير متاح"}

        # عدد المستندات في الفهرس
        count = es.count(index="articles")
        
        # معلومات الفهرس
        indices_info = es.indices.get(index="articles")

        return {
            "status": "success",
            "document_count": count['count'],
            "index_name": "articles",
            "indices_info": indices_info
        }

    except Exception as e:
        logger.error(f"❌ خطأ في الحصول على الإحصائيات: {str(e)}")
        return {"status": "failed", "error": str(e)}


# ============= Error Handlers =============

@app.task(bind=True, max_retries=3)
def retry_failed_task(self, task_name, *args, **kwargs):
    """
    مهمة للإعادة عند فشل عملية
    """
    try:
        logger.info(f"🔄 إعادة محاولة المهمة: {task_name}")
        # تنفيذ المهمة الأصلية
        task = app.tasks.get(task_name)
        if task:
            return task.apply_async(args=args, kwargs=kwargs)
    except Exception as exc:
        logger.error(f"❌ فشلت إعادة المحاولة: {str(exc)}")
        raise self.retry(exc=exc, countdown=60)
