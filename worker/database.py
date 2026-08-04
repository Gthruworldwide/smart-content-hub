import os
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Index
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime

# جلب رابط الاتصال من متغيرات البيئة
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://content_admin:secure_password_123@postgres_db:5432/smart_hub_db"
)

# إعداد محرك قاعدة البيانات
engine = create_engine(
    DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,  # التحقق من الاتصال قبل استخدامه
    echo=False  # set to True for SQL debugging
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
    
    # إنشاء فهارس لتسريع البحث
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


# ============= Database Initialization =============

def init_db():
    """إنشاء جميع الجداول في قاعدة البيانات"""
    try:
        Base.metadata.create_all(bind=engine)
        print("✅ تم إنشاء الجداول بنجاح")
    except Exception as e:
        print(f"❌ خطأ في إنشاء الجداول: {str(e)}")


# استدعاء init_db عند استيراد المودول
init_db()


def get_db():
    """دالة للحصول على جلسة قاعدة البيانات"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
