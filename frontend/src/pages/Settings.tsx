import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Bell, Languages, Moon } from 'lucide-react';
import { api, extractError } from '../services/api';
import { useAuthStore } from '../store/auth';
import { LANGUAGES, setLanguage } from '../i18n';
import { showToast } from '../components/ui';
import type { Language } from '../types';

export default function SettingsPage() {
  const { t } = useTranslation();
  const user = useAuthStore((s) => s.user);
  const setUser = useAuthStore((s) => s.setUser);
  const [telegramEnabled, setTelegramEnabled] = useState(user?.telegram_notifications_enabled ?? true);
  const [saving, setSaving] = useState(false);

  async function toggleTelegram(next: boolean) {
    setTelegramEnabled(next);
    setSaving(true);
    try {
      const resp = await api.patch('/users/me', { telegram_notifications_enabled: next });
      setUser(resp.data);
      showToast(t('settings.saved'), 'success');
    } catch (err) {
      setTelegramEnabled(!next);
      showToast(extractError(err).message, 'error');
    } finally {
      setSaving(false);
    }
  }

  async function changeLang(code: Language) {
    setLanguage(code);
    try {
      const resp = await api.patch('/users/me', { preferred_language: code });
      setUser(resp.data);
    } catch {
      /* local selection persists even if API fails */
    }
  }

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold">{t('settings.title')}</h1>
        <p className="text-sm text-textSecondary">{t('settings.subtitle')}</p>
      </div>

      <div className="card p-6">
        <div className="flex items-center gap-2 mb-4">
          <Moon size={17} className="text-primary" />
          <h2 className="font-semibold">{t('settings.appearance')}</h2>
        </div>
        <div className="flex items-center justify-between rounded-xl bg-surface2 border border-borderc px-4 py-3">
          <div>
            <p className="text-sm font-medium">{t('settings.darkMode')}</p>
            <p className="text-xs text-textSecondary">{t('settings.darkModeHint')}</p>
          </div>
          <span className="badge bg-primary/15 text-primary border border-primary/30">✓ {t('settings.darkMode')}</span>
        </div>
      </div>

      <div className="card p-6">
        <div className="flex items-center gap-2 mb-4">
          <Languages size={17} className="text-accent" />
          <h2 className="font-semibold">{t('settings.language')}</h2>
        </div>
        <p className="text-xs text-textSecondary mb-3">{t('settings.languageHint')}</p>
        <div className="grid grid-cols-2 gap-2">
          {LANGUAGES.map((l) => (
            <button
              key={l.code}
              type="button"
              onClick={() => changeLang(l.code)}
              className={`rounded-xl border px-4 py-3 text-sm text-left transition-colors ${
                user?.preferred_language === l.code
                  ? 'border-primary/50 bg-primary/10 text-primary'
                  : 'border-borderc bg-surface2 hover:border-primary/30'
              }`}
            >
              {l.flag} {l.name}
            </button>
          ))}
        </div>
      </div>

      <div className="card p-6">
        <div className="flex items-center gap-2 mb-4">
          <Bell size={17} className="text-warning" />
          <h2 className="font-semibold">{t('settings.notifications')}</h2>
        </div>
        <label className="flex items-center justify-between rounded-xl bg-surface2 border border-borderc px-4 py-3 cursor-pointer">
          <div>
            <p className="text-sm font-medium">{t('settings.telegramNotifications')}</p>
            <p className="text-xs text-textSecondary">{t('settings.telegramNotificationsHint')}</p>
          </div>
          <input
            type="checkbox"
            className="w-5 h-5 accent-[#22C55E]"
            checked={telegramEnabled}
            disabled={saving || !user?.telegram_id}
            onChange={(e) => toggleTelegram(e.target.checked)}
          />
        </label>
        {!user?.telegram_id && (
          <p className="text-xs text-textSecondary mt-2">{t('profile.telegramLinkHint')}</p>
        )}
      </div>
    </div>
  );
}
