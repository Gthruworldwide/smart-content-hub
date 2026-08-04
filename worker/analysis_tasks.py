import os
import requests
from bs4 import BeautifulSoup
from celery import Celery
from elasticsearch import Elasticsearch
from datetime import datetime
import logging
import json
import re
from collections import Counter

from database import SessionLocal, ArticleAnalysis

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============= Initialize Services =============

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
ELASTICSEARCH_URL = os.getenv("ELASTICSEARCH_URL", "http://elasticsearch:9200")

app = Celery('content_worker', broker=REDIS_URL, backend=REDIS_URL)

try:
    es = Elasticsearch([ELASTICSEARCH_URL])
    if es.ping():
        logger.info("✅ Connected to Elasticsearch")
except Exception as e:
    logger.error(f"❌ Elasticsearch connection failed: {str(e)}")
    es = None

# ============= Analysis Task =============

@app.task(
    name="analyze_and_fetch_related_task",
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={'max_retries': 3},
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True
)
def analyze_and_fetch_related_task(self, article_url: str, include_summary: bool = True, max_related: int = 10):
    """
    مهمة متقدمة: تحليل المقال وجلب 10 مقالات مرتبطة من مصادر مختلفة
    """
    db = SessionLocal()
    
    try:
        logger.info(f"🔍 جاري تحليل المقال: {article_url}")
        
        # ============= Step 1: جلب محتوى المقال =============
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(article_url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # استخراج العنوان
        title = soup.find('h1')
        if title:
            title = title.get_text(strip=True)
        else:
            title = soup.title.string if soup.title else "بدون عنوان"
        
        logger.info(f"📄 العنوان: {title}")
        
        # ============= Step 2: استخراج المحتوى والكلمات المفتاحية =============
        paragraphs = soup.find_all('p')
        full_text = " ".join([p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 30])
        
        # استخراج ملخص
        summary = full_text[:300] + "..." if len(full_text) > 300 else full_text
        
        # استخراج الكلمات المفتاحية
        keywords = extract_keywords(full_text, max_keywords=10)
        logger.info(f"🔑 الكلمات المفتاحية: {keywords}")
        
        # ============= Step 3: البحث عن مقالات مرتبطة من مصادر مختلفة =============
        related_articles = fetch_related_articles_from_web(title, keywords, max_related)
        logger.info(f"🔗 تم جلب {len(related_articles)} مقالات مرتبطة")
        
        # ============= Step 4: حفظ النتائج في قاعدة البيانات =============
        analysis = ArticleAnalysis(
            original_url=article_url,
            title=title,
            summary=summary,
            keywords=json.dumps(keywords),
            related_articles_count=len(related_articles),
            related_articles_data=json.dumps(related_articles),
            analysis_status="completed",
            celery_task_id=self.request.id
        )
        
        db.add(analysis)
        db.commit()
        db.refresh(analysis)
        
        logger.info(f"✅ تم حفظ التحليل في قاعدة البيانات برقم: {analysis.id}")
        
        # ============= Step 5: فهرسة في Elasticsearch =============
        if es:
            try:
                es_document = {
                    "article_id": analysis.id,
                    "original_url": article_url,
                    "title": title,
                    "summary": summary,
                    "keywords": keywords,
                    "related_articles_count": len(related_articles),
                    "analysis_date": datetime.utcnow().isoformat(),
                    "related_titles": [a["title"] for a in related_articles]
                }
                
                es.index(index="article_analyses", id=str(analysis.id), document=es_document)
                logger.info(f"📊 تم فهرسة التحليل في Elasticsearch")
            except Exception as es_error:
                logger.warning(f"⚠️ فشل الفهرسة في Elasticsearch: {str(es_error)}")
        
        # ============= Return Result =============
        return {
            "status": "success",
            "analysis_id": analysis.id,
            "original_url": article_url,
            "title": title,
            "summary": summary,
            "keywords": keywords,
            "related_articles_count": len(related_articles),
            "related_articles": related_articles[:5]  # إرجاع أول 5 فقط للإجابة السريعة
        }
    
    except requests.exceptions.Timeout:
        error_msg = f"انتهت المهلة الزمنية عند الوصول إلى {article_url}"
        logger.error(f"❌ {error_msg}")
        return {"status": "failed", "error": error_msg}
    
    except requests.exceptions.ConnectionError:
        error_msg = f"خطأ في الاتصال بـ {article_url}"
        logger.error(f"❌ {error_msg}")
        return {"status": "failed", "error": error_msg}
    
    except Exception as e:
        db.rollback()
        error_msg = f"خطأ في التحليل: {str(e)}"
        logger.error(f"❌ {error_msg}")
        return {"status": "failed", "error": error_msg}
    
    finally:
        db.close()


# ============= Helper Functions =============

def extract_keywords(text: str, max_keywords: int = 10) -> list:
    """
    استخراج الكلمات المفتاحية من النص
    """
    # تنظيف النص
    text = text.lower()
    text = re.sub(r'[^\w\s]', ' ', text)
    
    # كلمات Stop Words في العربية والإنجليزية
    stop_words = {
        'و', 'أو', 'في', 'من', 'إلى', 'هو', 'هي', 'هم', 'هن',
        'an', 'the', 'and', 'or', 'in', 'of', 'to', 'is', 'are'
    }
    
    # استخراج الكلمات
    words = [w for w in text.split() if len(w) > 2 and w not in stop_words]
    
    # حساب تكرار الكلمات
    word_freq = Counter(words)
    
    # إرجاع أكثر الكلمات تكراراً
    return [word for word, _ in word_freq.most_common(max_keywords)]


def fetch_related_articles_from_web(main_title: str, keywords: list, max_articles: int = 10) -> list:
    """
    جلب مقالات مرتبطة من مصادر مختلفة
    
    يمكن تحسينها باستخدام:
    1. Google Search API
    2. News API
    3. RSS Feeds من مواقع مختلفة
    4. Elasticsearch من قاعدة البيانات الخاصة
    """
    
    related_articles = []
    
    # Mock data - في الإنتاج يتم استبدال هذا بـ API حقيقي
    mock_sources = [
        "techcrunch.com",
        "medium.com",
        "dev.to",
        "reddit.com",
        "news.ycombinator.com",
        "wikipedia.org",
        "quora.com",
        "twitter.com",
        "linkedin.com",
        "github.com"
    ]
    
    search_query = f"{main_title} {' '.join(keywords[:3])}"
    logger.info(f"🔎 البحث عن مقالات باستخدام: {search_query}")
    
    # محاكاة جلب المقالات من مصادر مختلفة
    for i, source in enumerate(mock_sources[:max_articles], 1):
        article = {
            "title": f"{main_title} - شرح من {source}",
            "source_site": source,
            "url": f"https://{source}/article-{i}",
            "match_score": 0.95 - (i * 0.02),  # درجة تطابق من 0.95 إلى 0.75
            "description": f"مقال مشابه يتناول نفس الموضوع على منصة {source}",
            "published_date": datetime.utcnow().isoformat()
        }
        related_articles.append(article)
    
    return related_articles


# ============= Search in Elasticsearch =============

@app.task(name="search_in_analysis_results")
def search_in_analysis_results(query: str, limit: int = 10):
    """
    البحث في نتائج التحليلات المحفوظة في Elasticsearch
    """
    if not es:
        return {"status": "failed", "error": "Elasticsearch غير متاح"}
    
    try:
        search_body = {
            "query": {
                "multi_match": {
                    "query": query,
                    "fields": ["title^2", "summary", "keywords"],
                    "fuzziness": "AUTO"
                }
            },
            "size": limit
        }
        
        results = es.search(index="article_analyses", body=search_body)
        
        articles = []
        for hit in results['hits']['hits']:
            articles.append({
                "score": hit['_score'],
                "data": hit['_source']
            })
        
        logger.info(f"✅ تم العثور على {len(articles)} نتائج تحليل")
        
        return {
            "status": "success",
            "query": query,
            "total_results": len(articles),
            "results": articles
        }
    
    except Exception as e:
        logger.error(f"❌ خطأ في البحث: {str(e)}")
        return {"status": "failed", "error": str(e)}
