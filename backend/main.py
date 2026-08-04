from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from celery import Celery
from celery.result import AsyncResult
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List, Optional
import os
import logging

# استيراد Prometheus
from prometheus_fastapi_instrumentator import Instrumentator

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# استيراد إعدادات قاعدة البيانات
from database import SessionLocal, Article, SearchLog, get_db

# 1. تهيئة تطبيق FastAPI
app = FastAPI(
    title="Smart Content Hub API",
    description="API لسحب وتحليل والبحث عن المقالات",
    version="1.0.0"
)

# تفعيل CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# تفعيل مراقبة Prometheus
Instrumentator().instrument(app).expose(app, endpoint="/metrics")

# 2. إعداد الاتصال بـ Celery و Redis
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
celery_app = Celery('content_worker', broker=REDIS_URL, backend=REDIS_URL)

logger.info(f"Celery initialized with Redis: {REDIS_URL}")

# ============= Pydantic Models (Schemas) =============

class ArticleRequest(BaseModel):
    url: str
    article_id: Optional[str] = None

class SearchRequest(BaseModel):
    query: str
    limit: int = 10

class ArticleResponse(BaseModel):
    id: int
    url: str
    title: str
    content: str
    content_preview: Optional[str] = None
    content_length: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}

class ArticleListItem(BaseModel):
    id: int
    url: str
    title: str
    content_preview: Optional[str] = None
    content_length: Optional[int] = None
    created_at: datetime
    model_config = {"from_attributes": True}

class SearchLogResponse(BaseModel):
    id: int
    query: str
    results_count: int
    created_at: datetime
    model_config = {"from_attributes": True}

class PaginatedResponse(BaseModel):
    items: List[ArticleListItem]
    total: int
    skip: int
    limit: int
    has_more: bool

# ============= Health Check =============

@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "Smart Content Hub API",
        "version": "1.0.0"
    }

@app.get("/metrics")
async def prometheus_metrics():
    """Prometheus metrics endpoint"""
    pass  # Instrumentator handles this automatically

# ============= Root Endpoint =============

@app.get("/api/")
async def root():
    return {
        "name": "Smart Content Hub API",
        "version": "1.0.0",
        "description": "منصة ذكية لسحب وتحليل والبحث عن المقالات",
        "endpoints": {
            "health": {"method": "GET", "path": "/api/health"},
            "metrics": {"method": "GET", "path": "/metrics"},
            "articles": {"method": "GET", "path": "/api/articles"},
            "analyze": {"method": "POST", "path": "/api/analyze"},
            "status": {"method": "GET", "path": "/api/status/{task_id}"},
            "search": {"method": "POST", "path": "/api/search"},
            "stats": {"method": "GET", "path": "/api/stats"},
            "docs": {"path": "/docs"}
        }
    }

# ============= Article Endpoints =============

@app.get("/api/articles", response_model=PaginatedResponse)
async def get_all_articles(
    skip: int = 0,
    limit: int = 10,
    db: Session = Depends(get_db)
):
    if skip < 0:
        raise HTTPException(status_code=400, detail="skip يجب أن يكون أكبر من أو يساوي 0")
    if limit < 1 or limit > 100:
        raise HTTPException(status_code=400, detail="limit يجب أن يكون بين 1 و 100")
    
    try:
        total = db.query(Article).count()
        articles = db.query(Article).order_by(Article.created_at.desc()).offset(skip).limit(limit).all()
        
        logger.info(f"Retrieved {len(articles)} articles, total: {total}")
        
        return PaginatedResponse(
            items=articles,
            total=total,
            skip=skip,
            limit=limit,
            has_more=(skip + limit) < total
        )
    except Exception as e:
        logger.error(f"Error retrieving articles: {str(e)}")
        raise HTTPException(status_code=500, detail=f"خطأ في جلب المقالات: {str(e)}")

@app.get("/api/articles/{article_id}", response_model=ArticleResponse)
async def get_article(article_id: int, db: Session = Depends(get_db)):
    try:
        article = db.query(Article).filter(Article.id == article_id).first()
        if not article:
            raise HTTPException(status_code=404, detail="المقال غير موجود")
        return article
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving article {article_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"خطأ في جلب المقال: {str(e)}")

@app.delete("/api/articles/{article_id}")
async def delete_article(article_id: int, db: Session = Depends(get_db)):
    try:
        article = db.query(Article).filter(Article.id == article_id).first()
        if not article:
            raise HTTPException(status_code=404, detail="المقال غير موجود")
        db.delete(article)
        db.commit()
        logger.info(f"Deleted article: {article_id}")
        return {"message": "تم حذف المقال بنجاح", "article_id": article_id}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting article {article_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"خطأ في حذف المقال: {str(e)}")

# ============= Article Analysis Endpoints =============

@app.post("/api/analyze")
async def analyze_article(request: ArticleRequest):
    if not request.url.startswith("http"):
        raise HTTPException(status_code=400, detail="الرابط غير صالح.")
    
    try:
        task = celery_app.send_task("scrape_article", args=[request.url, request.article_id])
        logger.info(f"Scrape task created: {task.id} for URL: {request.url}")
        return {
            "status": "accepted",
            "message": "تم استلام الرابط بنجاح، جاري سحب وتحليل المقال.",
            "task_id": task.id,
            "check_status_url": f"/api/status/{task.id}"
        }
    except Exception as e:
        logger.error(f"Error creating scrape task: {str(e)}")
        raise HTTPException(status_code=500, detail=f"خطأ: {str(e)}")

@app.get("/api/status/{task_id}")
async def get_task_status(task_id: str):
    try:
        task_result = AsyncResult(task_id, app=celery_app)
        
        response = {
            "task_id": task_id,
            "status": task_result.state,
            "result": None,
            "message": ""
        }

        if task_result.state == 'PENDING':
            response["message"] = "المهمة قيد الانتظار"
        elif task_result.state == 'STARTED':
            response["message"] = "المهمة جاري تنفيذها"
        elif task_result.state == 'SUCCESS':
            response["result"] = task_result.result
            response["message"] = "اكتملت المهمة بنجاح"
        elif task_result.state == 'FAILURE':
            response["error"] = str(task_result.info)
            response["message"] = "فشلت المهمة"
        
        return response
    except Exception as e:
        logger.error(f"Error checking task status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"خطأ: {str(e)}")

# ============= Search Endpoints =============

@app.post("/api/search")
async def search_articles(request: SearchRequest, db: Session = Depends(get_db)):
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="يجب إدخال كلمة بحث")
    if request.limit < 1 or request.limit > 100:
        raise HTTPException(status_code=400, detail="limit يجب أن يكون بين 1 و 100")
    
    try:
        task = celery_app.send_task("search_articles", args=[request.query, request.limit])
        search_log = SearchLog(query=request.query, results_count=0)
        db.add(search_log)
        db.commit()
        logger.info(f"Search task created: {task.id} for query: {request.query}")
        return {
            "status": "processing",
            "message": f"جاري البحث عن: {request.query}",
            "task_id": task.id,
            "check_status_url": f"/api/status/{task.id}"
        }
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating search task: {str(e)}")
        raise HTTPException(status_code=500, detail=f"خطأ في البحث: {str(e)}")

@app.get("/api/search-logs", response_model=List[SearchLogResponse])
async def get_search_logs(limit: int = 10, db: Session = Depends(get_db)):
    try:
        logs = db.query(SearchLog).order_by(SearchLog.created_at.desc()).limit(limit).all()
        return logs
    except Exception as e:
        logger.error(f"Error retrieving search logs: {str(e)}")
        raise HTTPException(status_code=500, detail=f"خطأ: {str(e)}")

# ============= Statistics Endpoints =============

@app.get("/api/stats")
async def get_statistics(db: Session = Depends(get_db)):
    try:
        total_articles = db.query(Article).count()
        total_searches = db.query(SearchLog).count()
        recent_articles = db.query(Article).order_by(Article.created_at.desc()).limit(5).all()
        popular_searches = db.query(SearchLog).order_by(SearchLog.created_at.desc()).limit(5).all()
        
        return {
            "total_articles": total_articles,
            "total_searches": total_searches,
            "recent_articles": recent_articles,
            "popular_searches": popular_searches
        }
    except Exception as e:
        logger.error(f"Error retrieving statistics: {str(e)}")
        raise HTTPException(status_code=500, detail=f"خطأ: {str(e)}")

# ============= Error Handlers =============

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {str(exc)}")
    return {"error": str(exc), "status": "error"}

@app.get("/")
async def redirect_to_api():
    return {"message": "Smart Content Hub - استخدم /api/ أو /docs"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("BACKEND_PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
