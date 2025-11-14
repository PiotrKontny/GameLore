import React, { useEffect, useState } from "react";
import "./SearchResultsPage.css";

function SearchResultsPage() {
  const [results, setResults] = useState([]);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [loadingDetails, setLoadingDetails] = useState(false);

  useEffect(() => {
    async function loadData() {
      const res = await fetch("/app/results/?format=json", {
        headers: { "x-requested-with": "XMLHttpRequest" }
      });

      if (res.ok) {
        const data = await res.json();
        setResults(data.results || []);
        setQuery(data.query || "");
      }
      setLoading(false);
    }

    loadData();
  }, []);

  const openDetails = (url) => {
    setLoadingDetails(true);

    setTimeout(() => {
      window.location.href = `/app/details/?url=${encodeURIComponent(url)}`;
    }, 120);
  };

  return (
    <div className="results-container">

      {/* === HEADER (wrócił cały, poprawny!) === */}
      <div className="results-header">
        <h1>Search Results for "{query}"</h1>
        <p>Click any result to explore its story.</p>

        <a href="/app/search/" className="back-btn">
          Back to Search
        </a>
      </div>

      {/* === SPINNER POD NAGŁÓWKIEM === */}
      {(loading || loadingDetails) && (
        <div className="center-loader under-header">
          <div className="spinner"></div>
          <span>
            {loading ? "Loading results..." : "Loading game details..."}
          </span>
        </div>
      )}

      {/* === LISTA KAFELEK (NIGDY NIE ZNIKA PRZY KLIKNIĘCIU) === */}
      {loading ? null : results.length === 0 ? (
        <p className="no-results">No results found.</p>
      ) : (
        <div className="results-list">
          {results.map((r, idx) => (
            <div
              className="result-item"
              key={idx}
              onClick={() => openDetails(r.url)}
            >
              <div className="result-thumb">
                <img
                  src={`/media/results/result_${idx + 1}.png`}
                  onError={(e) => {
                    e.target.src = "/media/results/default_icon.png";
                  }}
                  alt="cover"
                />
              </div>

              <div className="result-info">
                <h5>{r.description}</h5>
                <small>{r.url}</small>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default SearchResultsPage;
