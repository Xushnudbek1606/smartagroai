import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { BadgeCheck, ExternalLink, MessageCircle, Search, Users } from 'lucide-react';
import { api, extractError } from '../services/api';
import { Badge, EmptyState, ErrorState, LoadingBlock } from '../components/ui';
import type { Conversation, Page, Subscription, User } from '../types';

export default function AgronomistsPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [data, setData] = useState<Page<User> | null>(null);
  const [search, setSearch] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [sub, setSub] = useState<Subscription | null>(null);

  useEffect(() => {
    const id = window.setTimeout(() => {
      api
        .get<Page<User>>('/agronomists', { params: { search: search || undefined, page_size: 50 } })
        .then((r) => setData(r.data))
        .catch((err) => setError(extractError(err).message));
    }, 250);
    api
      .get<Subscription>('/users/me/subscription')
      .then((r) => setSub(r.data))
      .catch(() => setSub(null));
    return () => window.clearTimeout(id);
  }, [search]);

  async function startChat(agronomId: string) {
    setBusyId(agronomId);
    try {
      const resp = await api.post<Conversation>('/conversations', { agronomist_id: agronomId });
      navigate(`/chat/${resp.data.id}`);
    } catch (err) {
      const e = extractError(err);
      if (e.code === 'subscription_required') {
        setError(t('subscription.limitReachedText'));
      } else {
        setError(e.message);
      }
    } finally {
      setBusyId(null);
    }
  }

  if (!data && !error) return <LoadingBlock />;
  if (error && !data) return <ErrorState message={error} />;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">{t('agronomists.title')}</h1>
        <p className="text-sm text-textSecondary">{t('agronomists.subtitle')}</p>
      </div>

      <div className="relative max-w-md">
        <Search size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-textSecondary" />
        <input
          className="input !pl-10"
          placeholder={t('agronomists.searchPlaceholder')}
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>

      {sub && !sub.unlimited && (
        <div className={`card p-4 ${sub.advice_remaining === 0 ? 'border-danger/40' : ''}`}>
          <div className="flex items-center justify-between text-sm">
            <span className="text-textSecondary">{t('subscription.adviceRemaining')}</span>
            {sub.advice_remaining === 0 ? (
              <a href="https://t.me/SmartAgroAIBot" target="_blank" rel="noreferrer" className="text-danger font-semibold underline flex items-center gap-1">
                {t('subscription.upgradeCta')} <ExternalLink size={12} />
              </a>
            ) : (
              <span className="font-semibold">{sub.advice_remaining} / {sub.advice_limit}</span>
            )}
          </div>
        </div>
      )}

      {data && data.items.length === 0 ? (
        <EmptyState icon={<Users size={28} />} title={t('agronomists.empty')} hint={t('agronomists.emptyHint')} />
      ) : (
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {data?.items.map((a) => (
            <div key={a.id} className="card p-5">
              <div className="flex items-center gap-3">
                {a.avatar_url ? (
                  <img src={a.avatar_url} alt="" className="w-12 h-12 rounded-xl object-cover" />
                ) : (
                  <div className="w-12 h-12 rounded-xl bg-accent/15 text-accent flex items-center justify-center text-lg font-bold">
                    {a.full_name.charAt(0)}
                  </div>
                )}
                <div className="min-w-0">
                  <p className="font-semibold truncate flex items-center gap-1">
                    {a.full_name}
                    <BadgeCheck size={15} className="text-primary shrink-0" />
                  </p>
                  <p className="text-xs text-textSecondary truncate">{[a.region, a.district].filter(Boolean).join(', ') || '—'}</p>
                </div>
              </div>
              <div className="flex items-center gap-2 mt-3 text-xs">
                <Badge tone="success">{t('agronomists.verificationVerified')}</Badge>
                {a.telegram_id && <Badge tone="accent">Telegram</Badge>}
              </div>
              <button
                type="button"
                className="btn-primary w-full mt-4"
                onClick={() => startChat(a.id)}
                disabled={busyId === a.id}
              >
                <MessageCircle size={15} />
                {busyId === a.id ? t('common.loading') : t('agronomists.startChat')}
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
