import { useEffect, useRef, useState } from 'react';
import { RotateCcw, Send, Menu, Square } from 'lucide-react';
import Message from './Message';
import { randomId, streamMessage } from '../services/api';

const WELCOME_MESSAGES = [
  'What is this document about?',
  'Summarize the key points.',
  'What are the main conclusions?',
];

export default function ChatInterface({ document, onToast, onToggleSidebar }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);
  const abortRef = useRef(null);

  useEffect(() => {
    inputRef.current?.focus();
    return () => abortRef.current?.abort();
  }, []);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const updateMessage = (id, fn) =>
    setMessages((prev) => prev.map((m) => (m.id === id ? fn(m) : m)));

  const handleSend = async (text = input.trim()) => {
    if (!text || isLoading) return;

    const history = messages
      .filter((m) => !m.streaming && m.content)
      .map((m) => ({ role: m.role, content: m.content }));

    const userMsg = { id: randomId(), role: 'user', content: text, timestamp: new Date().toISOString() };
    const aiId = randomId();
    const aiMsg = { id: aiId, role: 'assistant', content: '', sources: [], streaming: true, timestamp: new Date().toISOString() };

    setMessages((prev) => [...prev, userMsg, aiMsg]);
    setInput('');
    if (inputRef.current) inputRef.current.style.height = 'auto';
    setIsLoading(true);

    const controller = new AbortController();
    abortRef.current = controller;
    let received = false;

    try {
      await streamMessage(document.id, text, history, {
        signal: controller.signal,
        onSources: (sources) => updateMessage(aiId, (m) => ({ ...m, sources })),
        onToken: (token) => {
          received = true;
          updateMessage(aiId, (m) => ({ ...m, content: m.content + token }));
        },
      });
      updateMessage(aiId, (m) => ({ ...m, streaming: false }));
    } catch (err) {
      if (err.name === 'AbortError') {
        if (received) updateMessage(aiId, (m) => ({ ...m, streaming: false }));
        else setMessages((prev) => prev.filter((m) => m.id !== aiId && m.id !== userMsg.id));
        return;
      }
      onToast('error', `⚠️ ${err.message}`);
      if (received) {
        updateMessage(aiId, (m) => ({ ...m, streaming: false }));
      } else {
        // Nothing arrived: drop both messages so the question can be retried.
        setMessages((prev) => prev.filter((m) => m.id !== aiId && m.id !== userMsg.id));
        setInput(text);
      }
    } finally {
      abortRef.current = null;
      setIsLoading(false);
      inputRef.current?.focus();
    }
  };

  const handleStop = () => abortRef.current?.abort();

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleClear = () => {
    abortRef.current?.abort();
    setMessages([]);
    setInput('');
    inputRef.current?.focus();
  };

  return (
    <div className="chat-area">
      {/* Header */}
      <div className="chat-header">
        <button className="mobile-menu-btn" onClick={onToggleSidebar} aria-label="Open menu">
          <Menu size={20} />
        </button>
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
        {messages.length === 0 && (
          <div className="suggestions">
            <p className="suggestions-title">💡 Try asking:</p>
            <div className="suggestions-list">
              {WELCOME_MESSAGES.map((q) => (
                <button key={q} className="suggestion-btn" onClick={() => handleSend(q)}>
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg) => (
          <Message key={msg.id} message={msg} />
        ))}

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
            maxLength={4000}
            onInput={(e) => {
              e.target.style.height = 'auto';
              e.target.style.height = Math.min(e.target.scrollHeight, 120) + 'px';
            }}
          />
          {isLoading ? (
            <button id="stop-btn" className="send-btn" onClick={handleStop} title="Stop generating">
              <Square size={13} />
            </button>
          ) : (
            <button
              id="send-btn"
              className="send-btn"
              onClick={() => handleSend()}
              disabled={!input.trim()}
              title="Send message (Enter)"
            >
              <Send size={15} />
            </button>
          )}
        </div>
        <div className="input-hint">
          Press <strong>Enter</strong> to send · <strong>Shift+Enter</strong> for new line
        </div>
      </div>
    </div>
  );
}
