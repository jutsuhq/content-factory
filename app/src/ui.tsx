import { X } from './icons'
import { useEffect, useState, type ButtonHTMLAttributes, type ReactNode } from 'react'
import { api, type Format, type Job, type Status } from './api'

export const cx = (...c: (string | false | null | undefined)[]) => c.filter(Boolean).join(' ')

type Variant = 'primary' | 'ghost' | 'outline' | 'danger'

export function Button({ variant = 'outline', className, ...p }: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant }) {
  return (
    <button
      {...p}
      className={cx(
        'inline-flex h-[34px] cursor-pointer items-center justify-center gap-2 rounded-full px-3.5 text-[13px] font-semibold transition active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-40',
        variant === 'primary' && 'h-[42px] px-[18px] text-sm font-extrabold bg-accent text-accent-ink shadow-[0_8px_28px_-6px_rgb(255_106_61/0.45)] hover:brightness-110 hover:shadow-[0_8px_36px_-4px_rgb(255_106_61/0.6)] disabled:bg-raised disabled:text-faint disabled:shadow-none disabled:opacity-100',
        variant === 'outline' && 'border border-line bg-raised hover:border-white/20 hover:bg-white/11',
        variant === 'ghost' && 'text-muted hover:bg-raised hover:text-text',
        variant === 'danger' && 'border border-line bg-raised text-bad hover:border-white/20',
        className,
      )}
    />
  )
}

/** An on/off switch with its label and an optional line under it. */
export function Toggle({ on, onChange, label, hint }: { on: boolean; onChange: (on: boolean) => void; label: string; hint?: string }) {
  return (
    <button type="button" role="switch" aria-checked={on} onClick={() => onChange(!on)}
      className="flex w-full cursor-pointer items-start gap-3 rounded-xl py-1.5 text-left">
      <span className={cx('mt-0.5 flex h-5 w-9 shrink-0 items-center rounded-full p-0.5 transition', on ? 'bg-accent' : 'bg-raised ring-1 ring-line')}>
        <span className={cx('size-4 rounded-full transition', on ? 'translate-x-4 bg-accent-ink' : 'bg-muted')} />
      </span>
      <span>
        <span className="block text-sm text-text">{label}</span>
        {hint && <span className="mt-0.5 block text-xs text-muted">{hint}</span>}
      </span>
    </button>
  )
}

/** Bytes as people read them: 1.2 GB, 340 MB. */
export const bytes = (n: number) =>
  n >= 1e9 ? `${(n / 1e9).toFixed(1)} GB` : n >= 1e6 ? `${Math.round(n / 1e6)} MB` : n >= 1e3 ? `${Math.round(n / 1e3)} KB` : `${n} B`

/** A square button with only an icon; the label is its tooltip and accessible name. */
export function IconButton({ label, className, ...p }: ButtonHTMLAttributes<HTMLButtonElement> & { label: string }) {
  return (
    <button {...p} title={label} aria-label={label}
      className={cx('grid size-[34px] shrink-0 cursor-pointer place-items-center rounded-full text-muted transition hover:bg-raised hover:text-text active:scale-[0.95]', className)} />
  )
}

const STATUS: Record<Status, { label: string; tone: string }> = {
  draft: { label: 'Writing script', tone: 'text-muted border-line' },
  script: { label: 'Needs approval', tone: 'text-warn border-warn/40' },
  approved: { label: 'Queued', tone: 'text-muted border-line' },
  generating: { label: 'Generating', tone: 'text-accent border-accent/40' },
  review: { label: 'Ready to review', tone: 'text-warn border-warn/40' },
  done: { label: 'Accepted', tone: 'text-ok border-ok/40' },
  failed: { label: 'Failed', tone: 'text-bad border-bad/40' },
}

export function StatusBadge({ status }: { status: Status }) {
  const s = STATUS[status] ?? STATUS.draft
  return <span className={cx('inline-flex h-6 items-center rounded-full border bg-black/55 px-2.5 text-[10px] font-semibold uppercase tracking-[0.06em] backdrop-blur', s.tone)}>{s.label}</span>
}

export function Progress({ value, className }: { value: number; className?: string }) {
  return (
    <div className={cx('h-1.5 overflow-hidden rounded-full bg-raised', className)}>
      <div className="h-full rounded-full bg-brand transition-[width] duration-500" style={{ width: `${Math.round(Math.min(1, Math.max(0, value)) * 100)}%` }} />
    </div>
  )
}

export function Field({ label, hint, children }: { label: string; hint?: ReactNode; children: ReactNode }) {
  return (
    <label className="block space-y-1.5">
      <div className="flex items-baseline justify-between text-xs font-medium text-muted">
        <span>{label}</span>
        {hint}
      </div>
      {children}
    </label>
  )
}

export const inputCls =
  'w-full rounded-xl border border-line bg-panel px-3 py-2 text-sm outline-none transition placeholder:text-faint focus:border-accent/70 focus:ring-4 focus:ring-accent/10'

export function Modal({ open, onClose, title, children, wide }: { open: boolean; onClose: () => void; title: string; children: ReactNode; wide?: boolean }) {
  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open, onClose])
  if (!open) return null
  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/70 p-6 backdrop-blur-sm" onMouseDown={onClose}>
      <div
        className={cx('mt-8 w-full rounded-[22px] border border-line bg-[#0e0e10] shadow-2xl shadow-black/60', wide ? 'max-w-5xl' : 'max-w-2xl')}
        onMouseDown={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-line px-5 py-3.5">
          <h2 className="font-display text-2xl">{title}</h2>
          <button className="rounded-md p-1 text-muted hover:bg-raised hover:text-text" onClick={onClose} aria-label="Close">
            <X size={18} />
          </button>
        </div>
        <div className="p-5">{children}</div>
      </div>
    </div>
  )
}

export function Empty({ icon, title, text, action }: { icon: ReactNode; title: string; text: string; action?: ReactNode }) {
  return (
    <div className="flex flex-col items-center justify-center rounded-[18px] border border-line bg-panel px-6 py-16 text-center">
      <div className="mb-3 text-muted">{icon}</div>
      <div className="font-medium">{title}</div>
      <p className="mt-1 max-w-sm text-sm text-muted">{text}</p>
      {action && <div className="mt-5">{action}</div>}
    </div>
  )
}

export const compact = (n: number) =>
  n >= 1e6 ? `${(n / 1e6).toFixed(n >= 1e7 ? 0 : 1)}M` : n >= 1e3 ? `${(n / 1e3).toFixed(n >= 1e4 ? 0 : 1)}K` : String(n)

export const ago = (t?: number | null) => {
  if (!t) return ''
  const s = Date.now() / 1000 - t
  if (s < 60) return 'just now'
  if (s < 3600) return `${Math.floor(s / 60)} min ago`
  if (s < 86400) return `${Math.floor(s / 3600)} h ago`
  return new Date(t * 1000).toLocaleDateString('en-US', { day: 'numeric', month: 'short' })
}

export const STAGES: Record<string, string> = {
  frames: 'Frames',
  depth: 'Depth',
  transitions: 'Transitions',
  tts: 'Voice',
  align: 'Subtitles',
  render: 'Render',
  qa: 'Quality check',
}

export const JOB_KIND: Record<string, string> = {
  script: 'Script',
  generate: 'Generate',
  stages: 'Rebuild',
  style_preview: 'Style preview',
}

/** The running or queued job for an episode, if any. */
export const activeJob = (jobs: Job[], slug: string) =>
  jobs.find((j) => j.slug === slug && (j.status === 'running' || j.status === 'queued'))

/** The engine's formats (the default one first); empty until they load. */
export function useFormats(): Format[] {
  const [formats, setFormats] = useState<Format[]>([])
  useEffect(() => { api.formats().then(setFormats).catch(() => setFormats([])) }, [])
  return formats
}
