import React from 'react';
import RelatedArticlesList from './RelatedArticlesList';

// الكلمات المفتاحية مخزنة كمصفوفة JSON نصية، مع احتياط للتقسيم بفاصلة إن لم تكن كذلك
const parseKeywords = (rawKeywords) => {
  if (!rawKeywords) return [];
  if (Array.isArray(rawKeywords)) return rawKeywords;
  try {
    const parsed = JSON.parse(rawKeywords);
    if (Array.isArray(parsed)) return parsed;
  } catch (e) {
    // ليست JSON صالح
  }
  return rawKeywords.split(',').map((kw) => kw.trim()).filter(Boolean);
};

const AnalysisDetails = ({ analysis }) => {
  if (!analysis) return null;

  const keywords = parseKeywords(analysis.keywords);

  return (
    <div className="analysis-details">
      {analysis.summary && (
        <div className="analysis-summary">
          <strong className="analysis-summary-label">الخلاصة الذكية</strong>
          <p>{analysis.summary}</p>
        </div>
      )}

      {keywords.length > 0 && (
        <div className="analysis-keywords">
          <span className="analysis-keywords-label">الكلمات المفتاحية:</span>
          {keywords.map((kw, i) => (
            <span key={i} className="keyword-chip">{kw}</span>
          ))}
        </div>
      )}

      <RelatedArticlesList
        relatedArticlesData={analysis.related_articles_data}
        relatedArticlesCount={analysis.related_articles_count}
      />
    </div>
  );
};

export default AnalysisDetails;
