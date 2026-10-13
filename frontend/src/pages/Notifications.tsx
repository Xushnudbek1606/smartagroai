import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Bell, CheckCheck, CloudSun, Info, Lock, Stethoscope } from 'lucide-react';
import { api, extractError } from '../services/api';
import { Badge, EmptyState, ErrorState, LoadingBlock, showToast } from '../components/ui';
import { formatRelative } from '../utils/format';
import type { AppNotification, Page } from '../types';

const typeIcons: Record<string, React.ReactNode> = {
  chat: <Bell size={16} />,
  diagnosis: <Stethoscope size={16} />,
  weather: <CloudSun size={16} />,
  security: <Lock size={16} />,
  info: <Info size={16} />,
};

export default function NotificationsPage() {
  const { t, i18n } = useTranslation();
  const lang = i18n.language as never;
  const [data, setData] = useState<Page<AppNotification> | null>(null);
  const [error, setError] = useState<string | null>(null);

  function load() {
    api
      .get<Page<AppNotification>>('/notifications', { params: { page_size: 50 } })
        .then((r) => setData(r.data))
      .catch((err) => setError(extractError(err).message));
  }

  useEffect(load, []);

  async function markRead(n: AppNotification) {
    if (n.is_read) return;
    try {
      await api.patch(`/notifications/${n.id}/read`);
      load();
    } catch {
      /* best-effort */
    }
  }

  async function markAll() {
    try {
      await api.post('/notifications/read-all');
      showToast(t('common.success'), 'success');
      load();
    } catch (err) {
      showToast(extractError(err).message, 'error');
    }
  }

  if (!data && !error) return <LoadingBlock />;
  if (error && !data) return <ErrorState message={error} onRetry={load} />;

  const unread = data?.items.filter((n) => !n.is_read).length || 0;

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">{t('notifications.title')}</h1>
          <p className="text-sm text-textSecondary">
            {unread > 0 ? `${unread} ${t('chat.unread')}` : ''}
          </p>
        </div>
        {unread > 0 && (
          <button type="button" className="btn-secondary" onClick={markAll}>
            <CheckCheck size={16} /> {t('notifications.markAllRead')}
          </button>
        )}
      </div>

      {data && data.items.length === 0 ? (
        <EmptyState icon={<Bell size={28} />} title={t('notifications.empty')} hint={t('notifications.emptyHint')} />
      ) : (
        <div className="space-y-2">
          {data?.items.map((n) => (
            <button
              key={n.id}
              type="button"
              onClick={() => markRead(n)}
              className={`w-full text-left card p-4 flex items-start gap-3 transition-colors ${
                n.is_read ? 'opacity-70' : 'hover:border-primary/40'
              }`}
            >
              <div
                className={`rounded-xl p-2.5 shrink-0 ${
                  n.is_read ? 'bg-surface2 text-textSecondary' : 'bg-primary/10 text-primary'
                }`}
              >
                {typeIcons[n.type] || <Info size={16} />}
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex items-center justify-between gap-2">
                  <p className={`text-sm ${n.is_read ? 'text-textSecondary' : 'font-semibold'}`}>{n.title}</p>
                  {!n.is_read && <span className="w-2 h-2 rounded-full bg-primary shrink-0" />}
                </div>
                {n.body && <p className="text-xs text-textSecondary mt-0.5 break-words">{n.body}</p>}
                <div className="flex items-center gap-2 mt-1.5">
                  <Badge tone="default">{t(`notifications.type_${n.type}`) || n.type}</Badge>
                  <span className="text-[11px] text-textSecondary">{formatRelative(n.created_at, lang)}</span>
                  {n.link && (
                    <Link to={n.link} className="text-[11px] text-accent hover:underline" onClick={(e) => e.stopPropagation()}>
                      {t('common.viewDetails')}
                    </Link>
                  )}
                </div>
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
