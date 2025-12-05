import React, { useEffect, useState } from "react";
import "bootstrap/dist/css/bootstrap.min.css";
import "./AdminGamesPage.css";
import AdminNavbar from "../components/AdminNavbar";

function AdminGamesPage() {
  const [games, setGames] = useState([]);
  const [query, setQuery] = useState("");
  const [sortOption, setSortOption] = useState("oldest");

  const [loadingId, setLoadingId] = useState(null);

  const fetchGames = async () => {
    try {
      const params = new URLSearchParams({
        format: "json",
        sort: sortOption,
        q: query,
      });

      const res = await fetch(`/app/admin-panel/games/?${params.toString()}`, {
        credentials: "include",
      });

      const data = await res.json();
      setGames(data.games || []);
    } catch (err) {
      console.error("Error fetching games:", err);
    }
  };

  useEffect(() => {
    fetchGames();
  }, [sortOption]);

  const deleteGame = async (id) => {
    if (!window.confirm("Are you sure you want to delete this game?")) return;

    const res = await fetch(`/app/admin-panel/delete-game/${id}/`, {
      method: "POST",
      credentials: "include",
    });

    const data = await res.json();
    alert(data.message || data.error);
    fetchGames();
  };

  const reloadGame = async (id) => {
    if (!window.confirm("Re-scrape and regenerate summary for this game?"))
      return;

    setLoadingId(id);

    const res = await fetch(`/app/admin-panel/reload-game/${id}/`, {
      method: "POST",
      credentials: "include",
    });

    const data = await res.json();

    setLoadingId(null);

    alert(data.message || data.error);

    fetchGames();
  };

  const updateScore = async (id, newScore) => {
    const res = await fetch(`/app/admin-panel/edit-game-score/${id}/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ score: newScore }),
    });

    const data = await res.json();

    if (res.ok) {
      setGames((prev) =>
        prev.map((g) => (g.id === id ? { ...g, score: newScore } : g))
      );
    } else {
      alert(data.error || "Error updating score");
    }
  };

  const handleSearch = (e) => {
    e.preventDefault();
    fetchGames();
  };

  return (
    <>
      <AdminNavbar />

      <div className="table-container">
        <h2 className="explore-heading">
          <a href="/app/admin-panel/games/">Manage Games</a>
        </h2>

        <form onSubmit={handleSearch} className="mb-4 text-center">
          <div className="input-group mx-auto" style={{ maxWidth: "600px" }}>
            <input
              type="text"
              className="form-control search-input"
              placeholder="Search for a game..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
            <button className="btn btn-outline-primary" type="submit">
              Search
            </button>
          </div>

          <div className="d-flex justify-content-center align-items-center gap-2 mt-3">
            <label htmlFor="sortSelect" className="fw-bold mb-0 sort-label">
              Sort by:
            </label>
            <select
              id="sortSelect"
              className="form-select sort-select"
              value={sortOption}
              onChange={(e) => setSortOption(e.target.value)}
            >
              <option value="oldest">Date Added (Oldest)</option>
              <option value="newest">Date Added (Newest)</option>
              <option value="score">Score</option>
            </select>
          </div>
        </form>

        <table className="table table-striped align-middle">
          <thead>
            <tr>
              <th>ID</th>
              <th>Title</th>
              <th>Score</th>
              <th>Actions</th>
            </tr>
          </thead>

          <tbody>
            {games.length > 0 ? (
              games.map((game) => (
                <tr key={game.id}>
                  <td>{game.id}</td>

                  <td>
                    <a
                      href={`/app/games/${game.id}/`}
                      style={{
                        textDecoration: "none",
                        fontWeight: 600,
                        color: "#0f1836",
                      }}
                    >
                      {game.title}
                    </a>
                  </td>

                  <td className="score-cell">
                    <div className="score-layout">
                      <input
                        type="number"
                        value={game.score}
                        min="0"
                        max="10"
                        step="0.1"
                        onChange={(e) => updateScore(game.id, e.target.value)}
                        className="score-input"
                      />

                      {loadingId === game.id && (
                        <div className="spinner-small"></div>
                      )}
                    </div>
                  </td>

                  <td>
                    <button
                      className="btn btn-danger btn-sm"
                      onClick={() => deleteGame(game.id)}
                    >
                      Delete
                    </button>{" "}
                    <button
                      className="btn btn-dark btn-sm"
                      onClick={() => reloadGame(game.id)}
                    >
                      Reload
                    </button>
                  </td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan="4" className="text-center text-muted py-4">
                  No games found.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </>
  );
}

export default AdminGamesPage;
