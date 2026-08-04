import React, { useState, useEffect } from 'react';
import './ContentHub.css';

const ContentHub = () => {
  // ============= State Management =============
  const [articles, setArticles] = useState([]);
  const [urlInput, setUrlInput] = useState('');
  const [statusMessage, setStatusMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [stats, setStats] = useState(null);
  const [currentPage, setCurrentPage] = useState(0);
  const [totalArticles, setTotalArticles] = useState(0);

  const itemsPerPage = 10;

  // ============= Fetch Articles Function =============
  const fetchArticles = async (page = 0) => {
    try {
      const skip = page * itemsPerPage;
      const response = await fetch(`/api/articles?skip=${skip}&limit=${itemsPerPage}`);
      if (response.ok) {
        const data = await response.json();
        setArticles(data.items);
        setTotalArticles(data.total);
        setCurrentPage(page);
      }
    } catch (error) {
      console.error("خطأ في جلب المقالات:", error);
      setStatusMessage('❌ خطأ في جلب المقالات من الخادم');
    }
  };

  // ============= Fetch Statistics =============
  const fetchStatistics = async () => {
    try {
      const response = await fetch('/api/stats');
      if (response.ok) {
        const data = await response.json();
        setStats(data);
      }
    } catch (error) {
      console.error("خطأ في جلب الإحصائيات:", error);
    }
  };

  // ============= Initial Load =============
  useEffect(() => {
    fetchArticles(0);
    fetchStatistics();
  }, []);

  // ============= Polling Function for Task Status =============
  const pollTaskStatus = async (taskId, attempt = 0) => {
    const maxAttempts = 30; // محاولة لمدة دقيقة تقريباً (30 × 2 ثانية)

    if (attempt > maxAttempts) {
      setStatusMessage('⏱️ انتهت مهلة المعالجة. يرجى محاولة لاحقاً.');
      setIsLoading(false);
      return;
    }

    try {
      const response = await fetch(`/api/status/${taskId}`);
      const data = await response.json();

      console.log(`Poll attempt ${attempt}: Status = ${data.status}`);

      if (data.status === 'SUCCESS') {
        // المهمة اكتملت بنجاح
        setStatusMessage('✅ تم سحب المقال وحفظه بنجاح!');
        await fetchArticles(0); // تحديث قائمة المقالات
        await fetchStatistics(); // تحديث الإحصائيات
        setIsLoading(false);
      } else if (data.status === 'FAILURE') {
        // المهمة فشلت
        setStatusMessage(`❌ فشل سحب المقال: ${data.error || 'خطأ غير معروف'}`);
        setIsLoading(false);
      } else {
        // المهمة ما زالت قيد التنفيذ
        setStatusMessage(`⏳ جاري سحب وتحليل المقال... (محاولة ${attempt + 1}/${maxAttempts})`);
        // إعادة المحاولة بعد ثانيتين
        setTimeout(() => pollTaskStatus(taskId, attempt + 1), 2000);
      }
    } catch (error) {
      console.error("خطأ أثناء التحقق من حالة المهمة:", error);
      setStatusMessage('⚠️ حدث خطأ في الاتصال بالخادم أثناء متابعة المهمة.');
      setIsLoading(false);
    }
  };

  // ============= Handle Form Submission =============
  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!urlInput.trim()) {
      setStatusMessage('⚠️ يرجى إدخال رابط صحيح');
      return;
    }

    setIsLoading(true);
    setStatusMessage('🚀 جاري إرسال الرابط للخادم...');

    try {
      const response = await fetch('/api/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: urlInput.trim() })
      });

      const data = await response.json();

      if (response.ok) {
        setUrlInput(''); // تفريغ حقل الإدخال
        // بدء عملية الاستعلام الدوري
        pollTaskStatus(data.task_id);
      } else {
        setStatusMessage(`❌ خطأ: ${data.detail || 'فشل الإرسال'}`);
        setIsLoading(false);
      }
    } catch (error) {
      console.error("خطأ:", error);
      setStatusMessage('❌ حدث خطأ في الاتصال بالخادم');
      setIsLoading(false);
    }
  };

  // ============= Delete Article =============
  const handleDeleteArticle = async (articleId) => {
    if (!window.confirm('هل أنت متأكد من حذف هذا المقال؟')) return;

    try {
      const response = await fetch(`/api/articles/${articleId}`, {
        method: 'DELETE'
      });

      if (response.ok) {
        setStatusMessage('✅ تم حذف المقال بنجاح');
        await fetchArticles(currentPage);
        await fetchStatistics();
      } else {
        setStatusMessage('❌ فشل حذف المقال');
      }
    } catch (error) {
      console.error("خطأ في الحذف:", error);
      setStatusMessage('❌ حدث خطأ أثناء حذف المقال');
    }
  };

  // ============= Pagination Helpers =============
  const totalPages = Math.ceil(totalArticles / itemsPerPage);
  const canGoPrev = currentPage > 0;
  const canGoNext = currentPage < totalPages - 1;

  return (
    <div className="content-hub-container">
      {/* ============= Header ============= */}
      <header className="header">
        <div className="header-content">
          <h1>📰 Smart Content Hub</h1>
          <p>منصة ذكية لسحب وتحليل والبحث عن المقالات</p>
        </div>
      </header>

      <div className="main-container">
        {/* ============= Input Section ============= */}
        <section className="input-section">
          <h3>إضافة مقال جديد</h3>
          <form onSubmit={handleSubmit} className="input-form">
            <input
              type="url"
              placeholder="https://example.com/article"
              value={urlInput}
              onChange={(e) => setUrlInput(e.target.value)}
              disabled={isLoading}
              required
              className="url-input"
            />
            <button
              type="submit"
              disabled={isLoading}
              className="submit-button"
            >
              {isLoading ? 'جاري المعالجة...' : '🔍 سحب المقال'}
            </button>
          </form>

          {/* Status Message */}
          {statusMessage && (
            <div className={`status-message ${
              statusMessage.includes('✅') ? 'success' :
              statusMessage.includes('❌') ? 'error' :
              statusMessage.includes('⏳') ? 'loading' :
              'warning'
            }`}>
              {statusMessage}
            </div>
          )}
        </section>

        {/* ============= Statistics Section ============= */}
        {stats && (
          <section className="stats-section">
            <div className="stat-item">
              <span className="stat-label">📊 إجمالي المقالات</span>
              <span className="stat-value">{stats.total_articles}</span>
            </div>
            <div className="stat-item">
              <span className="stat-label">🔎 عمليات البحث</span>
              <span className="stat-value">{stats.total_searches}</span>
            </div>
          </section>
        )}

        {/* ============= Articles Section ============= */}
        <section className="articles-section">
          <div className="articles-header">
            <h3>المقالات المحفوظة ({totalArticles})</h3>
            <button
              onClick={() => fetchArticles(currentPage)}
              className="refresh-button"
              title="تحديث القائمة"
            >
              🔄
            </button>
          </div>

          {/* Articles List */}
          <div className="articles-list">
            {articles.length > 0 ? (
              articles.map((article) => (
                <article key={article.id} className="article-card">
                  <div className="article-header">
                    <h4 className="article-title">{article.title}</h4>
                    <button
                      onClick={() => handleDeleteArticle(article.id)}
                      className="delete-button"
                      title="حذف المقال"
                    >
                      🗑️
                    </button>
                  </div>

                  <p className="article-preview">
                    {article.content_preview || article.content?.substring(0, 150)}...
                  </p>

                  <div className="article-footer">
                    <a
                      href={article.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="original-link"
                    >
                      🔗 الرابط الأصلي
                    </a>
                    <span className="article-date">
                      📅 {new Date(article.created_at).toLocaleString('ar-EG')}
                    </span>
                  </div>

                  {article.content_length && (
                    <div className="article-meta">
                      📝 عدد الكلمات: {Math.ceil(article.content_length / 5)}
                    </div>
                  )}
                </article>
              ))
            ) : (
              <div className="no-articles">
                <p>لا توجد مقالات محفوظة حتى الآن</p>
                <p style={{ fontSize: '14px', color: '#888' }}>
                  ابدأ برمز رابط لسحب أول مقال لك
                </p>
              </div>
            )}
          </div>

          {/* Pagination Controls */}
          {totalPages > 1 && (
            <div className="pagination">
              <button
                onClick={() => fetchArticles(currentPage - 1)}
                disabled={!canGoPrev}
                className="pagination-button"
              >
                ← السابق
              </button>

              <span className="pagination-info">
                الصفحة {currentPage + 1} من {totalPages}
              </span>

              <button
                onClick={() => fetchArticles(currentPage + 1)}
                disabled={!canGoNext}
                className="pagination-button"
              >
                التالي →
              </button>
            </div>
          )}
        </section>
      </div>

      {/* ============= Footer ============= */}
      <footer className="footer">
        <p>© 2026 Smart Content Hub - جميع الحقوق محفوظة</p>
      </footer>
    </div>
  );
};

export default ContentHub;
