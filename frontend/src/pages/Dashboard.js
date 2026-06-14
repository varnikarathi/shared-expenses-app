import React, { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import API from '../api';

export default function Dashboard() {
  const [groups, setGroups] = useState([]);
  const [users, setUsers] = useState([]);
  const [showModal, setShowModal] = useState(false);
  const [form, setForm] = useState({ name: '', description: '' });
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();
  const user = JSON.parse(localStorage.getItem('user') || '{}');

  useEffect(() => {
    fetchGroups();
    fetchUsers();
  }, []);

  const fetchGroups = async () => {
    try {
      const res = await API.get('/groups/');
      setGroups(res.data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const fetchUsers = async () => {
    try {
      const res = await API.get('/users/list/');
      setUsers(res.data);
    } catch (err) {
      console.error(err);
    }
  };

  const createGroup = async (e) => {
    e.preventDefault();
    try {
      await API.post('/groups/', form);
      setShowModal(false);
      setForm({ name: '', description: '' });
      fetchGroups();
    } catch (err) {
      console.error(err);
    }
  };

  const logout = () => {
    localStorage.clear();
    navigate('/login');
  };

  return (
    <div>
      <nav className="navbar">
        <Link to="/" className="navbar-brand">💸 SplitApp</Link>
        <div className="navbar-links">
          <span style={{ color: '#aaa', fontSize: '0.9rem' }}>Hi, {user.username}</span>
          <Link to="/import">Import CSV</Link>
          <button onClick={logout}>Logout</button>
        </div>
      </nav>

      <div className="container">
        <div className="page-header">
          <h1>My Groups</h1>
          <button className="btn btn-primary" onClick={() => setShowModal(true)}>
            + New Group
          </button>
        </div>

        {loading ? (
          <div className="loading">Loading groups...</div>
        ) : groups.length === 0 ? (
          <div className="empty-state">
            <h3>No groups yet</h3>
            <p>Create a group to start splitting expenses</p>
          </div>
        ) : (
          <div className="grid-2">
            {groups.map(group => (
              <div
                key={group.id}
                className="group-card"
                onClick={() => navigate(`/group/${group.id}`)}
              >
                <h3>{group.name}</h3>
                <p>{group.description || 'No description'}</p>
                <p style={{ marginTop: '0.5rem', fontSize: '0.82rem', color: '#00d4aa' }}>
                  {group.member_count} member{group.member_count !== 1 ? 's' : ''}
                </p>
              </div>
            ))}
          </div>
        )}
      </div>

      {showModal && (
        <div className="modal-overlay" onClick={() => setShowModal(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <h3>Create New Group</h3>
            <form onSubmit={createGroup}>
              <div className="form-group">
                <label>Group Name</label>
                <input
                  type="text"
                  placeholder="Group Name"
                  value={form.name}
                  onChange={e => setForm({ ...form, name: e.target.value })}
                  required
                />
              </div>
              <div className="form-group">
                <label>Description (optional)</label>
                <input
                  type="text"
                  placeholder="Description"
                  value={form.description}
                  onChange={e => setForm({ ...form, description: e.target.value })}
                />
              </div>
              <div style={{ display: 'flex', gap: '1rem' }}>
                <button type="submit" className="btn btn-primary">Create</button>
                <button type="button" className="btn btn-secondary" onClick={() => setShowModal(false)}>Cancel</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}