import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';

import uzLatn from './locales/uz-Latn/translation.json';
import uzCyrl from './locales/uz-Cyrl/translation.json';
import en from './locales/en/translation.json';
import ru from './locales/ru/translation.json';
import type { Language } from './types';

export const LANGUAGES: { code: Language; name: string; flag: string }[] = [
  { code: 'uz-Latn', name: "O'zbekcha (Lotin)", flag: '🇺🇿' },
  { code: 'uz-Cyrl', name: 'Ўзбекча (Кирилл)', flag: '🇺🇿' },
  { code: 'en', name: 'English', flag: '🇬🇧' },
  { code: 'ru', name: 'Русский', flag: '🇷🇺' },
];

/** Intl locale mapping (uz-Cyrl support varies by runtime, fall back to uz). */
export const intlLocale: Record<Language, string> = {
  'uz-Latn': 'uz-Latn',
  'uz-Cyrl': 'uz-Cyrl',
  en: 'en-US',
  ru: 'ru-RU',
};

export const STORAGE_LANG = 'smartagro_lang';

function detectInitialLanguage(): Language {
  try {
    const stored = localStorage.getItem(STORAGE_LANG);
    if (stored && LANGUAGES.some((l) => l.code === stored)) return stored as Language;
  } catch {
    /* localStorage unavailable */
  }
  const nav = navigator.language || 'uz-Latn';
  if (nav.startsWith('ru')) return 'ru';
  if (nav.startsWith('en')) return 'en';
  return 'uz-Latn'; // spec: default for new users
}

i18n.use(initReactI18next).init({
  resources: {
    'uz-Latn': { translation: uzLatn },
    'uz-Cyrl': { translation: uzCyrl },
    en: { translation: en },
    ru: { translation: ru },
  },
  lng: detectInitialLanguage(),
  fallbackLng: 'uz-Latn',
  interpolation: { escapeValue: false },
  returnNull: false,
});

export function setLanguage(lang: Language): void {
  i18n.changeLanguage(lang);
  try {
    localStorage.setItem(STORAGE_LANG, lang);
  } catch {
    /* ignore */
  }
  document.documentElement.lang = lang;
}

export default i18n;
