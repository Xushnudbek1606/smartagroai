import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import {
  BrainCircuit,
  CloudSun,
  Languages,
  Leaf,
  MessageCircle,
  ShieldCheck,
  Smartphone,
  Sparkles,
  Sprout,
  Users,
  Zap,
} from 'lucide-react';
import LanguageSwitcher from '../components/LanguageSwitcher';
import { api } from '../services/api';

interface BannerSettings {
  title?: string;
  text?: string;
  image?: string;
}

interface LandingContact {
  email?: string;
  phone?: string;
  telegram?: string;
  address?: string;
}

interface PublicSettings {
  settings: { landing_banner?: BannerSettings; contact?: LandingContact };
}

const DEFAULT_CONTACT_EMAIL = 'info@smartagro.uz';

export default function Landing() {
  const { t } = useTranslation();
  const [banner, setBanner] = useState<BannerSettings | null>(null);
  const [contact, setContact] = useState<LandingContact | null>(null);

  useEffect(() => {
    // public, best-effort landing content maintained under Admin → Settings
    api
      .get<PublicSettings>('/public/settings')
      .then((r) => {
        setBanner(r.data.settings?.landing_banner || null);
        setContact(r.data.settings?.contact || null);
      })
      .catch(() => undefined);
  }, []);

  return (
    <div className="min-h-screen bg-background text-textPrimary">
      {/* header */}
      <header className="border-b border-borderc bg-surface/70 backdrop-blur sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between gap-3">
          <div className="flex items-center gap-2.5">
            <div className="rounded-xl bg-primary/15 p-2 text-primary">
              <Sprout size={22} />
            </div>
            <span className="font-bold text-lg tracking-tight">{t('common.appName')}</span>
          </div>
          <nav className="hidden md:flex items-center gap-6 text-sm text-textSecondary">
            <a href="#features" className="hover:text-textPrimary">{t('landing.benefitsTitle')}</a>
            <a href="#roles" className="hover:text-textPrimary">{t('landing.aboutTitle')}</a>
            <a href="#telegram" className="hover:text-textPrimary">{t('landing.telegramTitle')}</a>
          </nav>
          <div className="flex items-center gap-2">
            <LanguageSwitcher />
            <Link to="/login" className="btn-primary">{t('landing.login')}</Link>
          </div>
        </div>
      </header>

      {/* hero */}
      <section className="relative overflow-hidden">
        <div
          className="absolute inset-0 opacity-[0.13]"
          style={{
            backgroundImage:
              "url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='1400' height='700' viewBox='0 0 1400 700'%3E%3Cdefs%3E%3ClinearGradient id='g' x1='0' y1='0' x2='1' y2='1'%3E%3Cstop offset='0' stop-color='%2322C55E'/%3E%3Cstop offset='1' stop-color='%2338BDF8'/%3E%3C/linearGradient%3E%3C/defs%3E%3Crect width='1400' height='700' fill='%230B1220'/%3E%3Cpath d='M0 520 Q 200 420 400 500 T 800 480 T 1200 500 T 1400 460 L1400 700 L0 700Z' fill='url(%23g)' opacity='0.35'/%3E%3Cpath d='M0 580 Q 300 500 600 560 T 1200 545 T 1400 530 L1400 700 L0 700Z' fill='url(%23g)' opacity='0.25'/%3E%3Ccircle cx='1150' cy='170' r='90' fill='url(%23g)' opacity='0.35'/%3E%3C/svg%3E\")",
            backgroundSize: 'cover',
            backgroundPosition: 'center',
          }}
          aria-hidden
        />
        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 pt-20 pb-24 text-center">
          <div className="inline-flex items-center gap-2 rounded-full border border-primary/30 bg-primary/10 px-4 py-1.5 text-xs font-semibold text-primary mb-6">
            <Sparkles size={14} /> 🇺🇿 {t('landing.badge')}
          </div>
          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold tracking-tight max-w-4xl mx-auto leading-tight">
            <span className="bg-gradient-to-r from-primary via-accent to-primary bg-clip-text text-transparent">
              {banner?.title || t('landing.heroTitle')}
            </span>
          </h1>
          <p className="mt-6 text-textSecondary text-base sm:text-lg max-w-2xl mx-auto leading-relaxed">
            {banner?.text || t('landing.heroSubtitle')}
          </p>
          <div className="mt-9 flex flex-col sm:flex-row items-center justify-center gap-3">
            <Link to="/login" className="btn-primary !px-7 !py-3 text-base">
              {t('landing.getStarted')} →
            </Link>
            <a href="#features" className="btn-secondary !px-7 !py-3 text-base">
              {t('landing.benefitsTitle')}
            </a>
          </div>

          {/* hero stats strip */}
          <div className="mt-14 grid grid-cols-2 lg:grid-cols-4 gap-4 max-w-4xl mx-auto">
            {[
              { icon: BrainCircuit, label: t('landing.diagnosisTitle') },
              { icon: CloudSun, label: t('landing.weatherTitle') },
              { icon: MessageCircle, label: t('landing.collabTitle') },
              { icon: Languages, label: '🇺🇿 🇬🇧 🇷🇺' },
            ].map(({ icon: Icon, label }, i) => (
              <div key={i} className="card px-4 py-4 flex items-center gap-3">
                <div className="rounded-lg bg-surface2 p-2 text-primary"><Icon size={18} /></div>
                <span className="text-sm text-textSecondary text-left">{label}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* features */}
      <section id="features" className="max-w-7xl mx-auto px-4 sm:px-6 py-20">
        <h2 className="text-3xl font-bold text-center">{t('landing.benefitsTitle')}</h2>
        <div className="mt-12 grid sm:grid-cols-2 lg:grid-cols-4 gap-5">
          {[
            { icon: Zap, title: t('landing.benefit1Title'), text: t('landing.benefit1Text') },
            { icon: Languages, title: t('landing.benefit2Title'), text: t('landing.benefit2Text') },
            { icon: ShieldCheck, title: t('landing.benefit3Title'), text: t('landing.benefit3Text') },
            { icon: Smartphone, title: t('landing.benefit4Title'), text: t('landing.benefit4Text') },
          ].map(({ icon: Icon, title, text }, i) => (
            <div key={i} className="card p-6 hover:border-primary/40 transition-colors">
              <div className="rounded-xl bg-primary/10 w-fit p-3 text-primary mb-4"><Icon size={22} /></div>
              <h3 className="font-semibold mb-1.5">{title}</h3>
              <p className="text-sm text-textSecondary leading-relaxed">{text}</p>
            </div>
          ))}
        </div>
      </section>

      {/* how it works */}
      <section className="border-y border-borderc bg-surface/40">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-20 grid lg:grid-cols-3 gap-6">
          {[
            { icon: BrainCircuit, title: t('landing.diagnosisTitle'), text: t('landing.diagnosisText') },
            { icon: CloudSun, title: t('landing.weatherTitle'), text: t('landing.weatherText') },
            { icon: Users, title: t('landing.collabTitle'), text: t('landing.collabText') },
          ].map(({ icon: Icon, title, text }, i) => (
            <div key={i} className="flex gap-4">
              <div className="shrink-0 rounded-2xl bg-accent/10 text-accent w-12 h-12 flex items-center justify-center">
                <Icon size={22} />
              </div>
              <div>
                <h3 className="font-semibold mb-1">{title}</h3>
                <p className="text-sm text-textSecondary leading-relaxed">{text}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* roles */}
      <section id="roles" className="max-w-7xl mx-auto px-4 sm:px-6 py-20">
        <h2 className="text-3xl font-bold text-center">{t('landing.aboutTitle')}</h2>
        <div className="mt-12 grid md:grid-cols-3 gap-5">
          {[
            { icon: Sprout, title: t('landing.roleFarmer'), text: t('landing.roleFarmerText'), tone: 'text-primary bg-primary/10' },
            { icon: Leaf, title: t('landing.roleAgronom'), text: t('landing.roleAgronomText'), tone: 'text-accent bg-accent/10' },
            { icon: ShieldCheck, title: t('landing.roleAdmin'), text: t('landing.roleAdminText'), tone: 'text-warning bg-warning/10' },
          ].map(({ icon: Icon, title, text, tone }, i) => (
            <div key={i} className="card p-6">
              <div className={`rounded-xl w-fit p-3 mb-4 ${tone}`}><Icon size={22} /></div>
              <h3 className="font-semibold mb-1.5">{title}</h3>
              <p className="text-sm text-textSecondary leading-relaxed">{text}</p>
            </div>
          ))}
        </div>
      </section>

      {/* telegram */}
      <section id="telegram" className="max-w-7xl mx-auto px-4 sm:px-6 pb-20">
        <div className="card p-8 sm:p-12 bg-gradient-to-br from-surface to-surface2 flex flex-col md:flex-row items-center gap-8">
          <div className="rounded-2xl bg-accent/15 text-accent p-5 shrink-0">
            <MessageCircle size={40} />
          </div>
          <div className="text-center md:text-left">
            <h2 className="text-2xl font-bold">{t('landing.telegramTitle')}</h2>
            <p className="mt-2 text-textSecondary max-w-2xl">{t('landing.telegramText')}</p>
            <div className="mt-6 grid sm:grid-cols-2 gap-2 text-sm text-textSecondary max-w-2xl">
              {[
                { c: '/start', d: t('telegram.cmdStart') },
                { c: '/help', d: t('telegram.cmdHelp') },
                { c: '/account', d: t('telegram.cmdAccount') },
                { c: '/weather', d: t('telegram.cmdWeather') },
                { c: '/language', d: t('telegram.cmdLanguage') },
                { c: '/notifications', d: t('telegram.cmdNotifications') },
              ].map(({ c, d }) => (
                <div key={c} className="flex items-center gap-2">
                  <code className="rounded bg-surface px-2 py-0.5 text-primary text-xs">{c}</code>
                  <span className="truncate">{d}</span>
                </div>
              ))}
            </div>
            <Link to="/login" className="btn-primary mt-7 inline-flex">{t('landing.openApp')}</Link>
          </div>
        </div>
      </section>

      {/* footer */}
      <footer className="border-t border-borderc bg-surface">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-10 flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2.5">
            <div className="rounded-xl bg-primary/15 p-2 text-primary"><Sprout size={20} /></div>
            <span className="font-bold">{t('common.appName')}</span>
          </div>
          <p className="text-sm text-textSecondary">
            © {new Date().getFullYear()} {t('common.appName')}. {t('landing.footerRights')}
          </p>
          <p className="text-sm text-textSecondary">
            {t('landing.contactText')}{' '}
            <a
              href={`mailto:${contact?.email || DEFAULT_CONTACT_EMAIL}`}
              className="hover:text-textPrimary"
            >
              {contact?.email || DEFAULT_CONTACT_EMAIL}
            </a>
            {contact?.phone ? ` · ${contact.phone}` : ''}
            {contact?.telegram ? ` · ${contact.telegram}` : ''}
          </p>
        </div>
      </footer>
    </div>
  );
}
