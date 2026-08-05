import React from 'react';

const SearchFilterBar = ({
  searchQuery,
  onSearchQueryChange,
  filterMode,
  onFilterModeChange,
  resultsCount,
  isSearching,
  searchError,
  isSearchActive,
  onClearSearch,
}) => {
  return (
    <div className="search-filter-bar">
      <div className="search-input-wrapper">
        <span className="search-icon" aria-hidden="true">🔍</span>
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => onSearchQueryChange(e.target.value)}
          placeholder="بحث فوري في المقالات المفهرسة..."
          className="search-input"
        />
        {isSearchActive && (
          <button
            type="button"
            onClick={onClearSearch}
            className="search-clear-button"
            title="مسح البحث"
          >
            ✕
          </button>
        )}
      </div>

      <div className="filter-wrapper">
        <label htmlFor="article-filter" className="filter-label">🗂️ الفلترة:</label>
        <select
          id="article-filter"
          value={filterMode}
          onChange={(e) => onFilterModeChange(e.target.value)}
          className="filter-select"
        >
          <option value="all">كل المقالات</option>
          <option value="analyzed">لديها تحليل ومقالات مرتبطة</option>
          <option value="not-analyzed">بدون تحليل</option>
        </select>
      </div>

      <div className="search-status">
        {isSearching && (
          <span className="search-loading">⏳ جاري البحث عبر Elasticsearch...</span>
        )}
        {!isSearching && searchError && (
          <span className="search-error">⚠️ {searchError}</span>
        )}
        {!isSearching && !searchError && (
          <span className="search-results-count">النتائج: {resultsCount} مقال</span>
        )}
      </div>
    </div>
  );
};

export default SearchFilterBar;
