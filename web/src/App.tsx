import { useAuth } from './auth';
import { Login } from './pages/Login';
import { Dashboard } from './pages/Dashboard';

export function App() {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div style={{ minHeight: '100vh', display: 'grid', placeItems: 'center' }}>
        <span className="spinner" style={{ borderTopColor: 'var(--accent)', width: 26, height: 26 }} />
      </div>
    );
  }

  return user ? <Dashboard /> : <Login />;
}
