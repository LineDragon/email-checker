import { useState, useEffect } from 'react'
import axios from 'axios'
import EmailListView from './EmailListView'
import InboxView from './InboxView'
import './App.css'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

function App() {
  const [currentView, setCurrentView] = useState('send') // 'send', 'list', or 'inbox'
  const [googleConnected, setGoogleConnected] = useState(false)
  const [googleEmail, setGoogleEmail] = useState(null)
  const [outlookConnected, setOutlookConnected] = useState(false)
  const [outlookEmail, setOutlookEmail] = useState(null)
  const [connectingProvider, setConnectingProvider] = useState(null)
  const [sending, setSending] = useState(false)
  const [emailCount, setEmailCount] = useState(null)
  const [error, setError] = useState(null)
  const [selectedResumeFile, setSelectedResumeFile] = useState(null)
  const [senderName, setSenderName] = useState('')
  const [firstIndex, setFirstIndex] = useState('')
  const [lastIndex, setLastIndex] = useState('')
  const [selectedProvider, setSelectedProvider] = useState('google')
  const [emailStatus, setEmailStatus] = useState(null) // {targets: [{email, status, error}], total, sent, failed}
  const [eventSource, setEventSource] = useState(null)

  const isGoogleConnecting = connectingProvider === 'google'
  const isOutlookConnecting = connectingProvider === 'outlook'
  const isConnecting = Boolean(connectingProvider)
  const anyProviderConnected = googleConnected || outlookConnected
  const selectedProviderConnected =
    selectedProvider === 'google' ? googleConnected : outlookConnected

  // Cleanup EventSource on unmount
  useEffect(() => {
    return () => {
      if (eventSource) {
        eventSource.close()
      }
    }
  }, [eventSource])

  // Check provider connection status on mount and after redirect
  useEffect(() => {
    checkGoogleStatus()
    checkOutlookStatus()
    
    // Check URL params for OAuth callback
    const params = new URLSearchParams(window.location.search)
    if (params.get('google_connected') === 'true') {
      setGoogleConnected(true)
      setGoogleEmail(params.get('email'))
      // Clean URL
      window.history.replaceState({}, document.title, window.location.pathname)
    }
    if (params.get('outlook_connected') === 'true') {
      setOutlookConnected(true)
      setOutlookEmail(params.get('email'))
      window.history.replaceState({}, document.title, window.location.pathname)
    }
    if (params.get('error')) {
      setError(params.get('error'))
      window.history.replaceState({}, document.title, window.location.pathname)
    }
  }, [])

  useEffect(() => {
    if (selectedProvider === 'google' && !googleConnected && outlookConnected) {
      setSelectedProvider('outlook')
    } else if (selectedProvider === 'outlook' && !outlookConnected && googleConnected) {
      setSelectedProvider('google')
    } else if (!googleConnected && !outlookConnected && selectedProvider !== 'google') {
      setSelectedProvider('google')
    }
  }, [googleConnected, outlookConnected, selectedProvider])

  const checkGoogleStatus = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/api/google/status`)
      if (response.data.connected) {
        setGoogleConnected(true)
        setGoogleEmail(response.data.email)
      }
    } catch (err) {
      console.error('Error checking Google status:', err)
    }
  }

  const checkOutlookStatus = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/api/outlook/status`)
      if (response.data.connected) {
        setOutlookConnected(true)
        setOutlookEmail(response.data.email)
      } else {
        setOutlookConnected(false)
        setOutlookEmail(null)
      }
    } catch (err) {
      console.error('Error checking Outlook status:', err)
      setOutlookConnected(false)
      setOutlookEmail(null)
    }
  }



  const handleConnectGoogle = async () => {
    setConnectingProvider('google')
    setError(null)
    try {
      const response = await axios.get(`${API_BASE_URL}/api/google/auth`)
      // Redirect to Google OAuth
      window.location.href = response.data.authorization_url
    } catch (err) {
      setError('Failed to initiate Google OAuth: ' + (err.response?.data?.detail || err.message))
      setConnectingProvider(null)
    }
  }

  const handleConnectOutlook = async () => {
    setConnectingProvider('outlook')
    setError(null)
    try {
      const response = await axios.get(`${API_BASE_URL}/api/outlook/auth`)
      window.location.href = response.data.authorization_url
    } catch (err) {
      setError('Failed to initiate Outlook OAuth: ' + (err.response?.data?.detail || err.message))
      setConnectingProvider(null)
    }
  }


  const handleProviderChange = (e) => {
    setSelectedProvider(e.target.value)
  }

  const handleSendBulkEmails = async () => {
    if (!senderName || !senderName.trim()) {
      setError('Please enter your name')
      return
    }

    const providerConnected = selectedProvider === 'google' ? googleConnected : outlookConnected

    if (!providerConnected) {
      const providerName = selectedProvider === 'google' ? 'Google' : 'Outlook'
      setError(`Please connect your ${providerName} account first`)
      return
    }

    setSending(true)
    setError(null)
    setEmailCount(null)
    setEmailStatus(null)
    
    // Close any existing EventSource
    if (eventSource) {
      eventSource.close()
      setEventSource(null)
    }

    const endpoint =
      selectedProvider === 'google'
        ? `${API_BASE_URL}/api/google/send-bulk-emails`
        : `${API_BASE_URL}/api/outlook/send-bulk-emails`

    try {
      const formData = new FormData()
      formData.append('sender_name', senderName.trim())
      
      // Add index range if provided
      if (firstIndex && firstIndex.trim()) {
        const first = parseInt(firstIndex.trim(), 10)
        if (!isNaN(first) && first > 0) {
          formData.append('first_index', first.toString())
        }
      }
      if (lastIndex && lastIndex.trim()) {
        const last = parseInt(lastIndex.trim(), 10)
        if (!isNaN(last) && last > 0) {
          formData.append('last_index', last.toString())
        }
      }
      
      // Validate index range if both are provided
      if (firstIndex && lastIndex && firstIndex.trim() && lastIndex.trim()) {
        const first = parseInt(firstIndex.trim(), 10)
        const last = parseInt(lastIndex.trim(), 10)
        if (!isNaN(first) && !isNaN(last) && first > last) {
          setError('First index must be less than or equal to last index')
          setSending(false)
          return
        }
      }
      
      if (selectedResumeFile) {
        formData.append('resume', selectedResumeFile)
      }

      const response = await axios.post(endpoint, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      })

      if (response.data.success && response.data.job_id) {
        // Initialize status
        setEmailStatus({
          targets: [],
          total: response.data.total,
          sent: 0,
          failed: 0,
          status: 'sending'
        })
        
        // Connect to SSE endpoint
        const jobId = response.data.job_id
        const sseUrl = `${API_BASE_URL}/api/email/status/${jobId}`
        const es = new EventSource(sseUrl)
        setEventSource(es)
        
        es.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data)
            
            if (data.error) {
              setError(data.error)
              es.close()
              setSending(false)
              return
            }
            
            // Update status
            setEmailStatus(prev => {
              if (!prev) {
                // Initialize if not set
                return {
                  targets: data.targets || [],
                  total: data.total || 0,
                  sent: data.sent || 0,
                  failed: data.failed || 0,
                  status: data.status || 'sending',
                  errors: data.errors || null
                }
              }
              
              // Merge new targets with existing ones (replace if email already exists)
              const targetMap = new Map(prev.targets.map(t => [t.email, t]))
              data.targets.forEach(target => {
                targetMap.set(target.email, target)
              })
              const updatedTargets = Array.from(targetMap.values())
              
              return {
                targets: updatedTargets,
                total: data.total !== undefined ? data.total : prev.total,
                sent: data.sent !== undefined ? data.sent : prev.sent,
                failed: data.failed !== undefined ? data.failed : prev.failed,
                status: data.status || prev.status,
                errors: data.errors !== undefined ? data.errors : prev.errors
              }
            })
            
            // Close connection if job is completed
            if (data.status === 'completed' || data.status === 'failed') {
              es.close()
              setEventSource(null)
              setSending(false)
              
              if (data.status === 'completed') {
                setEmailCount(data.sent)
                if (data.failed > 0) {
                  alert(`Sent ${data.sent} email(s), ${data.failed} failed.`)
                } else {
                  alert(`Successfully sent ${data.sent} email(s)!`)
                }
              } else {
                setError('Failed to send emails')
                alert(`Error: Failed to send emails`)
              }
            }
          } catch (err) {
            console.error('Error parsing SSE data:', err)
          }
        }
        
        es.onerror = (err) => {
          console.error('SSE error:', err)
          es.close()
          setEventSource(null)
          setSending(false)
          setError('Connection to status stream lost')
        }
      } else {
        // Fallback for old API response format
        setEmailCount(response.data.sent)
        alert(`Successfully sent ${response.data.sent} email(s)!`)
        setSending(false)
      }
    } catch (err) {
      const errorMsg = err.response?.data?.detail || err.message || 'Failed to send emails'
      setError(errorMsg)
      alert(`Error: ${errorMsg}`)
      setSending(false)
      
      // Close SSE if open
      if (eventSource) {
        eventSource.close()
        setEventSource(null)
      }
    }
  }

  // Show email list view if selected
  if (currentView === 'list') {
    return (
      <div className="app">
        <div className="container">
          <div style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginBottom: '2rem',
            flexWrap: 'wrap',
            gap: '1rem'
          }}>
            <div>
              <h1 className="title">Bulk Email Sender</h1>
              <p className="subtitle">View and manage email recipients</p>
            </div>
            <button
              className="btn btn-primary"
              onClick={() => setCurrentView('send')}
            >
              ← Back to Send Emails
            </button>
          </div>
          <EmailListView />
        </div>
      </div>
    )
  }

  // Show inbox view if selected
  if (currentView === 'inbox') {
    const connectedProvider = googleConnected ? 'google' : 'outlook'
    const connectedEmail = googleConnected ? googleEmail : outlookEmail
    
    return (
      <div className="app">
        <div className="container">
          <div style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginBottom: '2rem',
            flexWrap: 'wrap',
            gap: '1rem'
          }}>
            <div>
              <h1 className="title">Bulk Email Sender</h1>
              <p className="subtitle">View inbox emails from connected account</p>
            </div>
            <button
              className="btn btn-primary"
              onClick={() => setCurrentView('send')}
            >
              ← Back to Send Emails
            </button>
          </div>
          <InboxView provider={connectedProvider} email={connectedEmail} />
        </div>
      </div>
    )
  }

  return (
    <div className="app">
      <div className="container">
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '1rem',
          flexWrap: 'wrap',
          gap: '1rem'
        }}>
          <div>
            <h1 className="title">Bulk Email Sender</h1>
            <p className="subtitle">Send emails to multiple recipients with ease</p>
          </div>
          <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
            <button
              className="btn btn-secondary"
              onClick={() => setCurrentView('list')}
            >
              📋 View Email List
            </button>
            {anyProviderConnected && (
              <button
                className="btn btn-secondary"
                onClick={() => setCurrentView('inbox')}
              >
                📬 View Inbox
              </button>
            )}
          </div>
        </div>

        <div className="card">
          <h2 className="card-title">Connect Your Account</h2>
          
          <div className="buttons-container">
            <button
              className={`btn ${googleConnected ? 'btn-success' : 'btn-primary'}`}
              onClick={handleConnectGoogle}
              disabled={isConnecting || sending}
            >
              {isGoogleConnecting ? (
                'Connecting...'
              ) : googleConnected ? (
                <>
                  <span className="btn-icon">✓</span>
                  Apply with Google
                </>
              ) : (
                <>
                  <span className="btn-icon">G</span>
                  Connect with Google
                </>
              )}
            </button>

            <button
              className={`btn ${outlookConnected ? 'btn-success' : 'btn-secondary'}`}
              onClick={handleConnectOutlook}
              disabled={isConnecting || sending}
            >
              {isOutlookConnecting ? (
                'Connecting...'
              ) : outlookConnected ? (
                <>
                  <span className="btn-icon">✓</span>
                  Connected to Outlook
                </>
              ) : (
                <>
                  <span className="btn-icon">O</span>
                  Connect with Outlook
                </>
              )}
            </button>
          </div>

          {googleEmail && (
            <div className="status-info">
              <p className="status-text">
                Connected as: <strong>{googleEmail}</strong>
              </p>
            </div>
          )}

          {outlookEmail && (
            <div className="status-info">
              <p className="status-text">
                Outlook account: <strong>{outlookEmail}</strong>
              </p>
            </div>
          )}

          {emailCount !== null && (
            <div className="status-info success">
              <p className="status-text">
                ✓ {emailCount} email(s) sent successfully!
              </p>
            </div>
          )}
        </div>

        {anyProviderConnected && (
          <div className="card">
            <h2 className="card-title">Send Emails</h2>
            
            <div className="form-group">
              <label>Send Using:</label>
              <div className="provider-options">
                <label
                  className={`provider-option ${selectedProvider === 'google' ? 'active' : ''} ${!googleConnected ? 'disabled' : ''}`}
                >
                  <div className="provider-option-header">
                    <input
                      type="radio"
                      name="provider"
                      value="google"
                      checked={selectedProvider === 'google'}
                      onChange={handleProviderChange}
                      disabled={!googleConnected || sending}
                    />
                    <span className="provider-name">Google</span>
                  </div>
                  <span className={`provider-status ${googleConnected ? 'connected' : ''}`}>
                    {googleConnected ? 'Connected' : 'Not connected'}
                  </span>
                </label>

                <label
                  className={`provider-option ${selectedProvider === 'outlook' ? 'active' : ''} ${!outlookConnected ? 'disabled' : ''}`}
                >
                  <div className="provider-option-header">
                    <input
                      type="radio"
                      name="provider"
                      value="outlook"
                      checked={selectedProvider === 'outlook'}
                      onChange={handleProviderChange}
                      disabled={!outlookConnected || sending}
                    />
                    <span className="provider-name">Outlook</span>
                  </div>
                  <span className={`provider-status ${outlookConnected ? 'connected' : ''}`}>
                    {outlookConnected ? 'Connected' : 'Not connected'}
                  </span>
                </label>
              </div>
            </div>

            <div className="form-group">
              <label htmlFor="senderName">Your Name:</label>
              <input
                id="senderName"
                type="text"
                value={senderName}
                onChange={(e) => setSenderName(e.target.value)}
                className="input"
                placeholder="Enter your name (e.g., Kyle)"
                disabled={sending}
                required
              />
            </div>

            <div className="form-group">
              <label>Email Range (Optional):</label>
              <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
                <div style={{ flex: 1 }}>
                  <label htmlFor="firstIndex" style={{ fontSize: '0.875rem', marginBottom: '0.25rem', display: 'block' }}>
                    First Index:
                  </label>
                  <input
                    id="firstIndex"
                    type="number"
                    value={firstIndex}
                    onChange={(e) => setFirstIndex(e.target.value)}
                    className="input"
                    placeholder="e.g., 1"
                    min="1"
                    disabled={sending}
                  />
                </div>
                <span style={{ marginTop: '1.5rem' }}>to</span>
                <div style={{ flex: 1 }}>
                  <label htmlFor="lastIndex" style={{ fontSize: '0.875rem', marginBottom: '0.25rem', display: 'block' }}>
                    Last Index:
                  </label>
                  <input
                    id="lastIndex"
                    type="number"
                    value={lastIndex}
                    onChange={(e) => setLastIndex(e.target.value)}
                    className="input"
                    placeholder="e.g., 100"
                    min="1"
                    disabled={sending}
                  />
                </div>
              </div>
              <p className="info-text" style={{ marginTop: '0.5rem', fontSize: '0.875rem' }}>
                Leave empty to send to all emails. Specify range to send only to emails within the index range.
              </p>
            </div>

            <div className="form-group">
              <label htmlFor="resume">Upload Resume (Optional):</label>
              <input
                id="resume"
                type="file"
                accept=".pdf,.doc,.docx"
                onChange={(e) => setSelectedResumeFile(e.target.files?.[0] || null)}
                className="input"
                disabled={sending}
              />
              {selectedResumeFile && (
                <p className="info-text" style={{ marginTop: '0.5rem', fontSize: '0.875rem', color: '#059669' }}>
                  ✓ Selected: {selectedResumeFile.name} ({(selectedResumeFile.size / 1024).toFixed(1)} KB)
                </p>
              )}
            </div>

            <button
              className="btn btn-primary btn-large"
              onClick={handleSendBulkEmails}
              disabled={sending || !senderName.trim() || !selectedProviderConnected}
            >
              {sending ? (
                <>
                  <span className="spinner"></span>
                  Sending Emails...
                </>
              ) : (
                <>
                  <span className="btn-icon">📧</span>
                  Send Bulk Emails
                </>
              )}
            </button>

            {emailStatus && emailStatus.targets.length > 0 && (
              <div className="card" style={{ marginTop: '1.5rem' }}>
                <h3 className="card-title" style={{ marginBottom: '1rem' }}>
                  Sending Status
                  {emailStatus.total && (
                    <span style={{ fontSize: '0.875rem', fontWeight: 'normal', marginLeft: '0.5rem', color: '#666' }}>
                      ({emailStatus.sent || 0} sent, {emailStatus.failed || 0} failed, {emailStatus.total} total)
                    </span>
                  )}
                </h3>
                <div style={{ 
                  maxHeight: '400px', 
                  overflowY: 'auto', 
                  border: '1px solid #e5e7eb', 
                  borderRadius: '0.5rem',
                  padding: '0.5rem'
                }}>
                  {emailStatus.targets.map((target, index) => (
                    <div
                      key={index}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        padding: '0.75rem',
                        marginBottom: '0.25rem',
                        borderRadius: '0.25rem',
                        backgroundColor: 
                          target.status === 'sent' ? '#d1fae5' :
                          target.status === 'failed' ? '#fee2e2' :
                          '#f3f4f6',
                        borderLeft: `4px solid ${
                          target.status === 'sent' ? '#10b981' :
                          target.status === 'failed' ? '#ef4444' :
                          '#9ca3af'
                        }`
                      }}
                    >
                      <span style={{ 
                        marginRight: '0.75rem',
                        fontSize: '1.25rem'
                      }}>
                        {target.status === 'sent' ? '✓' : target.status === 'failed' ? '✗' : '○'}
                      </span>
                      <div style={{ flex: 1 }}>
                        <div style={{ 
                          fontWeight: '500',
                          color: target.status === 'sent' ? '#065f46' : target.status === 'failed' ? '#991b1b' : '#374151'
                        }}>
                          {target.email}
                        </div>
                        {target.error && (
                          <div style={{ 
                            fontSize: '0.75rem', 
                            color: '#991b1b', 
                            marginTop: '0.25rem' 
                          }}>
                            {target.error}
                          </div>
                        )}
                      </div>
                      <span style={{
                        fontSize: '0.75rem',
                        fontWeight: '500',
                        color: 
                          target.status === 'sent' ? '#059669' :
                          target.status === 'failed' ? '#dc2626' :
                          '#6b7280',
                        textTransform: 'uppercase'
                      }}>
                        {target.status}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <p className="info-text">
              Emails will be sent via {selectedProvider === 'google' ? 'Google' : 'Outlook'} using targets from email_targets.json. Each email will use a randomly selected template from available templates.
            </p>
          </div>
        )}

        {error && (
          <div className="card error-card">
            <p className="error-text">⚠️ {error}</p>
          </div>
        )}
      </div>
    </div>
  )
}

export default App

