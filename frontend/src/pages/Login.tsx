import { useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import { ExternalLink, Eye, EyeOff, LogIn, MessageCircle, Send, Sprout } from 'lucide-react';
import LanguageSwitcher from '../components/LanguageSwitcher';
import { api, storeTokens, extractError } from '../services/api';
import { useAuthStore } from '../store/auth';
import type { TokenPair, User } from '../types';

interface FormValues {
  username: string;
  password: string;
}

export default function Login() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const setUser = useAuthStore((s) => s.setUser);
  const [showPassword, setShowPassword] = useState(false);
  const [serverError, setServerError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ defaultValues: { username: '', password: '' } });

  async function onSubmit(values: FormValues) {
    setServerError(null);
    try {
      const resp = await api.post<TokenPair>('/auth/login', {
        username: values.username.trim(),
        password: values.password,
      });
      storeTokens(resp.data);
      const me = await api.get<User>('/auth/me');
      setUser(me.data);
      const next = params.get('next');
      if (me.data.must_change_password) {
        navigate('/change-password', { replace: true });
      } else if (next && next.startsWith('/')) {
        navigate(next, { replace: true });
      } else {
        navigate('/dashboard', { replace: true });
      }
    } catch (err) {
      const e = extractError(err);
      if (e.code === 'invalid_credentials') setServerError(t('auth.invalidCredentials'));
      else if (e.code === 'account_deactivated') setServerError(t('auth.accountDeactivated'));
      else if (e.code === 'rate_limited') setServerError(t('errors.rateLimited'));
      else setServerError(e.message || t('errors.unexpected'));
    }
  }

  return (
    <div className="min-h-screen bg-background flex items-center justify-center px-4 py-10">
      <div className="w-full max-w-md">
        <div className="flex items-center justify-between mb-6">
          <Link to="/" className="flex items-center gap-2.5">
            <div className="rounded-xl bg-primary/15 p-2 text-primary"><Sprout size={22} /></div>
            <span className="font-bold text-lg">{t('common.appName')}</span>
          </Link>
          <LanguageSwitcher />
        </div>

        <div className="card p-7">
          <h1 className="text-2xl font-bold">{t('auth.loginTitle')}</h1>
          <p className="text-sm text-textSecondary mt-1">{t('auth.loginSubtitle')}</p>

          <form onSubmit={handleSubmit(onSubmit)} className="mt-6 space-y-4" noValidate>
            <div>
              <label className="label" htmlFor="username">{t('auth.username')}</label>
              <input
                id="username"
                className="input"
                autoComplete="username"
                {...register('username', {
                  required: { value: true, message: t('auth.usernameRequired') },
                  minLength: { value: 3, message: t('validation.minLength', { count: 3 }) },
                })}
              />
              {errors.username && (
                <p className="text-xs text-danger mt-1">{errors.username.message}</p>
              )}
            </div>

            <div>
              <label className="label" htmlFor="password">{t('auth.password')}</label>
              <div className="relative">
                <input
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  className="input !pr-11"
                  autoComplete="current-password"
                  placeholder={t('auth.passwordPlaceholder')}
                  {...register('password', {
                    required: { value: true, message: t('auth.passwordRequired') },
                  })}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((v) => !v)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-textSecondary hover:text-textPrimary"
                  aria-label={showPassword ? t('auth.hidePassword') : t('auth.showPassword')}
                >
                  {showPassword ? <EyeOff size={17} /> : <Eye size={17} />}
                </button>
              </div>
              {errors.password && (
                <p className="text-xs text-danger mt-1">{errors.password.message}</p>
              )}
            </div>

            {serverError && (
              <div className="rounded-xl bg-danger/10 border border-danger/30 px-4 py-3 text-sm text-danger">
                {serverError}
              </div>
            )}

            <button type="submit" className="btn-primary w-full !py-3" disabled={isSubmitting}>
              {isSubmitting ? (
                <span className="animate-pulse-soft">{t('common.loading')}</span>
              ) : (
                <>
                  <LogIn size={17} /> {t('auth.signIn')}
                </>
              )}
            </button>

            <p className="text-xs text-textSecondary text-center">{t('auth.forgotHint')}</p>
          </form>
        </div>

        {/* telegram onboarding guide */}
        <div className="card p-6 mt-5">
          <div className="flex items-center gap-2.5 mb-2">
            <div className="rounded-lg bg-accent/15 text-accent p-2"><MessageCircle size={16} /></div>
            <h2 className="font-semibold text-sm">{t('auth.telegramHelpTitle')}</h2>
          </div>
          <p className="text-xs text-textSecondary leading-relaxed">{t('auth.telegramHelpText')}</p>
          <p className="text-xs text-textSecondary mt-2">{t('telegram.linkHint')}</p>
          <a
            href="https://t.me/SmartAgroAIBot"
            target="_blank"
            rel="noreferrer"
            className="btn-secondary w-full mt-4"
          >
            <Send size={15} /> {t('telegram.openBot')} <ExternalLink size={12} />
          </a>
        </div>
      </div>
    </div>
  );
}
