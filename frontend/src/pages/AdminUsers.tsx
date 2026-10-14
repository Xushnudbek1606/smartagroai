import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Copy, Crown, KeyRound, Plus, Search, UserPlus, Users } from 'lucide-react';
import { useForm } from 'react-hook-form';
import { api, extractError } from '../services/api';
import { Badge, EmptyState, ErrorState, LoadingBlock, Modal, showToast } from '../components/ui';
import { formatDate, formatRelative } from '../utils/format';
import type {
  Language,
  Page,
  Role,
  SubscriptionAdmin,
  User,
} from '../types';

interface CreateValues {
  full_name: string;
  username: string;
  role: Role;
  region: string;
  preferred_language: Language;
  telegram_username: string;
}

export default function AdminUsers() {
  const { t, i18n } = useTranslation();
  const lang = i18n.language as never;
  const [data, setData] = useState<Page<User> | null>(null);
  const [search, setSearch] = useState('');
  const [roleFilter, setRoleFilter] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [open, setOpen] = useState(false);
  const [inviteResult, setInviteResult] = useState<{ code: string; username: string } | null>(null);
  const [tempPassword, setTempPassword] = useState<{ username: string; password: string } | null>(null);
  const [subTarget, setSubTarget] = useState<User | null>(null);
  const [subData, setSubData] = useState<SubscriptionAdmin | null>(null);
  const [subSaving, setSubSaving] = useState(false);

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<CreateValues>({
    defaultValues: {
      full_name: '',
      username: '',
      role: 'farmer',
      region: '',
      preferred_language: 'uz-Latn',
      telegram_username: '',
    },
  });

  function load() {
    api
      .get<Page<User>>('/users', {
        params: { search: search || undefined, role: roleFilter || undefined, page_size: 100 },
      })
      .then((r) => setData(r.data))
      .catch((err) => setError(extractError(err).message));
  }

  useEffect(() => {
    const id = window.setTimeout(load, 250);
    return () => window.clearTimeout(id);
  }, [search, roleFilter]);

  async function onCreate(values: CreateValues) {
    try {
      const resp = await api.post<{ invitation_code: string | null; user: User }>('/users', {
        full_name: values.full_name.trim(),
        username: values.username.trim(),
        role: values.role,
        region: values.region.trim() || null,
        preferred_language: values.preferred_language,
        telegram_username: values.telegram_username.trim().replace(/^@/, '') || null,
      });
      setOpen(false);
      reset();
      setInviteResult({ code: resp.data.invitation_code || '—', username: resp.data.user.username });
      showToast(t('admin.userCreated'), 'success');
      load();
    } catch (err) {
      showToast(extractError(err).message, 'error');
    }
  }

  async function toggleActive(u: User) {
    try {
      await api.post(`/users/${u.id}/${u.is_active ? 'deactivate' : 'activate'}`);
      showToast(u.is_active ? t('admin.userDeactivated') : t('admin.userActivated'), 'success');
      load();
    } catch (err) {
      showToast(extractError(err).message, 'error');
    }
  }

  async function regenPassword(u: User) {
    try {
      const resp = await api.post<{ temporary_password: string }>(`/users/${u.id}/temporary-password`);
      setTempPassword({ username: u.username, password: resp.data.temporary_password });
    } catch (err) {
      showToast(extractError(err).message, 'error');
    }
  }

  function copy(text: string) {
    navigator.clipboard?.writeText(text).then(
      () => showToast(t('admin.copied'), 'success'),
      () => undefined,
    );
  }

  async function openSubscription(u: User) {
    setSubTarget(u);
    setSubData(null);
    try {
      const resp = await api.get<SubscriptionAdmin>(`/users/${u.id}/subscription`);
      setSubData(resp.data);
    } catch (err) {
      showToast(extractError(err).message, 'error');
      setSubTarget(null);
    }
  }

  async function saveSubscription(values: {
    plan: 'free' | 'pro';
    diagnoses_limit: string;
    advice_limit: string;
    paid_until: string;
    reset_usage: boolean;
  }) {
    if (!subTarget) return;
    setSubSaving(true);
    try {
      const diag = values.diagnoses_limit.trim();
      const adv = values.advice_limit.trim();
      const resp = await api.patch<SubscriptionAdmin>(
        `/users/${subTarget.id}/subscription`,
        {
          plan: values.plan,
          ...(diag !== '' ? { diagnoses_limit: Number(diag) } : {}),
          ...(adv !== '' ? { advice_limit: Number(adv) } : {}),
          ...(values.paid_until ? { paid_until: new Date(values.paid_until).toISOString() } : {}),
          reset_usage: values.reset_usage,
        },
      );
      setSubData(resp.data);
      showToast(t('admin.subSaved'), 'success');
      load();
    } catch (err) {
      showToast(extractError(err).message, 'error');
    } finally {
      setSubSaving(false);
    }
  }

  if (!data && !error) return <LoadingBlock />;
  if (error && !data) return <ErrorState message={error} onRetry={load} />;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">{t('admin.usersTitle')}</h1>
          <p className="text-sm text-textSecondary">{t('admin.usersSubtitle')}</p>
        </div>
        <button type="button" className="btn-primary" onClick={() => setOpen(true)}>
          <UserPlus size={16} /> {t('admin.addUser')}
        </button>
      </div>

      <div className="flex flex-wrap gap-3">
        <div className="relative flex-1 min-w-[220px] max-w-md">
          <Search size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-textSecondary" />
          <input
            className="input !pl-10"
            placeholder={t('admin.searchUsers')}
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <select className="input !w-auto" value={roleFilter} onChange={(e) => setRoleFilter(e.target.value)}>
          <option value="">{t('common.all')}</option>
          <option value="farmer">{t('admin.role_farmer')}</option>
          <option value="agronom">{t('admin.role_agronom')}</option>
          <option value="admin">{t('admin.role_admin')}</option>
        </select>
      </div>

      {data && data.items.length === 0 ? (
        <EmptyState icon={<Users size={28} />} title={t('common.empty')} />
      ) : (
        <div className="card overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-borderc text-textSecondary text-left">
                <th className="px-5 py-3 font-medium">{t('admin.fullName')}</th>
                <th className="px-5 py-3 font-medium">{t('admin.username')}</th>
                <th className="px-5 py-3 font-medium">{t('admin.role')}</th>
                <th className="px-5 py-3 font-medium">{t('common.status')}</th>
                <th className="px-5 py-3 font-medium">Telegram</th>
                <th className="px-5 py-3 font-medium">{t('common.date')}</th>
                <th className="px-5 py-3 font-medium text-right">{t('common.actions')}</th>
              </tr>
            </thead>
            <tbody>
              {data?.items.map((u) => (
                <tr key={u.id} className="border-b border-borderc/50 hover:bg-surface2/40">
                  <td className="px-5 py-3.5">
                    <p className="font-medium">{u.full_name}</p>
                    {u.region && <p className="text-xs text-textSecondary">{u.region}</p>}
                  </td>
                  <td className="px-5 py-3.5 text-textSecondary">@{u.username}</td>
                  <td className="px-5 py-3.5">
                    <Badge tone={u.role === 'admin' ? 'warning' : u.role === 'agronom' ? 'accent' : 'success'}>
                      {t(`admin.role_${u.role}`)}
                    </Badge>
                  </td>
                  <td className="px-5 py-3.5">
                    <Badge tone={u.is_active ? 'success' : 'danger'}>
                      {u.is_active ? t('admin.active') : t('admin.inactive')}
                    </Badge>
                  </td>
                  <td className="px-5 py-3.5">
                    {u.telegram_id ? (
                      <Badge tone="accent">✓ {u.telegram_username ? `@${u.telegram_username}` : ''}</Badge>
                    ) : u.telegram_username ? (
                      <Badge tone="warning">@{u.telegram_username}</Badge>
                    ) : (
                      <span className="text-textSecondary">—</span>
                    )}
                  </td>
                  <td className="px-5 py-3.5 text-textSecondary" title={formatDate(u.created_at, lang)}>
                    {formatRelative(u.created_at, lang)}
                  </td>
                  <td className="px-5 py-3.5">
                    <div className="flex justify-end gap-1.5">
                      <button
                        type="button"
                        className="btn-secondary !py-1 !px-2.5 text-xs"
                        onClick={() => regenPassword(u)}
                        title={t('admin.regenPassword')}
                      >
                        <KeyRound size={13} />
                      </button>
                      {u.role !== 'admin' && (
                        <button
                          type="button"
                          className="btn-secondary !py-1 !px-2.5 text-xs"
                          onClick={() => openSubscription(u)}
                          title={t('admin.subManage')}
                        >
                          <Crown size={13} />
                        </button>
                      )}
                      <button
                        type="button"
                        className={u.is_active ? 'btn-danger !py-1 !px-2.5 text-xs' : 'btn-secondary !py-1 !px-2.5 text-xs'}
                        onClick={() => toggleActive(u)}
                      >
                        {u.is_active ? t('admin.deactivate') : t('admin.activate')}
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* create user modal */}
      <Modal open={open} onClose={() => setOpen(false)} title={t('admin.addUser')}>
        <form onSubmit={handleSubmit(onCreate)} className="space-y-4">
          <div>
            <label className="label" htmlFor="uname">{t('admin.fullName')} *</label>
            <input id="uname" className="input" {...register('full_name', { required: t('validation.required'), minLength: 2 })} />
            {errors.full_name && <p className="text-xs text-danger mt-1">{errors.full_name.message}</p>}
          </div>
          <div>
            <label className="label" htmlFor="ulogin">{t('admin.username')} *</label>
            <input
              id="ulogin"
              className="input"
              {...register('username', {
                required: t('validation.required'),
                minLength: { value: 3, message: t('validation.minLength', { count: 3 }) },
                pattern: { value: /^[a-zA-Z0-9_.-]+$/, message: t('validation.required') },
              })}
            />
            {errors.username && <p className="text-xs text-danger mt-1">{errors.username.message}</p>}
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="label" htmlFor="urole">{t('admin.role')} *</label>
              <select id="urole" className="input" {...register('role')}>
                <option value="farmer">{t('admin.role_farmer')}</option>
                <option value="agronom">{t('admin.role_agronom')}</option>
                <option value="admin">{t('admin.role_admin')}</option>
              </select>
            </div>
            <div>
              <label className="label" htmlFor="ulang">{t('profile.language')}</label>
              <select id="ulang" className="input" {...register('preferred_language')}>
                <option value="uz-Latn">🇺🇿 O'zbekcha (Lotin)</option>
                <option value="uz-Cyrl">🇺🇿 Ўзбекча (Кирилл)</option>
                <option value="en">🇬🇧 English</option>
                <option value="ru">🇷🇺 Русский</option>
              </select>
            </div>
          </div>
          <div>
            <label className="label" htmlFor="uregion">{t('common.region')}</label>
            <input id="uregion" className="input" {...register('region')} />
          </div>
          <div>
            <label className="label" htmlFor="utg">Telegram @username</label>
            <input
              id="utg"
              className="input"
              placeholder="@fermer_user"
              {...register('telegram_username', {
                pattern: { value: /^@?[a-zA-Z][a-zA-Z0-9_-]{3,63}$/, message: t('validation.required') },
              })}
            />
            <p className="text-xs text-textSecondary mt-1">{t('admin.tgUsernameHint')}</p>
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <button type="button" className="btn-secondary" onClick={() => setOpen(false)}>{t('common.cancel')}</button>
            <button type="submit" className="btn-primary" disabled={isSubmitting}>{t('common.create')}</button>
          </div>
        </form>
      </Modal>

      {/* invitation code modal */}
      <Modal open={Boolean(inviteResult)} onClose={() => setInviteResult(null)} title={t('admin.inviteCode')}>
        <p className="text-sm text-textSecondary">{t('admin.inviteCodeHint')}</p>
        <div className="mt-4 rounded-xl bg-surface2 border border-borderc p-5 text-center">
          <p className="text-xs text-textSecondary">@{inviteResult?.username}</p>
          <p className="text-3xl font-extrabold tracking-[0.3em] text-primary mt-1">{inviteResult?.code}</p>
        </div>
        <button type="button" className="btn-secondary w-full mt-4" onClick={() => copy(inviteResult?.code || '')}>
          <Copy size={15} /> {t('admin.copyCode')}
        </button>
      </Modal>

      {/* temp password modal */}
      <Modal open={Boolean(tempPassword)} onClose={() => setTempPassword(null)} title={t('admin.tempPassword')}>
        <p className="text-sm text-textSecondary">{t('admin.tempPasswordHint')}</p>
        <div className="mt-4 rounded-xl bg-surface2 border border-borderc p-5 text-center">
          <p className="text-xs text-textSecondary">@{tempPassword?.username}</p>
          <p className="text-2xl font-bold text-warning mt-1 select-all">{tempPassword?.password}</p>
        </div>
        <button type="button" className="btn-secondary w-full mt-4" onClick={() => copy(tempPassword?.password || '')}>
          <Copy size={15} /> {t('admin.copyCode')}
        </button>
      </Modal>

      {/* subscription management modal */}
      <SubscriptionModal
        target={subTarget}
        data={subData}
        saving={subSaving}
        onClose={() => {
          setSubTarget(null);
          setSubData(null);
        }}
        onSave={saveSubscription}
      />
    </div>
  );
}

function SubscriptionModal({
  target,
  data,
  saving,
  onClose,
  onSave,
}: {
  target: User | null;
  data: SubscriptionAdmin | null;
  saving: boolean;
  onClose: () => void;
  onSave: (v: {
    plan: 'free' | 'pro';
    diagnoses_limit: string;
    advice_limit: string;
    paid_until: string;
    reset_usage: boolean;
  }) => void;
}) {
  const { t } = useTranslation();
  const [plan, setPlan] = useState<'free' | 'pro'>('free');
  const [diagLimit, setDiagLimit] = useState('');
  const [advLimit, setAdvLimit] = useState('');
  const [paidUntil, setPaidUntil] = useState('');
  const [resetUsage, setResetUsage] = useState(false);
  const [loadedId, setLoadedId] = useState<string | null>(null);

  // Reset the form whenever a new user's subscription is loaded
  useEffect(() => {
    if (!data || !target || loadedId === target.id) return;
    setLoadedId(target.id);
    setPlan(data.plan === 'pro' ? 'pro' : 'free');
    setDiagLimit(String(data.diagnoses_limit));
    setAdvLimit(String(data.advice_limit));
    setPaidUntil(
      data.paid_until ? data.paid_until.slice(0, 10) : '',
    );
    setResetUsage(false);
  }, [data, target, loadedId]);

  return (
    <Modal open={Boolean(target)} onClose={onClose} title={t('admin.subManage')}>
      {!data ? (
        <LoadingBlock />
      ) : (
        <form
          className="space-y-4"
          onSubmit={(e) => {
            e.preventDefault();
            onSave({
              plan,
              diagnoses_limit: diagLimit,
              advice_limit: advLimit,
              paid_until: paidUntil,
              reset_usage: resetUsage,
            });
          }}
        >
          <div className="rounded-xl bg-surface2 border border-borderc p-4 text-sm">
            <p className="font-medium">@{data.username}</p>
            <p className="text-xs text-textSecondary mt-1">
              {t('admin.subRoleDefault', { role: t(`admin.role_${data.role}`) })} ·{' '}
              {data.diagnoses_used}/{data.diagnoses_limit === -1 ? '∞' : data.diagnoses_limit} ·{' '}
              {data.advice_used}/{data.advice_limit === -1 ? '∞' : data.advice_limit}
            </p>
          </div>

          <div>
            <label className="label" htmlFor="subplan">{t('admin.subPlan')}</label>
            <select id="subplan" className="input" value={plan} onChange={(e) => setPlan(e.target.value as 'free' | 'pro')}>
              <option value="free">{t('subscription.planFree')}</option>
              <option value="pro">{t('subscription.planPro')}</option>
            </select>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="label" htmlFor="subdiag">{t('admin.subDiagLimit')}</label>
              <input
                id="subdiag"
                type="number"
                min={-1}
                className="input"
                value={diagLimit}
                onChange={(e) => setDiagLimit(e.target.value)}
              />
              <p className="text-xs text-textSecondary mt-1">{t('admin.subUnlimitedHint')}</p>
            </div>
            <div>
              <label className="label" htmlFor="subadv">{t('admin.subAdvLimit')}</label>
              <input
                id="subadv"
                type="number"
                min={-1}
                className="input"
                value={advLimit}
                onChange={(e) => setAdvLimit(e.target.value)}
              />
              <p className="text-xs text-textSecondary mt-1">{t('admin.subUnlimitedHint')}</p>
            </div>
          </div>

          <div>
            <label className="label" htmlFor="subpaid">{t('admin.subPaidUntil')}</label>
            <input
              id="subpaid"
              type="date"
              className="input"
              value={paidUntil}
              onChange={(e) => setPaidUntil(e.target.value)}
            />
          </div>

          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={resetUsage} onChange={(e) => setResetUsage(e.target.checked)} />
            {t('admin.subResetUsage')}
          </label>

          <div className="flex justify-end gap-2 pt-2">
            <button type="button" className="btn-secondary" onClick={onClose}>{t('common.cancel')}</button>
            <button type="submit" className="btn-primary" disabled={saving}>{t('common.save')}</button>
          </div>
        </form>
      )}
    </Modal>
  );
}
