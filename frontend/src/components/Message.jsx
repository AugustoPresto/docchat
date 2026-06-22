import ReactMarkdown from 'react-markdown';

function formatTime(date) {
  return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
}

function TypingIndicator() {
  return (
    <div className="message assistant">
      <div className="message-avatar">🤖</div>
      <div className="typing-indicator">
        <div className="typing-dot" />
        <div className="typing-dot" />
        <div className="typing-dot" />
      </div>
    </div>
  );
}

function Sources({ sources }) {
  if (!sources?.length) return null;
  return (
    <div className="sources">
      <div className="sources-label">📚 Sources</div>
      {sources.map((src, i) => (
        <div key={i} className="source-item">
          <div className="source-page">Page {src.page}</div>
          <div>"{src.content}…"</div>
        </div>
      ))}
    </div>
  );
}

export default function Message({ message, isTyping }) {
  if (isTyping) return <TypingIndicator />;

  const { role, content, sources, timestamp } = message;
  const isUser = role === 'user';

  return (
    <div className={`message ${role}`} id={`msg-${timestamp}`}>
      <div className="message-avatar">
        {isUser ? '👤' : '🤖'}
      </div>
      <div className="message-bubble">
        <div className="message-content">
          {isUser ? (
            <p>{content}</p>
          ) : (
            <ReactMarkdown>{content}</ReactMarkdown>
          )}
        </div>
        {!isUser && <Sources sources={sources} />}
        <div className="message-time">
          {formatTime(new Date(timestamp))}
        </div>
      </div>
    </div>
  );
}
