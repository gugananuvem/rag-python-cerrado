import { useEffect, useRef, useState } from "react";
import "./App.css";

const ENDPOINT_KEY = "rag_api_endpoint";

export default function App() {
  const [endpoint, setEndpoint] = useState(
    () => localStorage.getItem(ENDPOINT_KEY) || ""
  );
  const [showSettings, setShowSettings] = useState(false);
  const [draftEndpoint, setDraftEndpoint] = useState(endpoint);
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  useEffect(() => {
    if (!endpoint) setShowSettings(true);
  }, [endpoint]);

  function saveEndpoint() {
    const value = draftEndpoint.trim();
    setEndpoint(value);
    localStorage.setItem(ENDPOINT_KEY, value);
    setShowSettings(false);
  }

  async function sendQuestion(e) {
    e.preventDefault();
    const text = question.trim();
    if (!text || loading) return;

    if (!endpoint) {
      setShowSettings(true);
      return;
    }

    setMessages((prev) => [...prev, { role: "user", text }]);
    setQuestion("");
    setLoading(true);

    try {
      const res = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: text }),
      });

      if (!res.ok) {
        const detail = await res.text();
        throw new Error(`HTTP ${res.status}: ${detail}`);
      }

      const data = await res.json();
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          text: data.answer || "(sem resposta)",
          sources: data.sources || [],
        },
      ]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { role: "error", text: `Erro: ${err.message}` },
      ]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="app">
      <header className="app__header">
        <div className="app__title">
          <span className="app__logo">🔎</span>
          <div>
            <h1>RAG Serverless</h1>
            <p>DynamoDB + Bedrock (Titan + Claude 3)</p>
          </div>
        </div>
        <button
          className="icon-btn"
          title="Configurar endpoint"
          onClick={() => {
            setDraftEndpoint(endpoint);
            setShowSettings((s) => !s);
          }}
        >
          ⚙️
        </button>
      </header>

      {showSettings && (
        <div className="settings">
          <label htmlFor="endpoint">API Endpoint (ApiEndpoint do SAM)</label>
          <div className="settings__row">
            <input
              id="endpoint"
              type="text"
              placeholder="https://xxxx.execute-api.us-east-1.amazonaws.com/chat"
              value={draftEndpoint}
              onChange={(e) => setDraftEndpoint(e.target.value)}
            />
            <button className="btn" onClick={saveEndpoint}>
              Salvar
            </button>
          </div>
        </div>
      )}

      <main className="chat">
        {messages.length === 0 && !loading && (
          <div className="chat__empty">
            <p>Faça uma pergunta sobre a base de conhecimento.</p>
            <p className="chat__hint">
              Ex.: "O que é RAG?" ou "Como funciona a busca vetorial no DynamoDB?"
            </p>
          </div>
        )}

        {messages.map((msg, i) => (
          <div key={i} className={`bubble bubble--${msg.role}`}>
            <div className="bubble__text">{msg.text}</div>
            {msg.sources && msg.sources.length > 0 && (
              <div className="sources">
                <span className="sources__label">Fontes:</span>
                {msg.sources.map((s) => (
                  <span key={s.id} className="source-chip">
                    {s.title} · {s.score}
                  </span>
                ))}
              </div>
            )}
          </div>
        ))}

        {loading && (
          <div className="bubble bubble--assistant">
            <div className="typing">
              <span></span>
              <span></span>
              <span></span>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </main>

      <form className="composer" onSubmit={sendQuestion}>
        <input
          type="text"
          placeholder="Digite sua pergunta..."
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          disabled={loading}
        />
        <button className="btn" type="submit" disabled={loading || !question.trim()}>
          Enviar
        </button>
      </form>
    </div>
  );
}
