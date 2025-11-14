import React, { useEffect, useState } from "react";

const chatbotStyles = `
  :root {
    --nav:#0f1836;
    --gold:#d6b679;
    --shadow:0 12px 28px rgba(0,0,0,.25);
    --radius:18px;
  }

  .chatbot-page {
    background:#f4f6fa;
    font-family:"Segoe UI", Roboto, sans-serif;
    margin:0;
    padding:0;
    min-height: calc(100vh - 70px); /* wysokość bez paska nawigacji */
  }

  .chatbot-wrapper {
    display:flex;
    height:calc(100vh - 80px); /* trochę luzu na navbar */
    max-height:calc(100vh - 80px);
    overflow:hidden;
  }

  /* LEFT PANEL */
  .chatbot-sidebar {
    width: 320px;
    background: #fff;
    border-right: 1px solid #ddd;
    display: flex;
    flex-direction: column;
    padding: 12px;
  }

  .chatbot-search-box input {
    width:100%;
    border-radius:8px;
    border:1px solid #ccc;
    padding:6px 10px;
    margin-bottom:10px;
    font-size: 14px;
  }

  .chatbot-games-list {
    overflow-y:auto;
    flex:1;
    padding-right:5px;
  }

  .chatbot-game-item {
    position: relative;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 10px;
    padding: 10px 8px;
    margin-bottom: 10px;
    border-radius: 10px;
    cursor: pointer;
    transition: all 0.2s ease;
    min-height: 64px;
    word-break: break-word;
    white-space: normal;
    border: 1px solid #e0e0e0;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
    background-color: #fff;
  }
  
  .chatbot-game-item img.cover {
    width: 42px;
    height: 58px;
    border-radius: 6px;
    object-fit: cover;
    margin-top: 3px;
    margin-bottom: 3px;
}


  .chatbot-game-item:hover {
    background: #f4f6fa;
    transform: scale(1.01);
  }

  .chatbot-game-item.active {
    background: var(--nav);
    color: white;
    font-weight: 600;
    border-color: #0f1836;
  }

  .chatbot-game-item.active:hover {
    background:#162a5c;
  }

  .chatbot-game-item span.title {
    flex: 1;
    text-align: center;
    font-size: 15px;
    line-height: 1.3;
    word-wrap: break-word;
  }

  .chatbot-delete-icon {
    position: absolute;
    top: 6px;
    right: 8px;
    width: 16px;
    height: 16px;
    object-fit: contain;
    display: block;
    opacity: 0.6;
    transition: all 0.2s ease;
    filter: grayscale(100%) brightness(85%);
  }

  .chatbot-delete-icon:hover {
    opacity: 1;
    transform: scale(1.2);
    filter: grayscale(0%) brightness(100%);
    cursor: pointer;
  }

  /* Ikona śmietnika na aktywnym (granatowym) kafelku */
  .chatbot-game-item.active .chatbot-delete-icon {
    filter: invert(1) brightness(1.8);
    opacity: 0.9;
  }

  .chatbot-game-item.active .chatbot-delete-icon:hover {
    transform: scale(1.2);
    opacity: 1;
    filter: invert(1) brightness(2.2);
  }

  /* RIGHT PANEL (CHAT) */
  .chatbot-chat-container {
    flex:1;
    display:flex;
    justify-content:center;
    align-items:center;
    padding:30px 30px;
  }

  .chatbot-chat-box {
    width:100%;
    max-width:1250px;
    height:calc(110vh - 220px);
    background:white;
    border-radius:var(--radius);
    box-shadow:var(--shadow);
    padding:25px;
    display:flex;
    flex-direction:column;
  }

  .chatbot-chat-messages {
    flex:1;
    overflow-y:auto;
    padding:10px;
  }

  .chatbot-message {
    display:flex;
    margin-bottom:12px;
  }

  .chatbot-message.user {
    justify-content:flex-end;
  }

  .chatbot-message.bot {
    justify-content:flex-start;
  }

  .chatbot-bubble {
    max-width:70%;
    padding:10px 14px;
    border-radius:15px;
    line-height:1.4;
    word-wrap:break-word;
    white-space:pre-wrap;
  }

  .chatbot-message.user .chatbot-bubble {
    background:var(--nav);
    color:#fff;
    border-bottom-right-radius:0;
  }

  .chatbot-message.bot .chatbot-bubble {
    background:#e9ecef;
    color:#222;
    border-bottom-left-radius:0;
  }

  .chatbot-input-row {
    display:flex;
    gap:10px;
    margin-top:10px;
  }

  .chatbot-input-row input {
    flex:1;
    border-radius:10px;
    border:1px solid #ccc;
    padding:8px 10px;
    font-size: 14px;
  }

  .chatbot-input-row button {
    background:var(--nav);
    color:var(--gold);
    border:none;
    border-radius:10px;
    padding:8px 20px;
    font-weight:600;
    box-shadow:var(--shadow);
  }

  .chatbot-input-row button:hover {
    background:#182b5c;
    color:#f5dca1;
  }

  .chatbot-typing {
    font-style:italic;
    color:#888;
    text-align:center;
    margin-bottom:10px;
  }

  .chatbot-empty-state {
    text-align:center;
    color:#555;
    margin-top:20px;
  }
`;

function ChatbotPage() {
  const [games, setGames] = useState([]);
  const [currentGameId, setCurrentGameId] = useState(null);
  const [messages, setMessages] = useState([]); // {role: 'user'|'bot', text: string}
  const [searchTerm, setSearchTerm] = useState("");
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [thinking, setThinking] = useState(false);
  const [inputValue, setInputValue] = useState("");

  // Wstrzyknięcie stylów tylko na tej stronie
  useEffect(() => {
    const styleTag = document.createElement("style");
    styleTag.innerHTML = chatbotStyles;
    document.head.appendChild(styleTag);
    return () => {
      document.head.removeChild(styleTag);
    };
  }, []);

  // Początkowe pobranie listy gier + domyślnej gry
  useEffect(() => {
    async function fetchInit() {
      try {
        const res = await fetch("/app/chatbot/?format=json", {
          credentials: "include",
          headers: {
            "x-requested-with": "XMLHttpRequest",
          },
        });
        if (!res.ok) {
          console.error("Failed to load chatbot init", res.status);
          return;
        }
        const data = await res.json();
        setGames(data.games || []);
        const defaultId =
          data.default_game_id ||
          (data.games && data.games.length > 0 ? data.games[0].id : null);
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
        credentials: "include",
      });
      if (!res.ok) {
        console.error("Failed to load history", res.status);
        setLoadingHistory(false);
        return;
      }
      const data = await res.json();
      const msgs = [];
      data.forEach((h) => {
        msgs.push({ role: "user", text: h.question });
        msgs.push({ role: "bot", text: h.answer });
      });
      setMessages(msgs);
    } catch (err) {
      console.error("Error loading history:", err);
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
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ question: text, game_id: currentGameId }),
      });

      const data = await res.json();
      if (!res.ok) {
        const errText = data.error || "Error from server.";
        setMessages((prev) => [...prev, { role: "bot", text: errText }]);
      } else {
        setMessages((prev) => [
          ...prev,
          { role: "bot", text: data.answer || "No response" },
        ]);
      }
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { role: "bot", text: "Error: connection failed" },
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
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ game_id: gameId }),
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
    } catch (err) {
      alert("Connection error while deleting chat history.");
    }
  }

  const filteredGames = games.filter((g) =>
    g.title.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="chatbot-page">
      <div className="chatbot-wrapper">
        {/* LEFT PANEL */}
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
              <div className="chatbot-empty-state">
                No games found in your history.
              </div>
            )}
          </div>
        </div>

        {/* RIGHT PANEL */}
        <div className="chatbot-chat-container">
          <div className="chatbot-chat-box">
            <div className="chatbot-chat-messages">
              {loadingHistory && (
                <p className="chatbot-typing">Loading chat history...</p>
              )}
              {messages.map((m, idx) => (
                <div
                  key={idx}
                  className={`chatbot-message ${m.role === "user" ? "user" : "bot"}`}
                >
                  <div className="chatbot-bubble">{m.text}</div>
                </div>
              ))}
              {thinking && (
                <p className="chatbot-typing">Bot is thinking...</p>
              )}
            </div>
            <div className="chatbot-input-row">
              <input
                type="text"
                placeholder={
                  currentGameId
                    ? "Ask something about this game..."
                    : "Select a game from the left..."
                }
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    e.preventDefault();
                    handleSend();
                  }
                }}
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
