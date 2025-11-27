// frontend/src/pages/ExplorePage.jsx

import React, { useEffect, useState } from "react";
import "./ExplorePage.css";
import "bootstrap/dist/css/bootstrap.min.css";

import Navbar from "../components/Navbar";
import NavbarLogin from "../components/NavbarLogin";

function ExplorePage() {
  const [games, setGames] = useState([]);
  const [genres, setGenres] = useState([]);
  const [query, setQuery] = useState("");
  const [selectedGenre, setSelectedGenre] = useState("");
  const [sort, setSort] = useState("oldest");

  const [user, setUser] = useState(null);

  /* === LOAD USER (identycznie jak w InformationPage) === */
  useEffect(() => {
    async function loadUser() {
      try {
        const res = await fetch("/app/api/user/", {
          credentials: "include",
          headers: { "x-requested-with": "XMLHttpRequest" },
        });
        if (res.ok) setUser(await res.json());
        else setUser(null);
      } catch (e) {
        setUser(null);
      }
    }
    loadUser();
  }, []);

  const fetchGames = async () => {
    const params = new URLSearchParams({
      format: "json",
      q: query,
      sort: sort,
      genre: selectedGenre,
    });

    const res = await fetch(`/app/explore/?${params.toString()}`, {
      credentials: "include",
    });

    const data = await res.json();

    setGames(data.games || []);
    setGenres(data.genres || []);
  };

  useEffect(() => {
    fetchGames();
  }, [sort, selectedGenre]);

  const handleSearch = (e) => {
    e.preventDefault();
    fetchGames();
  };

  return (
    <div>
      {/* === NAVBAR (dokładnie jak na InformationPage) === */}
      {user ? <Navbar user={user} /> : <NavbarLogin />}

      <div className="container text-center">
        <h2 className="explore-heading">
          <a href="/app/explore/">Explore Game Lores</a>
        </h2>

        {/* Search */}
        <form className="search-wrap mb-3" onSubmit={handleSearch}>
          <div className="input-group mx-auto" style={{ maxWidth: "720px" }}>
            <input
              type="text"
              className="form-control search-input"
              placeholder="Search for the games in the database"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />

            <button
              type="button"
              className="btn btn-outline-secondary"
              onClick={() =>
                document.getElementById("genrePanel").classList.toggle("open")
              }
            >
              Genres ▾
            </button>

            <button className="btn btn-outline-primary" type="submit">
              Search
            </button>
          </div>
        </form>

        {/* Genre Panel */}
        <div id="genrePanel" className="genre-panel">
          <div className="fw-semibold mb-2">Genres from the database</div>

          <div className="d-flex flex-wrap gap-2 justify-content-center">
            {genres.map((g) => (
              <button
                key={g}
                className={
                  "btn btn-sm btn-genre " +
                  (selectedGenre === g ? "active" : "")
                }
                onClick={() => setSelectedGenre(selectedGenre === g ? "" : g)}
              >
                {g}
              </button>
            ))}
          </div>
        </div>

        <div className="mb-4">
          <a href="/app/search/" className="btn btn-primary">
            Search for a new game
          </a>
        </div>

        {/* Sorter */}
        <div className="d-flex justify-content-center align-items-center mb-4 gap-3">
          <label className="fw-bold">Sort by:</label>
          <select
            className="form-select"
            style={{ width: "250px" }}
            value={sort}
            onChange={(e) => setSort(e.target.value)}
          >
            <option value="oldest">Date added (Oldest)</option>
            <option value="newest">Date added (Newest)</option>
            <option value="score">Score</option>
            <option value="rating">Rating</option>
          </select>
        </div>

        {/* GAMES GRID */}
        <div className="row gy-5 justify-content-center">
          {games.length > 0 ? (
            games.map((g) => (
              <div className="col-md-4 d-flex justify-content-center" key={g.id}>
                <div className="game-card">
                  <div className="img-container">
                    <img
                      src={
                        g.cover_image
                          ? `/media/${g.cover_image}`
                          : "/media/placeholder.jpg"
                      }
                      alt={g.title}
                    />
                  </div>

                  <div className="game-title">
                    <a href={`/app/games/${g.id}/`}>{g.title}</a>
                  </div>

                  <div className="rating-section mb-3">
                    <div className="rating-row">
                      <div className="score-item">
                        <span className="label">Score:</span>
                        <span className={`score-box ${getScoreColor(g.score)}`}>
                          {g.score ?? "?"}
                        </span>
                      </div>

                      <div className="rating-item">
                        <span className="label">Rating:</span>
                        {g.rating ? (
                          <>
                            {g.rating}/10 <span className="star">★</span>
                          </>
                        ) : (
                          <>
                            N/A <span className="star">★</span>
                          </>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            ))
          ) : (
            <p className="no-games">No games in the database yet.</p>
          )}
        </div>
      </div>
    </div>
  );
}

/* Helper for score badge colors */
function getScoreColor(score) {
  if (score == null) return "blue";
  if (score >= 9.0) return "gold";
  if (score >= 8.0) return "green";
  if (score >= 6.0) return "yellow";
  if (score >= 4.0) return "purple";
  return "red";
}

export default ExplorePage;
