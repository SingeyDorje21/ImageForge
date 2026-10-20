import React, { useState, lazy, Suspense } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import LandingPage from './pages/LandingPage';
import { getToken } from './auth';

// Admin pages load on demand so the public page doesn't ship the chart library.
const AdminLayout = lazy(() => import('./layouts/AdminLayout'));
const Overview = lazy(() => import('./pages/Overview'));
const QueueMonitor = lazy(() => import('./pages/QueueMonitor'));
const Login = lazy(() => import('./pages/Login'));

const ProtectedRoute = ({ children, isAuthenticated }) => {
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  return children;
};

function App() {
  // Read the token on first render so a reload of an admin page doesn't bounce through /login.
  const [isAuthenticated, setIsAuthenticated] = useState(() => Boolean(getToken()));

  return (
    <Router>
      <Suspense fallback={null}>
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
      </Suspense>
    </Router>
  );
}

export default App;
