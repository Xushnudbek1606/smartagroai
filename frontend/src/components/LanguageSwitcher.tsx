import { useState, useRef, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Languages, Check } from 'lucide-react';
import { LANGUAGES, setLanguage } from '../i18n';
import { api } from '../services/api';
import { useAuthStore } from '../store/auth';
import type { Language } from '../types';

export default function LanguageSwitcher({ className = '' }: { className?: string }) {
  const { i18n } = useTranslation();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const user = useAuthStore((s) => s.user);
  const setUser = useAuthStore((s) => s.setUser);

  useEffect(() => {
    function onClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener('mousedown', onClick);
    return () => document.removeEventListener('mousedown', onClick);
  }, []);

  const current = LANGUAGES.find((l) => l.code === i18n.language) || LANGUAGES[0];

  async function choose(lang: Language) {
    setLanguage(lang); // no page reload: i18next re-renders in place
    setOpen(false);
    if (user) {
      // persist to profile (best-effort)
      try {
        const resp = await api.patch('/users/me', { preferred_language: lang });
        setUser(resp.data);
      } catch {
        /* keep local selection even if the API call fails */
      }
    }
  }

  return (
    <div className={`relative ${className}`} ref={ref}>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="btn-secondary !px-3 !py-2"
        aria-label="Language"
        aria-expanded={open}
      >
        <Languages size={16} />
        <span className="hidden sm:inline">
          {current.flag} {current.name}
        </span>
        <span className="sm:hidden">{current.flag}</span>
      </button>
      {open && (
        <div className="absolute right-0 mt-2 w-52 card p-1.5 z-50 animate-fade-in">
          {LANGUAGES.map((lang) => (
            <button
              key={lang.code}
              type="button"
              onClick={() => choose(lang.code)}
              className={`w-full flex items-center justify-between gap-2 rounded-lg px-3 py-2 text-sm text-left transition-colors hover:bg-surface2 ${
                lang.code === i18n.language ? 'text-primary' : 'text-textPrimary'
              }`}
            >
              <span>
                {lang.flag} {lang.name}
              </span>
              {lang.code === i18n.language && <Check size={14} />}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
