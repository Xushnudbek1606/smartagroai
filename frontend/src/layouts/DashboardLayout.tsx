import { useEffect, useState } from 'react';
import { Link, NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import {
  Bell,
  BrainCircuit,
  ChevronLeft,
  ClipboardList,
  CloudSun,
  CreditCard,
  FlaskConical,
  History,
  Home,
  Leaf,
  LogOut,
  Menu,
  MessageCircle,
  Settings,
  ShieldCheck,
  Sprout,
  User,
  Users,
  X,
} from 'lucide-react';
import LanguageSwitcher from '../components/LanguageSwitcher';
import { useAuthStore } from '../store/auth';
import { api, assetUrl } from '../services/api';
import type { AppNotification } from '../types';
import { useNotificationSocket } from '../hooks/useNotificationSocket';

const farmerLinks = [
  { to: '/dashboard', key: 'nav.dashboard', icon: Home },
  { to: '/diagnosis', key: 'nav.diagnosis', icon: BrainCircuit },
  { to: '/diagnoses', key: 'nav.diagnosisHistory', icon: History },
  { to: '/weather', key: 'nav.weather', icon: CloudSun },
  { to: '/farms', key: 'nav.farms', icon: FlaskConical },
  { to: '/crops', key: 'nav.crops', icon: Sprout },
  { to: '/agronomists', key: 'nav.agronomists', icon: Users },
  { to: '/chat', key: 'nav.chat', icon: MessageCircle },
];

const agronomLinks = [
  { to: '/dashboard', key: 'nav.dashboard', icon: Home },
  { to: '/chat', key: 'nav.chat', icon: MessageCircle },
  { to: '/agronomists', key: 'nav.agronomists', icon: Users },
  { to: '/weather', key: 'nav.weather', icon: CloudSun },
  { to: '/diagnoses', key: 'nav.diagnosisHistory', icon: History },
];

const adminLinks = [
  { to: '/dashboard', key: 'nav.dashboard', icon: Home },
  { to: '/admin/users', key: 'nav.users', icon: Users },
  { to: '/admin/audit', key: 'nav.auditLog', icon: ShieldCheck },
  { to: '/admin/health', key: 'nav.systemHealth', icon: Leaf },
  { to: '/admin/settings', key: 'nav.adminSettings', icon: Settings },
  { to: '/farms', key: 'nav.farms', icon: FlaskConical },
  { to: '/diagnoses', key: 'nav.diagnosisHistory', icon: History },
  { to: '/chat', key: 'nav.chat', icon: MessageCircle },
];

const commonLinks = [
  { to: '/notifications', key: 'nav.notifications', icon: Bell },
  { to: '/subscription', key: 'nav.subscription', icon: CreditCard },
  { to: '/profile', key: 'nav.profile', icon: User },
  { to: '/settings', key: 'nav.settings', icon: Settings },
];

function linksFor(role: string | undefined) {
  if (role === 'admin') return [...adminLinks, ...commonLinks];
  if (role === 'agronom') return [...agronomLinks, ...commonLinks];
  return [...farmerLinks, ...commonLinks];
}

export default function DashboardLayout() {
  const { t } = useTranslation();
  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.logout);
  const navigate = useNavigate();
  const location = useLocation();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [unread, setUnread] = useState(0);
  const [menuOpen, setMenuOpen] = useState(false);
  const [banner, setBanner] = useState<string | null>(null);

  useNotificationSocket(setUnread);

  useEffect(() => {
    setMobileOpen(false);
    setMenuOpen(false);
  }, [location.pathname]);

  useEffect(() => {
    let cancelled = false;
    api
      .get('/notifications/unread-count')
      .then((r) => !cancelled && setUnread(r.data.count || 0))
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, [location.pathname]);

  useEffect(() => {
    if (user?.must_change_password && location.pathname !== '/change-password') {
      navigate('/change-password');
    }
  }, [user?.must_change_password, location.pathname, navigate]);

  const links = linksFor(user?.role);

  async function doLogout() {
    await logout();
    navigate('/login');
  }

  return (
    <div className="min-h-screen bg-background flex">
      {/* sidebar (desktop) */}
      <aside className="hidden lg:flex w-64 shrink-0 flex-col border-r border-borderc bg-surface">
        <div className="flex items-center gap-2.5 px-5 h-16 border-b border-borderc">
          <div className="rounded-xl bg-primary/15 p-2 text-primary">
            <Sprout size={20} />
          </div>
          <span className="font-bold text-lg tracking-tight">{t('common.appName')}</span>
        </div>
        <nav className="flex-1 overflow-y-auto p-3 space-y-1">
          {links.map(({ to, key, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/dashboard'}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-xl px-3.5 py-2.5 text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-primary/15 text-primary'
                    : 'text-textSecondary hover:bg-surface2 hover:text-textPrimary'
                }`
              }
            >
              <Icon size={18} />
              {t(key)}
            </NavLink>
          ))}
        </nav>
        <div className="p-3 border-t border-borderc">
          <button type="button" onClick={doLogout} className="btn-secondary w-full !justify-start">
            <LogOut size={16} /> {t('common.logout')}
          </button>
        </div>
      </aside>

      {/* sidebar (mobile drawer) */}
      {mobileOpen && (
        <div className="fixed inset-0 z-40 lg:hidden">
          <div className="absolute inset-0 bg-black/60" onClick={() => setMobileOpen(false)} />
          <aside className="absolute left-0 top-0 bottom-0 w-72 bg-surface border-r border-borderc flex flex-col animate-fade-in">
            <div className="flex items-center justify-between px-5 h-16 border-b border-borderc">
              <div className="flex items-center gap-2.5">
                <div className="rounded-xl bg-primary/15 p-2 text-primary">
                  <Sprout size={20} />
                </div>
                <span className="font-bold">{t('common.appName')}</span>
              </div>
              <button type="button" onClick={() => setMobileOpen(false)} aria-label={t('common.close')}>
                <X size={20} className="text-textSecondary" />
              </button>
            </div>
            <nav className="flex-1 overflow-y-auto p-3 space-y-1">
              {links.map(({ to, key, icon: Icon }) => (
                <NavLink
                  key={to}
                  to={to}
                  end={to === '/dashboard'}
                  className={({ isActive }) =>
                    `flex items-center gap-3 rounded-xl px-3.5 py-2.5 text-sm font-medium ${
                      isActive ? 'bg-primary/15 text-primary' : 'text-textSecondary'
                    }`
                  }
                >
                  <Icon size={18} />
                  {t(key)}
                </NavLink>
              ))}
            </nav>
            <div className="p-3 border-t border-borderc">
              <button type="button" onClick={doLogout} className="btn-secondary w-full !justify-start">
                <LogOut size={16} /> {t('common.logout')}
              </button>
            </div>
          </aside>
        </div>
      )}

      {/* main */}
      <div className="flex-1 flex flex-col min-w-0">
        <header className="h-16 border-b border-borderc bg-surface/80 backdrop-blur sticky top-0 z-30 flex items-center gap-3 px-4">
          <button
            type="button"
            className="lg:hidden text-textSecondary"
            onClick={() => setMobileOpen(true)}
            aria-label={t('nav.openMenu')}
          >
            <Menu size={22} />
          </button>
          <div className="min-w-0 flex-1">
            <p className="font-semibold truncate">
              {user ? `${t('dashboard.welcome')}, ${user.full_name}` : t('common.appName')}
            </p>
          </div>

          <LanguageSwitcher />

          <Link
            to="/notifications"
            className="relative rounded-xl p-2.5 text-textSecondary hover:text-textPrimary hover:bg-surface2"
            aria-label={t('nav.notifications')}
          >
            <Bell size={18} />
            {unread > 0 && (
              <span className="absolute -top-0.5 -right-0.5 min-w-[18px] h-[18px] px-1 rounded-full bg-danger text-[10px] font-bold flex items-center justify-center">
                {unread > 9 ? '9+' : unread}
              </span>
            )}
          </Link>

          <div className="relative">
            <button
              type="button"
              onClick={() => setMenuOpen((v) => !v)}
              className="flex items-center gap-2 rounded-xl p-1.5 hover:bg-surface2"
              aria-label={t('nav.profile')}
            >
              {user?.avatar_url ? (
                <img src={assetUrl(user.avatar_url)} alt="" className="w-8 h-8 rounded-lg object-cover" />
              ) : (
                <div className="w-8 h-8 rounded-lg bg-accent/20 text-accent flex items-center justify-center text-sm font-bold">
                  {(user?.full_name || '?').charAt(0).toUpperCase()}
                </div>
              )}
            </button>
            {menuOpen && (
              <div className="absolute right-0 mt-2 w-56 card p-1.5 z-50 animate-fade-in">
                <div className="px-3 py-2 border-b border-borderc mb-1">
                  <p className="text-sm font-semibold truncate">{user?.full_name}</p>
                  <p className="text-xs text-textSecondary">{user?.role}</p>
                </div>
                <Link to="/profile" className="block rounded-lg px-3 py-2 text-sm hover:bg-surface2">
                  {t('nav.profile')}
                </Link>
                <Link to="/settings" className="block rounded-lg px-3 py-2 text-sm hover:bg-surface2">
                  {t('nav.settings')}
                </Link>
                <button
                  type="button"
                  onClick={doLogout}
                  className="w-full text-left rounded-lg px-3 py-2 text-sm text-danger hover:bg-surface2"
                >
                  {t('common.logout')}
                </button>
              </div>
            )}
          </div>
        </header>

        {banner && (
          <div className="bg-accent/10 border-b border-accent/20 px-4 py-2.5 text-sm text-textPrimary">
            {banner}
          </div>
        )}

        <main className="flex-1 p-4 sm:p-6 lg:p-8 overflow-x-hidden">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
