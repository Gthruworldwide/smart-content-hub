import React, { useState } from 'react';

// يعرض قائمة قابلة للطي بالمقالات المرتبطة ونسب التطابق الخاصة بكل مقال
const RelatedArticlesList = ({ relatedArticlesData, relatedArticlesCount }) => {
  const [isExpanded, setIsExpanded] = useState(false);

  let relatedArticles = [];
  try {
    if (typeof relatedArticlesData === 'string') {
      relatedArticles = JSON.parse(relatedArticlesData);
    } else if (Array.isArray(relatedArticlesData)) {
      relatedArticles = relatedArticlesData;
    }
  } catch (e) {
    relatedArticles = [];
  }

  if (!Array.isArray(relatedArticles) || relatedArticles.length === 0) {
    return null;
  }

  const count = relatedArticlesCount || relatedArticles.length;

  return (
    <div className="related-articles">
      <button
        type="button"
        onClick={() => setIsExpanded((prev) => !prev)}
        className="related-articles-toggle"
      >
        <span>🔗 عرض {count} من المقالات المرتبطة ونسب التطابق</span>
        <span className="related-articles-chevron">{isExpanded ? '▲' : '▼'}</span>
      </button>

      {isExpanded && (
        <div className="related-articles-list">
          {relatedArticles.map((rel, index) => {
            const score = rel.match_score ?? rel.similarity_score;
            return (
              <div key={rel.url || rel.link || index} className="related-article-item">
                <div className="related-article-info">
                  <span className="related-article-index">#{index + 1}</span>
                  <a
                    href={rel.url || rel.link}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="related-article-link"
                    title={rel.title || rel.name}
                  >
                    {rel.title || rel.name}
                  </a>
                  {rel.source_site && (
                    <span className="related-article-source">({rel.source_site})</span>
                  )}
                </div>
                {typeof score === 'number' && (
                  <span className="related-article-score">
                    {Math.round(score * 100)}% تطابق
                  </span>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default RelatedArticlesList;
