import React, { useEffect, useState } from "react";
import "./ChatbotPage.css";

function ChatbotPage() {
  const [games, setGames] = useState([]);
  const [currentGameId, setCurrentGameId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [searchTerm, setSearchTerm] = useState("");
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [thinking, setThinking] = useState(false);
  const [inputValue, setInputValue] = useState("");

  useEffect(() => {
    async function fetchInit() {
      try {
        const res = await fetch("/app/chatbot/?format=json", {
          credentials: "include",
          headers: { "x-requested-with": "XMLHttpRequest" }
        });

        const data = await res.json();
        setGames(data.games || []);

        const defaultId =
          data.default_game_id ||
          (data.games && data.games.length ? data.games[0].id : null);

        if (defaultId) {
          setCurrentGameId(defaultId);
          await loadHistory(defaultId);
        }
      } catch (err) {
        console.error("Error loading chatbot init:", err);
      }
    }

    fetchInit();
  }, []);

  async function loadHistory(gameId) {
    setLoadingHistory(true);
    setMessages([]);

    try {
      const res = await fetch(`/app/chatbot/history/?game_id=${gameId}`, {
        credentials: "include"
      });

      const data = await res.json();

      const msgs = [];
      data.forEach((h) => {
        msgs.push({ role: "user", text: h.question });
        msgs.push({ role: "bot", text: h.answer });
      });

      setMessages(msgs);
    } catch {
      console.error("Error loading chatbot history");
    } finally {
      setLoadingHistory(false);
    }
  }

  async function handleSend() {
    const text = inputValue.trim();
    if (!text || !currentGameId || thinking) return;

    setMessages((prev) => [...prev, { role: "user", text }]);
    setInputValue("");
    setThinking(true);

    try {
      const res = await fetch("/app/chatbot/ask/", {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: text, game_id: currentGameId })
      });

      const data = await res.json();

      setMessages((prev) => [
        ...prev,
        { role: "bot", text: data.answer || "No response" }
      ]);
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: "bot", text: "Error: connection failed" }
      ]);
    } finally {
      setThinking(false);
    }
  }

  async function handleDeleteHistory(gameId) {
    const confirmDelete = window.confirm(
      "Are you sure you want to delete chat history for this game?"
    );
    if (!confirmDelete) return;

    try {
      const res = await fetch("/app/chatbot/delete/", {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ game_id })
      });

      const data = await res.json();

      if (!res.ok) {
        alert(data.error || "Error deleting history.");
        return;
      }

      alert("Chat history deleted successfully.");

      if (String(gameId) === String(currentGameId)) {
        setMessages([]);
      }
    } catch {
      alert("Connection error while deleting chat history.");
    }
  }

  const filteredGames = games.filter((g) =>
    g.title.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="chatbot-page">
      <div className="chatbot-wrapper">
        {/* LEFT */}
        <div className="chatbot-sidebar">
          <div className="chatbot-search-box">
            <input
              type="text"
              placeholder="Search game..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>

          <div className="chatbot-games-list">
            {filteredGames.map((g) => (
              <div
                key={g.id}
                className={
                  "chatbot-game-item" +
                  (String(g.id) === String(currentGameId) ? " active" : "")
                }
                onClick={() => {
                  if (String(g.id) === String(currentGameId)) return;
                  setCurrentGameId(g.id);
                  loadHistory(g.id);
                }}
              >
                <img
                  className="cover"
                  src={g.cover_image || "/media/icons/Logo.png"}
                  alt={g.title}
                />

                <span className="title">{g.title}</span>

                <img
                  className="chatbot-delete-icon"
                  src="/media/icons/Trash.png"
                  alt="Delete"
                  title="Delete chat history"
                  onClick={(e) => {
                    e.stopPropagation();
                    handleDeleteHistory(g.id);
                  }}
                />
              </div>
            ))}
            {filteredGames.length === 0 && (
              <div className="chatbot-empty-state">No games found.</div>
            )}
          </div>
        </div>

        {/* RIGHT */}
        <div className="chatbot-chat-container">
          <div className="chatbot-chat-box">
            <div className="chatbot-chat-messages">
              {loadingHistory && (
                <p className="chatbot-typing">Loading chat history...</p>
              )}

              {messages.map((m, idx) => (
                <div
                  key={idx}
                  className={`chatbot-message ${
                    m.role === "user" ? "user" : "bot"
                  }`}
                >
                  <div className="chatbot-bubble">{m.text}</div>
                </div>
              ))}

              {thinking && <p className="chatbot-typing">Bot is thinking...</p>}
            </div>

            <div className="chatbot-input-row">
              <input
                type="text"
                placeholder={
                  currentGameId
                    ? "Ask something about this game..."
                    : "Select a game..."
                }
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleSend()}
                disabled={!currentGameId}
              />

              <button onClick={handleSend} disabled={!currentGameId || thinking}>
                Send
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default ChatbotPage;
