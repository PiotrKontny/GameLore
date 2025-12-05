// src/pages/CompilationPage.jsx
import React, { useEffect, useState } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import "./CompilationPage.css";

function CompilationPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  const url = searchParams.get("url");
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      if (!url) return;

      const res = await fetch(`/app/compilation/?url=${encodeURIComponent(url)}&format=json`, {
        headers: { "x-requested-with": "XMLHttpRequest" }
      });

      const json = await res.json();
      setData(json);
      setLoading(false);
    }

    loadData();
  }, [url]);

  if (!url) return <p style={{ padding: 20 }}>Missing URL</p>;
  if (loading)
  return (
    <div className="compilation-container">
      <h2>Loading...</h2>

      <div className="center-loader mid-loader">
        <div className="spinner"></div>
        <span>Loading compilation...</span>
      </div>
    </div>
  );


  if (!data) return <p style={{ padding: 20 }}>Error loading compilation</p>;

  return (
    <div className="compilation-container">
      <h2>{data.title}</h2>

      <p>
        This title is a <strong>game compilation</strong>.
        Choose one of the included games to explore their plot.
      </p>

      <ul className="game-list">
        {data.included_games.map((g, i) => (
          <li key={i}>
            <div>
              <strong>{g.title}</strong>
              {g.year && <span> {g.year}</span>}
            </div>

            <button
              className="details-btn"
              onClick={() => navigate(`/app/details/?url=${encodeURIComponent(g.url)}`)}
            >
              Choose
            </button>
          </li>
        ))}
      </ul>

      <button className="back-link" onClick={() => navigate(-1)}>
        Go Back
      </button>
    </div>
  );
}

export default CompilationPage;
