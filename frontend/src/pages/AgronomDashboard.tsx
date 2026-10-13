import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { BrainCircuit, MessageCircle, Users } from 'lucide-react';
import { api } from '../services/api';
import { EmptyState, ErrorState, LoadingBlock, StatCard, Badge } from '../components/ui';
import { formatRelative } from '../utils/format';
import type { Conversation, User } from '../types';

export default function AgronomDashboard() {
  const { t, i18n } = useTranslation();
  const lang = i18n.language as never;
  const [convs, setConvs] = useState<Conversation[] | null>(null);
  const [farmers, setFarmers] = useState<User[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.get<Conversation[]>('/conversations').then((r) => setConvs(r.data)).catch((e) => setError(String(e)));
    api.get<{ items: User[] }>('/agronomists/assigned?page_size=20').then((r) => setFarmers(r.data.items)).catch(() => setFarmers([]));
  }, []);

  if (convs === null) return error ? <ErrorState onRetry={() => window.location.reload()} /> : <LoadingBlock />;

  const unread = convs.reduce((s, c) => s + c.unread_count, 0);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">{t('dashboard.agronomTitle')}</h1>
        <p className="text-sm text-textSecondary">{t('dashboard.welcome')}</p>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard label={t('dashboard.assignedFarmers')} value={farmers?.length ?? 0} icon={<Users size={20} />} />
        <StatCard label={t('dashboard.conversations')} value={convs.length} icon={<MessageCircle size={20} />} accent="text-accent" />
        <StatCard label={t('dashboard.pendingChats')} value={unread} icon={<MessageCircle size={20} />} accent="text-warning" />
        <StatCard label={t('dashboard.reviewDiagnoses')} value="—" icon={<BrainCircuit size={20} />} />
      </div>

      <div className="grid lg:grid-cols-2 gap-6">
        <div className="card p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold">{t('dashboard.newMessages')}</h2>
            <Link to="/chat" className="text-xs text-accent hover:underline">{t('common.viewAll')}</Link>
          </div>
          {convs.length === 0 ? (
            <EmptyState title={t('chat.empty')} hint={t('chat.emptyHint')} />
          ) : (
            <div className="space-y-2.5">
              {convs.slice(0, 6).map((c) => (
                <Link
                  key={c.id}
                  to={`/chat/${c.id}`}
                  className="flex items-center gap-3 rounded-xl border border-borderc bg-surface2/50 p-3 hover:border-primary/40 transition-colors"
                >
                  <div className="w-10 h-10 rounded-lg bg-accent/15 text-accent flex items-center justify-center font-bold shrink-0">
                    {(c.partner?.full_name || '?').charAt(0)}
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="font-medium text-sm truncate">{c.partner?.full_name}</p>
                    <p className="text-xs text-textSecondary truncate">{c.last_message_preview || '—'}</p>
                  </div>
                  <div className="text-right shrink-0">
                    {c.unread_count > 0 && (
                      <span className="inline-flex items-center justify-center min-w-[18px] h-[18px] px-1 rounded-full bg-danger text-[10px] font-bold">
                        {c.unread_count}
                      </span>
                    )}
                    <p className="text-[11px] text-textSecondary mt-1">{c.last_message_at ? formatRelative(c.last_message_at, lang) : ''}</p>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </div>

        <div className="card p-6">
          <h2 className="font-semibold mb-4">{t('dashboard.assignedFarmers')}</h2>
          {!farmers ? (
            <LoadingBlock />
          ) : farmers.length === 0 ? (
            <EmptyState title={t('dashboard.noFarmers')} />
          ) : (
            <div className="space-y-2.5">
              {farmers.map((f) => (
                <div key={f.id} className="flex items-center gap-3 rounded-xl border border-borderc bg-surface2/50 p-3">
                  <div className="w-10 h-10 rounded-lg bg-primary/15 text-primary flex items-center justify-center font-bold shrink-0">
                    {f.full_name.charAt(0)}
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="font-medium text-sm truncate">{f.full_name}</p>
                    <p className="text-xs text-textSecondary truncate">{[f.region, f.district].filter(Boolean).join(', ') || '—'}</p>
                  </div>
                  <Badge tone="accent">{f.role}</Badge>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
