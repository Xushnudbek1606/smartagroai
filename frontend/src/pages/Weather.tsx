import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { AlertTriangle, CloudSun, Droplets, MapPin, Thermometer, Wind } from 'lucide-react';
import { api, extractError } from '../services/api';
import { useAuthStore } from '../store/auth';
import { EmptyState, ErrorState, LoadingBlock } from '../components/ui';
import { formatDate, formatNumber, weekdayName } from '../utils/format';
import type { WeatherCurrent, WeatherForecast, WeatherRegion } from '../types';

export default function WeatherPage() {
  const { t, i18n } = useTranslation();
  const lang = i18n.language as never;
  const user = useAuthStore((s) => s.user);

  const [regions, setRegions] = useState<WeatherRegion[]>([]);
  const [region, setRegion] = useState<string>(user?.region || 'Toshkent shahri');
  const [district, setDistrict] = useState<string>(user?.district || '');
  const [current, setCurrent] = useState<WeatherCurrent | null>(null);
  const [forecast, setForecast] = useState<WeatherForecast | null>(null);
  const [error, setError] = useState<{ code: string; message: string } | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    api
      .get<WeatherRegion[]>('/weather/regions')
      .then((r) => setRegions(r.data))
      .catch(() => setRegions([]));
  }, []);

  useEffect(() => {
    if (!region) return;
    setLoading(true);
    setError(null);
    const loc = district ? `${region}, ${district}` : region;
    Promise.all([
      api.get<WeatherCurrent>('/weather/current', { params: { location: loc } }),
      api.get<WeatherForecast>('/weather/forecast', { params: { location: loc } }),
    ])
      .then(([c, f]) => {
        setCurrent(c.data);
        setForecast(f.data);
      })
      .catch((err) => {
        setCurrent(null);
        setForecast(null);
        setError(extractError(err));
      })
      .finally(() => setLoading(false));
  }, [region, district]);

  const districts = regions.find((r) => r.region === region)?.districts || [];
  const notConfigured = error?.code === 'weather_not_configured';

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">{t('weather.title')}</h1>
          <p className="text-sm text-textSecondary">{t('weather.subtitle')}</p>
        </div>
        <div className="flex flex-wrap gap-3">
          <div>
            <label className="label" htmlFor="region">{t('weather.selectLocation')}</label>
            <select id="region" className="input !w-auto" value={region} onChange={(e) => { setRegion(e.target.value); setDistrict(''); }}>
              {regions.length === 0 && <option value={region}>{region}</option>}
              {regions.map((r) => (
                <option key={r.region} value={r.region}>{r.region}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="label" htmlFor="district">{t('common.district')}</label>
            <select id="district" className="input !w-auto" value={district} onChange={(e) => setDistrict(e.target.value)}>
              <option value="">—</option>
              {districts.map((d) => (
                <option key={d} value={d}>{d}</option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {notConfigured && (
        <div className="card border-warning/40 p-6 max-w-2xl">
          <p className="font-semibold text-warning flex items-center gap-2"><AlertTriangle size={17} /> {t('weather.notConfiguredTitle')}</p>
          <p className="text-sm text-textSecondary mt-1">{t('weather.notConfiguredText')}</p>
        </div>
      )}

      {error && !notConfigured && <ErrorState message={error.message} />}

      {loading && !current && <LoadingBlock />}

      {current && (
        <div className="card p-6 sm:p-8">
          <div className="flex items-center gap-2 text-sm text-textSecondary mb-4">
            <MapPin size={14} /> {current.location}
          </div>
          <div className="flex flex-wrap items-center gap-8">
            <div>
              <div className="flex items-start">
                <span className="text-6xl font-extrabold tracking-tight">
                  {Math.round(current.temperature)}
                </span>
                <span className="text-3xl font-light text-textSecondary mt-1">{t('weather.temperatureUnit')}</span>
              </div>
              <p className="text-textSecondary capitalize mt-1">{current.description}</p>
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 flex-1 min-w-[280px]">
              <Metric icon={<Thermometer size={16} />} label={t('weather.feelsLike')} value={`${Math.round(current.feels_like)}°`} />
              <Metric icon={<Droplets size={16} />} label={t('weather.humidity')} value={`${current.humidity}%`} />
              <Metric icon={<Wind size={16} />} label={t('weather.wind')} value={`${current.wind_speed} ${t('weather.windUnit')}`} />
              <Metric
                icon={<CloudSun size={16} />}
                label={t('weather.precipitation')}
                value={current.precipitation_probability != null ? `${current.precipitation_probability}%` : '—'}
              />
            </div>
          </div>
          <p className="text-[11px] text-textSecondary mt-5">
            {t('weather.source')}: OpenWeatherMap · {t('weather.updatedAt')}: {formatDate(current.fetched_at, lang, { dateStyle: 'medium', timeStyle: 'short' })}
          </p>
        </div>
      )}

      {forecast && forecast.days.length > 0 && (
        <div className="card p-6">
          <h2 className="font-semibold mb-4">{t('weather.forecastTitle')}</h2>
          <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-3">
            {forecast.days.map((day) => (
              <div key={day.date} className="rounded-2xl bg-surface2 border border-borderc p-4 text-center">
                <p className="text-sm font-semibold">{weekdayName(day.date, lang)}</p>
                <p className="text-[11px] text-textSecondary">{formatDate(day.date + 'T12:00:00', lang)}</p>
                <p className="text-2xl font-bold mt-2">
                  {Math.round(day.temp_max)}° <span className="text-textSecondary text-base font-medium">{Math.round(day.temp_min)}°</span>
                </p>
                <p className="text-xs text-textSecondary mt-1 capitalize truncate">{day.description}</p>
                {day.precipitation_probability != null && (
                  <p className="text-[11px] text-accent mt-1">💧 {day.precipitation_probability}%</p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {forecast && forecast.advisories.length > 0 && (
        <div className="card p-6">
          <h2 className="font-semibold mb-3 flex items-center gap-2"><AlertTriangle size={17} className="text-warning" /> {t('weather.advisories')}</h2>
          <ul className="space-y-2 text-sm text-textSecondary">
            {forecast.advisories.map((a, i) => (
              <li key={i} className="flex gap-2">
                <span className="text-warning">•</span> {a}
              </li>
            ))}
          </ul>
        </div>
      )}

      {!loading && !current && !error && <EmptyState title={t('common.empty')} />}
    </div>
  );
}

function Metric({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return (
    <div className="rounded-xl bg-surface2 border border-borderc p-3">
      <p className="text-textSecondary text-xs flex items-center gap-1.5">{icon} {label}</p>
      <p className="font-semibold mt-1">{value}</p>
    </div>
  );
}
