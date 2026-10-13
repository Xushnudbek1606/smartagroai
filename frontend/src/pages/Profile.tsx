import { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Camera, MessageCircle, Save, User as UserIcon } from 'lucide-react';
import { api, extractError } from '../services/api';
import { useAuthStore } from '../store/auth';
import { Badge, LoadingBlock, showToast } from '../components/ui';
import { formatDate } from '../utils/format';
import type { Language } from '../types';
import { LANGUAGES } from '../i18n';
import { setLanguage } from '../i18n';

export default function ProfilePage() {
  const { t, i18n } = useTranslation();
  const lang = i18n.language as never;
  const user = useAuthStore((s) => s.user);
  const setUser = useAuthStore((s) => s.setUser);
  const fileRef = useRef<HTMLInputElement>(null);

  const [fullName, setFullName] = useState('');
  const [phone, setPhone] = useState('');
  const [region, setRegion] = useState('');
  const [district, setDistrict] = useState('');
  const [language, setLang] = useState<Language>('uz-Latn');
  const [saving, setSaving] = useState(false);
  const [uploading, setUploading] = useState(false);

  useEffect(() => {
    if (user) {
      setFullName(user.full_name);
      setPhone(user.phone || '');
      setRegion(user.region || '');
      setDistrict(user.district || '');
      setLang(user.preferred_language);
    }
  }, [user]);

  if (!user) return <LoadingBlock />;

  async function save(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    try {
      const resp = await api.patch('/users/me', {
        full_name: fullName.trim(),
        phone: phone.trim() || null,
        region: region.trim() || null,
        district: district.trim() || null,
        preferred_language: language,
      });
      setUser(resp.data);
      setLanguage(language);
      showToast(t('profile.saved'), 'success');
    } catch (err) {
      showToast(extractError(err).message, 'error');
    } finally {
      setSaving(false);
    }
  }

  async function uploadAvatar(file: File) {
    setUploading(true);
    try {
      const form = new FormData();
      form.append('file', file);
      const resp = await api.post('/users/me/avatar', form, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      setUser(resp.data);
      showToast(t('profile.saved'), 'success');
    } catch (err) {
      const e = extractError(err);
      showToast(e.code === 'file_too_large' ? t('profile.avatarTooLarge') : t('profile.avatarInvalid'), 'error');
    } finally {
      setUploading(false);
    }
  }

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold">{t('profile.title')}</h1>
        <p className="text-sm text-textSecondary">{t('profile.subtitle')}</p>
      </div>

      {/* avatar + identity */}
      <div className="card p-6 flex flex-wrap items-center gap-5">
        <div className="relative">
          {user.avatar_url ? (
            <img src={user.avatar_url} alt="" className="w-20 h-20 rounded-2xl object-cover" />
          ) : (
            <div className="w-20 h-20 rounded-2xl bg-accent/15 text-accent flex items-center justify-center text-2xl font-bold">
              {user.full_name.charAt(0)}
            </div>
          )}
          <input
            ref={fileRef}
            type="file"
            accept="image/jpeg,image/png,image/webp"
            className="hidden"
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) uploadAvatar(f);
              e.target.value = '';
            }}
          />
          <button
            type="button"
            className="absolute -bottom-2 -right-2 rounded-xl bg-primary text-background p-2"
            onClick={() => fileRef.current?.click()}
            disabled={uploading}
            aria-label={t('profile.uploadAvatar')}
          >
            <Camera size={15} />
          </button>
        </div>
        <div className="min-w-0">
          <p className="font-bold text-lg truncate">{user.full_name}</p>
          <p className="text-sm text-textSecondary">@{user.username}</p>
          <div className="flex flex-wrap items-center gap-2 mt-2">
            <Badge tone={user.role === 'admin' ? 'warning' : user.role === 'agronom' ? 'accent' : 'success'}>
              {t(`admin.role_${user.role}`)}
            </Badge>
            <Badge tone={user.telegram_id ? 'success' : 'default'}>
              {user.telegram_id ? t('profile.telegramLinked') : t('profile.telegramNotLinked')}
            </Badge>
          </div>
        </div>
      </div>

      {/* telegram linking hint */}
      <div className="card p-5">
        <div className="flex items-center gap-2 mb-1.5">
          <MessageCircle size={16} className="text-accent" />
          <p className="font-semibold text-sm">{t('profile.telegram')}</p>
        </div>
        <p className="text-xs text-textSecondary">{t('profile.telegramLinkHint')}</p>
      </div>

      {/* form */}
      <form onSubmit={save} className="card p-6 space-y-4">
        <div>
          <label className="label" htmlFor="pname">{t('profile.fullName')}</label>
          <input id="pname" className="input" value={fullName} onChange={(e) => setFullName(e.target.value)} required minLength={2} />
        </div>
        <div className="grid sm:grid-cols-2 gap-4">
          <div>
            <label className="label" htmlFor="pphone">{t('profile.phone')}</label>
            <input id="pphone" className="input" value={phone} onChange={(e) => setPhone(e.target.value)} placeholder="+998..." />
          </div>
          <div>
            <label className="label" htmlFor="plang">{t('profile.language')}</label>
            <select id="plang" className="input" value={language} onChange={(e) => setLang(e.target.value as Language)}>
              {LANGUAGES.map((l) => (
                <option key={l.code} value={l.code}>{l.flag} {l.name}</option>
              ))}
            </select>
          </div>
        </div>
        <div className="grid sm:grid-cols-2 gap-4">
          <div>
            <label className="label" htmlFor="pregion">{t('profile.region')}</label>
            <input id="pregion" className="input" value={region} onChange={(e) => setRegion(e.target.value)} />
          </div>
          <div>
            <label className="label" htmlFor="pdistrict">{t('profile.district')}</label>
            <input id="pdistrict" className="input" value={district} onChange={(e) => setDistrict(e.target.value)} />
          </div>
        </div>
        <p className="text-xs text-textSecondary">
          {t('profile.memberSince')}: {formatDate(user.created_at, lang)}
        </p>
        <button type="submit" className="btn-primary" disabled={saving}>
          <Save size={16} /> {saving ? t('common.loading') : t('common.save')}
        </button>
      </form>
    </div>
  );
}
