import React, { useState, useEffect, useMemo, useRef } from 'react';
import './ContentHub.css';
import AnalysisDetails from './AnalysisDetails';
import SearchFilterBar from './SearchFilterBar';

const ContentHub = () => {
  // ============= State Management =============
  const [articles, setArticles] = useState([]);
  const [urlInput, setUrlInput] = useState('');
  const [statusMessage, setStatusMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [stats, setStats] = useState(null);
  const [currentPage, setCurrentPage] = useState(0);
  const [totalArticles, setTotalArticles] = useState(0);
  const [analysesByUrl, setAnalysesByUrl] = useState({});

  // ============= Search & Filter State =============
  const [searchQuery, setSearchQuery] = useState('');
  const [filterMode, setFilterMode] = useState('all');
  const [searchResults, setSearchResults] = useState(null); // null = لا توجد نتائج Elasticsearch بعد لهذا الاستعلام
  const [isSearching, setIsSearching] = useState(false);
  const [searchError, setSearchError] = useState('');
  const searchQueryRef = useRef('');

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

  // ============= Fetch Related Articles Analyses =============
  const fetchAnalyses = async () => {
    try {
      const response = await fetch('/api/content/latest-analyses?limit=100');
      if (response.ok) {
        const data = await response.json();
        const map = {};
        data.forEach((analysis) => {
          if (analysis.original_url) {
            map[analysis.original_url] = analysis;
          }
        });
        setAnalysesByUrl(map);
      }
    } catch (error) {
      console.error("خطأ في جلب المقالات المرتبطة:", error);
    }
  };

  // ============= Initial Load =============
  useEffect(() => {
    fetchArticles(0);
    fetchStatistics();
    fetchAnalyses();
  }, []);

  // ============= Elasticsearch Instant Search (debounced) =============
  useEffect(() => {
    searchQueryRef.current = searchQuery;
    const trimmed = searchQuery.trim();

    if (!trimmed) {
      setSearchResults(null);
      setIsSearching(false);
      setSearchError('');
      return;
    }

    setIsSearching(true);
    setSearchError('');

    const handle = setTimeout(() => {
      performSearch(trimmed);
    }, 400);

    return () => clearTimeout(handle);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchQuery]);

  const performSearch = async (query) => {
    try {
      const response = await fetch('/api/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query, limit: 20 }),
      });
      const data = await response.json();

      if (response.ok && data.task_id) {
        pollSearchStatus(data.task_id, query);
      } else if (searchQueryRef.current.trim() === query) {
        setIsSearching(false);
        setSearchError(data.detail || 'تعذر تنفيذ البحث');
      }
    } catch (error) {
      console.error("خطأ في البحث الفوري:", error);
      if (searchQueryRef.current.trim() === query) {
        setIsSearching(false);
        setSearchError('حدث خطأ في الاتصال بمحرك البحث');
      }
    }
  };

  const pollSearchStatus = async (taskId, query, attempt = 0) => {
    // إذا تغيّر الاستعلام أثناء الانتظار، توقف عن المتابعة
    if (searchQueryRef.current.trim() !== query) return;

    const maxAttempts = 15;
    if (attempt > maxAttempts) {
      setIsSearching(false);
      setSearchError('انتهت مهلة البحث، حاول مجدداً');
      return;
    }

    try {
      const response = await fetch(`/api/status/${taskId}`);
      const data = await response.json();

      if (searchQueryRef.current.trim() !== query) return;

      if (data.status === 'SUCCESS') {
        const result = data.result || {};
        if (result.status === 'success') {
          setSearchResults(result.results || []);
          setIsSearching(false);
          setSearchError('');
        } else {
          setIsSearching(false);
          setSearchError(result.error || 'تعذر إتمام البحث');
        }
      } else if (data.status === 'FAILURE') {
        setIsSearching(false);
        setSearchError('فشل تنفيذ البحث');
      } else {
        setTimeout(() => pollSearchStatus(taskId, query, attempt + 1), 1000);
      }
    } catch (error) {
      console.error("خطأ أثناء متابعة نتائج البحث:", error);
      if (searchQueryRef.current.trim() === query) {
        setIsSearching(false);
        setSearchError('حدث خطأ أثناء متابعة نتائج البحث');
      }
    }
  };

  const handleClearSearch = () => {
    setSearchQuery('');
    setSearchResults(null);
    setIsSearching(false);
    setSearchError('');
  };

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
        await fetchAnalyses(); // تحديث المقالات المرتبطة
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
        if (searchQueryRef.current.trim()) {
          performSearch(searchQueryRef.current.trim());
        }
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

  // ============= Search & Filter Derivation =============
  const isSearchActive = searchQuery.trim().length > 0;

  // فلترة فورية للمقالات المحمّلة حالياً (بدون انتظار الخادم)
  const localSearchMatches = useMemo(() => {
    const trimmed = searchQuery.trim().toLowerCase();
    if (!trimmed) return articles;
    return articles.filter((article) => {
      const analysis = analysesByUrl[article.url];
      const haystack = [
        article.title,
        article.content_preview,
        analysis?.summary,
      ]
        .filter(Boolean)
        .join(' ')
        .toLowerCase();
      return haystack.includes(trimmed);
    });
  }, [articles, searchQuery, analysesByUrl]);

  // تحويل نتائج Elasticsearch إلى نفس شكل بيانات المقال المستخدم في البطاقات
  const searchResultArticles = useMemo(() => {
    if (!searchResults) return null;
    return searchResults.map((result) => ({
      id: result.article_id,
      url: result.url,
      title: result.title,
      content_preview: result.content_preview,
      created_at: result.created_at,
      _searchScore: result.score,
    }));
  }, [searchResults]);

  const baseArticles = isSearchActive
    ? (searchResultArticles !== null ? searchResultArticles : localSearchMatches)
    : articles;

  const displayedArticles = useMemo(() => {
    return baseArticles.filter((article) => {
      if (filterMode === 'all') return true;
      const hasAnalysis = Boolean(analysesByUrl[article.url]);
      return filterMode === 'analyzed' ? hasAnalysis : !hasAnalysis;
    });
  }, [baseArticles, filterMode, analysesByUrl]);

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
              onClick={() => {
                fetchArticles(currentPage);
                fetchAnalyses();
              }}
              className="refresh-button"
              title="تحديث القائمة"
            >
              🔄
            </button>
          </div>

          {/* شريط البحث الفوري والفلترة */}
          <SearchFilterBar
            searchQuery={searchQuery}
            onSearchQueryChange={setSearchQuery}
            filterMode={filterMode}
            onFilterModeChange={setFilterMode}
            resultsCount={displayedArticles.length}
            isSearching={isSearching}
            searchError={searchError}
            isSearchActive={isSearchActive}
            onClearSearch={handleClearSearch}
          />

          {/* Articles List */}
          <div className="articles-list">
            {displayedArticles.length > 0 ? (
              displayedArticles.map((article) => {
                const analysis = analysesByUrl[article.url];
                return (
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

                    {typeof article._searchScore === 'number' && (
                      <div className="article-meta">
                        <span className="search-score-badge">
                          🎯 درجة الصلة بالبحث: {article._searchScore}
                        </span>
                      </div>
                    )}

                    <AnalysisDetails analysis={analysis} />
                  </article>
                );
              })
            ) : (
              <div className="no-articles">
                {isSearchActive ? (
                  <p>لا توجد نتائج مطابقة لبحثك</p>
                ) : (
                  <>
                    <p>لا توجد مقالات محفوظة حتى الآن</p>
                    <p style={{ fontSize: '14px', color: '#888' }}>
                      ابدأ برمز رابط لسحب أول مقال لك
                    </p>
                  </>
                )}
              </div>
            )}
          </div>

          {/* Pagination Controls */}
          {!isSearchActive && totalPages > 1 && (
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
