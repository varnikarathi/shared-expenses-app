import React, { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import API from '../api';

export default function ImportCSV() {
  const [groups, setGroups] = useState([]);
  const [groupId, setGroupId] = useState('');
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [report, setReport] = useState(null);
  const [error, setError] = useState('');

  // Past sessions (Meera's approval workflow)
  const [sessions, setSessions] = useState([]);
  const [selectedSession, setSelectedSession] = useState(null);
  const [sessionAnomalies, setSessionAnomalies] = useState([]);
  const [sessionLoading, setSessionLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('import'); // 'import' | 'sessions'

  useEffect(() => {
    API.get('/groups/').then(res => setGroups(res.data)).catch(console.error);
    fetchSessions();
  }, []);

  const fetchSessions = async () => {
    try {
      const res = await API.get('/import/sessions/');
      setSessions(Array.isArray(res.data) ? res.data : []);
    } catch (err) {
      console.error(err);
    }
  };

  const handleImport = async (e) => {
    e.preventDefault();
    if (!file || !groupId) {
      setError('Please select a group and a CSV file');
      return;
    }
    setLoading(true);
    setError('');
    setReport(null);

    const formData = new FormData();
    formData.append('file', file);
    formData.append('group_id', groupId);

    try {
      const res = await API.post('/import/', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      setReport(res.data);
      fetchSessions(); // refresh past sessions list
    } catch (err) {
      setError(JSON.stringify(err.response?.data) || 'Import failed');
    } finally {
      setLoading(false);
    }
  };

  const openSession = useCallback(async (sessionId) => {
    if (selectedSession === sessionId) {
      setSelectedSession(null);
      setSessionAnomalies([]);
      return;
    }
    setSelectedSession(sessionId);
    setSessionLoading(true);
    try {
      const res = await API.get(`/import/report/${sessionId}/`);
      setSessionAnomalies(res.data.anomalies || []);
    } catch (err) {
      console.error(err);
    } finally {
      setSessionLoading(false);
    }
  }, [selectedSession]);

  const approveAnomaly = async (anomalyId, sessionId) => {
    try {
      await API.post(`/import/anomaly/${anomalyId}/approve/`);
      // Refresh anomalies for this session
      const res = await API.get(`/import/report/${sessionId}/`);
      setSessionAnomalies(res.data.anomalies || []);
      fetchSessions();
      // Also refresh current report if it's the same session
      if (report && report.session_id === sessionId) {
        setReport(prev => ({
          ...prev,
          anomalies: res.data.anomalies
        }));
      }
    } catch (err) {
      alert(err.response?.data?.error || 'Approval failed');
    }
  };

  const rejectAnomaly = async (anomalyId, sessionId) => {
    if (!window.confirm('Reject this anomaly? The row will be permanently discarded.')) return;
    try {
      await API.post(`/import/anomaly/${anomalyId}/reject/`);
      const res = await API.get(`/import/report/${sessionId}/`);
      setSessionAnomalies(res.data.anomalies || []);
      fetchSessions();
    } catch (err) {
      alert('Rejection failed');
    }
  };

  const getActionClass = (action) => {
    if (action === 'auto_fixed') return 'anomaly-auto_fixed';
    if (action === 'skipped') return 'anomaly-skipped';
    if (action === 'requires_approval') return 'anomaly-requires_approval';
    if (action === 'rejected') return 'anomaly-skipped';
    return '';
  };

  const renderAnomalyList = (anomalies, sessionId) => (
    <>
      <div style={{ marginBottom: '0.5rem', fontSize: '0.82rem', color: '#888', display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
        <span style={{ color: '#4caf50' }}>● Auto Fixed</span>
        <span style={{ color: '#ff9800' }}>● Skipped</span>
        <span style={{ color: '#e91e63' }}>● Needs Approval</span>
      </div>
      {anomalies.map((a, i) => (
        <div key={i} className={`anomaly-item ${getActionClass(a.action)}`}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '1rem' }}>
            <div style={{ flex: 1 }}>
              <strong>Row {a.row} [{a.type}]</strong> — {a.description}
              <br />
              <span style={{ color: '#555' }}>Action: {a.resolution}</span>
            </div>
            {/* Meera's requirement: approve/reject buttons for flagged rows */}
            {a.action === 'requires_approval' && sessionId && (
              <div style={{ display: 'flex', gap: '0.5rem', flexShrink: 0 }}>
                <button
                  className="btn btn-primary"
                  style={{ fontSize: '0.75rem', padding: '0.3rem 0.7rem' }}
                  onClick={() => approveAnomaly(a.id || i, sessionId)}
                >
                  ✓ Approve
                </button>
                <button
                  className="btn btn-danger"
                  style={{ fontSize: '0.75rem', padding: '0.3rem 0.7rem' }}
                  onClick={() => rejectAnomaly(a.id || i, sessionId)}
                >
                  ✕ Reject
                </button>
              </div>
            )}
            {a.action === 'auto_fixed' && a.approved_by && (
              <span style={{ fontSize: '0.75rem', color: '#4caf50' }}>✓ Approved by {a.approved_by}</span>
            )}
            {a.action === 'rejected' && (
              <span style={{ fontSize: '0.75rem', color: '#888' }}>✕ Rejected</span>
            )}
          </div>
        </div>
      ))}
    </>
  );

  return (
    <div>
      <nav className="navbar">
        <Link to="/" className="navbar-brand">💸 SplitApp</Link>
        <div className="navbar-links">
          <Link to="/">← Dashboard</Link>
        </div>
      </nav>

      <div className="container">
        <div className="page-header">
          <h1>CSV Import</h1>
        </div>

        {/* Tab bar */}
        <div className="tab-bar">
          <button className={`tab ${activeTab === 'import' ? 'active' : ''}`} onClick={() => setActiveTab('import')}>
            Import New CSV
          </button>
          <button className={`tab ${activeTab === 'sessions' ? 'active' : ''}`} onClick={() => setActiveTab('sessions')}>
            Past Imports {sessions.some(s => s.pending_approvals > 0) && (
              <span style={{ marginLeft: '0.4rem', background: '#e91e63', color: '#fff', borderRadius: '10px', padding: '0.1rem 0.5rem', fontSize: '0.72rem' }}>
                {sessions.reduce((acc, s) => acc + s.pending_approvals, 0)} pending
              </span>
            )}
          </button>
        </div>

        {activeTab === 'import' && (
          <>
            <div className="card">
              <h3 style={{ marginBottom: '1rem' }}>Upload expenses_export.csv</h3>
              {error && <div className="error-msg">{error}</div>}
              <form onSubmit={handleImport}>
                <div className="form-group">
                  <label>Select Group</label>
                  <select value={groupId} onChange={e => setGroupId(e.target.value)} required>
                    <option value="">Choose a group...</option>
                    {groups.map(g => <option key={g.id} value={g.id}>{g.name}</option>)}
                  </select>
                </div>
                <div className="form-group">
                  <label>CSV File</label>
                  <input
                    type="file"
                    accept=".csv"
                    onChange={e => setFile(e.target.files[0])}
                    required
                  />
                </div>
                <button className="btn btn-primary" disabled={loading}>
                  {loading ? 'Importing...' : 'Import CSV'}
                </button>
              </form>
            </div>

            {report && (
              <div>
                <div className="card">
                  <h3 style={{ marginBottom: '1rem' }}>Import Report</h3>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '1rem', marginBottom: '1.5rem' }}>
                    <div style={{ textAlign: 'center', padding: '1rem', background: '#f8f9fa', borderRadius: '8px' }}>
                      <div style={{ fontSize: '2rem', fontWeight: '800', color: '#1a1a2e' }}>{report.total_rows}</div>
                      <div style={{ color: '#888', fontSize: '0.85rem' }}>Total Rows</div>
                    </div>
                    <div style={{ textAlign: 'center', padding: '1rem', background: '#e8f5e9', borderRadius: '8px' }}>
                      <div style={{ fontSize: '2rem', fontWeight: '800', color: '#2e7d32' }}>{report.imported}</div>
                      <div style={{ color: '#888', fontSize: '0.85rem' }}>Imported</div>
                    </div>
                    <div style={{ textAlign: 'center', padding: '1rem', background: '#fff3e0', borderRadius: '8px' }}>
                      <div style={{ fontSize: '2rem', fontWeight: '800', color: '#e65100' }}>{report.skipped}</div>
                      <div style={{ color: '#888', fontSize: '0.85rem' }}>Skipped</div>
                    </div>
                    <div style={{ textAlign: 'center', padding: '1rem', background: '#fce4ec', borderRadius: '8px' }}>
                      <div style={{ fontSize: '2rem', fontWeight: '800', color: '#c62828' }}>{report.anomaly_count}</div>
                      <div style={{ color: '#888', fontSize: '0.85rem' }}>Anomalies</div>
                    </div>
                  </div>

                  <h4 style={{ marginBottom: '1rem' }}>Anomaly Log</h4>
                  {renderAnomalyList(report.anomalies, report.session_id)}
                </div>
              </div>
            )}
          </>
        )}

        {activeTab === 'sessions' && (
          <div className="card">
            <h3 style={{ marginBottom: '1rem' }}>Past Import Sessions</h3>
            {sessions.length === 0 ? (
              <div className="empty-state"><p>No imports yet</p></div>
            ) : (
              sessions.map(s => (
                <div key={s.id}>
                  <div
                    style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '0.8rem 0', borderBottom: '1px solid #f0f0f0', cursor: 'pointer' }}
                    onClick={() => openSession(s.id)}
                  >
                    <div>
                      <div style={{ fontWeight: 600 }}>{s.filename}</div>
                      <div style={{ fontSize: '0.82rem', color: '#888' }}>
                        {new Date(s.imported_at).toLocaleString('en-IN')} · {s.imported_rows}/{s.total_rows} rows imported
                      </div>
                    </div>
                    <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                      {s.pending_approvals > 0 && (
                        <span style={{ background: '#fce4ec', color: '#c62828', borderRadius: '12px', padding: '0.2rem 0.7rem', fontSize: '0.8rem', fontWeight: 600 }}>
                          {s.pending_approvals} need approval
                        </span>
                      )}
                      <span style={{ color: '#00d4aa', fontSize: '0.85rem' }}>
                        {selectedSession === s.id ? '▲' : '▼'}
                      </span>
                    </div>
                  </div>

                  {selectedSession === s.id && (
                    <div style={{ padding: '1rem 0' }}>
                      {sessionLoading ? (
                        <p style={{ color: '#888' }}>Loading anomalies...</p>
                      ) : sessionAnomalies.length === 0 ? (
                        <p style={{ color: '#888' }}>No anomalies logged for this session.</p>
                      ) : (
                        renderAnomalyList(sessionAnomalies, s.id)
                      )}
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
        )}
      </div>
    </div>
  );
}