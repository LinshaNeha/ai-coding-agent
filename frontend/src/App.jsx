import { useState, useEffect } from 'react'
import ChatView from './ChatView'
import AgentView from './AgentView'
import './App.css'

const API_BASE = 'http://127.0.0.1:8000'

function App() {
  const [tab, setTab] = useState('chat')
  const [stats, setStats] = useState(null)
  const [questions, setQuestions] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (tab !== 'dashboard') return

    async function fetchData() {
      setLoading(true)
      try {
        const [statsRes, questionsRes] = await Promise.all([
          fetch(`${API_BASE}/stats`),
          fetch(`${API_BASE}/stats/by-question`),
        ])
        if (!statsRes.ok || !questionsRes.ok) throw new Error('Failed to fetch data')
        setStats(await statsRes.json())
        setQuestions(await questionsRes.json())
      } catch (err) {
        setError(err.message)
      } finally {
        setLoading(false)
      }
    }
    fetchData()
  }, [tab])

  return (
    <div className="shell">
      <div className="header">
                <div className="brand">
          <div className="brand-mark" />
          <div className="brand-text">
            <span className="brand-name">AI Coding Agent</span>
            <span className="brand-sub">codebase Q&A</span>
          </div>
        </div>
        <div className="tabs">
          <button className={tab === 'chat' ? 'tab active' : 'tab'} onClick={() => setTab('chat')}>
            Chat
          </button>
          <button className={tab === 'dashboard' ? 'tab active' : 'tab'} onClick={() => setTab('dashboard')}>
            Dashboard
          </button>
          <button className={tab === 'agent' ? 'tab active' : 'tab'} onClick={() => setTab('agent')}>
            Agent
          </button>
        </div>
      </div>

      <div className="content">
        {tab === 'chat' && <ChatView />}
        {tab === 'agent' && <AgentView />}
        {tab === 'dashboard' && (
          <>
            {loading && <p>Loading...</p>}
            {error && <p>Error: {error}. Is the backend running on port 8000?</p>}
            {stats && (
              <>
                <p className="dash-heading">Overview</p>
                <div className="hero-stats">
                  <div className="hero-card is-primary">
                    <div className="hero-label">Total cost</div>
                    <div className="hero-value">${stats.total_cost_usd}</div>
                  </div>
                  <div className="hero-card">
                    <div className="hero-label">Total requests</div>
                    <div className="hero-value">{stats.total_requests}</div>
                  </div>
                  <div className="hero-card">
                    <div className="hero-label">Errors</div>
                    <div className={`hero-value ${stats.errors > 0 ? 'error-tone' : ''}`}>{stats.errors}</div>
                  </div>
                </div>

                <div className="stats-grid">
                  <StatCard label="Avg latency" value={`${stats.avg_latency_ms} ms`} />
                  <StatCard label="Input tokens" value={stats.total_input_tokens} />
                  <StatCard label="Output tokens" value={stats.total_output_tokens} />
                  <StatCard label="Cache hit rate" value={`${stats.cache_hit_rate_pct}%`} />
                </div>

                <p className="dash-heading" style={{ marginTop: '28px' }}>Recent Requests</p>
                <table>
                  <thead>
                    <tr>
                      <th>Question</th>
                      <th>Model</th>
                      <th>Input</th>
                      <th>Output</th>
                      <th>Cost</th>
                      <th>Latency</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {questions.map((q) => (
                      <tr key={q.id} className={q.status === 'error' ? 'row-error' : ''}>
                        <td className="question-cell">{q.question}</td>
                        <td>{q.model_used}</td>
                        <td>{q.input_tokens}</td>
                        <td>{q.output_tokens}</td>
                        <td>${q.cost_usd}</td>
                        <td>{q.latency_ms} ms</td>
                        <td>{q.status}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </>
            )}
          </>
        )}
      </div>
    </div>
  )
}

function StatCard({ label, value }) {
  return (
    <div className="stat-card">
      <div className="stat-label">{label}</div>
      <div className="stat-value">{value}</div>
    </div>
  )
}

export default App