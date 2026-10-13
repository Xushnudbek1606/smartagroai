import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import {
  BrainCircuit,
  CloudSun,
  FlaskConical,
  MessageCircle,
  Sprout,
  Upload,
  Wind,
} from 'lucide-react';
import { api, extractError } from '../services/api';
import { useAuthStore } from '../store/auth';
import { Badge, EmptyState, ErrorState, LoadingBlock, StatCard, showToast } from '../components/ui';
import { formatDate, formatNumber, formatRelative } from '../utils/format';
import type { Conversation, Diagnosis, Farm, WeatherCurrent } from '../types';

export default function FarmerDashboard() {
  const { t, i18n } = useTranslation();
  const lang = i18n.language as never;
  const user = useAuthStore((s) => s.user);
  const fileRef = useRef<HTMLInputElement>(null);

  const [farms, setFarms] = useState<Farm[] | null>(null);
  const [diagnoses, setDiagnoses] = useState<Diagnosis[] | null>(null);
  const [weather, setWeather] = useState<WeatherCurrent | null>(null);
  const [convs, setConvs] = useState<Conversation[] | null>(null);
  const [weatherError, setWeatherError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);

  useEffect(() => {
    api.get<{ items: Farm[] }>('/farms?page_size=50').then((r) => setFarms(r.data.items)).catch(() => setFarms([]));
    api.get<{ items: Diagnosis[] }>('/diagnoses?page_size=4').then((r) => setDiagnoses(r.data.items)).catch(() => setDiagnoses([]));
    api.get<Conversation[]>('/conversations').then((r) => setConvs(r.data)).catch(() => setConvs([]));
    const loc = user?.region ? `${user.region}${user.district ? ', ' + user.district : ''}` : 'Toshkent';
    api.get<WeatherCurrent>('/weather/current', { params: { location: loc } })
      .then((r) => setWeather(r.data))
      .catch((err) => setWeatherError(extractError(err).message));
  }, [user?.region, user?.district]);

  const totalArea = (farms || []).reduce((sum, f) => sum + (f.area_hectares || 0), 0);
  const unread = (convs || []).reduce((sum, c) => sum + c.unread_count, 0);

  async function quickUpload(file: File) {
    setUploading(true);
    try {
      const form = new FormData();
      form.append('file', file);
      await api.post('/diagnoses', form, { headers: { 'Content-Type': 'multipart/form-data' } });
      showToast(t('diagnosis.uploadSuccess'), 'success');
      const r = await api.get<{ items: Diagnosis[] }>('/diagnoses?page_size=4');
      setDiagnoses(r.data.items);
    } catch (err) {
      const e = extractError(err);
      showToast(e.code === 'ai_not_configured' ? t('diagnosis.notConfiguredText') : e.message, 'error');
    } finally {
      setUploading(false);
    }
  }

  if (farms === null || diagnoses === null) return <LoadingBlock />;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">{t('dashboard.farmerTitle')}</h1>
          <p className="text-sm text-textSecondary">
            {t('dashboard.welcome')}, {user?.full_name}
          </p>
        </div>
        <Link to="/diagnosis" className="btn-primary">
          <BrainCircuit size={17} /> {t('dashboard.newDiagnosis')}
        </Link>
      </div>

      {/* stat cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard label={t('dashboard.farms')} value={farms.length} icon={<FlaskConical size={20} />} />
        <StatCard
          label={t('dashboard.totalArea')}
          value={`${formatNumber(totalArea, lang, 1)} ${t('dashboard.hectares')}`}
          icon={<Sprout size={20} />}
          accent="text-accent"
        />
        <StatCard label={t('dashboard.diagnoses')} value={diagnoses.length} icon={<BrainCircuit size={20} />} accent="text-warning" />
        <StatCard label={t('dashboard.newMessages')} value={unread} icon={<MessageCircle size={20} />} accent="text-accent" />
      </div>

      <div className="grid lg:grid-cols-3 gap-6">
        {/* weather */}
        <div className="card p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold flex items-center gap-2"><CloudSun size={18} className="text-accent" /> {t('dashboard.currentWeather')}</h2>
            <Link to="/weather" className="text-xs text-accent hover:underline">{t('common.viewAll')}</Link>
          </div>
          {weatherError ? (
            <p className="text-sm text-textSecondary">{t('weather.notConfiguredText')}</p>
          ) : weather ? (
            <div>
              <div className="flex items-baseline gap-2">
                <span className="text-4xl font-bold">{Math.round(weather.temperature)}{t('weather.temperatureUnit')}</span>
                <span className="text-textSecondary text-sm capitalize">{weather.description}</span>
              </div>
              <div className="mt-4 grid grid-cols-3 gap-2 text-sm">
                <div className="rounded-xl bg-surface2 p-3">
                  <p className="text-textSecondary text-xs">{t('weather.feelsLike')}</p>
                  <p className="font-semibold">{Math.round(weather.feels_like)}°</p>
                </div>
                <div className="rounded-xl bg-surface2 p-3">
                  <p className="text-textSecondary text-xs">{t('weather.humidity')}</p>
                  <p className="font-semibold">{weather.humidity}%</p>
                </div>
                <div className="rounded-xl bg-surface2 p-3">
                  <p className="text-textSecondary text-xs">{t('weather.wind')}</p>
                  <p className="font-semibold">{weather.wind_speed} {t('weather.windUnit')}</p>
                </div>
              </div>
              <p className="text-[11px] text-textSecondary mt-3">
                {t('weather.updatedAt')}: {formatDate(weather.fetched_at, lang, { timeStyle: 'short' })}
              </p>
            </div>
          ) : (
            <LoadingBlock />
          )}
        </div>

        {/* latest diagnoses */}
        <div className="card p-6 lg:col-span-2">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold">{t('dashboard.latestDiagnoses')}</h2>
            <div className="flex gap-2">
              <input
                ref={fileRef}
                type="file"
                accept="image/jpeg,image/png,image/webp"
                className="hidden"
                onChange={(e) => {
                  const f = e.target.files?.[0];
                  if (f) quickUpload(f);
                  e.target.value = '';
                }}
              />
              <button type="button" className="btn-secondary !py-1.5 text-xs" onClick={() => fileRef.current?.click()} disabled={uploading}>
                <Upload size={14} /> {uploading ? t('common.loading') : t('dashboard.quickUpload')}
              </button>
              <Link to="/diagnoses" className="text-xs text-accent hover:underline self-center">{t('common.viewAll')}</Link>
            </div>
          </div>
          {diagnoses.length === 0 ? (
            <EmptyState title={t('dashboard.noDiagnoses')} hint={t('dashboard.noDiagnosesHint')} />
          ) : (
            <div className="space-y-3">
              {diagnoses.map((d) => (
                <Link
                  key={d.id}
                  to={`/diagnoses/${d.id}`}
                  className="flex items-center gap-4 rounded-xl border border-borderc bg-surface2/50 p-3 hover:border-primary/40 transition-colors"
                >
                  <img src={d.image_url} alt="" className="w-14 h-14 rounded-lg object-cover bg-surface2" />
                  <div className="min-w-0 flex-1">
                    <p className="font-medium truncate">{d.disease_name || t('diagnosis.severityUnknown')}</p>
                    <p className="text-xs text-textSecondary truncate">
                      {d.predicted_crop || '—'} · {formatRelative(d.created_at, lang)}
                    </p>
                  </div>
                  <Badge tone={d.severity === 'high' ? 'danger' : d.severity === 'medium' ? 'warning' : d.severity === 'low' ? 'success' : 'default'}>
                    {d.confidence != null ? `${Math.round(d.confidence * 100)}%` : '—'}
                  </Badge>
                </Link>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
