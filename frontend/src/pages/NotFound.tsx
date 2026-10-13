import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Compass, Sprout } from 'lucide-react';

export default function NotFound() {
  const { t } = useTranslation();
  return (
    <div className="min-h-screen bg-background flex flex-col items-center justify-center gap-5 px-4 text-center">
      <div className="rounded-2xl bg-primary/10 text-primary p-5">
        <Compass size={40} />
      </div>
      <h1 className="text-5xl font-extrabold">404</h1>
      <p className="font-semibold">{t('errors.pageNotFound')}</p>
      <p className="text-sm text-textSecondary max-w-sm">{t('errors.pageNotFoundText')}</p>
      <Link to="/" className="btn-primary mt-2">
        <Sprout size={16} /> {t('errors.goHome')}
      </Link>
    </div>
  );
}
