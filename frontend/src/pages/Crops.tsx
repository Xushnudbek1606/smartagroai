import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Pencil, Plus, Sprout, Trash2 } from 'lucide-react';
import { useForm } from 'react-hook-form';
import { api, extractError } from '../services/api';
import { useAuthStore } from '../store/auth';
import { Badge, EmptyState, ErrorState, LoadingBlock, Modal, showToast } from '../components/ui';
import { formatDate } from '../utils/format';
import type { Crop, Farm, Page } from '../types';

interface FormValues {
  farm_id: string;
  name: string;
  variety: string;
  planting_date: string;
  status: string;
}

const statusTone: Record<string, 'default' | 'success' | 'warning' | 'danger' | 'accent'> = {
  planned: 'accent',
  growing: 'success',
  harvested: 'default',
  failed: 'danger',
};

export default function CropsPage() {
  const { t, i18n } = useTranslation();
  const lang = i18n.language as never;
  const user = useAuthStore((s) => s.user);
  const [data, setData] = useState<Page<Crop> | null>(null);
  const [farms, setFarms] = useState<Farm[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<Crop | null>(null);
  const [confirmDelete, setConfirmDelete] = useState<Crop | null>(null);
  const [farmFilter, setFarmFilter] = useState('');

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ defaultValues: { farm_id: '', name: '', variety: '', planting_date: '', status: 'growing' } });

  function load(filter?: string) {
    const params: Record<string, unknown> = { page_size: 100 };
    if (filter) params.farm_id = filter;
    api
      .get<Page<Crop>>('/crops', { params })
      .then((r) => setData(r.data))
      .catch((err) => setError(extractError(err).message));
  }

  useEffect(() => {
    load(farmFilter);
  }, [farmFilter]);

  useEffect(() => {
    api
      .get<Page<Farm>>('/farms', { params: { page_size: 100 } })
      .then((r) => setFarms(r.data.items))
      .catch(() => setFarms([]));
  }, []);

  function openCreate() {
    setEditing(null);
    reset({ farm_id: farms[0]?.id || '', name: '', variety: '', planting_date: '', status: 'growing' });
    setOpen(true);
  }

  function openEdit(c: Crop) {
    setEditing(c);
    reset({
      farm_id: c.farm_id,
      name: c.name,
      variety: c.variety || '',
      planting_date: c.planting_date ? c.planting_date.slice(0, 10) : '',
      status: c.status,
    });
    setOpen(true);
  }

  async function onSubmit(values: FormValues) {
    try {
      const payload: Record<string, unknown> = {
        name: values.name.trim(),
        variety: values.variety.trim() || null,
        planting_date: values.planting_date ? new Date(values.planting_date).toISOString() : null,
        status: values.status,
      };
      if (editing) {
        await api.patch(`/crops/${editing.id}`, payload);
        showToast(t('crops.updated'), 'success');
      } else {
        await api.post('/crops', { ...payload, farm_id: values.farm_id });
        showToast(t('crops.created'), 'success');
      }
      setOpen(false);
      load(farmFilter);
    } catch (err) {
      showToast(extractError(err).message, 'error');
    }
  }

  async function doDelete() {
    if (!confirmDelete) return;
    try {
      await api.delete(`/crops/${confirmDelete.id}`);
      showToast(t('crops.deleted'), 'success');
      setConfirmDelete(null);
      load(farmFilter);
    } catch (err) {
      showToast(extractError(err).message, 'error');
    }
  }

  if (!data && !error) return <LoadingBlock />;
  if (error && !data) return <ErrorState message={error} onRetry={() => load(farmFilter)} />;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">{t('crops.title')}</h1>
          <p className="text-sm text-textSecondary">{t('crops.subtitle')}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <select className="input !w-auto" value={farmFilter} onChange={(e) => setFarmFilter(e.target.value)} aria-label={t('crops.farm')}>
            <option value="">{t('common.all')}</option>
            {farms.map((f) => (
              <option key={f.id} value={f.id}>{f.name}</option>
            ))}
          </select>
          {user?.role !== 'agronom' && farms.length > 0 && (
            <button type="button" className="btn-primary" onClick={openCreate}>
              <Plus size={16} /> {t('crops.addCrop')}
            </button>
          )}
        </div>
      </div>

      {data && data.items.length === 0 ? (
        <EmptyState icon={<Sprout size={28} />} title={t('crops.empty')} hint={t('crops.emptyHint')} />
      ) : (
        <div className="card overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-borderc text-textSecondary text-left">
                <th className="px-5 py-3 font-medium">{t('crops.cropName')}</th>
                <th className="px-5 py-3 font-medium">{t('crops.variety')}</th>
                <th className="px-5 py-3 font-medium">{t('crops.farm')}</th>
                <th className="px-5 py-3 font-medium">{t('crops.plantingDate')}</th>
                <th className="px-5 py-3 font-medium">{t('common.status')}</th>
                <th className="px-5 py-3 font-medium text-right">{t('common.actions')}</th>
              </tr>
            </thead>
            <tbody>
              {data?.items.map((c) => (
                <tr key={c.id} className="border-b border-borderc/50 hover:bg-surface2/40">
                  <td className="px-5 py-3.5 font-medium">{c.name}</td>
                  <td className="px-5 py-3.5 text-textSecondary">{c.variety || '—'}</td>
                  <td className="px-5 py-3.5 text-textSecondary">{c.farm_name || '—'}</td>
                  <td className="px-5 py-3.5 text-textSecondary">{c.planting_date ? formatDate(c.planting_date, lang) : '—'}</td>
                  <td className="px-5 py-3.5">
                    <Badge tone={statusTone[c.status] || 'default'}>{t(`crops.status_${c.status}`)}</Badge>
                  </td>
                  <td className="px-5 py-3.5">
                    {user?.role !== 'agronom' && (
                      <div className="flex justify-end gap-1">
                        <button type="button" className="p-1.5 text-textSecondary hover:text-accent" onClick={() => openEdit(c)} aria-label={t('common.edit')}>
                          <Pencil size={15} />
                        </button>
                        <button type="button" className="p-1.5 text-textSecondary hover:text-danger" onClick={() => setConfirmDelete(c)} aria-label={t('common.delete')}>
                          <Trash2 size={15} />
                        </button>
                      </div>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <Modal open={open} onClose={() => setOpen(false)} title={editing ? t('crops.editCrop') : t('crops.addCrop')}>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          {!editing && (
            <div>
              <label className="label" htmlFor="cfarm">{t('crops.selectFarm')} *</label>
              <select id="cfarm" className="input" {...register('farm_id', { required: t('crops.farmRequired') })}>
                {farms.map((f) => (
                  <option key={f.id} value={f.id}>{f.name}</option>
                ))}
              </select>
              {errors.farm_id && <p className="text-xs text-danger mt-1">{errors.farm_id.message}</p>}
            </div>
          )}
          <div>
            <label className="label" htmlFor="cname">{t('crops.cropName')} *</label>
            <input id="cname" className="input" {...register('name', { required: t('crops.nameRequired') })} />
            {errors.name && <p className="text-xs text-danger mt-1">{errors.name.message}</p>}
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="label" htmlFor="cvariety">{t('crops.variety')}</label>
              <input id="cvariety" className="input" {...register('variety')} />
            </div>
            <div>
              <label className="label" htmlFor="cdate">{t('crops.plantingDate')}</label>
              <input id="cdate" type="date" className="input" {...register('planting_date')} />
            </div>
          </div>
          <div>
            <label className="label" htmlFor="cstatus">{t('common.status')}</label>
            <select id="cstatus" className="input" {...register('status')}>
              {['planned', 'growing', 'harvested', 'failed'].map((s) => (
                <option key={s} value={s}>{t(`crops.status_${s}`)}</option>
              ))}
            </select>
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <button type="button" className="btn-secondary" onClick={() => setOpen(false)}>{t('common.cancel')}</button>
            <button type="submit" className="btn-primary" disabled={isSubmitting}>{t('common.save')}</button>
          </div>
        </form>
      </Modal>

      <Modal open={Boolean(confirmDelete)} onClose={() => setConfirmDelete(null)} title={t('common.delete')}>
        <p className="text-sm text-textSecondary">{t('crops.deleteConfirm')}</p>
        <div className="flex justify-end gap-2 mt-5">
          <button type="button" className="btn-secondary" onClick={() => setConfirmDelete(null)}>{t('common.cancel')}</button>
          <button type="button" className="btn-danger" onClick={doDelete}>{t('common.delete')}</button>
        </div>
      </Modal>
    </div>
  );
}
