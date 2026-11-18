import { useEffect, lazy, Suspense } from 'react';
import { BrowserRouter, Routes, Route, Navigate, useNavigate } from 'react-router-dom';
import DashboardLayout from './components/DashboardLayout';
const Chat = lazy(() => import('./pages/Chat'));
const Settings = lazy(() => import('./pages/Settings'));
const Workspace = lazy(() => import('./pro/Workspace'));
const Profile = lazy(() => import('./pages/Profile'));
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
    <Suspense fallback={<div className="route-loading" role="status">Cargando espacio de trabajo…</div>}><Routes>
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
          <Route index element={<Workspace />} />
          <Route path="map" element={<Workspace />} />
          <Route path="analytics" element={<Workspace />} />
          {['quality','reports','activity','help'].map(path=><Route key={path} path={path} element={<Workspace/>}/>)}
          <Route path="chat" element={<Chat />} />
          <Route path="parcels" element={<Workspace />} />
          <Route path="settings" element={<Settings />} />
          <Route path="profile" element={<Profile />} />
          <Route path="data-sources" element={<Workspace />} />
        </Route>
        
        {/* Redirect unknown routes */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes></Suspense>
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
