import { useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { ArrowLeft, MessageCircle } from 'lucide-react';
import { api, extractError } from '../services/api';
import { Badge, ErrorState, LoadingBlock } from '../components/ui';
import { formatDateTime } from '../utils/format';
import type { Diagnosis } from '../types';

export default function DiagnosisDetail() {
  const { t, i18n } = useTranslation();
  const lang = i18n.language as never;
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [d, setD] = useState<Diagnosis | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .get<Diagnosis>(`/diagnoses/${id}`)
      .then((r) => setD(r.data))
      .catch((err) => setError(extractError(err).message));
  }, [id]);

  if (error) return <ErrorState message={error} onRetry={() => navigate(-1)} />;
  if (!d) return <LoadingBlock />;

  const severityTone =
    d.severity === 'high' ? 'danger' : d.severity === 'medium' ? 'warning' : d.severity === 'low' ? 'success' : 'default';
  const severityLabel =
    d.severity === 'high'
      ? t('diagnosis.severityHigh')
      : d.severity === 'medium'
        ? t('diagnosis.severityMedium')
        : d.severity === 'low'
          ? t('diagnosis.severityLow')
          : t('diagnosis.severityUnknown');
  const lowConfidence = d.confidence != null && d.confidence < 0.5;
  const noFinding = d.status === 'no_finding';

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <button type="button" onClick={() => navigate(-1)} className="inline-flex items-center gap-1.5 text-sm text-textSecondary hover:text-textPrimary">
        <ArrowLeft size={16} /> {t('common.back')}
      </button>

      <div className="grid md:grid-cols-2 gap-6">
        <div className="card overflow-hidden">
          <img src={d.image_url} alt="" className="w-full max-h-[420px] object-contain bg-surface2" />
        </div>

        <div className="space-y-4">
          {noFinding && (
            <div className="rounded-xl bg-warning/10 border border-warning/30 px-4 py-3 text-sm text-warning">
              <p className="font-semibold">{t('diagnosis.noFindingTitle')}</p>
              <p className="mt-1 text-warning/90">{t('diagnosis.noFindingText')}</p>
            </div>
          )}

          <div className="card p-5">
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-xs text-textSecondary">{t('diagnosis.disease')}</p>
                <h1 className="text-xl font-bold mt-0.5">
                  {noFinding ? t('diagnosis.noFindingTitle') : d.disease_name || t('diagnosis.severityUnknown')}
                </h1>
              </div>
              <Badge tone={noFinding ? 'warning' : severityTone}>{noFinding ? t('diagnosis.noFindingBadge') : severityLabel}</Badge>
            </div>

            <div className="mt-4 space-y-2 text-sm">
              <Row label={t('diagnosis.predictedCrop')} value={d.predicted_crop || '—'} />
              <Row
                label={t('diagnosis.confidence')}
                value={d.confidence != null ? `${Math.round(d.confidence * 100)}%` : '—'}
              />
              <Row label={t('diagnosis.region')} value={d.region || '—'} />
              <Row label={t('common.date')} value={formatDateTime(d.created_at, lang)} />
              <Row label={t('diagnosis.modelVersion')} value={d.model_version || '—'} />
            </div>

            {lowConfidence && (
              <div className="mt-4 rounded-xl bg-warning/10 border border-warning/30 px-4 py-3 text-sm text-warning">
                {t('diagnosis.lowConfidenceWarning')}
              </div>
            )}
            <div className="mt-4 rounded-xl bg-surface2 px-4 py-3 text-xs text-textSecondary">
              {t('diagnosis.aiDisclaimer')}
            </div>
          </div>

          {d.symptoms && d.symptoms.length > 0 && (
            <div className="card p-5">
              <h2 className="font-semibold mb-2">{t('diagnosis.symptoms')}</h2>
              <ul className="list-disc pl-5 text-sm text-textSecondary space-y-1">
                {d.symptoms.map((s, i) => (
                  <li key={i}>{s}</li>
                ))}
              </ul>
            </div>
          )}

          {d.recommendations && d.recommendations.length > 0 && (
            <div className="card p-5">
              <h2 className="font-semibold mb-2">{t('diagnosis.recommendations')}</h2>
              <ul className="list-disc pl-5 text-sm text-textSecondary space-y-1">
                {d.recommendations.map((r, i) => (
                  <li key={i}>{r}</li>
                ))}
              </ul>
            </div>
          )}

          {d.next_steps && (
            <div className="card p-5">
              <h2 className="font-semibold mb-2">{t('diagnosis.nextSteps')}</h2>
              <p className="text-sm text-textSecondary">{d.next_steps}</p>
            </div>
          )}

          {d.user_notes && (
            <div className="card p-5">
              <h2 className="font-semibold mb-2">{t('diagnosis.notes')}</h2>
              <p className="text-sm text-textSecondary">{d.user_notes}</p>
            </div>
          )}

          <Link to="/agronomists" className="btn-primary w-full">
            <MessageCircle size={16} /> {t('diagnosis.contactAgronom')}
          </Link>
        </div>
      </div>
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-3 border-b border-borderc/60 pb-1.5">
      <span className="text-textSecondary">{label}</span>
      <span className="font-medium text-right capitalize">{value}</span>
    </div>
  );
}
