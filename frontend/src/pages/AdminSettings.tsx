import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Mail, MapPin, Phone, Save, Send, Sparkles } from 'lucide-react';
import { api, extractError } from '../services/api';
import { ErrorState, LoadingBlock, showToast } from '../components/ui';

interface LandingBanner {
  title?: string;
  text?: string;
  image?: string;
}

interface ContactInfo {
  email?: string;
  phone?: string;
  telegram?: string;
  address?: string;
}

interface SettingsResponse {
  settings: {
    landing_banner?: LandingBanner;
    contact?: ContactInfo;
  };
}

const EMPTY_CONTACT: ContactInfo = { email: '', phone: '', telegram: '', address: '' };

export default function AdminSettings() {
  const { t } = useTranslation();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const [banner, setBanner] = useState<LandingBanner>({ title: '', text: '', image: '' });
  const [contact, setContact] = useState<ContactInfo>(EMPTY_CONTACT);

  function load() {
    setLoading(true);
    setError(null);
    api
      .get<SettingsResponse>('/admin/settings')
      .then((r) => {
        const s = r.data.settings || {};
        setBanner({
          title: s.landing_banner?.title || '',
          text: s.landing_banner?.text || '',
          image: s.landing_banner?.image || '',
        });
        setContact({ ...EMPTY_CONTACT, ...(s.contact || {}) });
      })
      .catch((err) => setError(extractError(err).message))
      .finally(() => setLoading(false));
  }

  useEffect(load, []);

  async function save() {
    setSaving(true);
    try {
      const resp = await api.patch<SettingsResponse>('/admin/settings', {
        settings: {
          landing_banner: {
            title: banner.title?.trim() || '',
            text: banner.text?.trim() || '',
            image: banner.image?.trim() || '',
          },
          contact: {
            email: contact.email?.trim() || '',
            phone: contact.phone?.trim() || '',
            telegram: contact.telegram?.trim() || '',
            address: contact.address?.trim() || '',
          },
        },
      });
      const s = resp.data.settings || {};
      setBanner({
        title: s.landing_banner?.title || '',
        text: s.landing_banner?.text || '',
        image: s.landing_banner?.image || '',
      });
      setContact({ ...EMPTY_CONTACT, ...(s.contact || {}) });
      showToast(t('admin.settingsSaved'), 'success');
    } catch (err) {
      showToast(extractError(err).message, 'error');
    } finally {
      setSaving(false);
    }
  }

  if (error) return <ErrorState message={error} onRetry={load} />;
  if (loading) return <LoadingBlock />;

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold">{t('admin.settingsTitle')}</h1>
        <p className="text-sm text-textSecondary">{t('admin.settingsSubtitle')}</p>
      </div>

      {/* landing banner */}
      <div className="card p-6 space-y-4">
        <h2 className="font-semibold flex items-center gap-2">
          <Sparkles size={17} className="text-primary" /> {t('admin.bannerSection')}
        </h2>
        <div>
          <label className="label" htmlFor="banner-title">
            {t('admin.bannerTitle')}
          </label>
          <input
            id="banner-title"
            className="input"
            value={banner.title}
            onChange={(e) => setBanner((b) => ({ ...b, title: e.target.value }))}
            maxLength={140}
          />
        </div>
        <div>
          <label className="label" htmlFor="banner-text">
            {t('admin.bannerText')}
          </label>
          <textarea
            id="banner-text"
            className="input min-h-[80px]"
            value={banner.text}
            onChange={(e) => setBanner((b) => ({ ...b, text: e.target.value }))}
            maxLength={400}
          />
        </div>
        <div>
          <label className="label" htmlFor="banner-image">
            {t('admin.bannerImageUrl')}
          </label>
          <input
            id="banner-image"
            className="input"
            placeholder="https://..."
            value={banner.image}
            onChange={(e) => setBanner((b) => ({ ...b, image: e.target.value }))}
          />
        </div>
      </div>

      {/* contact info */}
      <div className="card p-6 space-y-4">
        <h2 className="font-semibold flex items-center gap-2">
          <Mail size={17} className="text-accent" /> {t('admin.contactSection')}
        </h2>
        <div className="grid sm:grid-cols-2 gap-4">
          <div>
            <label className="label" htmlFor="contact-email">
              {t('admin.contactEmail')}
            </label>
            <input
              id="contact-email"
              type="email"
              className="input"
              placeholder="info@smartagro.uz"
              value={contact.email}
              onChange={(e) => setContact((c) => ({ ...c, email: e.target.value }))}
            />
          </div>
          <div>
            <label className="label" htmlFor="contact-phone">
              <Phone size={13} className="inline mr-1" />
              {t('admin.contactPhone')}
            </label>
            <input
              id="contact-phone"
              className="input"
              placeholder="+998 71 000 00 00"
              value={contact.phone}
              onChange={(e) => setContact((c) => ({ ...c, phone: e.target.value }))}
            />
          </div>
          <div>
            <label className="label" htmlFor="contact-telegram">
              <Send size={13} className="inline mr-1" />
              {t('admin.contactTelegram')}
            </label>
            <input
              id="contact-telegram"
              className="input"
              placeholder="@SmartAgroAIBot"
              value={contact.telegram}
              onChange={(e) => setContact((c) => ({ ...c, telegram: e.target.value }))}
            />
          </div>
          <div>
            <label className="label" htmlFor="contact-address">
              <MapPin size={13} className="inline mr-1" />
              {t('admin.contactAddress')}
            </label>
            <input
              id="contact-address"
              className="input"
              value={contact.address}
              onChange={(e) => setContact((c) => ({ ...c, address: e.target.value }))}
            />
          </div>
        </div>
      </div>

      <div className="flex items-center justify-between gap-3">
        <p className="text-xs text-textSecondary">{t('admin.settingsHint')}</p>
        <button type="button" className="btn-primary" onClick={save} disabled={saving}>
          <Save size={15} /> {saving ? t('common.loading') : t('common.save')}
        </button>
      </div>
    </div>
  );
}
