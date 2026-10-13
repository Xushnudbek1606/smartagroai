import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Activity, Bot, BrainCircuit, CloudSun, Database, Settings, Wifi } from 'lucide-react';
import { api, extractError } from '../services/api';
import { Badge, ErrorState, LoadingBlock } from '../components/ui';
import { formatDateTime } from '../utils/format';
import type { SystemHealth } from '../types';

export default function AdminHealth() {
  const { t, i18n } = useTranslation();
  const lang = i18n.language as never;
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [error, setError] = useState<string | null>(null);

  function load() {
    api
      .get<SystemHealth>('/admin/system-health')
      .then((r) => setHealth(r.data))
      .catch((err) => setError(extractError(err).message));
  }

  useEffect(load, []);

  if (error) return <ErrorState message={error} onRetry={load} />;
  if (!health) return <LoadingBlock />;

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">{t('admin.healthTitle')}</h1>
          <p className="text-sm text-textSecondary">{formatDateTime(health.checked_at, lang)}</p>
        </div>
        <Badge tone={health.status === 'ok' ? 'success' : health.status === 'degraded' ? 'warning' : 'danger'}>
          <Activity size={12} /> {health.status === 'ok' ? t('admin.healthy') : health.status === 'degraded' ? t('admin.degraded') : t('admin.errorHolat')}
        </Badge>
      </div>

      <div className="grid sm:grid-cols-2 gap-4">
        <Row icon={<Database size={18} />} label={t('admin.database')} status={health.database} />
        <Row icon={<Wifi size={18} />} label={t('admin.redis')} status={health.redis} />
        <Row icon={<CloudSun size={18} />} label={t('admin.weatherApi')} status={health.weather_api.configured ? 'ok' : 'not_configured'} />
        <Row icon={<BrainCircuit size={18} />} label={t('admin.aiService')} status={health.ai_service.configured ? 'ok' : 'not_configured'} />
        <Row
          icon={<Bot size={18} />}
          label={t('admin.telegramBot')}
          status={health.telegram_bot.configured ? (health.telegram_bot.online ? 'ok' : 'offline') : 'not_configured'}
        />
        <div className="card p-5 flex items-center justify-between">
          <span className="text-sm text-textSecondary">Version / Env</span>
          <span className="text-sm font-semibold">{health.version} · {health.environment}</span>
        </div>
      </div>

      {/* landing banner + contact settings live on their own page */}
      <div className="card p-6 flex items-center justify-between gap-4">
        <div>
          <h2 className="font-semibold flex items-center gap-2">
            <Settings size={17} className="text-primary" /> {t('admin.settingsTitle')}
          </h2>
          <p className="text-sm text-textSecondary mt-1">{t('admin.settingsSubtitle')}</p>
        </div>
        <Link to="/admin/settings" className="btn-primary !py-2 shrink-0">
          {t('admin.openSettings')}
        </Link>
      </div>
    </div>
  );
}

function Row({ icon, label, status }: { icon: React.ReactNode; label: string; status: string }) {
  const { t } = useTranslation();
  const tone = status === 'ok' ? 'success' : status === 'not_configured' ? 'warning' : 'danger';
  const text =
    status === 'ok'
      ? t('admin.healthy')
      : status === 'not_configured'
        ? t('admin.notConfigured')
        : status === 'not_configured'
          ? t('common.offline')
          : status === 'offline'
            ? t('common.offline')
            : t('admin.errorHolat');
  return (
    <div className="card p-5 flex items-center justify-between gap-3">
      <span className="flex items-center gap-2.5 text-sm text-textSecondary">{icon} {label}</span>
      <Badge tone={tone}>{status === 'offline' ? t('common.offline') : text}</Badge>
    </div>
  );
}
