import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Login from './pages/Login';
import Register from './pages/Register';
import Dashboard from './pages/Dashboard';
import GroupDetail from './pages/GroupDetail';
import ImportCSV from './pages/ImportCSV';
import './App.css';

const PrivateRoute = ({ children }) => {
  const token = localStorage.getItem('access_token');
  return token ? children : <Navigate to="/login" />;
};

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="/" element={<PrivateRoute><Dashboard /></PrivateRoute>} />
        <Route path="/group/:id" element={<PrivateRoute><GroupDetail /></PrivateRoute>} />
        <Route path="/import" element={<PrivateRoute><ImportCSV /></PrivateRoute>} />
      </Routes>
    </Router>
  );
}

export default App;