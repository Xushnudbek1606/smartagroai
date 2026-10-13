import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { BrainCircuit, Trash2 } from 'lucide-react';
import { api, extractError } from '../services/api';
import { Badge, EmptyState, ErrorState, LoadingBlock, Modal, showToast } from '../components/ui';
import { formatRelative } from '../utils/format';
import type { Diagnosis, Page } from '../types';

export default function DiagnosisHistory() {
  const { t, i18n } = useTranslation();
  const lang = i18n.language as never;
  const [data, setData] = useState<Page<Diagnosis> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [confirmDelete, setConfirmDelete] = useState<Diagnosis | null>(null);

  function load(p: number) {
    setError(null);
    api
      .get<Page<Diagnosis>>('/diagnoses', { params: { page: p, page_size: 12 } })
      .then((r) => setData(r.data))
      .catch((err) => setError(extractError(err).message));
  }

  useEffect(() => load(page), [page]);

  async function doDelete() {
    if (!confirmDelete) return;
    try {
      await api.delete(`/diagnoses/${confirmDelete.id}`);
      showToast(t('common.success'), 'success');
      setConfirmDelete(null);
      load(page);
    } catch (err) {
      showToast(extractError(err).message, 'error');
    }
  }

  if (!data && !error) return <LoadingBlock />;
  if (error && !data) return <ErrorState message={error} onRetry={() => load(page)} />;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">{t('diagnosis.historyTitle')}</h1>
          <p className="text-sm text-textSecondary">{t('diagnosis.subtitle')}</p>
        </div>
        <Link to="/diagnosis" className="btn-primary">
          <BrainCircuit size={16} /> {t('dashboard.newDiagnosis')}
        </Link>
      </div>

      {data && data.items.length === 0 ? (
        <EmptyState title={t('diagnosis.historyEmpty')} hint={t('diagnosis.historyEmptyHint')} />
      ) : (
        <>
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {data?.items.map((d) => (
              <div key={d.id} className="card overflow-hidden hover:border-primary/40 transition-colors group">
                <Link to={`/diagnoses/${d.id}`}>
                  <img src={d.image_url} alt="" className="w-full h-44 object-cover bg-surface2" />
                </Link>
                <div className="p-4">
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0">
                      <p className="font-semibold truncate">
                        {d.status === 'no_finding' ? t('diagnosis.noFindingTitle') : d.disease_name || t('diagnosis.severityUnknown')}
                      </p>
                      <p className="text-xs text-textSecondary truncate">
                        {d.predicted_crop || '—'} · {formatRelative(d.created_at, lang)}
                      </p>
                    </div>
                    <Badge
                      tone={
                        d.status === 'no_finding'
                          ? 'warning'
                          : d.severity === 'high' ? 'danger' : d.severity === 'medium' ? 'warning' : d.severity === 'low' ? 'success' : 'default'
                      }
                    >
                      {d.status === 'no_finding' ? t('diagnosis.noFindingBadge') : d.confidence != null ? `${Math.round(d.confidence * 100)}%` : '—'}
                    </Badge>
                  </div>
                  <div className="flex items-center justify-between mt-3">
                    <Link to={`/diagnoses/${d.id}`} className="text-xs text-accent hover:underline">
                      {t('common.viewDetails')}
                    </Link>
                    <button
                      type="button"
                      onClick={() => setConfirmDelete(d)}
                      className="text-textSecondary hover:text-danger"
                      aria-label={t('common.delete')}
                    >
                      <Trash2 size={15} />
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>

          {data && data.pages > 1 && (
            <div className="flex items-center justify-center gap-3">
              <button
                type="button"
                className="btn-secondary !py-1.5"
                disabled={page <= 1}
                onClick={() => setPage((p) => p - 1)}
              >
                {t('common.previous')}
              </button>
              <span className="text-sm text-textSecondary">
                {t('common.page')} {data.page} {t('common.of')} {data.pages}
              </span>
              <button
                type="button"
                className="btn-secondary !py-1.5"
                disabled={page >= data.pages}
                onClick={() => setPage((p) => p + 1)}
              >
                {t('common.next')}
              </button>
            </div>
          )}
        </>
      )}

      <Modal open={Boolean(confirmDelete)} onClose={() => setConfirmDelete(null)} title={t('common.delete')}>
        <p className="text-sm text-textSecondary">{t('diagnosis.deleteConfirm')}</p>
        <div className="flex justify-end gap-2 mt-5">
          <button type="button" className="btn-secondary" onClick={() => setConfirmDelete(null)}>
            {t('common.cancel')}
          </button>
          <button type="button" className="btn-danger" onClick={doDelete}>
            {t('common.delete')}
          </button>
        </div>
      </Modal>
    </div>
  );
}
