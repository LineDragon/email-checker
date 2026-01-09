import { useState, useEffect } from 'react'
import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

function InboxView({ provider, email }) {
  const [emails, setEmails] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [selectedEmail, setSelectedEmail] = useState(null)
  const [nextPageToken, setNextPageToken] = useState(null)
  const [hasMore, setHasMore] = useState(false)
  const [totalCount, setTotalCount] = useState(0)

  useEffect(() => {
    loadEmails()
  }, [provider])

  const loadEmails = async (pageToken = null) => {
    setLoading(true)
    setError(null)
    try {
      const endpoint = provider === 'google' 
        ? `${API_BASE_URL}/api/google/inbox`
        : `${API_BASE_URL}/api/outlook/inbox`
      
      const params = provider === 'google' 
        ? { max_results: 50, ...(pageToken && { page_token: pageToken }) }
        : { max_results: 50, skip: pageToken ? emails.length : 0 }
      
      const response = await axios.get(endpoint, { params })
      
      if (pageToken) {
        setEmails(prev => [...prev, ...response.data.emails])
      } else {
        setEmails(response.data.emails)
        setTotalCount(response.data.total || response.data.emails.length)
      }
      
      setNextPageToken(response.data.next_page_token || null)
      setHasMore(response.data.has_more || false)
    } catch (err) {
      setError('Failed to load emails: ' + (err.response?.data?.detail || err.message))
    } finally {
      setLoading(false)
    }
  }

  const formatDate = (dateString) => {
    if (!dateString) return 'Unknown date'
    try {
      const date = new Date(dateString)
      const now = new Date()
      const diffMs = now - date
      const diffMins = Math.floor(diffMs / 60000)
      const diffHours = Math.floor(diffMs / 3600000)
      const diffDays = Math.floor(diffMs / 86400000)
      
      if (diffMins < 1) return 'Just now'
      if (diffMins < 60) return `${diffMins}m ago`
      if (diffHours < 24) return `${diffHours}h ago`
      if (diffDays < 7) return `${diffDays}d ago`
      
      return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: date.getFullYear() !== now.getFullYear() ? 'numeric' : undefined })
    } catch {
      return dateString
    }
  }

  const stripHtmlTags = (html) => {
    if (!html) return ''
    // Create a temporary div element
    const tmp = document.createElement('div')
    tmp.innerHTML = html
    // Get text content and clean up
    let text = tmp.textContent || tmp.innerText || ''
    // Clean up extra whitespace
    text = text.replace(/\s+/g, ' ').replace(/\n\s*\n/g, '\n\n').trim()
    return text
  }

  const formatBody = (body) => {
    if (!body) return 'No content available'
    // Strip HTML tags if present
    let cleanBody = stripHtmlTags(body)
    // Convert \n to line breaks and preserve formatting
    return cleanBody.split('\n').map((line, index) => (
      <span key={index}>
        {line}
        {index < cleanBody.split('\n').length - 1 && <br />}
      </span>
    ))
  }

  const extractSenderName = (fromString) => {
    if (!fromString) return 'Unknown'
    // Extract name from "Name <email@example.com>" format
    const match = fromString.match(/^(.+?)\s*<(.+)>$/)
    if (match) {
      return match[1].replace(/['"]/g, '')
    }
    return fromString
  }

  const extractSenderEmail = (fromString) => {
    if (!fromString) return 'Unknown'
    // Extract email from "Name <email@example.com>" format
    const match = fromString.match(/<(.+)>$/)
    if (match) {
      return match[1]
    }
    return fromString
  }

  return (
    <div className="inbox-view">
      <div className="container">
        {/* Header with total count */}
        <div className="card" style={{
          marginBottom: '1.5rem',
          backgroundColor: '#f8fafc',
          border: '1px solid #e2e8f0'
        }}>
          <div style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            flexWrap: 'wrap',
            gap: '1rem'
          }}>
            <div>
              <h2 style={{
                margin: '0 0 0.25rem 0',
                color: '#1e293b',
                fontSize: '1.5rem',
                fontWeight: '600'
              }}>
                Inbox
              </h2>
              <p style={{
                margin: 0,
                color: '#64748b',
                fontSize: '0.875rem'
              }}>
                {email}
              </p>
            </div>
            <div style={{
              textAlign: 'right'
            }}>
              <div style={{
                fontSize: '2rem',
                fontWeight: '700',
                color: '#3b82f6',
                lineHeight: '1'
              }}>
                {totalCount > 0 ? totalCount.toLocaleString() : emails.length}
              </div>
              <div style={{
                fontSize: '0.875rem',
                color: '#64748b',
                marginTop: '0.25rem'
              }}>
                Email{totalCount !== 1 ? 's' : ''} Total
              </div>
            </div>
          </div>
        </div>

        {error && (
          <div className="card error-card" style={{ marginBottom: '1.5rem' }}>
            <p className="error-text">⚠️ {error}</p>
          </div>
        )}

        {loading && emails.length === 0 ? (
          <div className="card">
            <div style={{ textAlign: 'center', padding: '3rem' }}>
              <div className="spinner"></div>
              <p style={{ marginTop: '1rem', color: '#64748b' }}>Loading emails...</p>
            </div>
          </div>
        ) : emails.length === 0 ? (
          <div className="card">
            <p style={{ textAlign: 'center', padding: '3rem', color: '#64748b' }}>
              No emails found in inbox.
            </p>
          </div>
        ) : (
          <>
            {/* Professional email list */}
            <div style={{
              display: 'flex',
              flexDirection: 'column',
              gap: '0.5rem'
            }}>
              {emails.map((emailItem, index) => {
                const senderName = extractSenderName(emailItem.from)
                const senderEmail = extractSenderEmail(emailItem.from)
                const isSelected = selectedEmail === index
                
                return (
                  <div
                    key={emailItem.id || index}
                    style={{
                      backgroundColor: isSelected ? '#ffffff' : '#ffffff',
                      border: isSelected ? '2px solid #3b82f6' : '1px solid #e2e8f0',
                      borderRadius: '0.5rem',
                      padding: isSelected ? '1.5rem' : '1rem',
                      cursor: 'pointer',
                      transition: 'all 0.2s ease',
                      boxShadow: isSelected ? '0 4px 6px -1px rgba(0, 0, 0, 0.1)' : '0 1px 2px 0 rgba(0, 0, 0, 0.05)'
                    }}
                    onClick={() => setSelectedEmail(isSelected ? null : index)}
                    onMouseEnter={(e) => {
                      if (!isSelected) {
                        e.currentTarget.style.borderColor = '#cbd5e1'
                        e.currentTarget.style.boxShadow = '0 2px 4px 0 rgba(0, 0, 0, 0.1)'
                      }
                    }}
                    onMouseLeave={(e) => {
                      if (!isSelected) {
                        e.currentTarget.style.borderColor = '#e2e8f0'
                        e.currentTarget.style.boxShadow = '0 1px 2px 0 rgba(0, 0, 0, 0.05)'
                      }
                    }}
                  >
                    {isSelected ? (
                      // Expanded view
                      <div>
                        <div style={{
                          display: 'flex',
                          justifyContent: 'space-between',
                          alignItems: 'flex-start',
                          marginBottom: '1.5rem',
                          paddingBottom: '1.5rem',
                          borderBottom: '2px solid #e2e8f0'
                        }}>
                          <div style={{ flex: 1 }}>
                            <h3 style={{
                              margin: '0 0 1rem 0',
                              color: '#1e293b',
                              fontSize: '1.5rem',
                              fontWeight: '600',
                              lineHeight: '1.3'
                            }}>
                              {emailItem.subject || '(No Subject)'}
                            </h3>
                            <div style={{
                              display: 'flex',
                              flexDirection: 'column',
                              gap: '0.5rem'
                            }}>
                              <div style={{
                                color: '#475569',
                                fontSize: '0.9375rem'
                              }}>
                                <strong style={{ color: '#334155' }}>From:</strong> {senderName}
                                {senderEmail !== senderName && (
                                  <span style={{ color: '#64748b' }}> &lt;{senderEmail}&gt;</span>
                                )}
                              </div>
                              <div style={{
                                color: '#64748b',
                                fontSize: '0.875rem'
                              }}>
                                <strong>Date:</strong> {formatDate(emailItem.date)}
                              </div>
                            </div>
                          </div>
                          <button
                            onClick={(e) => {
                              e.stopPropagation()
                              setSelectedEmail(null)
                            }}
                            style={{
                              background: '#f1f5f9',
                              border: '1px solid #e2e8f0',
                              borderRadius: '0.375rem',
                              width: '2rem',
                              height: '2rem',
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'center',
                              cursor: 'pointer',
                              color: '#64748b',
                              fontSize: '1.25rem',
                              flexShrink: 0
                            }}
                            onMouseEnter={(e) => {
                              e.currentTarget.style.backgroundColor = '#e2e8f0'
                              e.currentTarget.style.color = '#475569'
                            }}
                            onMouseLeave={(e) => {
                              e.currentTarget.style.backgroundColor = '#f1f5f9'
                              e.currentTarget.style.color = '#64748b'
                            }}
                          >
                            ✕
                          </button>
                        </div>
                        <div style={{
                          backgroundColor: '#f8fafc',
                          padding: '1.5rem',
                          borderRadius: '0.5rem',
                          border: '1px solid #e2e8f0',
                          whiteSpace: 'pre-wrap',
                          lineHeight: '1.8',
                          color: '#334155',
                          fontSize: '0.9375rem',
                          maxHeight: '600px',
                          overflowY: 'auto',
                          fontFamily: 'system-ui, -apple-system, "Segoe UI", sans-serif'
                        }}>
                          {formatBody(emailItem.full_body || emailItem.body || emailItem.snippet)}
                        </div>
                      </div>
                    ) : (
                      // Collapsed list view
                      <div style={{
                        display: 'grid',
                        gridTemplateColumns: 'auto 1fr auto',
                        gap: '1rem',
                        alignItems: 'center'
                      }}>
                        <div style={{
                          width: '3rem',
                          height: '3rem',
                          borderRadius: '50%',
                          backgroundColor: '#3b82f6',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          color: 'white',
                          fontWeight: '600',
                          fontSize: '1rem',
                          flexShrink: 0
                        }}>
                          {senderName.charAt(0).toUpperCase()}
                        </div>
                        <div style={{ flex: 1, minWidth: 0 }}>
                          <div style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '0.75rem',
                            marginBottom: '0.25rem',
                            flexWrap: 'wrap'
                          }}>
                            <h3 style={{
                              margin: 0,
                              color: '#1e293b',
                              fontSize: '1rem',
                              fontWeight: '600',
                              overflow: 'hidden',
                              textOverflow: 'ellipsis',
                              whiteSpace: 'nowrap',
                              flex: 1,
                              minWidth: '200px'
                            }}>
                              {emailItem.subject || '(No Subject)'}
                            </h3>
                            <div style={{
                              color: '#64748b',
                              fontSize: '0.8125rem',
                              whiteSpace: 'nowrap',
                              flexShrink: 0
                            }}>
                              {formatDate(emailItem.date)}
                            </div>
                          </div>
                          <div style={{
                            color: '#475569',
                            fontSize: '0.875rem',
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                            whiteSpace: 'nowrap'
                          }}>
                            {senderName}
                            {senderEmail !== senderName && (
                              <span style={{ color: '#94a3b8' }}> • {senderEmail}</span>
                            )}
                          </div>
                        </div>
                        <div style={{
                          color: '#cbd5e1',
                          fontSize: '1.25rem',
                          flexShrink: 0
                        }}>
                          ▶
                        </div>
                      </div>
                    )}
                  </div>
                )
              })}
            </div>

            {(nextPageToken || hasMore) && (
              <div className="card" style={{
                textAlign: 'center',
                marginTop: '1.5rem',
                backgroundColor: '#f8fafc'
              }}>
                <button
                  className="btn btn-primary"
                  onClick={() => loadEmails(nextPageToken)}
                  disabled={loading}
                  style={{
                    minWidth: '200px'
                  }}
                >
                  {loading ? 'Loading...' : `Load More (${emails.length} of ${totalCount || '?'})`}
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}

export default InboxView
