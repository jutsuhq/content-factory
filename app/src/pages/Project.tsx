import { Check, ChevronsUpDown, Grid, Loader2, Plus, Save, Trash2, Users, X } from '../icons'
import { useEffect, useRef, useState } from 'react'
import { PLATFORMS, api, file, type Character, type Platform, type Project, type Settings, type Style, type Variant } from '../api'
import { useApp } from '../App'
import { Library } from './Library'
import { Button, Empty, Field, IconButton, Modal, Toggle, cx, inputCls, useFormats } from '../ui'

const COLORS = ['#ff6a3d', '#e8a33d', '#4cc38a', '#3d9cff', '#a07cff', '#ff5c93']

/** A channel's mark: its color with the first letter of its name. */
export function Avatar({ p, size = 32 }: { p: Pick<Project, 'name' | 'color'>; size?: number }) {
  return (
    <span className="grid shrink-0 place-items-center rounded-[9px] font-display text-black/80"
      style={{ width: size, height: size, background: p.color, fontSize: size * 0.5 }}>
      {p.name.trim()[0]?.toUpperCase() ?? '?'}
    </span>
  )
}

/** The channel picker at the top of the sidebar: a channel, all channels, or a new one. */
export function Switcher({ onNew }: { onNew: () => void }) {
  const { projects, project, go } = useApp()
  const [open, setOpen] = useState(false)
  const pick = (to: string) => { setOpen(false); go(to) }
  return (
    <div className="relative mb-4">
      <button onClick={() => setOpen(!open)}
        className="flex w-full items-center gap-2.5 rounded-xl border border-line bg-raised/60 px-2.5 py-2 text-left transition hover:border-white/20">
        {project ? <Avatar p={project} /> : <span className="grid size-8 place-items-center rounded-[9px] bg-raised text-muted"><Grid size={17} /></span>}
        <span className="min-w-0 flex-1">
          <span className="block truncate text-[13px] font-semibold">{project?.name ?? 'All channels'}</span>
          <span className="block truncate text-[11px] text-muted">{project ? project.handle || PLATFORMS[project.platform] : `${projects.length} channels`}</span>
        </span>
        <ChevronsUpDown size={14} className="text-muted" />
      </button>
      {open && (
        <>
          <div className="fixed inset-0 z-40" onClick={() => setOpen(false)} />
          <div className="absolute inset-x-0 top-full z-50 mt-1.5 rounded-xl border border-line bg-[#141416] p-1.5 shadow-2xl shadow-black/60">
            <div className="eyebrow px-2 py-1.5">Channels</div>
            {projects.map((p) => (
              <button key={p.id} onClick={() => pick(`/p/${p.id}`)}
                className="flex w-full items-center gap-2.5 rounded-lg px-2 py-1.5 text-left text-[13px] hover:bg-white/5">
                <Avatar p={p} size={22} /><span className="flex-1 truncate">{p.name}</span>
                {p.id === project?.id && <Check size={14} className="text-accent" />}
              </button>
            ))}
            <div className="my-1.5 border-t border-line" />
            <button onClick={() => pick('/projects')} className="flex w-full items-center gap-2.5 rounded-lg px-2 py-1.5 text-left text-[13px] hover:bg-white/5">
              <Grid size={16} className="text-muted" /> All channels
            </button>
            <button onClick={() => { setOpen(false); onNew() }} className="flex w-full items-center gap-2.5 rounded-lg px-2 py-1.5 text-left text-[13px] hover:bg-white/5">
              <Plus size={16} className="text-accent" /> New channel
            </button>
          </div>
        </>
      )}
    </div>
  )
}

function PlatformPick({ value, onChange }: { value: Platform; onChange: (p: Platform) => void }) {
  return (
    <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
      {(Object.keys(PLATFORMS) as Platform[]).map((k) => (
        <button key={k} type="button" onClick={() => onChange(k)}
          className={cx('rounded-xl border px-3 py-2 text-left text-xs transition', value === k ? 'border-accent bg-accent/10 text-text' : 'border-line text-muted hover:border-muted')}>
          {PLATFORMS[k]}
        </button>
      ))}
    </div>
  )
}

function ColorPick({ value, onChange }: { value: string; onChange: (c: string) => void }) {
  return (
    <div className="flex items-center gap-2">
      {COLORS.map((c) => (
        <button key={c} type="button" onClick={() => onChange(c)} aria-label={c}
          className={cx('size-7 rounded-full ring-offset-2 ring-offset-[#0e0e10] transition', value === c && 'ring-2 ring-text')} style={{ background: c }} />
      ))}
    </div>
  )
}

/** A new channel: what it is called and where it posts. Its first variant takes the defaults from Settings. */
export function NewProject({ onClose }: { onClose: () => void }) {
  const { go, reloadProjects } = useApp()
  const [name, setName] = useState('')
  const [platform, setPlatform] = useState<Platform>('tiktok')
  const [handle, setHandle] = useState('')
  const [color, setColor] = useState(COLORS[Math.floor(Math.random() * COLORS.length)])
  const [brief, setBrief] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const create = async () => {
    setBusy(true)
    try {
      const p = await api.createProject({ name: name.trim(), platform, handle: handle.trim(), color, brief: brief.trim() })
      await reloadProjects()
      onClose()
      go(`/p/${p.id}/variants`)
    } catch (e) {
      setError((e as Error).message)
      setBusy(false)
    }
  }
  return (
    <Modal open onClose={onClose} title="New channel">
      <div className="space-y-5">
        <p className="text-sm text-muted">A channel keeps its videos alike: the same look, voice and characters. Set them up once, then every new video starts from them.</p>
        <div className="flex items-end gap-4">
          <Avatar p={{ name: name || '?', color }} size={44} />
          <Field label="Name"><input autoFocus value={name} onChange={(e) => setName(e.target.value)} placeholder="Tiny Town Tales" className={inputCls} /></Field>
        </div>
        <Field label="Where it posts"><PlatformPick value={platform} onChange={setPlatform} /></Field>
        <div className="grid grid-cols-2 gap-4">
          <Field label="Handle"><input value={handle} onChange={(e) => setHandle(e.target.value)} placeholder="@tinytowntales" className={inputCls} /></Field>
          <Field label="Color"><ColorPick value={color} onChange={setColor} /></Field>
        </div>
        <Field label="What the channel is about" hint="Claude reads it before writing a script">
          <textarea value={brief} onChange={(e) => setBrief(e.target.value)} rows={3} className={cx(inputCls, 'resize-none')}
            placeholder="Cozy 3D stories about a boy and his dog in a small town. Warm, a little funny, a lesson at the end." />
        </Field>
        {error && <p className="text-sm text-bad">{error}</p>}
        <div className="flex justify-end gap-2">
          <Button variant="ghost" onClick={onClose}>Cancel</Button>
          <Button variant="primary" disabled={busy || !name.trim()} onClick={create}>
            {busy ? <Loader2 size={16} className="animate-spin" /> : <Plus size={16} />} Create channel
          </Button>
        </div>
      </div>
    </Modal>
  )
}

/** Every channel, with how much each holds. */
export function Projects({ onNew }: { onNew: () => void }) {
  const { projects, episodes } = useApp()
  const loose = episodes.filter((e) => !e.project).length
  return (
    <div className="mx-auto max-w-7xl px-8 py-8">
      <div className="mb-6 flex items-center justify-between">
        <div><div className="eyebrow">Workspace</div><h1 className="font-display text-[40px]">All channels</h1></div>
        <Button variant="primary" onClick={onNew}><Plus size={16} /> New channel</Button>
      </div>
      {!projects.length ? (
        <Empty icon={<Users />} title="No channels yet" text="A channel is one TikTok or YouTube account: its look, voice and characters, set up once for every video."
          action={<Button variant="primary" onClick={onNew}>New channel</Button>} />
      ) : (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
          {projects.map((p) => {
            const eps = episodes.filter((e) => e.project === p.id)
            const thumbs = eps.filter((e) => e.thumb).slice(0, 4)
            return (
              <a key={p.id} href={`#/p/${p.id}`} className="group rounded-[18px] border border-line bg-panel p-4 transition hover:-translate-y-0.5 hover:border-muted/60">
                <div className="flex items-center gap-3">
                  <Avatar p={p} size={40} />
                  <div className="min-w-0">
                    <div className="truncate font-semibold">{p.name}</div>
                    <div className="truncate text-xs text-muted">{PLATFORMS[p.platform]}{p.handle && ` · ${p.handle}`}</div>
                  </div>
                </div>
                <div className="mt-4 grid grid-cols-4 gap-1.5">
                  {[0, 1, 2, 3].map((i) => (
                    <div key={i} className="aspect-[9/16] overflow-hidden rounded-lg bg-raised">
                      {thumbs[i] && <img src={file(`episodes/${thumbs[i].slug}/${thumbs[i].thumb}`, thumbs[i].updated)} className="size-full object-cover" alt="" />}
                    </div>
                  ))}
                </div>
                <div className="mt-3 flex gap-4 text-xs text-muted">
                  <span><span className="tabular text-text">{eps.length}</span> videos</span>
                  <span><span className="tabular text-text">{p.cast.length}</span> characters</span>
                  <span><span className="tabular text-text">{p.variants.length}</span> variants</span>
                </div>
              </a>
            )
          })}
        </div>
      )}
      {loose > 0 && <p className="mt-6 text-sm text-muted"><a href="#/videos" className="text-text underline-offset-2 hover:underline">{loose} videos</a> belong to no channel.</p>}
    </div>
  )
}

const TABS = [
  { id: '', label: 'Videos' },
  { id: 'cast', label: 'Cast' },
  { id: 'variants', label: 'Variants' },
  { id: 'channel', label: 'Channel' },
]

/** One channel: its videos, its cast, its variants and its own details. Edits stay a draft until saved. */
export function ProjectPage({ id, tab }: { id: string; tab: string }) {
  const { projects, reloadProjects, compose, go } = useApp()
  const saved = projects.find((p) => p.id === id)
  const [draft, setDraft] = useState<Project | null>(saved ?? null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const loaded = useRef('')
  useEffect(() => {
    if (saved && loaded.current !== id) { loaded.current = id; setDraft(saved) }
  }, [id, saved])
  if (!saved || !draft) return <div className="p-8 text-muted">{projects.length ? 'No such channel.' : ''}</div>
  const dirty = JSON.stringify(draft) !== JSON.stringify(saved)
  const edit = (patch: Partial<Project>) => setDraft({ ...draft, ...patch })

  const save = async (p: Project = draft) => {
    setBusy(true)
    setError('')
    try {
      setDraft(await api.saveProject(p))
      await reloadProjects()
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setBusy(false)
    }
  }
  // reference images are saved at once: take the new list of each character into the draft too
  const refsFrom = (p: Project) => {
    setDraft((d) => d && { ...d, cast: d.cast.map((c) => ({ ...c, refs: p.cast.find((x) => x.id === c.id)?.refs ?? c.refs })) })
    reloadProjects()
  }

  return (
    <div className="mx-auto max-w-7xl px-8 py-8 pb-28">
      <div className="mb-5 flex items-center gap-4">
        <Avatar p={draft} size={52} />
        <div className="min-w-0">
          <div className="eyebrow">{PLATFORMS[saved.platform]}{saved.handle && ` · ${saved.handle}`}</div>
          <h1 className="truncate font-display text-[40px] leading-tight">{saved.name}</h1>
        </div>
        <Button variant="primary" className="ml-auto" onClick={() => compose({ project: saved.id })}><Plus size={16} /> New video</Button>
      </div>
      <div className="mb-6 flex gap-1 border-b border-line">
        {TABS.map((t) => (
          <a key={t.id} href={`#/p/${id}${t.id && `/${t.id}`}`}
            className={cx('-mb-px border-b-2 px-3 py-2 text-sm font-medium transition', tab === t.id ? 'border-accent text-text' : 'border-transparent text-muted hover:text-text')}>
            {t.label}
            {t.id === 'cast' && <span className="tabular ml-1.5 text-muted">{saved.cast.length}</span>}
            {t.id === 'variants' && <span className="tabular ml-1.5 text-muted">{saved.variants.length}</span>}
          </a>
        ))}
      </div>

      {tab === '' && <Library project={saved} />}
      {tab === 'cast' && <Cast p={draft} edit={edit} save={save} refsFrom={refsFrom} />}
      {tab === 'variants' && <Variants p={draft} edit={edit} />}
      {tab === 'channel' && (
        <div className="max-w-2xl space-y-5">
          <Field label="Name"><input value={draft.name} onChange={(e) => edit({ name: e.target.value })} className={inputCls} /></Field>
          <Field label="Where it posts"><PlatformPick value={draft.platform} onChange={(platform) => edit({ platform })} /></Field>
          <div className="grid grid-cols-2 gap-4">
            <Field label="Handle"><input value={draft.handle} onChange={(e) => edit({ handle: e.target.value })} className={inputCls} /></Field>
            <Field label="Color"><ColorPick value={draft.color} onChange={(color) => edit({ color })} /></Field>
          </div>
          <Field label="What the channel is about" hint="Claude reads it before writing a script">
            <textarea value={draft.brief} onChange={(e) => edit({ brief: e.target.value })} rows={5} className={cx(inputCls, 'resize-none')} />
          </Field>
          <div className="flex items-center justify-between rounded-xl border border-line p-4">
            <div><div className="text-sm">Delete the channel</div><div className="text-xs text-muted">Its videos stay in All videos. The channel goes to the trash.</div></div>
            <Button variant="danger" onClick={async () => {
              if (!window.confirm(`Delete ${saved.name}?`)) return
              await api.removeProject(saved.id)
              await reloadProjects()
              go('/projects')
            }}><Trash2 size={15} /> Delete</Button>
          </div>
        </div>
      )}

      {(dirty || error) && (
        <div className="fixed inset-x-0 bottom-5 z-30 flex justify-center pl-60">
          <div className="flex items-center gap-3 rounded-full border border-line bg-[#141416] py-1.5 pl-4 pr-1.5 shadow-2xl shadow-black/60">
            <span className={cx('text-sm', error ? 'text-bad' : 'text-muted')}>{error || 'Unsaved changes'}</span>
            <Button variant="ghost" onClick={() => { setDraft(saved); setError('') }}>Discard</Button>
            <Button variant="primary" className="!h-9" disabled={busy} onClick={() => save()}>
              {busy ? <Loader2 size={15} className="animate-spin" /> : <Save size={15} />} Save
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}

type Edit = (patch: Partial<Project>) => void

function Cast({ p, edit, save, refsFrom }: { p: Project; edit: Edit; save: (p: Project) => Promise<void>; refsFrom: (p: Project) => void }) {
  const set = (i: number, patch: Partial<Character>) => edit({ cast: p.cast.map((c, k) => (k === i ? { ...c, ...patch } : c)) })
  // a new character is saved at once, so it has an id its reference images can go under
  const add = () => save({ ...p, cast: [...p.cast, { id: '', name: `Character ${p.cast.length + 1}`, looks: '', refs: [] }] })
  return (
    <div>
      <p className="mb-5 max-w-2xl text-sm text-muted">
        The channel's recurring characters. When a video has them, their looks go into every frame prompt word for word and up to three of
        their images go with every frame, so they look the same in every scene and every video. The first image matters most: make it the face.
      </p>
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {p.cast.map((c, i) => (
          <div key={c.id || i} className="rounded-[18px] border border-line bg-panel p-4">
            <div className="mb-3 flex items-center gap-2">
              <input value={c.name} onChange={(e) => set(i, { name: e.target.value })} aria-label="Name"
                className="min-w-0 flex-1 bg-transparent font-display text-2xl outline-none" />
              <IconButton label="Remove the character" onClick={() => edit({ cast: p.cast.filter((_, k) => k !== i) })}><Trash2 size={15} /></IconButton>
            </div>
            <div className="mb-3 flex gap-2 overflow-x-auto">
              {c.refs.map((r, k) => (
                <div key={r} className="group relative h-28 shrink-0">
                  <img src={file(r)} className={cx('h-full rounded-lg object-cover', k === 0 && 'ring-2 ring-accent')} alt="" />
                  {c.id && (
                    <button onClick={() => api.removeRef(p.id, c.id, r).then(refsFrom)} aria-label="Remove the image"
                      className="absolute right-1 top-1 hidden rounded-full bg-black/70 p-1 group-hover:block"><X size={12} /></button>
                  )}
                </div>
              ))}
              {c.id ? (
                <label className="grid h-28 w-20 shrink-0 cursor-pointer place-items-center rounded-lg border border-dashed border-line text-center text-[11px] text-muted hover:border-muted">
                  <span><Plus size={16} className="mx-auto mb-1" />image</span>
                  <input type="file" accept="image/png,image/jpeg,image/webp" multiple className="hidden" onChange={async (e) => {
                    let last: Project | null = null
                    for (const f of Array.from(e.target.files ?? [])) last = await api.addRef(p.id, c.id, f)
                    if (last) refsFrom(last)
                    e.target.value = ''
                  }} />
                </label>
              ) : <span className="self-center text-xs text-muted">Save to add images</span>}
            </div>
            <Field label="Looks, added to every frame prompt">
              <textarea value={c.looks} onChange={(e) => set(i, { looks: e.target.value })} rows={3} className={cx(inputCls, 'resize-none')}
                placeholder="A cheerful 8-year-old boy, round face, brown hair in a small top-knot, mustard-yellow puffer jacket, orange scarf." />
            </Field>
          </div>
        ))}
        <button onClick={add} className="grid min-h-48 place-items-center rounded-[18px] border border-dashed border-line text-sm text-muted transition hover:border-muted hover:text-text">
          <span><Plus size={20} className="mx-auto mb-1.5" />Add a character</span>
        </button>
      </div>
    </div>
  )
}

function Variants({ p, edit }: { p: Project; edit: Edit }) {
  const [settings, setSettings] = useState<Settings | null>(null)
  useEffect(() => { api.settings().then(setSettings) }, [])
  const set = (i: number, v: Variant) => edit({ variants: p.variants.map((x, k) => (k === i ? v : x)) })
  return (
    <div>
      <p className="mb-5 max-w-2xl text-sm text-muted">
        A variant is a ready set of settings for one kind of video on this channel: a series in English and its Russian twin, long stories and
        quick facts. A new video picks one and can still change anything. What a variant leaves empty comes from Settings.
      </p>
      <div className="space-y-4">
        {p.variants.map((v, i) => (
          <VariantCard key={v.id || i} v={v} cast={p.cast} languages={settings?.languages ?? {}}
            onChange={(n) => set(i, n)} onRemove={p.variants.length > 1 ? () => edit({ variants: p.variants.filter((_, k) => k !== i) }) : undefined} />
        ))}
      </div>
      <Button className="mt-4" onClick={() => edit({ variants: [...p.variants, { ...p.variants[0], id: '', name: `Variant ${p.variants.length + 1}` }] })}>
        <Plus size={15} /> Add a variant
      </Button>
    </div>
  )
}

function VariantCard({ v, cast, languages, onChange, onRemove }: {
  v: Variant; cast: Character[]; languages: Record<string, string>; onChange: (v: Variant) => void; onRemove?: () => void
}) {
  const formats = useFormats()
  const fmt = formats.find((f) => f.id === v.format) ?? formats[0]
  const modeId = v.render_mode && fmt?.render_modes[v.render_mode] ? v.render_mode : Object.keys(fmt?.render_modes ?? {})[0]
  const mode = fmt?.render_modes[modeId]
  const looks = mode && typeof mode.style === 'object' ? mode.style.looks : null
  const [styles, setStyles] = useState<Style[]>([])
  useEffect(() => { if (fmt) api.styles(fmt.id).then(setStyles) }, [fmt?.id]) // eslint-disable-line react-hooks/exhaustive-deps -- per format
  const set = (patch: Partial<Variant>) => onChange({ ...v, ...patch })
  const [custom, setCustom] = useState(!!v.style_prompt) // a described style, not a preset
  const style = custom ? 'custom' : v.style ?? ''
  const castIds = v.cast ?? []

  return (
    <div className="rounded-[18px] border border-line bg-panel p-4">
      <div className="mb-4 flex items-center gap-2">
        <input value={v.name} onChange={(e) => set({ name: e.target.value })} aria-label="Variant name"
          className="min-w-0 flex-1 bg-transparent font-display text-2xl outline-none" />
        {onRemove && <IconButton label="Remove the variant" onClick={onRemove}><Trash2 size={15} /></IconButton>}
      </div>
      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <Field label="Format">
          <select value={fmt?.id ?? ''} onChange={(e) => { setCustom(false); set({ format: e.target.value, render_mode: undefined, style: undefined, style_prompt: undefined }) }} className={inputCls}>
            {formats.map((f) => <option key={f.id} value={f.id}>{f.title}</option>)}
          </select>
        </Field>
        {fmt && Object.keys(fmt.render_modes).length > 1 ? (
          <Field label="Picture">
            <select value={modeId} onChange={(e) => set({ render_mode: e.target.value, style: undefined, style_prompt: undefined })} className={inputCls}>
              {Object.entries(fmt.render_modes).map(([id, r]) => <option key={id} value={id}>{r.title}</option>)}
            </select>
          </Field>
        ) : <div className="hidden md:block" />}
        <Field label={looks ? 'Look' : 'Style'}>
          <select value={style} className={inputCls}
            onChange={(e) => {
              setCustom(e.target.value === 'custom')
              set(e.target.value === 'custom' ? { style: undefined } : { style: e.target.value || undefined, style_prompt: undefined })
            }}>
            <option value="">Default</option>
            {looks ? looks.map((l) => <option key={l.id} value={l.id}>{l.id}</option>) : styles.map((s) => <option key={s.id} value={s.id}>{s.title}</option>)}
            {!looks && <option value="custom">Custom…</option>}
          </select>
        </Field>
        {style === 'custom' && (
          <div className="md:col-span-3">
            <Field label="Style description, for the image model">
              <textarea value={v.style_prompt ?? ''} onChange={(e) => set({ style_prompt: e.target.value || undefined })} rows={2} className={cx(inputCls, 'resize-none')}
                placeholder="Soft toon 3D, warm afternoon light, pastel colors, rounded shapes" />
            </Field>
          </div>
        )}
        <Field label="Language">
          <select value={v.language ?? ''} onChange={(e) => set({ language: e.target.value || undefined })} className={inputCls}>
            <option value="">Default</option>
            {Object.entries(languages).map(([code, name]) => <option key={code} value={code}>{name}</option>)}
          </select>
        </Field>
        <Field label="Length, seconds">
          <input type="number" min={fmt?.duration_seconds.min} max={fmt?.duration_seconds.max} step={5} value={v.duration ?? ''} placeholder="Default"
            onChange={(e) => set({ duration: e.target.value ? +e.target.value : undefined })} className={inputCls} />
        </Field>
        <div className="pt-5"><Toggle on={v.voice ?? true} onChange={(voice) => set({ voice })} label={v.voice ?? true ? 'Voice + subtitles' : 'On-screen text only'} /></div>
        {cast.length > 0 && (
          <div className="md:col-span-3">
            <div className="mb-1.5 text-xs font-medium text-muted">In every video, unless a video picks others</div>
            <CastPick cast={cast} value={castIds} onChange={(ids) => set({ cast: ids })} />
          </div>
        )}
        <div className="md:col-span-3">
          <Field label="Hashtags, added to every post caption">
            <input value={v.hashtags ?? ''} onChange={(e) => set({ hashtags: e.target.value })} placeholder="#cozy #animation #storytime" className={inputCls} />
          </Field>
        </div>
      </div>
    </div>
  )
}

/** Characters to toggle, each with its first image. */
export function CastPick({ cast, value, onChange }: { cast: Character[]; value: string[]; onChange: (ids: string[]) => void }) {
  return (
    <div className="flex flex-wrap gap-2">
      {cast.map((c) => {
        const on = value.includes(c.id)
        return (
          <button key={c.id} type="button" onClick={() => onChange(on ? value.filter((x) => x !== c.id) : [...value, c.id])}
            className={cx('flex items-center gap-2 rounded-full border py-1 pl-1 pr-3 text-xs transition', on ? 'border-accent bg-accent/10 text-text' : 'border-line text-muted hover:border-muted')}>
            {c.refs[0] ? <img src={file(c.refs[0])} className="size-6 rounded-full object-cover" alt="" /> : <span className="grid size-6 place-items-center rounded-full bg-raised">{c.name[0]}</span>}
            {c.name}
          </button>
        )
      })}
    </div>
  )
}
