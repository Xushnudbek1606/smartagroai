import { useEffect } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useAuthStore } from '../store/auth';
import { getStoredTokens } from '../services/api';
import { LoadingBlock } from './ui';
import type { Role } from '../types';

export function ProtectedRoute({ children, roles }: { children: React.ReactNode; roles?: Role[] }) {
  const { t } = useTranslation();
  const user = useAuthStore((s) => s.user);
  const loading = useAuthStore((s) => s.loading);
  const initialized = useAuthStore((s) => s.initialized);
  const fetchMe = useAuthStore((s) => s.fetchMe);
  const location = useLocation();

  useEffect(() => {
    if (!initialized && getStoredTokens()) {
      fetchMe();
    }
  }, [initialized, fetchMe]);

  if (!getStoredTokens()) {
    return <Navigate to={`/login?next=${encodeURIComponent(location.pathname)}`} replace />;
  }

  if (!initialized || loading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <LoadingBlock label={t('common.loading')} />
      </div>
    );
  }

  if (!user) {
    return <Navigate to={`/login?next=${encodeURIComponent(location.pathname)}`} replace />;
  }

  // force password change before anything else
  if (user.must_change_password && location.pathname !== '/change-password') {
    return <Navigate to="/change-password" replace />;
  }

  if (roles && !roles.includes(user.role)) {
    return <Navigate to="/dashboard" replace />;
  }

  return <>{children}</>;
}

export function PublicOnly({ children }: { children: React.ReactNode }) {
  const user = useAuthStore((s) => s.user);
  const initialized = useAuthStore((s) => s.initialized);
  const fetchMe = useAuthStore((s) => s.fetchMe);

  useEffect(() => {
    if (!initialized && getStoredTokens()) fetchMe();
  }, [initialized, fetchMe]);

  if (getStoredTokens() && user) {
    return <Navigate to="/dashboard" replace />;
  }
  return <>{children}</>;
}
