import { useState } from 'react'

const API_BASE = 'http://127.0.0.1:8000'

function diffLines(before, after) {
  const beforeLines = before.split('\n')
  const afterLines = after.split('\n')
  const maxLen = Math.max(beforeLines.length, afterLines.length)
  const rows = []

  for (let i = 0; i < maxLen; i++) {
    const b = beforeLines[i]
    const a = afterLines[i]
    if (b === a) {
      rows.push({ type: 'same', text: b ?? '' })
    } else {
      if (b !== undefined) rows.push({ type: 'removed', text: b })
      if (a !== undefined) rows.push({ type: 'added', text: a })
    }
  }
  return rows
}

function AgentView() {
  const [apiKey, setApiKey] = useState('')
  const [filePath, setFilePath] = useState('')
  const [testPath, setTestPath] = useState('tests')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)

  async function runFix() {
    setLoading(true)
    setError(null)
    setResult(null)

    try {
      const res = await fetch(`${API_BASE}/agent/fix`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': apiKey,
        },
        body: JSON.stringify({ file_path: filePath, test_path: testPath }),
      })

      if (!res.ok) {
        const errBody = await res.json().catch(() => ({}))
        throw new Error(errBody.detail ? JSON.stringify(errBody.detail) : `Request failed (${res.status})`)
      }

      setResult(await res.json())
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const diff = result ? diffLines(result.original_code, result.final_code) : []

    return (
    <div className="agent-container">
      <div className="agent-intro">
        Point this at a file in your codebase. The agent reads it, runs the matching tests, and if any fail, it diagnoses the failure, writes a patch, and re-runs the tests to confirm the fix — up to 3 attempts. A timestamped backup is saved before any file is changed.
      </div>

      <div className="agent-form">
        <input
          type="password"
          placeholder="API Key"
          value={apiKey}
          onChange={(e) => setApiKey(e.target.value)}
          className="api-key-input"
        />
        <input
          type="text"
          placeholder="File to fix (e.g. app/services/buggy_math.py)"
          value={filePath}
          onChange={(e) => setFilePath(e.target.value)}
          className="agent-input"
        />
        <input
          type="text"
          placeholder="Test path (default: tests)"
          value={testPath}
          onChange={(e) => setTestPath(e.target.value)}
          className="agent-input"
        />
        <button onClick={runFix} disabled={loading || !apiKey.trim() || !filePath.trim()}>
          {loading ? 'Running fix-loop...' : 'Run Fix'}
        </button>
      </div>

      {error && <div className="error-banner">Error: {error}</div>}

      {result && (
        <div className="agent-result">
          <div className={`result-banner ${result.success ? 'success' : 'fail'}`}>
            {result.success ? 'Tests passing' : 'Tests still failing'} · {result.attempts} attempt(s) · {result.changed ? 'file changed' : 'no changes made'}
          </div>

          <h3>Diff</h3>
          <div className="diff-view">
            {diff.map((line, i) => (
              <div key={i} className={`diff-line diff-${line.type}`}>
                <span className="diff-marker">
                  {line.type === 'added' ? '+' : line.type === 'removed' ? '-' : ' '}
                </span>
                <span className="diff-text">{line.text}</span>
              </div>
            ))}
          </div>

          <h3>Test Output</h3>
          <pre className="test-output">{result.final_output}</pre>
        </div>
      )}
    </div>
  )
}

export default AgentView