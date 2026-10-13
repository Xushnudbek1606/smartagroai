import { useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { BrainCircuit, Camera, ExternalLink, ImagePlus, X } from 'lucide-react';
import { api, extractError } from '../services/api';
import { useAuthStore } from '../store/auth';
import { Badge, ErrorState, LoadingBlock, showToast } from '../components/ui';
import type { Diagnosis, IntegrationStatus, Subscription } from '../types';
import { useEffect } from 'react';

const MAX_BYTES = 8 * 1024 * 1024;
const ACCEPTED = ['image/jpeg', 'image/png', 'image/webp'];

export default function DiagnosisPage() {
  const { t, i18n } = useTranslation();
  const lang = i18n.language as never;
  const user = useAuthStore((s) => s.user);
  const navigate = useNavigate();
  const fileRef = useRef<HTMLInputElement>(null);
  const cameraRef = useRef<HTMLInputElement>(null);

  const [status, setStatus] = useState<IntegrationStatus | null>(null);
  const [sub, setSub] = useState<Subscription | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [cropType, setCropType] = useState('');
  const [region, setRegion] = useState(user?.region || '');
  const [notes, setNotes] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .get<IntegrationStatus>('/diagnoses/integration-status')
      .then((r) => setStatus(r.data))
      .catch(() => setStatus(null));
    api
      .get<Subscription>('/users/me/subscription')
      .then((r) => setSub(r.data))
      .catch(() => setSub(null));
  }, []);

  function pick(f: File | undefined | null) {
    setError(null);
    if (!f) return;
    if (!ACCEPTED.includes(f.type)) {
      setError(t('diagnosis.uploadHint'));
      return;
    }
    if (f.size > MAX_BYTES) {
      setError(t('diagnosis.uploadHint'));
      return;
    }
    setFile(f);
    setPreview(URL.createObjectURL(f));
  }

  async function submit() {
    if (!file) {
      setError(t('diagnosis.imageRequired'));
      return;
    }
    if (!cropType.trim()) {
      setError(t('diagnosis.cropRequired'));
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const form = new FormData();
      form.append('file', file);
      form.append('crop_type', cropType.trim());
      if (region.trim()) form.append('region', region.trim());
      if (notes.trim()) form.append('notes', notes.trim());
      const resp = await api.post<Diagnosis>('/diagnoses', form, {
        headers: { 'Content-Type': 'multipart/form-data' },
        timeout: 120000,
      });
      showToast(t('diagnosis.resultTitle'), 'success');
      navigate(`/diagnoses/${resp.data.id}`);
    } catch (err) {
      const e = extractError(err);
      if (e.code === 'subscription_required') {
        setSub(null);
        setError(t('subscription.limitReachedText'));
      } else if (e.code === 'ai_not_configured') setError(t('diagnosis.notConfiguredText'));
      else setError(e.message || t('errors.unexpected'));
    } finally {
      setBusy(false);
    }
  }

  if (status === null) return <LoadingBlock />;

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold">{t('diagnosis.title')}</h1>
        <p className="text-sm text-textSecondary">{t('diagnosis.subtitle')}</p>
      </div>

      {sub && !sub.unlimited && (
        <div className={`card p-4 ${sub.diagnoses_remaining === 0 ? 'border-danger/40' : ''}`}>
          <div className="flex items-center justify-between text-sm">
            <span className="text-textSecondary">{t('subscription.diagnosesRemaining')}</span>
            {sub.diagnoses_remaining === 0 ? (
              <a href="https://t.me/SmartAgroAIBot" target="_blank" rel="noreferrer" className="text-danger font-semibold underline flex items-center gap-1">
                {t('subscription.upgradeCta')} <ExternalLink size={12} />
              </a>
            ) : (
              <span className="font-semibold">{sub.diagnoses_remaining} / {sub.diagnoses_limit}</span>
            )}
          </div>
        </div>
      )}

      {!status.configured && (
        <div className="card border-warning/40 p-5">
          <p className="font-semibold text-warning">{t('diagnosis.notConfiguredTitle')}</p>
          <p className="text-sm text-textSecondary mt-1">{t('diagnosis.notConfiguredText')}</p>
        </div>
      )}

      <div className="card p-6 space-y-5">
        {/* upload area */}
        <div>
          <p className="label">{t('diagnosis.uploadTitle')}</p>
          {preview ? (
            <div className="relative inline-block">
              <img
                src={preview}
                alt=""
                className="rounded-2xl max-h-72 border border-borderc object-contain bg-surface2"
              />
              <button
                type="button"
                onClick={() => {
                  setFile(null);
                  setPreview(null);
                }}
                className="absolute -top-2 -right-2 rounded-full bg-danger text-white p-1.5"
                aria-label={t('common.cancel')}
              >
                <X size={14} />
              </button>
            </div>
          ) : (
            <div
              className="rounded-2xl border-2 border-dashed border-borderc bg-surface2/50 p-10 flex flex-col items-center gap-3 text-center cursor-pointer hover:border-primary/50 transition-colors"
              onClick={() => fileRef.current?.click()}
              onDragOver={(e) => e.preventDefault()}
              onDrop={(e) => {
                e.preventDefault();
                pick(e.dataTransfer.files?.[0]);
              }}
            >
              <div className="rounded-xl bg-primary/10 text-primary p-3">
                <ImagePlus size={26} />
              </div>
              <p className="text-sm text-textSecondary">{t('diagnosis.dropHint')}</p>
              <p className="text-xs text-textSecondary">{t('diagnosis.uploadHint')}</p>
            </div>
          )}
          <input
            ref={fileRef}
            type="file"
            accept={ACCEPTED.join(',')}
            className="hidden"
            onChange={(e) => {
              pick(e.target.files?.[0]);
              e.target.value = '';
            }}
          />
          <input
            ref={cameraRef}
            type="file"
            accept="image/*"
            capture="environment"
            className="hidden"
            onChange={(e) => {
              pick(e.target.files?.[0]);
              e.target.value = '';
            }}
          />
          <div className="flex gap-2 mt-3">
            <button type="button" className="btn-secondary" onClick={() => fileRef.current?.click()}>
              <ImagePlus size={16} /> {t('diagnosis.chooseFile')}
            </button>
            <button type="button" className="btn-secondary" onClick={() => cameraRef.current?.click()}>
              <Camera size={16} /> {t('diagnosis.takePhoto')}
            </button>
          </div>
        </div>

        <div className="grid sm:grid-cols-2 gap-4">
          <div>
            <label className="label" htmlFor="cropType">{t('diagnosis.cropType')} *</label>
            <input
              id="cropType"
              className="input"
              placeholder={t('diagnosis.cropTypePlaceholder')}
              value={cropType}
              onChange={(e) => setCropType(e.target.value)}
            />
          </div>
          <div>
            <label className="label" htmlFor="region">{t('diagnosis.region')}</label>
            <input id="region" className="input" value={region} onChange={(e) => setRegion(e.target.value)} />
          </div>
        </div>

        <div>
          <label className="label" htmlFor="notes">{t('diagnosis.notes')}</label>
          <textarea
            id="notes"
            className="input min-h-[80px]"
            placeholder={t('diagnosis.notesPlaceholder')}
            value={notes}
            maxLength={2000}
            onChange={(e) => setNotes(e.target.value)}
          />
        </div>

        {error && (
          <div className="rounded-xl bg-danger/10 border border-danger/30 px-4 py-3 text-sm text-danger break-words">
            {error}
          </div>
        )}

        <button type="button" className="btn-primary w-full !py-3" onClick={submit} disabled={busy || !status.configured}>
          {busy ? (
            <span className="animate-pulse-soft">{t('diagnosis.analyzing')}</span>
          ) : (
            <>
              <BrainCircuit size={17} /> {t('diagnosis.analyze')}
            </>
          )}
        </button>

        <p className="text-xs text-textSecondary text-center">{t('diagnosis.aiDisclaimer')}</p>
      </div>
    </div>
  );
}
