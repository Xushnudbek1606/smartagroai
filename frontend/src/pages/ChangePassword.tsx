import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import { KeyRound, Sprout } from 'lucide-react';
import LanguageSwitcher from '../components/LanguageSwitcher';
import { api, extractError } from '../services/api';
import { useAuthStore } from '../store/auth';

interface FormValues {
  current_password: string;
  new_password: string;
  confirm: string;
}

export default function ChangePassword() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const user = useAuthStore((s) => s.user);
  const fetchMe = useAuthStore((s) => s.fetchMe);
  const [serverError, setServerError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    defaultValues: { current_password: '', new_password: '', confirm: '' },
  });

  const newPassword = watch('new_password');

  async function onSubmit(values: FormValues) {
    setServerError(null);
    try {
      await api.post('/auth/change-password', {
        current_password: values.current_password,
        new_password: values.new_password,
      });
      await fetchMe();
      navigate('/dashboard', { replace: true });
    } catch (err) {
      const e = extractError(err);
      if (e.code === 'wrong_current_password') setServerError(t('auth.invalidCredentials'));
      else setServerError(e.message || t('errors.unexpected'));
    }
  }

  return (
    <div className="min-h-screen bg-background flex items-center justify-center px-4 py-10">
      <div className="w-full max-w-md">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-2.5">
            <div className="rounded-xl bg-primary/15 p-2 text-primary"><Sprout size={22} /></div>
            <span className="font-bold text-lg">{t('common.appName')}</span>
          </div>
          <LanguageSwitcher />
        </div>

        <div className="card p-7">
          <div className="rounded-xl bg-warning/10 text-warning w-fit p-3 mb-4">
            <KeyRound size={22} />
          </div>
          <h1 className="text-2xl font-bold">{t('auth.changePasswordTitle')}</h1>
          <p className="text-sm text-textSecondary mt-1">{t('auth.changePasswordSubtitle')}</p>

          {user?.must_change_password && (
            <div className="mt-4 rounded-xl bg-warning/10 border border-warning/30 px-4 py-3 text-sm text-warning">
              {t('auth.mustChangeBanner')}
            </div>
          )}

          <form onSubmit={handleSubmit(onSubmit)} className="mt-6 space-y-4" noValidate>
            <div>
              <label className="label" htmlFor="current_password">{t('auth.currentPassword')}</label>
              <input
                id="current_password"
                type="password"
                className="input"
                autoComplete="current-password"
                {...register('current_password', { required: t('auth.passwordRequired') })}
              />
              {errors.current_password && (
                <p className="text-xs text-danger mt-1">{errors.current_password.message}</p>
              )}
            </div>

            <div>
              <label className="label" htmlFor="new_password">{t('auth.newPassword')}</label>
              <input
                id="new_password"
                type="password"
                className="input"
                autoComplete="new-password"
                {...register('new_password', {
                  required: t('auth.passwordRequired'),
                  minLength: { value: 8, message: t('auth.passwordTooShort') },
                })}
              />
              {errors.new_password && (
                <p className="text-xs text-danger mt-1">{errors.new_password.message}</p>
              )}
            </div>

            <div>
              <label className="label" htmlFor="confirm">{t('auth.confirmPassword')}</label>
              <input
                id="confirm"
                type="password"
                className="input"
                autoComplete="new-password"
                {...register('confirm', {
                  validate: (v) => v === newPassword || t('auth.passwordMismatch'),
                })}
              />
              {errors.confirm && (
                <p className="text-xs text-danger mt-1">{errors.confirm.message}</p>
              )}
            </div>

            {serverError && (
              <div className="rounded-xl bg-danger/10 border border-danger/30 px-4 py-3 text-sm text-danger">
                {serverError}
              </div>
            )}

            <button type="submit" className="btn-primary w-full !py-3" disabled={isSubmitting}>
              {t('auth.changePassword')}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
