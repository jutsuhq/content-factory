import { ArrowRight, Check, CircleCheck, Copy, Download, ExternalLink, Key, Loader2, RefreshCw, Terminal, WifiOff } from '../icons'
import { useEffect, useState } from 'react'
import { api, type Component, type Defaults, type ImageProvider, type Settings, type Style } from '../api'
import { useApp } from '../App'
import { Button, Field, Toggle, cx, inputCls } from '../ui'

const inTauri = typeof window !== 'undefined' && '__TAURI_INTERNALS__' in window
const invoke = async <T,>(cmd: string) => (await import('@tauri-apps/api/core')).invoke<T>(cmd)

function CopyLine({ text }: { text: string }) {
  const [done, setDone] = useState(false)
  return (
    <div className="flex items-center gap-2 rounded-xl border border-line bg-black/40 py-1.5 pl-3 pr-1.5">
      <code className="min-w-0 flex-1 truncate font-mono text-xs text-text">{text}</code>
      <button onClick={() => { navigator.clipboard.writeText(text); setDone(true); setTimeout(() => setDone(false), 1500) }}
        className="shrink-0 rounded-lg p-1.5 text-muted hover:bg-white/10 hover:text-text" aria-label="Copy command">
        {done ? <Check size={14} className="text-ok" /> : <Copy size={14} />}
      </button>
    </div>
  )
}

/** The engine is not answering. In the app: install uv if it is missing, or show the first-launch progress. */
export function EngineDown() {
  type Info = { uv: boolean; running: boolean; starting: boolean; log: string }
  const [info, setInfo] = useState<Info | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!inTauri) return
    const tick = () => invoke<Info>('engine_info').then(setInfo).catch(() => {})
    tick()
    const id = window.setInterval(tick, 1500)
    return () => window.clearInterval(id)
  }, [])

  const act = async (cmds: string[]) => {
    setBusy(true)
    setError('')
    try { for (const c of cmds) await invoke(c) } catch (e) { setError(String(e)) } finally { setBusy(false) }
  }

  if (!inTauri) {
    return (
      <Centered icon={<WifiOff />} title="The engine is not running">
        In development, start it in the project folder: <CopyLine text="uv run --project engine factory serve" />
      </Centered>
    )
  }
  if (info && !info.uv) {
    return (
      <Centered icon={<Download />} title="One more piece: uv">
        <p>Content Factory runs its engine with uv, a small Python manager. It installs into the app's own folder and does not touch your system.</p>
        <Button variant="primary" className="mt-5" onClick={() => act(['install_uv', 'restart_engine'])} disabled={busy}>
          {busy ? <Loader2 size={16} className="animate-spin" /> : <Download size={16} />} Install uv and start
        </Button>
        {error && <p className="mt-3 text-sm text-bad">{error}</p>}
      </Centered>
    )
  }
  return (
    <Centered icon={info?.starting ? <Loader2 className="animate-spin" /> : <WifiOff />} title={info?.starting ? 'Starting the engine' : 'The engine stopped'}>
      <p>{info?.starting ? 'The first launch downloads Python and the engine packages, a few minutes. Later launches take seconds.' : 'It may have crashed; the log is below.'}</p>
      {info?.log && <pre className="mt-4 max-h-56 overflow-auto whitespace-pre-wrap rounded-xl bg-bg p-3 text-left font-mono text-[11px] text-muted">{info.log}</pre>}
      {!info?.starting && (
        <Button className="mt-4" onClick={() => act(['restart_engine'])} disabled={busy}><RefreshCw size={15} /> Start again</Button>
      )}
      {error && <p className="mt-3 text-sm text-bad">{error}</p>}
    </Centered>
  )
}

function Centered({ icon, title, children }: { icon: React.ReactNode; title: string; children: React.ReactNode }) {
  return (
    <div className="grid h-full place-items-center p-10">
      <div className="w-full max-w-lg text-center text-sm text-muted">
        <div className="mx-auto mb-4 grid size-12 place-items-center rounded-2xl bg-raised text-text">{icon}</div>
        <h1 className="mb-2 font-display text-[28px] text-text">{title}</h1>
        {children}
      </div>
    </div>
  )
}

/** What the engine needs on this machine: installs what it can fetch, gives a command for the rest. */
export function Components({ onReady }: { onReady?: (ready: boolean) => void }) {
  const { jobs } = useApp()
  const [items, setItems] = useState<Component[]>([])
  const job = jobs.find((j) => j.kind === 'setup')
  const busy = job?.status === 'running' || job?.status === 'queued'
  const load = () => api.setup().then((r) => { setItems(r.components); onReady?.(r.ready) })
  useEffect(() => { load() }, [job?.status]) // eslint-disable-line react-hooks/exhaustive-deps -- reload when a setup job ends
  const has = (id?: string) => !id || items.find((c) => c.id === id)?.ok
  const installable = items.filter((c) => !c.ok && c.install && !c.optional && has(c.needs))

  return (
    <div>
      <ul className="divide-y divide-line rounded-xl border border-line">
        {items.length === 0 && (
          <li className="flex items-center gap-3 px-4 py-3 text-sm text-muted"><Loader2 size={18} className="animate-spin" /> Checking this machine…</li>
        )}
        {items.map((c) => (
          <li key={c.id} className="flex flex-wrap items-center gap-3 px-4 py-3">
            {c.ok ? <CircleCheck size={18} className="shrink-0 text-ok" /> : <span className="size-[18px] shrink-0 rounded-full border-2 border-line" />}
            <div className="min-w-0 flex-1">
              <div className="text-sm text-text">{c.title}{c.optional && <span className="ml-2 text-xs text-faint">optional</span>}</div>
              <div className="text-xs text-muted">{c.detail}</div>
            </div>
            {!c.ok && c.install && (
              has(c.needs)
                ? <Button className="h-8" disabled={busy} onClick={() => api.install([c.id])}><Download size={14} /> Install</Button>
                : <span className="text-xs text-faint">needs {items.find((x) => x.id === c.needs)?.title}</span>
            )}
            {!c.ok && !c.install && c.command && <div className="w-full pl-[30px] sm:w-72 sm:pl-0"><CopyLine text={c.command} /></div>}
          </li>
        ))}
      </ul>
      <div className="mt-3 flex flex-wrap items-center gap-2">
        {installable.length > 0 && (
          <Button variant="primary" disabled={busy} onClick={() => api.install(installable.map((c) => c.id))}>
            {busy ? <Loader2 size={15} className="animate-spin" /> : <Download size={15} />} Install {installable.length === 1 ? installable[0].title.toLowerCase() : `all ${installable.length}`}
          </Button>
        )}
        <Button variant="ghost" onClick={load} disabled={busy}><RefreshCw size={15} /> Check again</Button>
        {items.some((c) => !c.ok && c.command) && <span className="flex items-center gap-1.5 text-xs text-muted"><Terminal size={14} /> Run the commands in a terminal, then check again.</span>}
      </div>
      {job && (busy || job.status === 'failed') && (
        <pre className={cx('mt-3 max-h-40 overflow-auto whitespace-pre-wrap rounded-xl bg-bg p-3 font-mono text-[11px]', job.status === 'failed' ? 'text-bad' : 'text-muted')}>
          {job.status === 'failed' ? job.error : job.log.trim().split('\n').slice(-6).join('\n') || 'starting…'}
        </pre>
      )}
    </div>
  )
}

/** Image generation: API keys per provider, on or off, and a key check that generates nothing. */
export function ImageProviders({ onChange }: { onChange?: (on: number) => void }) {
  const [items, setItems] = useState<ImageProvider[]>([])
  const [keys, setKeys] = useState<Record<string, string>>({})
  const [note, setNote] = useState<Record<string, { ok: boolean; text: string }>>({})
  const [busy, setBusy] = useState('')
  const set = (list: ImageProvider[]) => { setItems(list); onChange?.(list.filter((p) => p.enabled > 0).length) }
  useEffect(() => { api.images().then(set) }, []) // eslint-disable-line react-hooks/exhaustive-deps -- once

  const save = async (p: ImageProvider) => {
    setBusy(p.id)
    let saved = false
    try {
      set(await api.saveImages({ keys: { [p.key!]: keys[p.id] }, workers: { [p.id]: p.workers } }))
      saved = true
      setKeys({ ...keys, [p.id]: '' })
      const r = await api.checkImages(p.id)
      setNote({ ...note, [p.id]: { ok: true, text: r.message } })
    } catch (e) {
      setNote({ ...note, [p.id]: { ok: false, text: (e as Error).message } })
      // a key that failed its check stays saved but off, so no video starts on it; the toggle turns it back on
      if (saved) set(await api.saveImages({ workers: { [p.id]: 0 } }).catch(() => items))
    } finally { setBusy('') }
  }
  const toggle = async (p: ImageProvider, on: boolean) => set(await api.saveImages({ workers: { [p.id]: on ? p.workers : 0 } }))

  return (
    <ul className="space-y-3">
      {items.length === 0 && (
        <li className="flex items-center gap-3 rounded-xl border border-line p-4 text-sm text-muted"><Loader2 size={18} className="animate-spin" /> Loading providers…</li>
      )}
      {items.map((p) => (
        <li key={p.id} className={cx('rounded-xl border p-4', p.enabled ? 'border-accent/50 bg-accent/[0.04]' : 'border-line')}>
          <div className="flex flex-wrap items-start gap-3">
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2 text-sm text-text">
                {p.title}
                {p.price != null && <span className="tabular rounded-full bg-raised px-2 py-0.5 text-[11px] text-muted">≈ ${p.price.toFixed(3)} / image</span>}
                {p.private && <span className="rounded-full bg-raised px-2 py-0.5 text-[11px] text-muted">local</span>}
              </div>
              <p className="mt-0.5 text-xs text-muted">{p.note}</p>
            </div>
            {(p.key_set || p.private) && <div className="w-40"><Toggle on={p.enabled > 0} onChange={(v) => toggle(p, v)} label={p.enabled ? `On · ${p.enabled} at once` : 'Off'} /></div>}
          </div>
          {p.key && (
            <div className="mt-3 flex flex-wrap items-center gap-2">
              <div className="relative min-w-0 flex-1">
                <Key size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-faint" />
                <input type="password" autoComplete="off" value={keys[p.id] ?? ''} onChange={(e) => setKeys({ ...keys, [p.id]: e.target.value })}
                  placeholder={p.key_set ? 'Key saved · paste a new one to replace' : `${p.key}`} className={cx(inputCls, 'pl-9 font-mono text-xs')} />
              </div>
              <Button onClick={() => save(p)} disabled={busy === p.id || !keys[p.id]}>{busy === p.id ? <Loader2 size={15} className="animate-spin" /> : <Check size={15} />} Save and check</Button>
              {p.signup && <a href={p.signup} target="_blank" rel="noreferrer" className="flex items-center gap-1 text-xs text-muted hover:text-text">Get a key <ExternalLink size={12} /></a>}
            </div>
          )}
          {note[p.id] && <p className={cx('mt-2 text-xs', note[p.id].ok ? 'text-ok' : 'text-bad')}>{note[p.id].text}</p>}
        </li>
      ))}
      <li className="text-xs text-faint">Keys stay on this computer, in the engine's data folder. Frames are the only paid part: about 8 per video. No key yet? Drawn videos need none.</li>
    </ul>
  )
}

/** First run: what is needed, the image provider, the defaults; then the app. */
export function Onboarding({ settings, onDone }: { settings: Settings; onDone: () => void }) {
  const [step, setStep] = useState(0)
  const [ready, setReady] = useState(false)
  const [images, setImages] = useState(0)
  const [styles, setStyles] = useState<Style[]>([])
  const [d, setD] = useState<Defaults>(settings.defaults)
  useEffect(() => { api.styles().then(setStyles) }, [])

  const finish = async () => {
    await api.saveSettings({ defaults: d, onboarded: true })
    onDone()
  }
  const steps = ['Welcome', 'Components', 'Images', 'Defaults']

  return (
    <div className="mx-auto max-w-2xl px-8 py-10">
      <div className="mb-8 flex gap-2">
        {steps.map((s, i) => (
          <div key={s} className="flex-1">
            <div className={cx('h-1 rounded-full', i <= step ? 'bg-accent' : 'bg-raised')} />
            <div className={cx('mt-2 text-xs', i === step ? 'text-text' : 'text-faint')}>{s}</div>
          </div>
        ))}
      </div>

      {step === 0 && (
        <section>
          <h1 className="font-display text-[40px] leading-none">Welcome to Content Factory</h1>
          <p className="mt-4 text-[15px] leading-relaxed text-muted">
            It turns a script into a finished vertical video on this computer: frames from an image API (or scenes
            Claude draws in code, for free), then motion, transitions, voice, subtitles, music and the final cut, all
            computed locally. Three short steps to set it up.
          </p>
          <Button variant="primary" className="mt-8" onClick={() => setStep(1)}>Set it up <ArrowRight size={15} /></Button>
        </section>
      )}
      {step === 1 && (
        <section>
          <h2 className="font-display text-[28px]">What the engine needs</h2>
          <p className="mb-5 mt-1 text-sm text-muted">Downloads go to the app's data folder. You can come back to this in Settings.</p>
          <Components onReady={setReady} />
          <Nav back={() => setStep(0)} next={() => setStep(2)} label={ready ? 'Next' : 'Skip for now'} />
        </section>
      )}
      {step === 2 && (
        <section>
          <h2 className="font-display text-[28px]">Where frames come from</h2>
          <p className="mb-5 mt-1 text-sm text-muted">Pick one image API and paste its key. Several on at once share the work.</p>
          <ImageProviders onChange={setImages} />
          <Nav back={() => setStep(1)} next={() => setStep(3)} label={images ? 'Next' : 'Skip for now'} />
        </section>
      )}
      {step === 3 && (
        <section>
          <h2 className="font-display text-[28px]">Your defaults</h2>
          <p className="mb-5 mt-1 text-sm text-muted">What a new video starts with. Every video can change them.</p>
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Language">
              <select value={d.language} onChange={(e) => setD({ ...d, language: e.target.value })} className={inputCls}>
                {Object.entries(settings.languages).map(([code, name]) => <option key={code} value={code}>{name}</option>)}
              </select>
            </Field>
            <Field label="Style">
              <select value={d.style} onChange={(e) => setD({ ...d, style: e.target.value })} className={inputCls}>
                {styles.map((s) => <option key={s.id} value={s.id}>{s.title}</option>)}
              </select>
            </Field>
          </div>
          <div className="mt-4"><Toggle on={d.voice} onChange={(v) => setD({ ...d, voice: v })} label="Narration with subtitles" hint="Off: on-screen text only." /></div>
          <Nav back={() => setStep(2)} next={finish} label="Start making videos" />
        </section>
      )}
    </div>
  )
}

function Nav({ back, next, label }: { back: () => void; next: () => void; label: string }) {
  return (
    <div className="mt-8 flex items-center justify-between">
      <Button variant="ghost" onClick={back}>Back</Button>
      <Button variant="primary" onClick={next}>{label} <ArrowRight size={15} /></Button>
    </div>
  )
}
