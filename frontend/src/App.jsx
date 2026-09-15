import { useState, useEffect } from 'react'
import './App.css'

const API_BASE = 'http://127.0.0.1:8000'

function App() {
  const [stats, setStats] = useState(null)
  const [questions, setQuestions] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    async function fetchData() {
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
  }, [])

  if (loading) return <div className="container"><p>Loading...</p></div>
  if (error) return <div className="container"><p>Error: {error}. Is the backend running on port 8000?</p></div>

  return (
    <div className="container">
      <h1>AI Coding Agent — Dashboard</h1>

      <div className="stats-grid">
        <StatCard label="Total Requests" value={stats.total_requests} />
        <StatCard label="Total Cost" value={`$${stats.total_cost_usd}`} />
        <StatCard label="Avg Latency" value={`${stats.avg_latency_ms} ms`} />
        <StatCard label="Input Tokens" value={stats.total_input_tokens} />
        <StatCard label="Output Tokens" value={stats.total_output_tokens} />
        <StatCard label="Cache Hit Rate" value={`${stats.cache_hit_rate_pct}%`} />
        <StatCard label="Errors" value={stats.errors} />
      </div>

      <h2>Recent Requests</h2>
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