import React, { useState, useEffect } from "react";
import "./SearchFormPage.css";

function SearchFormPage() {
  const [user, setUser] = useState(null);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    async function load() {
      const res = await fetch("/app/api/user/", {
        credentials: "include",
        headers: { "x-requested-with": "XMLHttpRequest" }
      });
      if (res.ok) {
        setUser(await res.json());
      }
    }
    load();
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!query.trim()) return;

    setLoading(true);

    const res = await fetch("/app/search/", {
      method: "POST",
      credentials: "include",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({ game: query.trim() })
    });

    if (res.ok) {
      window.location.href = "/app/results/";
    } else {
      setLoading(false);
      alert("Failed to fetch results. Please try again.");
    }
  };

  return (
    <div className="search-page">

      <div className="search-container">
        <img src="/media/icons/Logo.png" alt="GameLore" className="search-logo" />

        <form onSubmit={handleSubmit} className="search-box">
          <input
            type="text"
            placeholder="Enter game title..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          <button type="submit">Search</button>
        </form>

        {loading && (
          <div id="loader">
            <div className="spinner"></div>
            <span>Searching for games...</span>
          </div>
        )}

        <p className="hint">
          Search for any game and GameLore will fetch information from MobyGames and Wikipedia.
        </p>
      </div>
    </div>
  );
}

export default SearchFormPage;
