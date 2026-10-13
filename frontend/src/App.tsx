import { lazy, Suspense } from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';
import { ProtectedRoute, PublicOnly } from './components/ProtectedRoute';
import DashboardLayout from './layouts/DashboardLayout';
import { ToastHost, LoadingBlock } from './components/ui';

// eager: landing + auth (first paint)
import Landing from './pages/Landing';
import Login from './pages/Login';
import ChangePassword from './pages/ChangePassword';

const FarmerDashboard = lazy(() => import('./pages/FarmerDashboard'));
const AgronomDashboard = lazy(() => import('./pages/AgronomDashboard'));
const AdminDashboard = lazy(() => import('./pages/AdminDashboard'));
const DiagnosisPage = lazy(() => import('./pages/Diagnosis'));
const DiagnosisHistory = lazy(() => import('./pages/DiagnosisHistory'));
const DiagnosisDetail = lazy(() => import('./pages/DiagnosisDetail'));
const WeatherPage = lazy(() => import('./pages/Weather'));
const FarmsPage = lazy(() => import('./pages/Farms'));
const CropsPage = lazy(() => import('./pages/Crops'));
const AgronomistsPage = lazy(() => import('./pages/Agronomists'));
const ChatPage = lazy(() => import('./pages/Chat'));
const NotificationsPage = lazy(() => import('./pages/Notifications'));
const ProfilePage = lazy(() => import('./pages/Profile'));
const SettingsPage = lazy(() => import('./pages/Settings'));
const SubscriptionPage = lazy(() => import('./pages/Subscription'));
const AdminUsers = lazy(() => import('./pages/AdminUsers'));
const AdminAudit = lazy(() => import('./pages/AdminAudit'));
const AdminHealth = lazy(() => import('./pages/AdminHealth'));
const AdminSettings = lazy(() => import('./pages/AdminSettings'));
const NotFound = lazy(() => import('./pages/NotFound'));

export default function App() {
  return (
    <>
      <Suspense
        fallback={
          <div className="min-h-screen bg-background flex items-center justify-center">
            <LoadingBlock />
          </div>
        }
      >
        <Routes>
          <Route path="/" element={<Landing />} />
          <Route
            path="/login"
            element={
              <PublicOnly>
                <Login />
              </PublicOnly>
            }
          />
          <Route
            path="/change-password"
            element={
              <ProtectedRoute>
                <ChangePassword />
              </ProtectedRoute>
            }
          />

          <Route
            element={
              <ProtectedRoute>
                <DashboardLayout />
              </ProtectedRoute>
            }
          >
            <Route path="/dashboard" element={<RoleHome />} />
            <Route path="/diagnosis" element={<DiagnosisPage />} />
            <Route path="/diagnoses" element={<DiagnosisHistory />} />
            <Route path="/diagnoses/:id" element={<DiagnosisDetail />} />
            <Route path="/weather" element={<WeatherPage />} />
            <Route path="/farms" element={<FarmsPage />} />
            <Route path="/crops" element={<CropsPage />} />
            <Route path="/agronomists" element={<AgronomistsPage />} />
            <Route path="/chat" element={<ChatPage />} />
            <Route path="/chat/:conversationId" element={<ChatPage />} />
            <Route path="/notifications" element={<NotificationsPage />} />
            <Route path="/profile" element={<ProfilePage />} />
            <Route path="/settings" element={<SettingsPage />} />
            <Route path="/subscription" element={<SubscriptionPage />} />
            <Route
              path="/admin/users"
              element={
                <ProtectedRoute roles={['admin']}>
                  <AdminUsers />
                </ProtectedRoute>
              }
            />
            <Route
              path="/admin/audit"
              element={
                <ProtectedRoute roles={['admin']}>
                  <AdminAudit />
                </ProtectedRoute>
              }
            />
            <Route
              path="/admin/health"
              element={
                <ProtectedRoute roles={['admin']}>
                  <AdminHealth />
                </ProtectedRoute>
              }
            />
            <Route
              path="/admin/settings"
              element={
                <ProtectedRoute roles={['admin']}>
                  <AdminSettings />
                </ProtectedRoute>
              }
            />
          </Route>

          <Route path="*" element={<NotFound />} />
        </Routes>
      </Suspense>
      <ToastHost />
    </>
  );
}

import { useAuthStore } from './store/auth';

function RoleHome() {
  const user = useAuthStore((s) => s.user);
  if (user?.role === 'admin') return <AdminDashboard />;
  if (user?.role === 'agronom') return <AgronomDashboard />;
  return <FarmerDashboard />;
}
