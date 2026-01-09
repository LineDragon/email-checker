import { useState, useEffect } from 'react'
import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

function EmailListView() {
  const [emailTargets, setEmailTargets] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [searchTerm, setSearchTerm] = useState('')
  const [currentPage, setCurrentPage] = useState(1)
  const [pagination, setPagination] = useState(null)
  const [stats, setStats] = useState(null)
  const pageSize = 50

  useEffect(() => {
    loadStats()
  }, [])

  useEffect(() => {
    loadEmailTargets()
  }, [currentPage, searchTerm])

  const loadStats = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/api/email/targets/stats`)
      setStats(response.data)
    } catch (err) {
      console.error('Error loading stats:', err)
    }
  }

  const loadEmailTargets = async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await axios.get(`${API_BASE_URL}/api/email/targets`, {
        params: {
          page: currentPage,
          page_size: pageSize,
          search: searchTerm || undefined
        }
      })
      setEmailTargets(response.data.targets)
      setPagination(response.data.pagination)
    } catch (err) {
      setError('Failed to load email targets: ' + (err.response?.data?.detail || err.message))
    } finally {
      setLoading(false)
    }
  }

  const handleSearch = (e) => {
    setSearchTerm(e.target.value)
    setCurrentPage(1) // Reset to first page on search
  }

  const handlePageChange = (newPage) => {
    setCurrentPage(newPage)
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  return (
    <div className="email-list-view">
      <div className="container">
        <h1 className="title">Email Targets</h1>
        <p className="subtitle">View and search all email recipients</p>

        {stats && (
          <div className="stats-card" style={{
            backgroundColor: '#f3f4f6',
            padding: '1rem',
            borderRadius: '0.5rem',
            marginBottom: '1.5rem',
            display: 'flex',
            gap: '2rem',
            flexWrap: 'wrap'
          }}>
            <div>
              <strong>Total Emails:</strong> {stats.total.toLocaleString()}
            </div>
            <div>
              <strong>With Names:</strong> {stats.has_name.toLocaleString()}
            </div>
            <div>
              <strong>With Index:</strong> {stats.has_index.toLocaleString()}
            </div>
          </div>
        )}

        <div className="card" style={{ marginBottom: '1.5rem' }}>
          <div style={{ display: 'flex', gap: '1rem', alignItems: 'center', flexWrap: 'wrap' }}>
            <input
              type="text"
              placeholder="Search by email or name..."
              value={searchTerm}
              onChange={handleSearch}
              className="input"
              style={{ flex: 1, minWidth: '200px' }}
            />
            {searchTerm && (
              <button
                onClick={() => setSearchTerm('')}
                className="btn btn-secondary"
                style={{ padding: '0.5rem 1rem' }}
              >
                Clear
              </button>
            )}
          </div>
        </div>

        {error && (
          <div className="card error-card">
            <p className="error-text">⚠️ {error}</p>
          </div>
        )}

        {loading ? (
          <div className="card">
            <div style={{ textAlign: 'center', padding: '2rem' }}>
              <div className="spinner"></div>
              <p style={{ marginTop: '1rem' }}>Loading email targets...</p>
            </div>
          </div>
        ) : emailTargets.length === 0 ? (
          <div className="card">
            <p style={{ textAlign: 'center', padding: '2rem', color: '#666' }}>
              {searchTerm ? 'No email targets found matching your search.' : 'No email targets found.'}
            </p>
          </div>
        ) : (
          <>
            <div className="card" style={{ overflowX: 'auto' }}>
              <div style={{ minWidth: '600px' }}>
                <table style={{
                  width: '100%',
                  borderCollapse: 'collapse'
                }}>
                  <thead>
                    <tr style={{
                      backgroundColor: '#f9fafb',
                      borderBottom: '2px solid #e5e7eb'
                    }}>
                      <th style={{
                        padding: '0.75rem',
                        textAlign: 'left',
                        fontWeight: '600',
                        color: '#374151'
                      }}>Index</th>
                      <th style={{
                        padding: '0.75rem',
                        textAlign: 'left',
                        fontWeight: '600',
                        color: '#374151'
                      }}>Name</th>
                      <th style={{
                        padding: '0.75rem',
                        textAlign: 'left',
                        fontWeight: '600',
                        color: '#374151'
                      }}>Email</th>
                    </tr>
                  </thead>
                  <tbody>
                    {emailTargets.map((target, index) => (
                      <tr
                        key={target.index || index}
                        style={{
                          borderBottom: '1px solid #e5e7eb',
                          transition: 'background-color 0.2s'
                        }}
                        onMouseEnter={(e) => e.currentTarget.style.backgroundColor = '#f9fafb'}
                        onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'transparent'}
                      >
                        <td style={{ padding: '0.75rem', color: '#6b7280' }}>
                          {target.index || '-'}
                        </td>
                        <td style={{ padding: '0.75rem', fontWeight: '500' }}>
                          {target.name || '-'}
                        </td>
                        <td style={{ padding: '0.75rem' }}>
                          <a
                            href={`mailto:${target.target_email}`}
                            style={{
                              color: '#3b82f6',
                              textDecoration: 'none'
                            }}
                            onMouseEnter={(e) => e.currentTarget.style.textDecoration = 'underline'}
                            onMouseLeave={(e) => e.currentTarget.style.textDecoration = 'none'}
                          >
                            {target.target_email}
                          </a>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {pagination && pagination.total_pages > 1 && (
              <div className="card" style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                flexWrap: 'wrap',
                gap: '1rem'
              }}>
                <div style={{ color: '#6b7280' }}>
                  Showing {((currentPage - 1) * pageSize) + 1} to {Math.min(currentPage * pageSize, pagination.total)} of {pagination.total.toLocaleString()} emails
                </div>
                <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                  <button
                    className="btn btn-secondary"
                    onClick={() => handlePageChange(currentPage - 1)}
                    disabled={currentPage === 1}
                    style={{
                      padding: '0.5rem 1rem',
                      opacity: currentPage === 1 ? 0.5 : 1,
                      cursor: currentPage === 1 ? 'not-allowed' : 'pointer'
                    }}
                  >
                    Previous
                  </button>
                  <span style={{
                    padding: '0.5rem 1rem',
                    backgroundColor: '#f3f4f6',
                    borderRadius: '0.25rem',
                    fontWeight: '500'
                  }}>
                    Page {currentPage} of {pagination.total_pages}
                  </span>
                  <button
                    className="btn btn-secondary"
                    onClick={() => handlePageChange(currentPage + 1)}
                    disabled={currentPage === pagination.total_pages}
                    style={{
                      padding: '0.5rem 1rem',
                      opacity: currentPage === pagination.total_pages ? 0.5 : 1,
                      cursor: currentPage === pagination.total_pages ? 'not-allowed' : 'pointer'
                    }}
                  >
                    Next
                  </button>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}

export default EmailListView
