import { useEffect, useRef, useState } from 'react';
import { RotateCcw, Send } from 'lucide-react';
import Message from './Message';
import { sendMessage } from '../services/api';

const WELCOME_MESSAGES = [
  "What is this document about?",
  "Summarize the key points.",
  "What are the main conclusions?",
];

export default function ChatInterface({ document, onToast }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  // Reset chat when document changes
  useEffect(() => {
    setMessages([]);
    setInput('');
    inputRef.current?.focus();
  }, [document.id]);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  const handleSend = async (text = input.trim()) => {
    if (!text || isLoading) return;

    const userMsg = {
      role: 'user',
      content: text,
      timestamp: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    setIsLoading(true);

    try {
      // Build conversation history for context
      const history = messages.map((m) => ({
        role: m.role,
        content: m.content,
      }));

      const response = await sendMessage(document.id, text, history);

      const aiMsg = {
        role: 'assistant',
        content: response.answer,
        sources: response.sources,
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, aiMsg]);
    } catch (err) {
      const detail = err.response?.data?.detail || err.message;
      onToast('error', `⚠️ ${detail}`);
      // Remove the user message on error so they can retry
      setMessages((prev) => prev.slice(0, -1));
      setInput(text);
    } finally {
      setIsLoading(false);
      inputRef.current?.focus();
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleClear = () => {
    setMessages([]);
    setInput('');
    inputRef.current?.focus();
  };

  return (
    <div className="chat-area">
      {/* Header */}
      <div className="chat-header">
        <span className="chat-header-icon">💬</span>
        <div className="chat-header-info">
          <h3>{document.filename}</h3>
          <p>{document.page_count} pages · {document.chunk_count} indexed chunks</p>
        </div>
        {messages.length > 0 && (
          <div className="chat-actions">
            <button className="btn-ghost" onClick={handleClear} id="clear-chat-btn" title="Clear conversation">
              <RotateCcw size={13} />
              Clear
            </button>
          </div>
        )}
      </div>

      {/* Messages */}
      <div className="messages-container" id="messages-container">
        {messages.length === 0 && !isLoading ? (
          <div style={{ marginTop: '24px' }}>
            <p style={{ fontSize: '13px', color: 'var(--text-muted)', marginBottom: '16px', textAlign: 'center' }}>
              💡 Try asking:
            </p>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', maxWidth: '440px', margin: '0 auto' }}>
              {WELCOME_MESSAGES.map((q) => (
                <button
                  key={q}
                  onClick={() => handleSend(q)}
                  style={{
                    padding: '10px 16px',
                    background: 'var(--bg-elevated)',
                    border: '1px solid var(--border)',
                    borderRadius: 'var(--radius-md)',
                    color: 'var(--text-secondary)',
                    fontSize: '13px',
                    textAlign: 'left',
                    cursor: 'pointer',
                    transition: 'var(--transition)',
                  }}
                  onMouseEnter={(e) => { e.target.style.borderColor = 'var(--accent)'; e.target.style.color = 'var(--text-primary)'; }}
                  onMouseLeave={(e) => { e.target.style.borderColor = 'var(--border)'; e.target.style.color = 'var(--text-secondary)'; }}
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        ) : null}

        {messages.map((msg) => (
          <Message key={msg.timestamp} message={msg} />
        ))}

        {isLoading && <Message isTyping />}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="input-area">
        <div className="input-form">
          <textarea
            ref={inputRef}
            id="message-input"
            className="message-input"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask anything about this document…"
            rows={1}
            disabled={isLoading}
            style={{ height: 'auto' }}
            onInput={(e) => {
              e.target.style.height = 'auto';
              e.target.style.height = Math.min(e.target.scrollHeight, 120) + 'px';
            }}
          />
          <button
            id="send-btn"
            className="send-btn"
            onClick={() => handleSend()}
            disabled={!input.trim() || isLoading}
            title="Send message (Enter)"
          >
            <Send size={15} />
          </button>
        </div>
        <div className="input-hint">
          Press <strong>Enter</strong> to send · <strong>Shift+Enter</strong> for new line
        </div>
      </div>
    </div>
  );
}
