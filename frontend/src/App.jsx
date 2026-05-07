import { useState, useEffect, useRef } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism'
import './App.css'

const API = 'http://localhost:8000'

function App() {
  const [repoUrl, setRepoUrl] = useState('')
  const [question, setQuestion] = useState('')
  const [status, setStatus] = useState(null)
  const [messages, setMessages] = useState([])
  const [ingesting, setIngesting] = useState(false)
  const [querying, setQuerying] = useState(false)
  const [error, setError] = useState(null)

  const chatEndRef = useRef(null)

  useEffect(() => {
    fetch(`${API}/reset`, { method: 'POST' })
      .then(() => fetch(`${API}/status`))
      .then(r => r.json())
      .then(setStatus)
      .catch(() => setStatus(null))
  }, [])

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleIngest = async (e) => {
    e.preventDefault()
    if (!repoUrl.trim()) return

    setIngesting(true)
    setError(null)
    setMessages([])

    try {
      const res = await fetch(`${API}/ingest`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ repo_url: repoUrl })
      })

      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail)
      }

      const data = await res.json()

      setStatus({ ready: true })

      setMessages([{
        role: 'assistant',
        content: `# Repository Loaded\n\nYou can now ask questions about the codebase.`
      }])

      setRepoUrl('')
    } catch (err) {
      setError(err.message)
    } finally {
      setIngesting(false)
    }
  }

  const handleQuery = async (e) => {
    e.preventDefault()
    if (!question.trim()) return

    const userMessage = { role: 'user', content: question }
    setMessages(prev => [...prev, userMessage])
    const currentQuestion = question
    setQuestion('')
    setQuerying(true)
    setError(null)

    try {
      const res = await fetch(`${API}/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: currentQuestion })
      })

      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail)
      }

      const data = await res.json()

      setMessages(prev => [
        ...prev,
        {
          role: 'assistant',
          content: data.answer,
          model: data.model_used
        }
      ])
    } catch (err) {
      setError(err.message)
    } finally {
      setQuerying(false)
    }
  }

  return (
    <div className="app">
      <header className="topbar">
        <div className="logo">RepoGPT</div>

        <form onSubmit={handleIngest} className="repo-form">
          <input
            type="text"
            value={repoUrl}
            onChange={(e) => setRepoUrl(e.target.value)}
            placeholder="Paste GitHub repository URL..."
            className="repo-input"
          />
          <button type="submit" disabled={ingesting} className="repo-btn">
            {ingesting ? 'Loading...' : 'Load'}
          </button>
        </form>
      </header>

      <main className="chat-area">
        {!status?.ready && !ingesting && (
          <div className="empty-state">
            <h1>RepoGPT</h1>
            <p>Load a GitHub repository and ask questions about the codebase.</p>
          </div>
        )}

        {messages.map((msg, index) => (
          <div key={index} className={`message ${msg.role}`}>
            <div className="message-label">
              {msg.role === 'user' ? 'You' : 'RepoGPT'}
            </div>

            <div className="message-content">
              {msg.role === 'user' ? (
                <p>{msg.content}</p>
              ) : (
                <>
                  <ReactMarkdown
                    remarkPlugins={[remarkGfm]}
                    components={{
                      code({ className, children, ...props }) {
                        const match = /language-(\w+)/.exec(className || '')
                        if (match) {
                          return (
                            <SyntaxHighlighter
                              style={vscDarkPlus}
                              language={match[1]}
                              PreTag="div"
                              className="code-block"
                              customStyle={{
                                margin: '16px 0',
                                borderRadius: '14px',
                                fontSize: '0.9rem',
                                padding: '18px'
                              }}
                              {...props}
                            >
                              {String(children).replace(/\n$/, '')}
                            </SyntaxHighlighter>
                          )
                        }
                        return (
                          <code className="inline-code" {...props}>
                            {children}
                          </code>
                        )
                      }
                    }}
                  >
                    {msg.content}
                  </ReactMarkdown>

                  <div className="message-footer">
                    {msg.model && (
                      <span className="model-pill">{msg.model}</span>
                    )}
                  </div>
                </>
              )}
            </div>
          </div>
        ))}

        {querying && (
          <div className="message assistant">
            <div className="message-label">RepoGPT</div>
            <div className="message-content typing">Thinking...</div>
          </div>
        )}

        <div ref={chatEndRef} />
      </main>

      {status?.ready && (
        <footer className="chatbar">
          <form onSubmit={handleQuery} className="chat-form">
            <input
              type="text"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="Ask anything about the repository..."
              className="chat-input"
            />
            <button type="submit" disabled={querying} className="send-btn">
              →
            </button>
          </form>
        </footer>
      )}

      {error && <div className="error-toast">{error}</div>}
    </div>
  )
}

export default App