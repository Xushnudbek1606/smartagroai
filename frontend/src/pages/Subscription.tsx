import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  BrainCircuit,
  Crown,
  ExternalLink,
  Infinity as InfinityIcon,
  MessageCircle,
  ShieldCheck,
  Sprout,
  TrendingUp,
} from 'lucide-react';
import { api } from '../services/api';
import { useAuthStore } from '../store/auth';
import { ErrorState, LoadingBlock, Badge } from '../components/ui';
import type { Subscription } from '../types';

const BOT_LINK = 'https://t.me/SmartAgroAIBot';

function UsageBar({
  label,
  used,
  limit,
  remaining,
  unlimited,
}: {
  label: string;
  used: number;
  limit: number; // -1 = unlimited
  remaining: number | null;
  unlimited: boolean;
}) {
  const noLimit = unlimited || limit === -1;
  const pct = noLimit ? 100 : limit > 0 ? Math.min(100, (used / limit) * 100) : 0;
  const exhausted = !noLimit && remaining === 0;
  return (
    <div className="card p-6">
      <div className="flex items-center justify-between mb-3">
        <p className="font-semibold flex items-center gap-2">{label}</p>
        {noLimit ? (
          <Badge tone="success"><InfinityIcon size={13} /></Badge>
        ) : exhausted ? (
          <Badge tone="danger">0</Badge>
        ) : (
          <Badge tone="accent">{`${used}/${limit}`}</Badge>
        )}
      </div>
      <div className="h-2.5 rounded-full bg-surface2 overflow-hidden">
        <div
          className={`h-full rounded-full transition-all ${exhausted ? 'bg-danger' : 'bg-primary'}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <p className="text-xs text-textSecondary mt-2">
        {noLimit
          ? '∞'
          : exhausted
            ? `${used} / ${limit} — 0`
            : `${limit - used} / ${limit}`}
      </p>
    </div>
  );
}

export default function SubscriptionPage() {
  const { t } = useTranslation();
  const user = useAuthStore((s) => s.user);
  const [sub, setSub] = useState<Subscription | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .get<Subscription>('/users/me/subscription')
      .then((r) => setSub(r.data))
      .catch((err) => setError(err?.response?.data?.error?.message || 'Error'));
  }, []);

  if (error && !sub) return <ErrorState message={error} />;
  if (!sub) return <LoadingBlock />;

  const isFarmer = sub.role === 'farmer';
  const isAgronom = sub.role === 'agronom';

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold">{t('subscription.title')}</h1>
        <p className="text-sm text-textSecondary">
          {isFarmer
            ? t('subscription.subtitleFarmer')
            : isAgronom
              ? t('subscription.subtitleAgronom')
              : t('subscription.subtitle')}
        </p>
      </div>

      {/* Role plan card */}
      <div className="card p-5 flex items-center gap-4">
        <div
          className={`rounded-xl p-3 ${
            isAgronom
              ? 'bg-accent/15 text-accent'
              : 'bg-primary/15 text-primary'
          }`}
        >
          {isAgronom ? (
            <ShieldCheck size={22} />
          ) : (
            <Sprout size={22} />
          )}
        </div>
        <div className="flex-1">
          <p className="font-semibold">
            {isAgronom
              ? t('subscription.agronomPlanTitle')
              : isFarmer
                ? t('subscription.farmerPlanTitle')
                : t('subscription.adminPlanTitle')}
          </p>
          <p className="text-xs text-textSecondary">
            {isAgronom
              ? t('subscription.agronomPlanText')
              : isFarmer
                ? t('subscription.farmerPlanText')
                : t('subscription.adminPlanText')}
          </p>
        </div>
        <Badge tone={sub.plan === 'pro' ? 'accent' : 'default'}>
          {sub.plan === 'pro' ? t('subscription.planPro') : t('subscription.planFree')}
        </Badge>
      </div>

      <div className="grid sm:grid-cols-2 gap-4">
        <UsageBar
          label={t('subscription.diagnosesUsage')}
          used={sub.diagnoses_used}
          limit={sub.diagnoses_limit}
          remaining={sub.diagnoses_remaining}
          unlimited={sub.unlimited}
        />
        <UsageBar
          label={t('subscription.adviceUsage')}
          used={sub.advice_used}
          limit={sub.advice_limit}
          remaining={sub.advice_remaining}
          unlimited={sub.unlimited}
        />
      </div>

      {sub.paid_until && (
        <div className="card p-4 border-accent/40 flex items-center gap-3 text-sm">
          <Crown size={17} className="text-accent" />
          <span>
            {t('subscription.paidUntil')}{' '}
            <strong>{new Date(sub.paid_until).toLocaleDateString()}</strong>
          </span>
        </div>
      )}

      {sub.unlimited && (
        <div className="card p-6 border-success/40">
          <p className="font-semibold text-success flex items-center gap-2">
            <TrendingUp size={17} /> {t('subscription.adminUnlimited')}
          </p>
        </div>
      )}

      {!sub.unlimited && (
        <div className="card p-6 space-y-4">
          <div className="flex items-center gap-2.5">
            <div className="rounded-lg bg-primary/15 text-primary p-2">
              <BrainCircuit size={17} />
            </div>
            <h2 className="font-semibold">
              {isAgronom
                ? t('subscription.agronomFeaturesTitle')
                : t('subscription.freePlanTitle')}
            </h2>
          </div>
          <ul className="text-sm text-textSecondary space-y-1.5 list-disc list-inside">
            {isAgronom ? (
              <>
                <li>{t('subscription.agronomFeatureAdvice')}</li>
                <li>{t('subscription.agronomFeatureDiagnoses', { count: sub.diagnoses_limit })}</li>
                <li>{t('subscription.proFeaturePriority')}</li>
              </>
            ) : (
              <>
                <li>{t('subscription.freeDiagnoses', { count: sub.diagnoses_limit })}</li>
                <li>{t('subscription.freeAdvice', { count: sub.advice_limit })}</li>
                <li>{t('subscription.proFeatureMore')}</li>
              </>
            )}
          </ul>

          <div className="rounded-xl bg-warning/10 border border-warning/30 p-4 text-sm">
            <p className="font-semibold text-warning mb-1">{t('subscription.limitReachedTitle')}</p>
            <p className="text-textSecondary">{t('subscription.limitReachedText')}</p>
          </div>

          <div>
            <p className="text-sm text-textSecondary mb-2">
              {t('subscription.upgradeContact')}
            </p>
            <a
              href={BOT_LINK}
              target="_blank"
              rel="noreferrer"
              className="btn-primary inline-flex"
            >
              <MessageCircle size={16} /> {t('subscription.openBot')}
              <ExternalLink size={13} />
            </a>
          </div>
        </div>
      )}
    </div>
  );
}
