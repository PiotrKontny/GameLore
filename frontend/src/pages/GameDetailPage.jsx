// src/pages/GameDetailPage.jsx
import React, { useEffect, useState, useMemo } from "react";
import { useParams, useNavigate } from "react-router-dom";
import "./GameDetailPage.css";

/* --- CSRF --- */
function getCookie(name) {
  const match = document.cookie.match(
    "(^|;)\\s*" + name + "\\s*=\\s*([^;]+)"
  );
  return match ? decodeURIComponent(match.pop()) : "";
}

function getScoreColor(rawScore) {
  if (rawScore == null) return "blue";
  const score = Number(rawScore);
  if (Number.isNaN(score)) return "blue";

  if (score >= 9.0) return "gold";
  if (score >= 8.0) return "green";
  if (score >= 6.0) return "yellow";
  if (score >= 4.0) return "purple";
  return "red";
}

const TAB_FULL = "full";
const TAB_SUMMARY = "summary";
const TAB_CHATBOT = "chatbot";

const GameDetailPage = () => {
  const { id } = useParams();
  const gameId = id;
  const navigate = useNavigate();
  const csrftoken = getCookie("csrftoken");

  const [loading, setLoading] = useState(true);
  const [gameData, setGameData] = useState(null);
  const [activeTab, setActiveTab] = useState(TAB_FULL);

  const [summaryHtml, setSummaryHtml] = useState("");
  const [isGeneratingSummary, setIsGeneratingSummary] = useState(false);
  const [summaryError, setSummaryError] = useState("");

  const [ratingStats, setRatingStats] = useState({
    avg: 0,
    votes: 0,
    user_rating: null,
  });
  const [currentAvg, setCurrentAvg] = useState(0);
  const [hoverValue, setHoverValue] = useState(null);

  const [chatLoaded, setChatLoaded] = useState(false);
  const [chatMessages, setChatMessages] = useState([]);
  const [chatInput, setChatInput] = useState("");
  const [chatThinking, setChatThinking] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function fetchGame() {
      setLoading(true);
      try {
        const res = await fetch(`/app/api/game/${gameId}/`, {
          credentials: "include",
          headers: {
            "x-requested-with": "XMLHttpRequest",
            Accept: "application/json",
          },
        });

        if (res.status === 404) {
          if (!cancelled) {
            setLoading(false);
            navigate("/error/404");
          }
          return;
        }

        if (!res.ok) {
          throw new Error("HTTP " + res.status);
        }

        const data = await res.json();
        const gameObj = data.game || data;

        const fullPlotHtml =
          data.full_plot_html || gameObj.full_plot_html || "";
        const summaryHtmlRaw =
          data.summary_html || gameObj.summary_html || "";

        let normalizedScore = null;
        if (
          gameObj.score !== undefined &&
          gameObj.score !== null
        ) {
          const s = Number(gameObj.score);
          normalizedScore = Number.isNaN(s) ? null : s;
        }

        if (!cancelled) {
          setGameData({
            id: gameObj.id,
            title: gameObj.title,
            release_date: gameObj.release_date,
            genre: gameObj.genre,
            studio: gameObj.studio,
            cover_image: gameObj.cover_image,
            mobygames_url: gameObj.mobygames_url,
            wikipedia_url: gameObj.wikipedia_url,
            score: normalizedScore,
            full_plot_html: fullPlotHtml,
          });
          setSummaryHtml(summaryHtmlRaw || "");
        }
      } catch (e) {
        console.error("Game fetch error", e);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    fetchGame();
    return () => {
      cancelled = true;
    };
  }, [gameId, navigate]);

  const isSummaryMissing = useMemo(() => {
    if (!summaryHtml) return true;
    const clean = summaryHtml
      .toLowerCase()
      .replace(/\s+/g, "")
      .replace(/<p>/g, "")
      .replace(/<\/p>/g, "")
      .trim();

    return (
      clean === "" ||
      clean === "<p></p>" ||
      clean === "&nbsp;" ||
      clean.includes("nosummaryavailable") ||
      clean.includes("summarynotyetgenerated") ||
      clean.includes("thisgamehasnoplotavailable") ||
      clean.includes("noplotsummary") ||
      clean.length < 5
    );
  }, [summaryHtml]);

  useEffect(() => {
    if (!gameId) return;

    async function loadRating() {
      try {
        const res = await fetch(`/app/games/${gameId}/rating/`, {
          credentials: "include",
          headers: {
            "x-requested-with": "XMLHttpRequest",
            Accept: "application/json",
          },
        });
        if (!res.ok)
          throw new Error("Rating HTTP " + res.status);

        const data = await res.json();
        const avg = Number(data.avg || 0);

        setRatingStats({
          avg,
          votes: data.votes || 0,
          user_rating: data.user_rating ?? null,
        });
        setCurrentAvg(avg);
      } catch (err) {
        console.error("Rating fetch error", err);
      }
    }

    loadRating();
  }, [gameId]);

  const handleStarClick = async (value) => {
    try {
      const res = await fetch(`/app/games/${gameId}/rating/`, {
        method: "POST",
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": csrftoken,
          "x-requested-with": "XMLHttpRequest",
          Accept: "application/json",
        },
        body: JSON.stringify({ rating: value }),
      });

      const data = await res.json();
      const avg = Number(data.avg || 0);

      setRatingStats({
        avg,
        votes: data.votes || 0,
        user_rating: value,
      });
      setCurrentAvg(avg);
    } catch (err) {
      console.error("Rating save error", err);
    }
  };

  const handleGenerateSummary = async () => {
    setIsGeneratingSummary(true);
    setSummaryError("");

    try {
      const res = await fetch(
        `/app/games/${gameId}/generate-summary/`,
        {
          method: "POST",
          credentials: "include",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": csrftoken,
            "x-requested-with": "XMLHttpRequest",
            Accept: "application/json",
          },
          body: JSON.stringify({}),
        }
      );

      const data = await res.json();
      if (data.summary) {
        setSummaryHtml(data.summary);
      } else {
        setSummaryError(data.error || "Unexpected error.");
      }
    } catch (err) {
      console.error("Summary error:", err);
      setSummaryError("Request failed.");
    } finally {
      setIsGeneratingSummary(false);
    }
  };

  useEffect(() => {
    if (activeTab !== TAB_CHATBOT || chatLoaded) return;

    async function loadHistory() {
      try {
        const res = await fetch(
          `/app/chatbot/history/?game_id=${gameId}`,
          {
            credentials: "include",
            headers: {
              "x-requested-with": "XMLHttpRequest",
              Accept: "application/json",
            },
          }
        );
        if (!res.ok)
          throw new Error("Chat history HTTP " + res.status);

        const history = await res.json();
        const msgs = [];
        history.forEach((h) => {
          msgs.push({ role: "user", text: h.question });
          msgs.push({ role: "bot", text: h.answer });
        });
        setChatMessages(msgs);
        setChatLoaded(true);
      } catch (err) {
        console.error("Chat history error", err);
      }
    }

    loadHistory();
  }, [activeTab, chatLoaded, gameId]);

  const handleSendChat = async () => {
    const question = (chatInput || "").trim();
    if (!question) return;

    setChatInput("");
    setChatMessages((prev) => [
      ...prev,
      { role: "user", text: question },
    ]);
    setChatThinking(true);

    try {
      const res = await fetch("/app/chatbot/ask/", {
        method: "POST",
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": csrftoken,
          "x-requested-with": "XMLHttpRequest",
          Accept: "application/json",
        },
        body: JSON.stringify({ question, game_id: gameId }),
      });

      const data = await res.json();
      let answer =
        data.answer || data.error || "No answer from chatbot.";

      answer = answer
        .replace(/~~(.*?)~~/g, "$1")
        .replace(/<\/?s>/g, "")
        .replace(/\[OUT\]/gi, "")
        .replace(/\[INST\]/gi, "")
        .replace(/\[\/?INSTR?\]/gi, "")
        .trim();

      setChatMessages((prev) => [
        ...prev,
        { role: "bot", text: answer },
      ]);
    } catch (err) {
      console.error("Chat ask error", err);
      setChatMessages((prev) => [
        ...prev,
        { role: "bot", text: "Request failed." },
      ]);
    } finally {
      setChatThinking(false);
    }
  };

  const highlightStyle = useMemo(() => {
    const index =
      activeTab === TAB_FULL
        ? 0
        : activeTab === TAB_SUMMARY
        ? 1
        : 2;
    return {
      transform: `translateX(${index * 100}%)`,
    };
  }, [activeTab]);

  if (loading || !gameData) {
    return (
      <div className="game-detail-loading">
        Loading game details...
      </div>
    );
  }

  return (
    <div className="game-detail-page">
      <div className="game-container">
        <h2 className="game-title">{gameData.title}</h2>

        {gameData.cover_image && (
          <img
            className="cover"
            src={gameData.cover_image}
            alt={gameData.title}
          />
        )}

        <div className="game-info">
          {gameData.release_date && (
            <span>
              <strong>Released on:</strong> {gameData.release_date}
            </span>
          )}
          {gameData.genre && (
            <span>
              <strong>Genre:</strong> {gameData.genre}
            </span>
          )}
          {gameData.studio && (
            <span>
              <strong>Studio:</strong> {gameData.studio}
            </span>
          )}
        </div>

        {gameData.score != null && (
          <div className="score-line">
            <span>
              <strong>Score:</strong>
            </span>
            <span
              className={`score-box ${getScoreColor(
                gameData.score
              )}`}
            >
              {gameData.score.toFixed
                ? gameData.score.toFixed(1)
                : gameData.score}
            </span>
          </div>
        )}

        {(gameData.mobygames_url ||
          gameData.wikipedia_url) && (
          <div className="sources">
            <h5>
              <strong>Sources:</strong>
            </h5>
            {gameData.mobygames_url && (
              <a
                href={gameData.mobygames_url}
                target="_blank"
                rel="noreferrer"
              >
                MobyGames
              </a>
            )}
            {gameData.wikipedia_url && (
              <a
                href={gameData.wikipedia_url}
                target="_blank"
                rel="noreferrer"
              >
                Wikipedia
              </a>
            )}
          </div>
        )}

        {/* RATING */}
        <div id="rating-section">
          <h5>
            <strong>Rating:</strong>
          </h5>
          <div id="stars">
            {Array.from({ length: 10 }, (_, i) => {
              const starValue = i + 1;

              const starColor = hoverValue
                ? starValue <= hoverValue
                  ? "limegreen"
                  : "#ccc"
                : starValue <= Math.round(currentAvg)
                ? "#f6c700"
                : "#ccc";

              return (
                <span
                  key={i}
                  className="star"
                  onClick={() => handleStarClick(starValue)}
                  onMouseEnter={() => setHoverValue(starValue)}
                  onMouseLeave={() => setHoverValue(null)}
                  style={{ color: starColor }}
                >
                  ★
                </span>
              );
            })}
          </div>
          <p id="rating-stats" className="mt-2 text-muted">
            {(ratingStats.avg || 0).toFixed(2)}/10 –{" "}
            {ratingStats.votes || 0} votes
          </p>
        </div>

        {/* TABS */}
        <div className="tab-wrapper">
          <div className="tab-control" role="tablist">
            <div
              className="tab-highlight"
              style={highlightStyle}
            />
            <button
              type="button"
              className={
                activeTab === TAB_FULL
                  ? "tab-btn active"
                  : "tab-btn"
              }
              onClick={() => setActiveTab(TAB_FULL)}
            >
              Full Lore
            </button>
            <button
              type="button"
              className={
                activeTab === TAB_SUMMARY
                  ? "tab-btn active"
                  : "tab-btn"
              }
              onClick={() => setActiveTab(TAB_SUMMARY)}
            >
              Summary
            </button>
            <button
              type="button"
              className={
                activeTab === TAB_CHATBOT
                  ? "tab-btn active"
                  : "tab-btn"
              }
              onClick={() => setActiveTab(TAB_CHATBOT)}
            >
              Chatbot
            </button>
          </div>
        </div>

        {activeTab === TAB_FULL && (
          <div
            className="markdown-content"
            dangerouslySetInnerHTML={{
              __html: gameData.full_plot_html,
            }}
          />
        )}

        {activeTab === TAB_SUMMARY && (
          <div className="tab-pane">
            {isSummaryMissing && !isGeneratingSummary && (
              <div className="text-center mt-4">
                <p className="muted">
                  Summary not yet generated.
                </p>
                {summaryError && (
                  <p className="text-danger">
                    {summaryError}
                  </p>
                )}
                <button
                  className="btn btn-primary"
                  onClick={handleGenerateSummary}
                >
                  Generate Summary
                </button>
              </div>
            )}

            {isGeneratingSummary && (
              <div className="text-center mt-4">
                <div className="spinner-border text-primary"></div>
                <p className="mt-2">Generating summary...</p>
              </div>
            )}

            {!isSummaryMissing && !isGeneratingSummary && (
              <div
                className="markdown-content mt-3"
                dangerouslySetInnerHTML={{ __html: summaryHtml }}
              />
            )}
          </div>
        )}

        {activeTab === TAB_CHATBOT && (
          <div className="tab-pane">
            <div id="chat-window">
              <div id="chat-history">
                {chatMessages.map((m, idx) => (
                  <div
                    key={idx}
                    className={`message ${m.role}`}
                  >
                    <div className="bubble">{m.text}</div>
                  </div>
                ))}
                {chatThinking && (
                  <p className="typing">Bot is thinking...</p>
                )}
              </div>
            </div>
            <div className="input-group">
              <input
                className="form-control"
                value={chatInput}
                onChange={(e) =>
                  setChatInput(e.target.value)
                }
                onKeyDown={(e) =>
                  e.key === "Enter" && handleSendChat()
                }
              />
              <button
                className="btn btn-primary"
                onClick={handleSendChat}
              >
                Send
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default GameDetailPage;
