import os
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Index
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime

# جلب رابط الاتصال من متغيرات البيئة
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://content_admin:[REDACTED]@postgres_db:5432/smart_hub_db"
)

# إعداد محرك قاعدة البيانات
engine = create_engine(
    DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# ============= Database Models =============

class Article(Base):
    """جدول المقالات المسحوبة"""
    __tablename__ = "articles"

    id = Column(Integer, primary_key=True, index=True)
    url = Column(String(2048), unique=True, index=True, nullable=False)
    title = Column(String(500), nullable=False)
    content = Column(Text, nullable=False)
    content_preview = Column(String(500), nullable=True)
    content_length = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_articles_url', 'url'),
        Index('idx_articles_created_at', 'created_at'),
        Index('idx_articles_title', 'title'),
    )

    def __repr__(self):
        return f"<Article(id={self.id}, title='{self.title[:50]}...')>"


class SearchLog(Base):
    """جدول سجل البحث"""
    __tablename__ = "search_logs"

    id = Column(Integer, primary_key=True, index=True)
    query = Column(String(500), nullable=False, index=True)
    results_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    def __repr__(self):
        return f"<SearchLog(id={self.id}, query='{self.query}', results_count={self.results_count})>"


class ArticleAnalysis(Base):
    """جدول نتائج تحليل المقالات"""
    __tablename__ = "article_analyses"

    id = Column(Integer, primary_key=True, index=True)
    original_url = Column(String(2048), unique=True, index=True, nullable=False)
    title = Column(String(500), nullable=False)
    summary = Column(Text, nullable=True)
    keywords = Column(Text, nullable=True)  # JSON array stored as text
    related_articles_count = Column(Integer, default=0)
    related_articles_data = Column(Text, nullable=True)  # JSON stored as text
    analysis_status = Column(String(50), default="pending")  # pending, processing, completed, failed
    celery_task_id = Column(String(200), nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_analyses_url', 'original_url'),
        Index('idx_analyses_created_at', 'created_at'),
        Index('idx_analyses_status', 'analysis_status'),
    )

    def __repr__(self):
        return f"<ArticleAnalysis(id={self.id}, title='{self.title[:50]}...')>"


# ============= Database Initialization =============

def init_db():
    """إنشاء جميع الجداول في قاعدة البيانات"""
    try:
        Base.metadata.create_all(bind=engine)
    except Exception as e:
        print(f"Database initialization warning: {str(e)}")


init_db()


def get_db():
    """دالة للحصول على جلسة قاعدة البيانات"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
