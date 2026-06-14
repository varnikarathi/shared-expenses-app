import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import API from '../api';

export default function ImportCSV() {
  const [groups, setGroups] = useState([]);
  const [groupId, setGroupId] = useState('');
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [report, setReport] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    API.get('/groups/').then(res => setGroups(res.data)).catch(console.error);
  }, []);

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
    } catch (err) {
      setError(JSON.stringify(err.response?.data) || 'Import failed');
    } finally {
      setLoading(false);
    }
  };

  const getActionClass = (action) => {
    if (action === 'auto_fixed') return 'anomaly-auto_fixed';
    if (action === 'skipped') return 'anomaly-skipped';
    if (action === 'requires_approval') return 'anomaly-requires_approval';
    return '';
  };

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
          <h1>Import Expenses CSV</h1>
        </div>

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
              <div style={{ marginBottom: '0.5rem', fontSize: '0.82rem', color: '#888', display: 'flex', gap: '1rem' }}>
                <span style={{ color: '#4caf50' }}>● Auto Fixed</span>
                <span style={{ color: '#ff9800' }}>● Skipped</span>
                <span style={{ color: '#e91e63' }}>● Needs Approval</span>
              </div>
              {report.anomalies.map((a, i) => (
                <div key={i} className={`anomaly-item ${getActionClass(a.action)}`}>
                  <strong>Row {a.row} [{a.type}]</strong> — {a.description}
                  <br />
                  <span style={{ color: '#555' }}>Action: {a.resolution}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}