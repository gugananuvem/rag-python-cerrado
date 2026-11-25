import React, { useState, useRef, useEffect } from 'react';
import { Send, Bot, User, Sparkles, Settings, RefreshCw, BookOpen, AlertCircle } from 'lucide-react';
import './App.css';

const DEFAULT_API_ENDPOINT = import.meta.env.VITE_API_ENDPOINT || 'https://xxxxxxxxxx.execute-api.us-east-1.amazonaws.com/chat';

export default function App() {
  const [messages, setMessages] = useState([
    {
      id: 'welcome',
      sender: 'assistant',
      text: 'Olá! Sou o assistente RAG Serverless. Posso tirar suas dúvidas sobre AWS DynamoDB Vector Search, Python Serverless e Amazon Bedrock.',
      sources: []
    }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [apiEndpoint, setApiEndpoint] = useState(() => {
    return localStorage.getItem('rag_api_endpoint') || DEFAULT_API_ENDPOINT;
  });
  const [showSettings, setShowSettings] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  const handleSaveEndpoint = (e) => {
    e.preventDefault();
    localStorage.setItem('rag_api_endpoint', apiEndpoint);
    setShowSettings(false);
    setErrorMsg('');
  };

  const handleSendMessage = async (customText = null) => {
    const textToSend = customText || input;
    if (!textToSend.trim() || loading) return;

    setErrorMsg('');
    const userMsgId = Date.now().toString();
    const newUserMessage = {
      id: userMsgId,
      sender: 'user',
      text: textToSend
    };

    setMessages(prev => [...prev, newUserMessage]);
    if (!customText) setInput('');
    setLoading(true);

    try {
      const response = await fetch(apiEndpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ pergunta: textToSend }),
      });

      if (!response.ok) {
        throw new Error(`Erro na API (${response.status}): ${response.statusText}`);
      }

      const data = await response.json();

      const assistantMessage = {
        id: (Date.now() + 1).toString(),
        sender: 'assistant',
        text: data.resposta || 'Não foi possível obter uma resposta do modelo.',
        sources: data.fontes || []
      };

      setMessages(prev => [...prev, assistantMessage]);
    } catch (err) {
      console.error('Erro na requisição RAG:', err);
      setErrorMsg(err.message || 'Erro ao comunicar com a API Serverless.');
      setMessages(prev => [
        ...prev,
        {
          id: (Date.now() + 1).toString(),
          sender: 'assistant',
          text: '⚠️ Desculpe, ocorreu um erro ao consultar a base de conhecimento. Verifique se o endpoint da API Gateway está correto nas configurações.',
          isError: true
        }
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const suggestions = [
    'O que é DynamoDB Vector Search?',
    'Como construir um RAG Serverless em Python?',
    'Como tratar erros de throttling no Amazon Bedrock?'
  ];

  return (
    <div className="app-container">
      {/* Header */}
      <header className="app-header">
        <div className="header-title">
          <div className="logo-icon">
            <Sparkles size={24} className="icon-glow" />
          </div>
          <div>
            <h1>RAG Serverless Assistant</h1>
            <p className="subtitle">DynamoDB Vector Search • Amazon Bedrock • Python 3.12</p>
          </div>
        </div>
        <button 
          className="settings-btn"
          onClick={() => setShowSettings(!showSettings)}
          title="Configurar Endpoint da API"
        >
          <Settings size={20} />
        </button>
      </header>

      {/* Modal de Configuração de Endpoint */}
      {showSettings && (
        <div className="settings-modal-overlay">
          <div className="settings-modal">
            <h3>⚙️ Configuração do Endpoint</h3>
            <p>Informe a URL do API Gateway gerada pelo AWS SAM:</p>
            <form onSubmit={handleSaveEndpoint}>
              <input 
                type="text" 
                value={apiEndpoint}
                onChange={(e) => setApiEndpoint(e.target.value)}
                placeholder="https://xxx.execute-api.us-east-1.amazonaws.com/chat"
                className="endpoint-input"
              />
              <div className="modal-actions">
                <button type="button" onClick={() => setShowSettings(false)} className="btn-secondary">
                  Cancelar
                </button>
                <button type="submit" className="btn-primary">
                  Salvar
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Exibição de Alertas/Erros */}
      {errorMsg && (
        <div className="error-banner">
          <AlertCircle size={18} />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* Área Principal do Chat */}
      <main className="chat-history">
        {messages.map((msg) => (
          <div 
            key={msg.id} 
            className={`message-row ${msg.sender === 'user' ? 'user-row' : 'bot-row'}`}
          >
            <div className={`avatar ${msg.sender === 'user' ? 'user-avatar' : 'bot-avatar'}`}>
              {msg.sender === 'user' ? <User size={18} /> : <Bot size={18} />}
            </div>

            <div className={`message-bubble ${msg.isError ? 'error-bubble' : ''}`}>
              <div className="message-content">
                {msg.text.split('\n').map((paragraph, index) => (
                  <p key={index}>{paragraph}</p>
                ))}
              </div>

              {/* Fontes de Contexto Recuperadas do DynamoDB */}
              {msg.sources && msg.sources.length > 0 && (
                <div className="sources-container">
                  <div className="sources-header">
                    <BookOpen size={14} />
                    <span>Fontes Recuperadas (DynamoDB Vector):</span>
                  </div>
                  <div className="sources-list">
                    {msg.sources.map((src, i) => (
                      <div key={i} className="source-item">
                        <div className="source-title-row">
                          <span className="source-title">{src.title}</span>
                          <span className="source-similarity">
                            Similaridade: {(src.similarity * 100).toFixed(1)}%
                          </span>
                        </div>
                        <p className="source-snippet">{src.snippet}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        ))}

        {loading && (
          <div className="message-row bot-row">
            <div className="avatar bot-avatar">
              <Bot size={18} />
            </div>
            <div className="message-bubble loading-bubble">
              <RefreshCw size={18} className="spinner" />
              <span>Buscando vetores no DynamoDB e gerando resposta via Bedrock...</span>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </main>

      {/* Sugestões de Perguntas */}
      {messages.length === 1 && (
        <div className="suggestions-container">
          <p className="suggestions-label">Perguntas sugeridas:</p>
          <div className="suggestions-list">
            {suggestions.map((item, idx) => (
              <button 
                key={idx} 
                className="suggestion-chip"
                onClick={() => handleSendMessage(item)}
              >
                {item}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Campo de Envio de Mensagem */}
      <footer className="chat-input-container">
        <div className="input-wrapper">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Pergunte sobre DynamoDB Vector, Python Serverless..."
            rows={1}
            disabled={loading}
          />
          <button 
            onClick={() => handleSendMessage()} 
            disabled={!input.trim() || loading}
            className="send-btn"
          >
            <Send size={18} />
          </button>
        </div>
        <p className="footer-disclaimer">
          Respostas geradas por Amazon Bedrock Claude 3 utilizando dados recuperados do DynamoDB.
        </p>
      </footer>
    </div>
  );
}
