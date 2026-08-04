from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, HttpUrl
from sqlalchemy.orm import Session
from celery.result import AsyncResult
from typing import Optional
import logging

from database import get_db
from tasks import analyze_and_fetch_related_task

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/content", tags=["Content Analysis"])

# ============= Pydantic Models =============

class ArticleAnalyzeRequest(BaseModel):
    """طلب تحليل مقال"""
    url: str
    include_summary: bool = True
    max_related_articles: int = 10

class RelatedArticleResponse(BaseModel):
    """مقال مرتبط"""
    title: str
    source_site: str
    url: str
    match_score: float
    description: Optional[str] = None

class AnalysisResultResponse(BaseModel):
    """نتيجة التحليل"""
    original_url: str
    title: str
    summary: Optional[str] = None
    keywords: list
    related_articles: list
    analysis_date: str
    
    class Config:
        from_attributes = True

# ============= Analysis Endpoints =============

@router.post("/analyze")
async def analyze_article_endpoint(
    payload: ArticleAnalyzeRequest,
    db: Session = Depends(get_db)
):
    """
    تحليل مقال وجلب 10 مقالات مرتبطة من مصادر مختلفة
    
    Request:
    ```json
    {
        "url": "https://example.com/article",
        "include_summary": true,
        "max_related_articles": 10
    }
    ```
    
    Response:
    ```json
    {
        "status": "processing",
        "task_id": "task-id-123",
        "message": "جاري تحليل المقال والبحث عن مقالات مرتبطة..."
    }
    ```
    """
    try:
        if not payload.url.startswith("http"):
            raise HTTPException(
                status_code=400,
                detail="الرابط يجب أن يبدأ بـ http أو https"
            )
        
        # إرسال المهمة للـ Worker
        task = analyze_and_fetch_related_task.delay(
            str(payload.url),
            payload.include_summary,
            payload.max_related_articles
        )
        
        logger.info(f"Analysis task created: {task.id} for URL: {payload.url}")
        
        return {
            "status": "processing",
            "task_id": task.id,
            "message": "تم بدء عملية التحليل والبحث عن مقالات مرتبطة في الخلفية بنجاح.",
            "check_status_url": f"/api/status/{task.id}"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in analyze_article: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"خطأ في بدء التحليل: {str(e)}"
        )

@router.get("/analysis-status/{task_id}")
async def get_analysis_status(task_id: str):
    """
    الحصول على حالة عملية التحليل والنتائج
    """
    try:
        task_result = AsyncResult(task_id)
        
        response = {
            "task_id": task_id,
            "status": task_result.state,
            "result": None
        }
        
        if task_result.state == "PENDING":
            response["message"] = "جاري معالجة الطلب..."
        elif task_result.state == "STARTED":
            response["message"] = "جاري تحليل المقال..."
        elif task_result.state == "SUCCESS":
            response["result"] = task_result.result
            response["message"] = "اكتمل التحليل بنجاح"
        elif task_result.state == "FAILURE":
            response["error"] = str(task_result.info)
            response["message"] = "فشل التحليل"
        
        return response
    
    except Exception as e:
        logger.error(f"Error getting analysis status: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"خطأ في جلب الحالة: {str(e)}"
        )

@router.get("/latest-analyses", response_model=list)
async def get_latest_analyses(limit: int = 10, db: Session = Depends(get_db)):
    """
    الحصول على آخر التحليلات
    """
    try:
        from database import ArticleAnalysis
        
        analyses = db.query(ArticleAnalysis)\
            .order_by(ArticleAnalysis.created_at.desc())\
            .limit(limit)\
            .all()
        
        return analyses
    
    except Exception as e:
        logger.error(f"Error fetching latest analyses: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"خطأ في جلب التحليلات: {str(e)}"
        )
