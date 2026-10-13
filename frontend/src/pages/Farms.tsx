import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { FlaskConical, MapPin, Pencil, Plus, Trash2, Undo2 } from 'lucide-react';
import { useForm } from 'react-hook-form';
import { api, extractError } from '../services/api';
import { useAuthStore } from '../store/auth';
import FarmMap, { boundaryToGeoJSON, geoJSONToPoints, type LatLng } from '../components/FarmMap';
import { EmptyState, ErrorState, LoadingBlock, Modal, showToast } from '../components/ui';
import { formatNumber } from '../utils/format';
import type { Farm, Page } from '../types';

interface FormValues {
  name: string;
  region: string;
  district: string;
  area_hectares: number;
}

export default function FarmsPage() {
  const { t, i18n } = useTranslation();
  const lang = i18n.language as never;
  const user = useAuthStore((s) => s.user);
  const [data, setData] = useState<Page<Farm> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<Farm | null>(null);
  const [confirmDelete, setConfirmDelete] = useState<Farm | null>(null);
  const [drawPoints, setDrawPoints] = useState<LatLng[]>([]);

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ defaultValues: { name: '', region: user?.region || '', district: user?.district || '', area_hectares: 0 } });

  function load() {
    api
      .get<Page<Farm>>('/farms', { params: { page_size: 100 } })
      .then((r) => setData(r.data))
      .catch((err) => setError(extractError(err).message));
  }

  useEffect(load, []);

  function openCreate() {
    setEditing(null);
    setDrawPoints([]);
    reset({ name: '', region: user?.region || '', district: user?.district || '', area_hectares: 0 });
    setOpen(true);
  }

  function openEdit(f: Farm) {
    setEditing(f);
    setDrawPoints(geoJSONToPoints(f.boundary));
    reset({
      name: f.name,
      region: f.region,
      district: f.district,
      area_hectares: f.area_hectares || 0,
    });
    setOpen(true);
  }

  async function onSubmit(values: FormValues) {
    try {
      let center: { lat: number; lng: number } | null = null;
      if (drawPoints.length > 0) {
        const ring = drawPoints.map((p) => [p.lat, p.lng] as [number, number]);
        center = {
          lat: ring.reduce((s, p) => s + p[0], 0) / ring.length,
          lng: ring.reduce((s, p) => s + p[1], 0) / ring.length,
        };
      }
      const payload = {
        name: values.name.trim(),
        region: values.region.trim(),
        district: values.district.trim(),
        area_hectares: Number(values.area_hectares) || null,
        boundary: drawPoints.length > 0 ? boundaryToGeoJSON(drawPoints) : null,
        center_lat: center?.lat ?? null,
        center_lng: center?.lng ?? null,
      };
      if (editing) {
        await api.patch(`/farms/${editing.id}`, payload);
        showToast(t('farms.updated'), 'success');
      } else {
        await api.post('/farms', payload);
        showToast(t('farms.created'), 'success');
      }
      setOpen(false);
      load();
    } catch (err) {
      showToast(extractError(err).message, 'error');
    }
  }

  async function doDelete() {
    if (!confirmDelete) return;
    try {
      await api.delete(`/farms/${confirmDelete.id}`);
      showToast(t('farms.deleted'), 'success');
      setConfirmDelete(null);
      load();
    } catch (err) {
      showToast(extractError(err).message, 'error');
    }
  }

  if (!data && !error) return <LoadingBlock />;
  if (error && !data) return <ErrorState message={error} onRetry={load} />;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">{t('farms.title')}</h1>
          <p className="text-sm text-textSecondary">{t('farms.subtitle')}</p>
        </div>
        {user?.role !== 'agronom' && (
          <button type="button" className="btn-primary" onClick={openCreate}>
            <Plus size={16} /> {t('farms.addFarm')}
          </button>
        )}
      </div>

      {data && data.items.length === 0 ? (
        <EmptyState
          icon={<FlaskConical size={28} />}
          title={t('farms.empty')}
          hint={t('farms.emptyHint')}
          action={
            user?.role !== 'agronom' ? (
              <button type="button" className="btn-primary" onClick={openCreate}>
                <Plus size={16} /> {t('farms.addFarm')}
              </button>
            ) : undefined
          }
        />
      ) : (
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {data?.items.map((f) => (
            <div key={f.id} className="card p-5">
              <div className="flex items-start justify-between gap-2">
                <div className="rounded-xl bg-primary/10 text-primary p-2.5">
                  <FlaskConical size={19} />
                </div>
                {user?.role !== 'agronom' && (
                  <div className="flex gap-1">
                    <button type="button" className="p-2 text-textSecondary hover:text-accent" onClick={() => openEdit(f)} aria-label={t('common.edit')}>
                      <Pencil size={15} />
                    </button>
                    <button type="button" className="p-2 text-textSecondary hover:text-danger" onClick={() => setConfirmDelete(f)} aria-label={t('common.delete')}>
                      <Trash2 size={15} />
                    </button>
                  </div>
                )}
              </div>
              <h3 className="font-semibold mt-3">{f.name}</h3>
              <p className="text-xs text-textSecondary flex items-center gap-1 mt-1">
                <MapPin size={12} /> {f.region}, {f.district}
              </p>
              <div className="flex items-center gap-4 mt-3 text-sm">
                {f.area_hectares != null && (
                  <span className="text-textSecondary">
                    {formatNumber(f.area_hectares, lang, 1)} {t('dashboard.hectares')}
                  </span>
                )}
                <span className="text-textSecondary">
                  {f.crops_count} {t('dashboard.crops')}
                </span>
              </div>
              {f.boundary && (
                <div className="mt-3 -mx-2">
                  <FarmMap boundary={f.boundary} className="w-full h-36 rounded-xl z-0" />
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      <Modal open={open} onClose={() => setOpen(false)} title={editing ? t('farms.editFarm') : t('farms.addFarm')}>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div>
            <label className="label" htmlFor="fname">{t('farms.farmName')} *</label>
            <input id="fname" className="input" {...register('name', { required: t('farms.nameRequired'), minLength: 2 })} />
            {errors.name && <p className="text-xs text-danger mt-1">{errors.name.message}</p>}
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="label" htmlFor="fregion">{t('common.region')} *</label>
              <input id="fregion" className="input" {...register('region', { required: t('farms.regionRequired') })} />
              {errors.region && <p className="text-xs text-danger mt-1">{errors.region.message}</p>}
            </div>
            <div>
              <label className="label" htmlFor="fdistrict">{t('common.district')} *</label>
              <input id="fdistrict" className="input" {...register('district', { required: t('validation.required') })} />
              {errors.district && <p className="text-xs text-danger mt-1">{errors.district.message}</p>}
            </div>
          </div>
          <div>
            <label className="label" htmlFor="farea">{t('farms.area')}</label>
            <input id="farea" type="number" step="0.1" min="0" className="input" {...register('area_hectares')} />
          </div>
          <div>
            <p className="label">{t('farms.drawOnMap')}</p>
            <p className="text-xs text-textSecondary mb-2">{t('farms.drawHint')}</p>
            <FarmMap
              drawPoints={drawPoints}
              onMapClick={(p) => setDrawPoints((prev) => [...prev, p])}
              onMoveLast={(p) =>
                setDrawPoints((prev) => (prev.length ? [...prev.slice(0, -1), p] : prev))
              }
              className="w-full h-64 rounded-xl z-0"
            />
            <div className="flex items-center gap-2 mt-2">
              <span className="text-xs text-textSecondary">
                {t('farms.pointsCount', { count: drawPoints.length })}
              </span>
              <button
                type="button"
                className="btn-secondary !py-1.5 !px-3 text-xs"
                onClick={() => setDrawPoints((prev) => prev.slice(0, -1))}
                disabled={drawPoints.length === 0}
              >
                <Undo2 size={13} /> {t('farms.undoPoint')}
              </button>
              <button
                type="button"
                className="btn-secondary !py-1.5 !px-3 text-xs"
                onClick={() => setDrawPoints([])}
                disabled={drawPoints.length === 0}
              >
                <Trash2 size={13} /> {t('farms.clearPoints')}
              </button>
            </div>
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <button type="button" className="btn-secondary" onClick={() => setOpen(false)}>{t('common.cancel')}</button>
            <button type="submit" className="btn-primary" disabled={isSubmitting}>{t('common.save')}</button>
          </div>
        </form>
      </Modal>

      <Modal open={Boolean(confirmDelete)} onClose={() => setConfirmDelete(null)} title={t('common.delete')}>
        <p className="text-sm text-textSecondary">{t('farms.deleteConfirm')}</p>
        <div className="flex justify-end gap-2 mt-5">
          <button type="button" className="btn-secondary" onClick={() => setConfirmDelete(null)}>{t('common.cancel')}</button>
          <button type="button" className="btn-danger" onClick={doDelete}>{t('common.delete')}</button>
        </div>
      </Modal>
    </div>
  );
}
