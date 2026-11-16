import { useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate, useNavigate } from 'react-router-dom';
import DashboardLayout from './components/DashboardLayout';
import Dashboard from './pages/Dashboard';
import MapView from './pages/MapView';
import Analytics from './pages/Analytics';
import Chat from './pages/Chat';
import Parcels from './pages/Parcels';
import Settings from './pages/Settings';
import DataSources from './pages/DataSources';
import Census from './pages/Census';
import Profile from './pages/Profile';
import Login from './pages/Login';
import Signup from './pages/Signup';

// Protected Route Component
const ProtectedRoute = ({ children }) => {
  const token = localStorage.getItem('authToken');
  return token ? children : <Navigate to="/login" replace />;
};

function AppRoutes() {
  const navigate = useNavigate();
  useEffect(() => {
    const onLogout = () => navigate('/login', { replace: true });
    window.addEventListener('auth:logout', onLogout);
    return () => window.removeEventListener('auth:logout', onLogout);
  }, [navigate]);

  return (
    <Routes>
        {/* Public Routes */}
        <Route path="/login" element={<Login />} />
        <Route path="/signup" element={<Signup />} />
        
        {/* Protected Routes */}
        <Route
          path="/"
          element={
            <ProtectedRoute>
              <DashboardLayout />
            </ProtectedRoute>
          }
        >
          <Route index element={<Census />} />
          <Route path="monitor-ciudad" element={<Navigate to="/" replace />} />
          <Route path="map" element={<Census />} />
          <Route path="analytics" element={<Census />} />
          <Route path="chat" element={<Chat />} />
          <Route path="parcels" element={<Census />} />
          <Route path="settings" element={<Settings />} />
          <Route path="profile" element={<Profile />} />
          <Route path="data-sources" element={<Census />} />
        </Route>
        
        {/* Redirect unknown routes */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
  );
}

function App() {
  return (
    <BrowserRouter>
      <AppRoutes />
    </BrowserRouter>
  );
}

export default App;
