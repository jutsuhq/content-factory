import { Check, Copy, ExternalLink, FolderOpen, Loader2, Mic, MicOff, RefreshCw, Trash2 } from '../icons'
import { useEffect, useState, type ReactNode } from 'react'
import { api, type Defaults, type Format, type Settings, type Storage, type Style } from '../api'
import { Button, Field, OwnBadge, Toggle, bytes, cx, inputCls } from '../ui'
import { Components, ImageProviders } from './Setup'

type Profile = {
  platform?: string
  gpu?: string
  tools?: Record<string, string | null>
  rife?: string | null
  depth_model?: string | null
  providers?: { image?: Record<string, number>; depth?: string; stt?: string; render?: string }
}

function Section({ title, text, action, children }: { title: string; text: string; action?: ReactNode; children: ReactNode }) {
  return (
    <section className="rounded-[18px] border border-line bg-panel p-5">
      <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="font-display text-xl">{title}</div>
          <p className="mt-1 text-sm text-muted">{text}</p>
        </div>
        {action}
      </div>
      {children}
    </section>
  )
}

export function SettingsPage() {
  const [s, setS] = useState<Settings | null>(null)
  const [formats, setFormats] = useState<Format[]>([])
  const [styles, setStyles] = useState<Style[]>([])
  const format = s?.defaults.format

  useEffect(() => {
    api.settings().then(setS)
    api.formats().then(setFormats)
  }, [])
  useEffect(() => {
    if (format) api.styles(format).then(setStyles)
  }, [format])

  if (!s) return <div className="grid h-64 place-items-center text-muted"><Loader2 className="animate-spin" /></div>

  return (
    <div className="mx-auto max-w-3xl space-y-5 px-8 py-8">
      <h1 className="font-display text-[40px]">Settings</h1>
      <NewVideos s={s} formats={formats} styles={styles} onSaved={setS} />
      <Formats formats={formats} onRemoved={() => api.formats().then(setFormats)} />
      <Images />
      <StorageSection />
      <Claude command={s.mcp} />
      <Machine />
      <About />
    </div>
  )
}

// What the composer starts with. Saved as soon as something changes.
function NewVideos({ s, formats, styles, onSaved }: { s: Settings; formats: Format[]; styles: Style[]; onSaved: (s: Settings) => void }) {
  const [d, setD] = useState<Defaults>(s.defaults)
  const [saved, setSaved] = useState(false)
  const change = async (patch: Partial<Defaults>) => {
    setD({ ...d, ...patch })
    setSaved(false)
    const next = await api.saveSettings({ defaults: patch })
    setD(next.defaults) // a new format brings its own first style
    onSaved(next)
    setSaved(true)
  }
  return (
    <Section title="New videos" text="What a new video starts with. You can still change any of it in the composer."
      action={saved ? <span className="flex items-center gap-1 text-xs text-ok"><Check size={13} /> Saved</span> : null}>
      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="Format">
          <select value={d.format} onChange={(e) => change({ format: e.target.value })} className={inputCls}>
            {formats.map((f) => <option key={f.id} value={f.id} title={f.description}>{f.title}</option>)}
          </select>
        </Field>
        <Field label="Language">
          <select value={d.language} onChange={(e) => change({ language: e.target.value })} className={inputCls}>
            {Object.entries(s.languages).map(([code, name]) => <option key={code} value={code}>{name}</option>)}
          </select>
        </Field>
        <Field label="Style">
          <select value={d.style} onChange={(e) => change({ style: e.target.value })} className={inputCls}>
            {styles.map((st) => <option key={st.id} value={st.id}>{st.title}</option>)}
          </select>
        </Field>
        <Field label="Length" hint={<span className="tabular text-text">{d.duration}s</span>}>
          <input type="range" min={15} max={300} step={5} value={d.duration} onChange={(e) => setD({ ...d, duration: +e.target.value })}
            onPointerUp={() => change({ duration: d.duration })} onKeyUp={() => change({ duration: d.duration })}
            className="mt-2 w-full accent-[var(--color-accent)]" />
        </Field>
        <Field label="Narration">
          <button type="button" onClick={() => change({ voice: !d.voice })}
            className={cx('flex h-[38px] w-full items-center gap-2 rounded-xl border px-3 text-sm', d.voice ? 'border-accent bg-accent/10' : 'border-line text-muted')}>
            {d.voice ? <Mic size={15} /> : <MicOff size={15} />}
            {d.voice ? 'Voice + subtitles' : 'On-screen text only'}
          </button>
        </Field>
      </div>
    </Section>
  )
}

function Claude({ command }: { command: string }) {
  const [copied, setCopied] = useState(false)
  const copy = async () => {
    await navigator.clipboard.writeText(command)
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }
  return (
    <Section title="Claude" text="Let Claude make, edit and review videos for you over MCP. Run this once in a terminal, then ask Claude for a video.">
      <div className="flex items-start gap-2 rounded-xl border border-line bg-black/40 p-3">
        <code className="min-w-0 flex-1 break-all font-mono text-xs leading-relaxed text-text">{command}</code>
        <button onClick={copy} className="shrink-0 rounded-lg p-1.5 text-muted hover:bg-white/10 hover:text-text" aria-label="Copy command">
          {copied ? <Check size={15} className="text-ok" /> : <Copy size={15} />}
        </button>
      </div>
      <p className="mt-3 text-xs text-faint">Claude uses the same queue as this app: jobs it starts show up in Queue.</p>
    </Section>
  )
}

function Machine() {
  const [profile, setProfile] = useState<Profile>({})
  const [busy, setBusy] = useState(false)
  useEffect(() => { api.profile().then((p) => setProfile(p as Profile)) }, [])
  const doctor = async () => {
    setBusy(true)
    try { setProfile((await api.doctor()) as Profile) } finally { setBusy(false) }
  }
  return (
    <Section title="Components" text={`What the engine uses on this computer${profile.platform ? ` (${profile.platform}, ${profile.gpu === 'cpu' ? 'no GPU' : profile.gpu} GPU)` : ''}. Everything except the frames runs locally.`}
      action={<Button variant="ghost" onClick={doctor} disabled={busy}>{busy ? <Loader2 size={15} className="animate-spin" /> : <RefreshCw size={15} />} Detect again</Button>}>
      <Components />
    </Section>
  )
}

function Images() {
  return (
    <Section title="Image generation" text="Frames are drawn by an image API with your own key. Turn on one or several; they share the work.">
      <ImageProviders />
    </Section>
  )
}

const PARTS = [
  ['videos', 'Videos', 'bg-accent'],
  ['frames', 'Frames', 'bg-ok'],
  ['cache', 'Cache', 'bg-warn'],
  ['other', 'Voice and other', 'bg-muted'],
  ['trash', 'Trash', 'bg-bad'],
] as const

// Where accepted videos go and what the episodes folder holds; clearing only touches what the engine can remake.
function StorageSection() {
  const [st, setSt] = useState<Storage | null>(null)
  const [busy, setBusy] = useState('')
  const [note, setNote] = useState('')
  useEffect(() => { api.storage().then(setSt) }, [])
  if (!st) return null
  const u = st.usage
  const used = PARTS.reduce((sum, [k]) => sum + u[k], 0)

  const run = async (name: string, fn: () => Promise<Storage & { freed?: number }>) => {
    setBusy(name)
    setNote('')
    try {
      const r = await fn()
      setSt(r)
      if (r.freed !== undefined) setNote(`Freed ${bytes(r.freed)}`)
    } catch (e) { setNote((e as Error).message) } finally { setBusy('') }
  }
  const clearCache = () => confirm('Delete the transition cache of finished videos? Rebuilding one then takes a few more minutes.') && run('cache', api.clearCache)
  const emptyTrash = () => confirm('Delete the episodes in the trash for good?') && run('trash', api.emptyTrash)

  return (
    <Section title="Storage" text="Where finished videos are saved and what takes space on this disk.">
      <Field label="Save accepted videos to">
        <div className="flex items-center gap-2">
          <div className="flex h-[38px] min-w-0 flex-1 items-center rounded-xl border border-line bg-bg px-3 font-mono text-xs text-text" title={st.export_shown}>
            <span className="truncate">{st.export_shown}</span>
          </div>
          <Button onClick={() => run('pick', api.chooseFolder)} disabled={!!busy}>{busy === 'pick' ? <Loader2 size={15} className="animate-spin" /> : <FolderOpen size={15} />} Choose…</Button>
          <Button variant="ghost" onClick={() => api.openFolder('export')} title="Open the folder"><ExternalLink size={15} /></Button>
        </div>
      </Field>
      <div className="mt-3 space-y-1">
        <Toggle on={st.copy_on_accept} onChange={(v) => run('t', () => api.saveStorage({ copy_on_accept: v }))}
          label="Copy each video there when you accept it" hint="Named after the title; an existing file is never replaced." />
        <Toggle on={st.clean_after_accept} onChange={(v) => run('t', () => api.saveStorage({ clean_after_accept: v }))}
          label="Free the cache after accepting" hint="Saves about 0.5 GB per video. Rebuilding it later takes a few more minutes." />
      </div>

      <div className="mt-6 flex items-baseline justify-between text-xs">
        <span className="font-medium text-muted">Episodes folder · {bytes(used)}</span>
        <span className="text-muted">{bytes(u.free)} free on this disk</span>
      </div>
      <div className="mt-2 flex h-2 overflow-hidden rounded-full bg-raised">
        {PARTS.map(([k, , color]) => u[k] > 0 && <div key={k} className={color} style={{ width: `${(u[k] / Math.max(used, 1)) * 100}%` }} />)}
      </div>
      <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted">
        {PARTS.map(([k, label, color]) => (
          <span key={k} className="flex items-center gap-1.5"><span className={cx('size-2 rounded-full', color)} />{label} <span className="tabular text-text">{bytes(u[k])}</span></span>
        ))}
      </div>
      <div className="mt-4 flex flex-wrap items-center gap-2">
        <Button onClick={clearCache} disabled={!!busy || u.cache === 0}>{busy === 'cache' ? <Loader2 size={15} className="animate-spin" /> : <RefreshCw size={15} />} Clear cache</Button>
        <Button onClick={emptyTrash} disabled={!!busy || u.trash === 0}>{busy === 'trash' ? <Loader2 size={15} className="animate-spin" /> : <Trash2 size={15} />} Empty trash</Button>
        <Button variant="ghost" onClick={() => api.openFolder('episodes')}><FolderOpen size={15} /> Open episodes folder</Button>
        {note && <span className="text-sm text-muted">{note}</span>}
      </div>
      <p className="mt-3 text-xs text-faint">The cache is the in-between frames of the transitions, remade on the next rebuild. Frames, voice and videos are kept.</p>
    </Section>
  )
}

// Shipped formats and the ones Claude added through save_format; own ones can be removed.
function Formats({ formats, onRemoved }: { formats: Format[]; onRemoved: () => void }) {
  const [busy, setBusy] = useState('')
  const remove = async (f: Format) => {
    if (!window.confirm(`Remove the format ${f.title}? Its videos stay, but cannot be rebuilt until it is back.`)) return
    setBusy(f.id)
    try {
      await api.removeFormat(f.id)
      onRemoved()
    } finally {
      setBusy('')
    }
  }
  return (
    <Section title="Formats" text="What videos the factory makes. Ask Claude for a new one: it writes the format and the engine checks it before it shows up here.">
      <div className="divide-y divide-line">
        {formats.map((f) => (
          <div key={f.id} className="flex items-center justify-between gap-3 py-2.5">
            <div className="min-w-0">
              <div className="text-sm font-medium text-text">{f.title}{f.own && <OwnBadge />}</div>
              <p className="truncate text-xs text-muted" title={f.description}>{f.description}</p>
            </div>
            {f.own && (
              <Button variant="danger" onClick={() => remove(f)} disabled={busy === f.id}>
                {busy === f.id ? <Loader2 size={15} className="animate-spin" /> : <Trash2 size={15} />} Remove
              </Button>
            )}
          </div>
        ))}
      </div>
    </Section>
  )
}

function About() {
  const [info, setInfo] = useState<{ version: string; root: string } | null>(null)
  useEffect(() => { api.health().then(setInfo) }, [])
  return (
    <Section title="About" text="Open source and local: no account and no video model. Only image prompts leave this computer, to the image API you pick.">
      <dl className="grid gap-x-8 text-sm sm:grid-cols-2">
        <div className="flex justify-between gap-3 border-b border-line py-2"><dt className="text-muted">Version</dt><dd className="tabular">{info?.version ?? '—'}</dd></div>
        <div className="flex justify-between gap-3 border-b border-line py-2"><dt className="text-muted">Engine</dt><dd className="truncate font-mono text-xs" title={info?.root}>{info?.root ?? '—'}</dd></div>
      </dl>
    </Section>
  )
}
