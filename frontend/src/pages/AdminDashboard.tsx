import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import {
  Activity,
  Bot,
  BrainCircuit,
  CloudSun,
  Database,
  MessageCircle,
  ShieldCheck,
  Sprout,
  Users,
} from 'lucide-react';
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { api } from '../services/api';
import { Badge, LoadingBlock, StatCard } from '../components/ui';
import { formatDate } from '../utils/format';
import type { AdminStatistics, SystemHealth } from '../types';

export default function AdminDashboard() {
  const { t, i18n } = useTranslation();
  const lang = i18n.language as never;
  const [stats, setStats] = useState<AdminStatistics | null>(null);
  const [health, setHealth] = useState<SystemHealth | null>(null);

  useEffect(() => {
    api.get<AdminStatistics>('/admin/statistics').then((r) => setStats(r.data)).catch(() => setStats(null));
    api.get<SystemHealth>('/admin/system-health').then((r) => setHealth(r.data)).catch(() => setHealth(null));
  }, []);

  if (!stats) return <LoadingBlock />;

  const chartData = stats.activity.map((a) => ({
    ...a,
    day: a.date.slice(5),
  }));

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-bold">{t('dashboard.adminTitle')}</h1>
        <div className="flex gap-2">
          <Link to="/admin/users" className="btn-secondary !py-2"><Users size={16} /> {t('nav.users')}</Link>
          <Link to="/admin/audit" className="btn-secondary !py-2"><ShieldCheck size={16} /> {t('nav.auditLog')}</Link>
          <Link to="/admin/health" className="btn-secondary !py-2"><Activity size={16} /> {t('nav.systemHealth')}</Link>
        </div>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard label={t('dashboard.totalUsers')} value={stats.total_users} icon={<Users size={20} />} />
        <StatCard label={t('dashboard.farmers')} value={stats.total_farmers} icon={<Sprout size={20} />} />
        <StatCard label={t('dashboard.agronomists')} value={stats.total_agronomists} icon={<BrainCircuit size={20} />} accent="text-accent" />
        <StatCard label={t('dashboard.activeUsers')} value={stats.active_users} icon={<Users size={20} />} accent="text-warning" />
        <StatCard label={t('dashboard.farms')} value={stats.total_farms} icon={<Sprout size={20} />} />
        <StatCard label={t('dashboard.diagnoses')} value={stats.total_diagnoses} icon={<BrainCircuit size={20} />} />
        <StatCard label={t('dashboard.diagnosesToday')} value={stats.diagnoses_today} icon={<Activity size={20} />} accent="text-warning" />
        <StatCard label={t('dashboard.registeredToday')} value={stats.users_registered_today} icon={<Users size={20} />} accent="text-accent" />
      </div>

      <div className="grid lg:grid-cols-3 gap-6">
        <div className="card p-6 lg:col-span-2">
          <h2 className="font-semibold mb-4">{t('dashboard.platformActivity')}</h2>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
                <CartesianGrid stroke="#263449" strokeDasharray="3 3" />
                <XAxis dataKey="day" stroke="#94A3B8" fontSize={11} />
                <YAxis stroke="#94A3B8" fontSize={11} allowDecimals={false} />
                <Tooltip
                  contentStyle={{ background: '#111C2E', border: '1px solid #263449', borderRadius: 12, color: '#F8FAFC' }}
                />
                <Line type="monotone" dataKey="diagnoses" stroke="#22C55E" strokeWidth={2} dot={false} name={t('dashboard.diagnoses')} />
                <Line type="monotone" dataKey="registrations" stroke="#38BDF8" strokeWidth={2} dot={false} name={t('dashboard.registeredToday')} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="card p-6">
          <h2 className="font-semibold mb-4">{t('dashboard.systemHealth')}</h2>
          {!health ? (
            <LoadingBlock />
          ) : (
            <div className="space-y-3 text-sm">
              <HealthRow icon={<Database size={16} />} label={t('admin.database')} status={health.database} />
              <HealthRow icon={<CloudSun size={16} />} label={t('admin.weatherApi')} status={health.weather_api.configured ? 'ok' : 'not_configured'} />
              <HealthRow icon={<BrainCircuit size={16} />} label={t('admin.aiService')} status={health.ai_service.configured ? 'ok' : 'not_configured'} />
              <HealthRow
                icon={<Bot size={16} />}
                label={t('admin.telegramBot')}
                status={health.telegram_bot.configured ? (health.telegram_bot.online ? 'ok' : 'offline') : 'not_configured'}
              />
              <div className="pt-3 border-t border-borderc flex items-center justify-between">
                <span className="text-textSecondary">{t('dashboard.conversations')}</span>
                <span className="font-semibold">{stats.total_conversations}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-textSecondary">{t('dashboard.messages')}</span>
                <span className="font-semibold">{stats.messages_total}</span>
              </div>
              {health.checked_at && (
                <p className="text-[11px] text-textSecondary pt-2">
                  {t('weather.updatedAt')}: {formatDate(health.checked_at, lang, { timeStyle: 'short' })}
                </p>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function HealthRow({ icon, label, status }: { icon: React.ReactNode; label: string; status: string }) {
  const { t } = useTranslation();
  const tone = status === 'ok' ? 'success' : status === 'not_configured' ? 'warning' : 'danger';
  const text =
    status === 'ok' ? t('admin.healthy') : status === 'not_configured' ? t('admin.notConfigured') : status === 'offline' ? t('common.offline') : t('admin.errorHolat');
  return (
    <div className="flex items-center justify-between">
      <span className="flex items-center gap-2 text-textSecondary">{icon} {label}</span>
      <Badge tone={tone}>{text}</Badge>
    </div>
  );
}
