import { intlLocale } from '../i18n';
import type { Language } from '../types';

type LangArg = Language | undefined;

export function formatDate(value: string | Date | null | undefined, lang: LangArg, opts?: Intl.DateTimeFormatOptions): string {
  if (!value) return '—';
  const d = typeof value === 'string' ? new Date(value) : value;
  if (Number.isNaN(d.getTime())) return '—';
  try {
    return new Intl.DateTimeFormat(intlLocale[lang || 'uz-Latn'], opts || { dateStyle: 'medium' }).format(d);
  } catch {
    return d.toISOString().slice(0, 10);
  }
}

export function formatDateTime(value: string | Date | null | undefined, lang: LangArg): string {
  return formatDate(value, lang, { dateStyle: 'medium', timeStyle: 'short' });
}

export function formatNumber(value: number | null | undefined, lang: LangArg, digits = 0): string {
  if (value === null || value === undefined || Number.isNaN(value)) return '—';
  try {
    return new Intl.NumberFormat(intlLocale[lang || 'uz-Latn'], {
      minimumFractionDigits: digits,
      maximumFractionDigits: digits,
    }).format(value);
  } catch {
    return String(value);
  }
}

export function formatPercent(value: number | null | undefined, lang: LangArg): string {
  if (value === null || value === undefined) return '—';
  return formatNumber(value * 100, lang, 0) + '%';
}

/** "3 daqiqa oldin" / "5 minutes ago" — locale-aware relative time. */
export function formatRelative(value: string | Date | null | undefined, lang: LangArg): string {
  if (!value) return '—';
  const d = typeof value === 'string' ? new Date(value) : value;
  const diffMs = Date.now() - d.getTime();
  const minutes = Math.floor(diffMs / 60000);
  const rtf = new Intl.RelativeTimeFormat(intlLocale[lang || 'uz-Latn'], { numeric: 'auto' });
  try {
    if (minutes < 1) return rtf.format(0, 'minute');
    if (minutes < 60) return rtf.format(-minutes, 'minute');
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return rtf.format(-hours, 'hour');
    const days = Math.floor(hours / 24);
    if (days < 7) return rtf.format(-days, 'day');
    return formatDate(d, lang);
  } catch {
    return formatDate(d, lang);
  }
}

export function weekdayName(dateStr: string, lang: LangArg): string {
  const d = new Date(dateStr + 'T12:00:00');
  try {
    return new Intl.DateTimeFormat(intlLocale[lang || 'uz-Latn'], { weekday: 'short' }).format(d);
  } catch {
    return dateStr;
  }
}
