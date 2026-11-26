import ReactMarkdown from 'react-markdown';

function formatTime(date) {
  return date.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' });
}

function TypingDots() {
  return (
    <div className="typing-indicator">
      <div className="typing-dot" />
      <div className="typing-dot" />
      <div className="typing-dot" />
    </div>
  );
}

function Sources({ sources }) {
  if (!sources?.length) return null;
  return (
    <details className="sources">
      <summary className="sources-label">📚 Sources ({sources.length})</summary>
      {sources.map((src, i) => (
        <div key={i} className="source-item">
          <div className="source-page">Page {src.page}</div>
          <div>&ldquo;{src.content}…&rdquo;</div>
        </div>
      ))}
    </details>
  );
}

export default function Message({ message }) {
  const { role, content, sources, timestamp, streaming } = message;
  const isUser = role === 'user';

  if (!isUser && streaming && !content) {
    return (
      <div className="message assistant">
        <div className="message-avatar">🤖</div>
        <TypingDots />
      </div>
    );
  }

  return (
    <div className={`message ${role}`}>
      <div className="message-avatar">{isUser ? '👤' : '🤖'}</div>
      <div className="message-bubble">
        <div className="message-content">
          {isUser ? <p>{content}</p> : <ReactMarkdown>{content}</ReactMarkdown>}
        </div>
        {!isUser && !streaming && <Sources sources={sources} />}
        <div className="message-time">{formatTime(new Date(timestamp))}</div>
      </div>
    </div>
  );
}
