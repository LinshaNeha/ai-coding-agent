import { useState } from 'react'
import ReactMarkdown from 'react-markdown'

const API_BASE = 'http://127.0.0.1:8000'

function ChatView() {
  const [apiKey, setApiKey] = useState('')
  const [question, setQuestion] = useState('')
  const [messages, setMessages] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  async function sendMessage() {
    if (!question.trim() || !apiKey.trim()) return

    const userQuestion = question
    setMessages((prev) => [...prev, { role: 'user', text: userQuestion }])
    setQuestion('')
    setLoading(true)
    setError(null)

    try {
      const res = await fetch(`${API_BASE}/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': apiKey,
        },
        body: JSON.stringify({ question: userQuestion }),
      })

      if (!res.ok) {
        const errBody = await res.json().catch(() => ({}))
        throw new Error(errBody.detail ? JSON.stringify(errBody.detail) : `Request failed (${res.status})`)
      }

      const data = await res.json()
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          text: data.answer,
          sources: data.sources || [],
          cached: data.cached || false,
          tier: data.tier,
          model_used: data.model_used,
          latency_ms: data.latency_ms,
        },
      ])
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  return (
    <div className="chat-container">
      <div className="api-key-row">
        <input
          type="password"
          placeholder="API Key"
          value={apiKey}
          onChange={(e) => setApiKey(e.target.value)}
          className="api-key-input"
        />
      </div>

      <div className="messages">
                {messages.length === 0 && (
          <div className="empty-state">
            <div className="empty-state-icon">{'</>'}</div>
            <div className="empty-state-title">Ask about your codebase</div>
            <div className="empty-state-sub">Questions are answered using real, retrieved source code — not guesses.</div>
          </div>
        )}
        {messages.map((m, i) => (
          <div key={i} className={`message ${m.role}`}>
            <div className="message-role">{m.role === 'user' ? 'You' : 'Assistant'}</div>
            <div className="message-text">
 		 {m.role === 'assistant' ? (
   			 <ReactMarkdown>{m.text}</ReactMarkdown>
 	     ) : (
   		 m.text
 	     )}
 		</div>
            {m.role === 'assistant' && (
              <div className="message-meta">
                {m.cached && <span className="badge badge-cached">cached</span>}
                {m.tier && <span className="badge">{m.tier} · {m.model_used}</span>}
                {m.latency_ms != null && <span className="badge">{m.latency_ms} ms</span>}
              </div>
            )}
            {m.sources && m.sources.length > 0 && (
              <div className="sources">
                {m.sources.map((s, j) => (
                  <div key={j} className="source-chip">
                    {s.chunk_name} ({s.file_path})
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}{loading && (
  <div className="message assistant">
    <div className="message-role">Assistant</div>
    <div className="thinking-dots">
      <span></span>
      <span></span>
      <span></span>
    </div>
  </div>
)}
        {error && <div className="error-banner">Error: {error}</div>}
      </div>

      <div className="input-row">
        <textarea
          placeholder="Ask about your codebase..."
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={handleKeyDown}
          rows={2}
        />
        <button onClick={sendMessage} disabled={loading || !question.trim() || !apiKey.trim()}>
          Send
        </button>
      </div>
    </div>
  )
}

export default ChatView