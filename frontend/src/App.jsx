import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import AdminLayout from './layouts/AdminLayout';
import Overview from './pages/Overview';
import QueueMonitor from './pages/QueueMonitor';
import Login from './pages/Login';
import LandingPage from './pages/LandingPage';

const ProtectedRoute = ({ children, isAuthenticated }) => {
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  return children;
};

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  useEffect(() => {
    const token = localStorage.getItem('imageforge_token');
    if (token) setIsAuthenticated(true);
  }, []);

  return (
    <Router>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/login" element={
          isAuthenticated ? <Navigate to="/admin" replace /> : <Login onLogin={() => setIsAuthenticated(true)} />
        } />
        
        {/* Admin Routes */}
        <Route path="/admin" element={
          <ProtectedRoute isAuthenticated={isAuthenticated}>
            <AdminLayout isAuthenticated={isAuthenticated}>
              <Overview />
            </AdminLayout>
          </ProtectedRoute>
        } />
        <Route path="/admin/queue" element={
          <ProtectedRoute isAuthenticated={isAuthenticated}>
            <AdminLayout isAuthenticated={isAuthenticated}>
              <QueueMonitor />
            </AdminLayout>
          </ProtectedRoute>
        } />
      </Routes>
    </Router>
  );
}

export default App;
