import React, { useEffect, useState } from "react";
import "./MyLibraryPage.css";

function MyLibraryPage() {
  const [games, setGames] = useState([]);
  const [query, setQuery] = useState("");
  const [sort, setSort] = useState("newest");
  const [loading, setLoading] = useState(true);

  // Pobieranie biblioteki
  async function loadLibrary() {
    setLoading(true);
    const res = await fetch(`/app/api/my_library/?q=${query}&sort=${sort}`, {
      credentials: "include",
      headers: { "x-requested-with": "XMLHttpRequest" },
    });

    if (res.ok) {
      const data = await res.json();
      setGames(data.games || []);
    }
    setLoading(false);
  }

  useEffect(() => {
    loadLibrary();
  }, [sort]);

  // wyszukiwanie
  const handleSearch = (e) => {
    e.preventDefault();
    loadLibrary();
  };

  // usuwanie gry
  async function deleteGame(id) {
    if (!window.confirm("Are you sure you want to remove this game?"))
      return;

    const res = await fetch("/app/delete_history/", {
      method: "POST",
      credentials: "include",
      headers: {
        "Content-Type": "application/json",
        "x-requested-with": "XMLHttpRequest",
      },
      body: JSON.stringify({ game_id: id }),
    });

    const data = await res.json();
    if (data.message) {
      setGames((prev) => prev.filter((g) => g.id !== id));
    }
  }

  return (
    <div className="library-page">

      <h2 className="explore-heading">
      <a href="/app/my_library/" className="explore-link">
        My Game Library
      </a>
    </h2>


      {/* SEARCH BAR */}
      <form className="search-wrap" onSubmit={handleSearch}>
        <div className="input-group mx-auto" style={{ maxWidth: "720px" }}>
          <input
            type="text"
            className="form-control search-input"
            placeholder="Search for your games"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          <button className="btn btn-outline-primary">Search</button>
        </div>
      </form>

      {/* SORTER */}
      <div className="sort-row">
        <label className="me-2 fw-semibold">Sort by:</label>
        <select
          value={sort}
          onChange={(e) => setSort(e.target.value)}
          className="form-select w-auto d-inline-block"
        >
          <option value="newest">Date Viewed (Newest)</option>
          <option value="oldest">Date Viewed (Oldest)</option>
          <option value="rating">Rating</option>
        </select>
      </div>

      {/* GAMES GRID */}
      <div className="library-container">
        <div className="row gy-5 justify-content-center">

          {/* ADD CARD */}
          <div className="col-md-4 d-flex justify-content-center">
            <a
              href="/app/search/"
              className="text-decoration-none"
              style={{ width: "100%", display: "flex", justifyContent: "center" }}
            >
              <div className="add-card w-100">+</div>
            </a>
          </div>

          {/* LISTA GIER */}
          {loading ? (
            <p className="text-muted text-center mt-4">Loading...</p>
          ) : games.length === 0 ? (
            <p className="text-muted">No games in your library yet.</p>
          ) : (
            games.map((game) => (
              <div key={game.id} className="col-md-4 d-flex justify-content-center">
                <div className="game-card">
                  <button
                    className="delete-btn"
                    onClick={() => deleteGame(game.id)}
                  >
                    &times;
                  </button>

                  <div className="img-container">
                    {game.cover_image ? (
                      <img src={game.cover_image} alt={game.title} />
                    ) : (
                      <img src="/media/placeholder.jpg" alt="No image" />
                    )}
                  </div>

                  <div className="game-title">
                    <a href={`/app/games/${game.id}/`}>{game.title}</a>
                  </div>

                  <div className="rating-section mb-3">
                    <div className="rating-row d-flex justify-content-center align-items-center gap-2">
                      <span className="label">Your Rating:</span>
                      {game.user_rating ? (
                        <>
                          <span className="fw-semibold">{game.user_rating}/10</span>
                          <span className="star">★</span>
                        </>
                      ) : (
                        <>
                          <span className="text-muted">N/A</span>
                          <span className="star">★</span>
                        </>
                      )}
                    </div>
                  </div>

                </div>
              </div>
            ))
          )}
        </div>
      </div>

    </div>
  );
}

export default MyLibraryPage;
