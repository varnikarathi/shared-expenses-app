import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import API from '../api';

export default function GroupDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [group, setGroup] = useState(null);
  const [expenses, setExpenses] = useState([]);
  const [balances, setBalances] = useState([]);
  const [suggestions, setSuggestions] = useState([]);
  const [settlements, setSettlements] = useState([]);
  const [users, setUsers] = useState([]);
  const [tab, setTab] = useState('expenses');
  const [showExpenseModal, setShowExpenseModal] = useState(false);
  const [showSettleModal, setShowSettleModal] = useState(false);
  const [showMemberModal, setShowMemberModal] = useState(false);
  const [expenseForm, setExpenseForm] = useState({
    description: '', amount: '', currency: 'INR',
    paid_by: '', date: new Date().toISOString().split('T')[0],
    split_type: 'equal', notes: ''
  });
  const [settleForm, setSettleForm] = useState({ paid_by: '', paid_to: '', amount: '', date: new Date().toISOString().split('T')[0], notes: '' });
  const [memberForm, setMemberForm] = useState({ user_id: '', joined_at: new Date().toISOString().split('T')[0] });
  const [error, setError] = useState('');

  useEffect(() => {
    fetchAll();
  }, [id]);

  const fetchAll = async () => {
    try {
      const [groupRes, expRes, balRes, sugRes, setRes, usersRes] = await Promise.all([
        API.get(`/groups/${id}/`),
        API.get(`/expenses/${id}/expenses/`),
        API.get(`/expenses/${id}/balances/`),
        API.get(`/expenses/${id}/settlement-suggestions/`),
        API.get(`/expenses/${id}/settlements/`),
        API.get('/users/list/'),
      ]);
      setGroup(groupRes.data);
      setExpenses(expRes.data);
      setBalances(balRes.data);
      setSuggestions(sugRes.data);
      setSettlements(setRes.data);
      setUsers(usersRes.data);
    } catch (err) {
      console.error(err);
    }
  };

  const createExpense = async (e) => {
    e.preventDefault();
    setError('');
    try {
      await API.post(`/expenses/${id}/expenses/`, expenseForm);
      setShowExpenseModal(false);
      setExpenseForm({ description: '', amount: '', currency: 'INR', paid_by: '', date: new Date().toISOString().split('T')[0], split_type: 'equal', notes: '' });
      fetchAll();
    } catch (err) {
      setError(JSON.stringify(err.response?.data) || 'Error creating expense');
    }
  };

  const createSettlement = async (e) => {
    e.preventDefault();
    try {
      await API.post(`/expenses/${id}/settlements/`, settleForm);
      setShowSettleModal(false);
      fetchAll();
    } catch (err) {
      console.error(err);
    }
  };

  const addMember = async (e) => {
    e.preventDefault();
    try {
      await API.post(`/groups/${id}/add-member/`, memberForm);
      setShowMemberModal(false);
      fetchAll();
    } catch (err) {
      console.error(err);
    }
  };

  const deleteExpense = async (expId) => {
    if (!window.confirm('Delete this expense?')) return;
    try {
      await API.delete(`/expenses/${id}/expenses/${expId}/`);
      fetchAll();
    } catch (err) {
      console.error(err);
    }
  };

  const members = group?.memberships?.filter(m => m.is_active) || [];

  if (!group) return <div className="loading">Loading...</div>;

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
          <div>
            <h1>{group.name}</h1>
            <p style={{ color: '#888', marginTop: '0.3rem' }}>{group.description}</p>
          </div>
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <button className="btn btn-secondary" onClick={() => setShowMemberModal(true)}>+ Member</button>
            <button className="btn btn-secondary" onClick={() => setShowSettleModal(true)}>💰 Settle</button>
            <button className="btn btn-primary" onClick={() => setShowExpenseModal(true)}>+ Expense</button>
          </div>
        </div>

        <div className="card">
          <strong>Members:</strong>
          <div className="members-list">
            {members.map(m => (
              <span key={m.id} className="member-chip">{m.user.username}</span>
            ))}
          </div>
        </div>

        <div className="tab-bar">
          {['expenses', 'balances', 'settlements'].map(t => (
            <button key={t} className={`tab ${tab === t ? 'active' : ''}`} onClick={() => setTab(t)}>
              {t.charAt(0).toUpperCase() + t.slice(1)}
            </button>
          ))}
        </div>

        {tab === 'expenses' && (
          <div className="card">
            {expenses.length === 0 ? (
              <div className="empty-state"><p>No expenses yet</p></div>
            ) : (
              expenses.map(exp => (
                <div key={exp.id} className="expense-item">
                  <div>
                    <div className="expense-desc">
                      {exp.description}
                      <span className={`badge badge-${exp.split_type}`}>{exp.split_type}</span>
                      {exp.currency === 'USD' && <span className="badge badge-usd">USD</span>}
                    </div>
                    <div className="expense-meta">
                      {exp.date} · Paid by {exp.paid_by?.username}
                    </div>
                    <div className="expense-meta">
                      Split: {exp.splits?.map(s => `${s.user?.username} ₹${s.amount_owed}`).join(', ')}
                    </div>
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '0.5rem' }}>
                    <div className="expense-amount">₹{exp.amount_inr || exp.amount}</div>
                    <button className="btn btn-danger" style={{ fontSize: '0.75rem', padding: '0.3rem 0.6rem' }} onClick={() => deleteExpense(exp.id)}>Delete</button>
                  </div>
                </div>
              ))
            )}
          </div>
        )}

        {tab === 'balances' && (
          <div>
            <div className="card">
              <h3 style={{ marginBottom: '1rem' }}>Individual Balances</h3>
              {balances.map((b, i) => (
                <div key={i} style={{ display: 'flex', justifyContent: 'space-between', padding: '0.7rem 0', borderBottom: '1px solid #f0f0f0' }}>
                  <span>{b.username}</span>
                  <span className={b.balance > 0 ? 'balance-positive' : b.balance < 0 ? 'balance-negative' : 'balance-zero'}>
                    {b.balance > 0 ? `gets back ₹${b.balance.toFixed(2)}` : b.balance < 0 ? `owes ₹${Math.abs(b.balance).toFixed(2)}` : 'settled up'}
                  </span>
                </div>
              ))}
            </div>

            <div className="card">
              <h3 style={{ marginBottom: '1rem' }}>Who Pays Whom</h3>
              {suggestions.length === 0 ? (
                <p style={{ color: '#888' }}>Everyone is settled up! 🎉</p>
              ) : (
                suggestions.map((s, i) => (
                  <div key={i} className="suggestion-item">
                    <span><strong>{s.from}</strong> → <strong>{s.to}</strong></span>
                    <span style={{ color: '#ff6b6b', fontWeight: 700 }}>₹{s.amount.toFixed(2)}</span>
                  </div>
                ))
              )}
            </div>
          </div>
        )}

        {tab === 'settlements' && (
          <div className="card">
            {settlements.length === 0 ? (
              <div className="empty-state"><p>No settlements yet</p></div>
            ) : (
              settlements.map(s => (
                <div key={s.id} className="expense-item">
                  <div>
                    <div className="expense-desc">{s.paid_by?.username} paid {s.paid_to?.username}</div>
                    <div className="expense-meta">{s.date} {s.notes && `· ${s.notes}`}</div>
                  </div>
                  <div className="expense-amount balance-positive">₹{s.amount}</div>
                </div>
              ))
            )}
          </div>
        )}
      </div>

      {/* Add Expense Modal */}
      {showExpenseModal && (
        <div className="modal-overlay" onClick={() => setShowExpenseModal(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <h3>Add Expense</h3>
            {error && <div className="error-msg">{error}</div>}
            <form onSubmit={createExpense}>
              <div className="form-group">
                <label>Description</label>
                <input type="text" placeholder="Dinner, groceries..." value={expenseForm.description} onChange={e => setExpenseForm({ ...expenseForm, description: e.target.value })} required />
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '1rem' }}>
                <div className="form-group">
                  <label>Amount</label>
                  <input type="number" step="0.01" placeholder="0.00" value={expenseForm.amount} onChange={e => setExpenseForm({ ...expenseForm, amount: e.target.value })} required />
                </div>
                <div className="form-group">
                  <label>Currency</label>
                  <select value={expenseForm.currency} onChange={e => setExpenseForm({ ...expenseForm, currency: e.target.value })}>
                    <option value="INR">INR</option>
                    <option value="USD">USD</option>
                  </select>
                </div>
              </div>
              <div className="form-group">
                <label>Paid By</label>
                <select value={expenseForm.paid_by} onChange={e => setExpenseForm({ ...expenseForm, paid_by: e.target.value })} required>
                  <option value="">Select person</option>
                  {members.map(m => <option key={m.user.id} value={m.user.id}>{m.user.username}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Date</label>
                <input type="date" value={expenseForm.date} onChange={e => setExpenseForm({ ...expenseForm, date: e.target.value })} required />
              </div>
              <div className="form-group">
                <label>Split Type</label>
                <select value={expenseForm.split_type} onChange={e => setExpenseForm({ ...expenseForm, split_type: e.target.value })}>
                  <option value="equal">Equal</option>
                  <option value="unequal">Unequal</option>
                  <option value="percentage">Percentage</option>
                  <option value="share">By Share</option>
                </select>
              </div>
              <div className="form-group">
                <label>Notes (optional)</label>
                <input type="text" value={expenseForm.notes} onChange={e => setExpenseForm({ ...expenseForm, notes: e.target.value })} />
              </div>
              <div style={{ display: 'flex', gap: '1rem' }}>
                <button type="submit" className="btn btn-primary">Add Expense</button>
                <button type="button" className="btn btn-secondary" onClick={() => setShowExpenseModal(false)}>Cancel</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Settle Modal */}
      {showSettleModal && (
        <div className="modal-overlay" onClick={() => setShowSettleModal(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <h3>Record Settlement</h3>
            <form onSubmit={createSettlement}>
              <div className="form-group">
                <label>Who Paid</label>
                <select value={settleForm.paid_by} onChange={e => setSettleForm({ ...settleForm, paid_by: e.target.value })} required>
                  <option value="">Select person</option>
                  {users.map(u => <option key={u.id} value={u.id}>{u.username}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Paid To</label>
                <select value={settleForm.paid_to} onChange={e => setSettleForm({ ...settleForm, paid_to: e.target.value })} required>
                  <option value="">Select person</option>
                  {users.map(u => <option key={u.id} value={u.id}>{u.username}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Amount (₹)</label>
                <input type="number" step="0.01" value={settleForm.amount} onChange={e => setSettleForm({ ...settleForm, amount: e.target.value })} required />
              </div>
              <div className="form-group">
                <label>Date</label>
                <input type="date" value={settleForm.date} onChange={e => setSettleForm({ ...settleForm, date: e.target.value })} required />
              </div>
              <div className="form-group">
                <label>Notes</label>
                <input type="text" value={settleForm.notes} onChange={e => setSettleForm({ ...settleForm, notes: e.target.value })} />
              </div>
              <div style={{ display: 'flex', gap: '1rem' }}>
                <button type="submit" className="btn btn-primary">Record</button>
                <button type="button" className="btn btn-secondary" onClick={() => setShowSettleModal(false)}>Cancel</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Add Member Modal */}
      {showMemberModal && (
        <div className="modal-overlay" onClick={() => setShowMemberModal(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <h3>Add Member</h3>
            <form onSubmit={addMember}>
              <div className="form-group">
                <label>Select User</label>
                <select value={memberForm.user_id} onChange={e => setMemberForm({ ...memberForm, user_id: e.target.value })} required>
                  <option value="">Select user</option>
                  {users.filter(u => !members.some(m => m.user.id === u.id)).map(u => (
                    <option key={u.id} value={u.id}>{u.username}</option>
                    ))}
                </select>
              </div>
              <div className="form-group">
                <label>Joined On</label>
                <input type="date" value={memberForm.joined_at} onChange={e => setMemberForm({ ...memberForm, joined_at: e.target.value })} required />
              </div>
              <div style={{ display: 'flex', gap: '1rem' }}>
                <button type="submit" className="btn btn-primary">Add</button>
                <button type="button" className="btn btn-secondary" onClick={() => setShowMemberModal(false)}>Cancel</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}