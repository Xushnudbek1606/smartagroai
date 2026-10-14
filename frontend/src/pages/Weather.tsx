import { useCallback, useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { AlertTriangle, CloudRain, CloudSun, Droplets, LocateFixed, MapPin, Thermometer, Wind } from 'lucide-react';
import { api, extractError } from '../services/api';
import { useAuthStore } from '../store/auth';
import { EmptyState, ErrorState, LoadingBlock } from '../components/ui';
import { formatDate, formatNumber, weekdayName } from '../utils/format';
import type { WeatherCurrent, WeatherForecast, WeatherRegion } from '../types';

type GeoState = 'idle' | 'locating' | 'active' | 'denied' | 'unavailable';

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

  const [geoPos, setGeoPos] = useState<{ lat: number; lon: number } | null>(null);
  const [geoState, setGeoState] = useState<GeoState>('idle');
  const geoAsked = useRef(false);
  const geoTimer = useRef<number | null>(null);
  const geoReqId = useRef(0);

  // Ask the browser for GPS coordinates once on load; when the user has
  // already granted geolocation, this resolves silently and the weather
  // below switches to their real position.
  const requestGeo = useCallback(() => {
    if (!('geolocation' in navigator)) {
      setGeoState('unavailable');
      return;
    }
    const reqId = ++geoReqId.current;
    setGeoState('locating');
    // Safety net: an unanswered permission prompt must not leave the page stuck.
    if (geoTimer.current) window.clearTimeout(geoTimer.current);
    geoTimer.current = window.setTimeout(() => {
      setGeoState((s) => (reqId === geoReqId.current && s === 'locating' ? 'unavailable' : s));
    }, 12000);
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        if (reqId !== geoReqId.current) return; // superseded by a newer request
        if (geoTimer.current) window.clearTimeout(geoTimer.current);
        setGeoPos({ lat: pos.coords.latitude, lon: pos.coords.longitude });
        setGeoState('active');
      },
      (err) => {
        if (reqId !== geoReqId.current) return; // superseded by a newer request
        if (geoTimer.current) window.clearTimeout(geoTimer.current);
        setGeoState(err.code === err.PERMISSION_DENIED ? 'denied' : 'unavailable');
      },
      { enableHighAccuracy: false, timeout: 10000, maximumAge: 5 * 60 * 1000 },
    );
  }, []);

  useEffect(() => {
    if (geoAsked.current) return;
    geoAsked.current = true;
    requestGeo();
  }, [requestGeo]);

  useEffect(() => {
    api
      .get<WeatherRegion[]>('/weather/regions')
      .then((r) => setRegions(r.data))
      .catch(() => setRegions([]));
  }, []);

  const usingGeo = geoState === 'active' && geoPos !== null;
  const today = forecast?.days[0] ?? null;
  const rainProb = today?.precipitation_probability ?? null;

  useEffect(() => {
    const params = usingGeo && geoPos
      ? { lat: geoPos.lat, lon: geoPos.lon }
      : region
        ? { location: district ? `${region}, ${district}` : region }
        : null;
    if (!params) return;
    setLoading(true);
    setError(null);
    Promise.all([
      api.get<WeatherCurrent>('/weather/current', { params }),
      api.get<WeatherForecast>('/weather/forecast', { params }),
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
  }, [region, district, geoPos, usingGeo]);

  // Manual selection always wins over the GPS position.
  const selectRegion = (value: string) => {
    setRegion(value);
    setDistrict('');
    if (usingGeo) setGeoState('idle');
  };
  const selectDistrict = (value: string) => {
    setDistrict(value);
    if (usingGeo) setGeoState('idle');
  };

  const districts = regions.find((r) => r.region === region)?.districts || [];
  const notConfigured = error?.code === 'weather_not_configured';

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">{t('weather.title')}</h1>
          <p className="text-sm text-textSecondary">{t('weather.subtitle')}</p>
        </div>
        <div className="flex flex-wrap items-end gap-3">
          <button
            type="button"
            className="btn-secondary !py-2.5"
            onClick={requestGeo}
          >
            <LocateFixed size={16} className={usingGeo ? 'text-primary' : undefined} />
            {geoState === 'locating' ? t('weather.locating') : t('weather.useMyLocation')}
          </button>
          <div>
            <label className="label" htmlFor="region">{t('weather.selectLocation')}</label>
            <select id="region" className="input !w-auto" value={region} onChange={(e) => selectRegion(e.target.value)}>
              {regions.length === 0 && <option value={region}>{region}</option>}
              {regions.map((r) => (
                <option key={r.region} value={r.region}>{r.region}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="label" htmlFor="district">{t('common.district')}</label>
            <select id="district" className="input !w-auto" value={district} onChange={(e) => selectDistrict(e.target.value)}>
              <option value="">—</option>
              {districts.map((d) => (
                <option key={d} value={d}>{d}</option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {(geoState === 'denied' || geoState === 'unavailable') && (
        <p className="text-xs text-textSecondary">
          {geoState === 'denied' ? t('weather.geoDenied') : t('weather.geoUnavailable')}
        </p>
      )}

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
            {usingGeo && (
              <span className="badge bg-primary/15 text-primary">{t('weather.usingGeo')}</span>
            )}
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
          {today && (
            <div
              className={`mt-4 flex flex-wrap items-center gap-2 rounded-xl border p-3 text-sm ${
                rainProb != null && rainProb >= 60
                  ? 'border-warning/40 bg-warning/10 text-warning'
                  : 'border-borderc bg-surface2 text-textSecondary'
              }`}
            >
              <CloudRain size={16} />
              {rainProb != null && rainProb > 0 ? (
                <>
                  <span className="font-semibold text-textPrimary">{t('weather.rainToday', { prob: rainProb })}</span>
                  {today.rain_periods.length > 0 && (
                    <span>— {t('weather.rainExpectedAt')}: {today.rain_periods.join(', ')}</span>
                  )}
                </>
              ) : (
                <span>{t('weather.noRainToday')}</span>
              )}
            </div>
          )}
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
                {day.rain_periods.length > 0 && (
                  <p className="text-[11px] text-textSecondary mt-1">🌧 {day.rain_periods.join(', ')}</p>
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
