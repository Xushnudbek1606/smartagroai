import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { ShieldCheck } from 'lucide-react';
import { api, extractError } from '../services/api';
import { Badge, EmptyState, ErrorState, LoadingBlock } from '../components/ui';
import { formatDateTime } from '../utils/format';
import type { AuditLog, Page } from '../types';

export default function AdminAudit() {
  const { t, i18n } = useTranslation();
  const lang = i18n.language as never;
  const [data, setData] = useState<Page<AuditLog> | null>(null);
  const [page, setPage] = useState(1);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .get<Page<AuditLog>>('/admin/audit-logs', { params: { page, page_size: 30 } })
      .then((r) => setData(r.data))
      .catch((err) => setError(extractError(err).message));
  }, [page]);

  if (!data && !error) return <LoadingBlock />;
  if (error && !data) return <ErrorState message={error} />;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">{t('admin.auditTitle')}</h1>
        <p className="text-sm text-textSecondary">{t('admin.auditSubtitle')}</p>
      </div>

      {data && data.items.length === 0 ? (
        <EmptyState icon={<ShieldCheck size={28} />} title={t('common.empty')} />
      ) : (
        <div className="card overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-borderc text-textSecondary text-left">
                <th className="px-5 py-3 font-medium">{t('common.time')}</th>
                <th className="px-5 py-3 font-medium">{t('admin.actor')}</th>
                <th className="px-5 py-3 font-medium">{t('admin.action')}</th>
                <th className="px-5 py-3 font-medium">{t('admin.entity')}</th>
              </tr>
            </thead>
            <tbody>
              {data?.items.map((log) => (
                <tr key={log.id} className="border-b border-borderc/50 hover:bg-surface2/40">
                  <td className="px-5 py-3 text-textSecondary whitespace-nowrap">{formatDateTime(log.created_at, lang)}</td>
                  <td className="px-5 py-3">{log.actor_name || '—'}</td>
                  <td className="px-5 py-3">
                    <Badge tone={log.action.includes('failed') ? 'danger' : log.action.startsWith('admin') ? 'accent' : 'default'}>
                      {log.action}
                    </Badge>
                  </td>
                  <td className="px-5 py-3 text-textSecondary">
                    {log.entity_type ? `${log.entity_type}${log.entity_id ? ` · ${log.entity_id.slice(0, 8)}` : ''}` : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {data && data.pages > 1 && (
        <div className="flex items-center justify-center gap-3">
          <button type="button" className="btn-secondary !py-1.5" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
            {t('common.previous')}
          </button>
          <span className="text-sm text-textSecondary">
            {t('common.page')} {data.page} {t('common.of')} {data.pages}
          </span>
          <button type="button" className="btn-secondary !py-1.5" disabled={page >= data.pages} onClick={() => setPage((p) => p + 1)}>
            {t('common.next')}
          </button>
        </div>
      )}
    </div>
  );
}
