import { useEffect, useState, type ReactNode } from 'react';
import { useTranslation } from 'react-i18next';
import { AlertTriangle, Inbox, Loader2, X } from 'lucide-react';

export function Spinner({ size = 20, className = '' }: { size?: number; className?: string }) {
  return <Loader2 size={size} className={`animate-spin ${className}`} />;
}

export function LoadingBlock({ label }: { label?: string }) {
  const { t } = useTranslation();
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-14 text-textSecondary">
      <Spinner size={28} className="text-primary" />
      <p className="text-sm">{label || t('common.loading')}</p>
    </div>
  );
}

export function EmptyState({
  icon,
  title,
  hint,
  action,
}: {
  icon?: ReactNode;
  title: string;
  hint?: string;
  action?: ReactNode;
}) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 py-14 text-center px-6">
      <div className="rounded-2xl bg-surface2 p-4 text-textSecondary">
        {icon || <Inbox size={28} />}
      </div>
      <p className="font-semibold text-textPrimary">{title}</p>
      {hint && <p className="text-sm text-textSecondary max-w-sm">{hint}</p>}
      {action && <div className="mt-3">{action}</div>}
    </div>
  );
}

export function ErrorState({ message, onRetry }: { message?: string; onRetry?: () => void }) {
  const { t } = useTranslation();
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-14 text-center px-6">
      <div className="rounded-2xl bg-danger/10 p-4 text-danger">
        <AlertTriangle size={28} />
      </div>
      <p className="font-semibold text-textPrimary">{t('common.error')}</p>
      {message && <p className="text-sm text-textSecondary max-w-md break-words">{message}</p>}
      {onRetry && (
        <button type="button" onClick={onRetry} className="btn-secondary mt-2">
          {t('common.retry')}
        </button>
      )}
    </div>
  );
}

export function StatCard({
  label,
  value,
  icon,
  accent = 'text-primary',
  hint,
}: {
  label: string;
  value: ReactNode;
  icon?: ReactNode;
  accent?: string;
  hint?: string;
}) {
  return (
    <div className="card p-5 flex items-start gap-4">
      {icon && (
        <div className={`rounded-xl bg-surface2 p-3 ${accent}`}>
          {icon}
        </div>
      )}
      <div className="min-w-0">
        <p className="text-sm text-textSecondary truncate">{label}</p>
        <p className="text-2xl font-bold mt-0.5 truncate">{value}</p>
        {hint && <p className="text-xs text-textSecondary mt-1 truncate">{hint}</p>}
      </div>
    </div>
  );
}

export function Badge({
  children,
  tone = 'default',
}: {
  children: ReactNode;
  tone?: 'default' | 'success' | 'warning' | 'danger' | 'accent';
}) {
  const tones: Record<string, string> = {
    default: 'bg-surface2 text-textSecondary border border-borderc',
    success: 'bg-primary/15 text-primary border border-primary/30',
    warning: 'bg-warning/15 text-warning border border-warning/30',
    danger: 'bg-danger/15 text-danger border border-danger/30',
    accent: 'bg-accent/15 text-accent border border-accent/30',
  };
  return <span className={`badge ${tones[tone]}`}>{children}</span>;
}

export function Modal({
  open,
  onClose,
  title,
  children,
  wide = false,
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
  wide?: boolean;
}) {
  if (!open) return null;
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        className={`card w-full ${wide ? 'max-w-2xl' : 'max-w-md'} max-h-[90vh] overflow-y-auto animate-fade-in`}
        role="dialog"
        aria-modal="true"
        aria-label={title}
      >
        <div className="flex items-center justify-between border-b border-borderc px-5 py-4">
          <h3 className="font-semibold">{title}</h3>
          <button type="button" onClick={onClose} className="text-textSecondary hover:text-textPrimary" aria-label="close">
            <X size={18} />
          </button>
        </div>
        <div className="p-5">{children}</div>
      </div>
    </div>
  );
}

// ---- toast (lightweight, i18n-friendly) ----
export type ToastKind = 'success' | 'error';
type ToastItem = { id: string; msg: string; kind: ToastKind };
let toastFn: ((msg: string, kind: ToastKind) => void) | null = null;

export function ToastHost() {
  const [items, setItems] = useState<ToastItem[]>([]);

  // (Re)register the imperative sender on every mount. Registering only when
  // `toastFn` is null leaves a stale callback pointing at an unmounted
  // instance after a remount (HMR / StrictMode), so toasts silently stop
  // appearing. The cleanup guarantees the live instance owns the callback.
  useEffect(() => {
    toastFn = (msg: string, kind: ToastKind) => {
      const id = Math.random().toString(36).slice(2);
      setItems((prev) => [...prev, { id, msg, kind }]);
      setTimeout(() => setItems((prev) => prev.filter((i) => i.id !== id)), 4000);
    };
    return () => {
      toastFn = null;
    };
  }, []);

  return (
    <div className="fixed bottom-4 right-4 z-[60] flex flex-col gap-2 max-w-sm">
      {items.map((i) => (
        <div
          key={i.id}
          className={`card px-4 py-3 text-sm animate-fade-in border-l-4 ${
            i.kind === 'success' ? 'border-l-primary' : 'border-l-danger'
          }`}
        >
          {i.msg}
        </div>
      ))}
    </div>
  );
}

export function showToast(msg: string, kind: ToastKind = 'success') {
  toastFn?.(msg, kind);
}
