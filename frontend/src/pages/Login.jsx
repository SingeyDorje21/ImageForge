import React, { useState } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import { Loader2 } from 'lucide-react';
import { API_BASE } from '../config';
import ThemeToggle from '../components/ThemeToggle';

const Login = ({ onLogin }) => {
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const res = await axios.post(`${API_BASE}/login`, { password });
      if (res.data.token) {
        localStorage.setItem('imageforge_token', res.data.token);
        onLogin();
        navigate('/admin');
      }
    } catch (err) {
      const status = err.response?.status;
      setError(status === 503
        ? 'Admin login is not configured on the server.'
        : status === 429
          ? 'Too many failed attempts. Try again later.'
          : 'Invalid admin password.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center px-5">
      <ThemeToggle className="fixed top-5 right-5" />
      <div className="w-full max-w-sm">
        <div className="flex items-center gap-2 font-semibold tracking-tight mb-8">
          <img src="/favicon.svg" alt="" className="h-6 w-6" />
          ImageForge
        </div>
        <h1 className="text-xl font-semibold tracking-tight">Admin sign in</h1>
        <p className="text-sm text-muted mt-1 mb-6">Enter the admin password to view the dashboard.</p>

        <form onSubmit={handleSubmit} className="space-y-4">
          <label className="flex flex-col gap-1.5">
            <span className="label">Password</span>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="input py-2.5"
              autoFocus
              required
            />
          </label>
          {error && <p className="text-sm text-danger">{error}</p>}
          <button type="submit" disabled={loading} className="btn-primary w-full py-2.5">
            {loading && <Loader2 size={16} className="animate-spin" />}
            {loading ? 'Signing in…' : 'Sign in'}
          </button>
        </form>
      </div>
    </div>
  );
};

export default Login;
