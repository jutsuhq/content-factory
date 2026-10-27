import { ArrowLeft, Check, CircleCheck, CircleX, Copy, ExternalLink, Film, FolderOpen, Info, Music, ChevronDown, Languages, Loader2, Play, Plus, RefreshCw, Save, Square, Trash2, TriangleAlert } from '../icons'
import { useEffect, useState } from 'react'
import { ENGINE, api, episodeFile, formatOf, type Beat, type Beats, type Episode, type FieldSpec, type Job, type Track, type Voice } from '../api'
import { useApp } from '../App'
import { Button, Field, IconButton, Progress, STAGES, StatusBadge, activeJob, cx, inputCls, useFormats } from '../ui'

const pad = (n: number) => String(n).padStart(2, '0')
const text = (v: unknown) => (typeof v === 'string' ? v : '')
// An svg field's scene as a thumbnail: ids get the beat's suffix so url(#sky) finds its own gradient, and scripts
// and on* handlers are dropped, since the markup comes from a file an agent wrote.
const thumb = (svg: string, k: number) =>
  svg.replace(/<script[\s\S]*?<\/script>/gi, '').replace(/\son\w+="[^"]*"/gi, '')
    .replace(/id="([^"]+)"/g, `id="$1-t${k}"`).replace(/url\(#([^)]+)\)/g, `url(#$1-t${k})`)

export function EpisodePage({ slug }: { slug: string }) {
  const { episodes, jobs, refresh, go } = useApp()
  const fromList = episodes.find((e) => e.slug === slug)
  const [ep, setEp] = useState<Episode | null>(fromList ?? null)

  // The list refreshes on every job event; keep the page in step with it.
  useEffect(() => {
    if (fromList) setEp(fromList)
    else api.episode(slug).then(setEp).catch(() => setEp(null))
  }, [fromList, slug])

  if (!ep) return <div className="p-10 text-muted">Loading…</div>
  const job = activeJob(jobs, slug)
  const lastJob = jobs.find((j) => j.slug === slug)

  const remove = async () => {
    if (!confirm('Move this episode to the trash (episodes/.trash)?')) return
    await api.remove(slug)
    refresh()
    go('/videos')
  }

  return (
    <div className="mx-auto max-w-7xl px-8 py-6">
      <div className="mb-5 flex items-center gap-3">
        <a href="#/videos" className="rounded-xl p-1.5 text-muted hover:bg-raised hover:text-text" aria-label="Back"><ArrowLeft size={18} /></a>
        <div className="min-w-0 flex-1">
          <h1 className="line-clamp-2 font-display text-[32px] leading-[1.05]">{ep.title}</h1>
          {ep.topic && ep.topic !== ep.title && <p className="mt-1 truncate text-sm text-muted">{ep.topic}</p>}
        </div>
        <StatusBadge status={ep.status} />
        <Button variant="ghost" onClick={remove} title="Move to trash"><Trash2 size={16} /></Button>
      </div>

      {ep.status === 'failed' && <Failed ep={ep} job={lastJob} />}
      {(ep.status === 'approved' || ep.status === 'generating' || job?.kind === 'stages') && <Pipeline ep={ep} job={job} />}
      {(ep.status === 'review' || ep.status === 'done') && !job && <Review ep={ep} />}
      {ep.beats && <ScriptEditor ep={ep} key={ep.slug + (ep.updated ?? '')} />}
    </div>
  )
}

function Failed({ ep, job }: { ep: Episode; job?: Job }) {
  return (
    <div className="mb-6 rounded-[18px] border border-bad/30 bg-bad/5 p-5">
      <div className="flex items-start gap-3">
        <TriangleAlert className="mt-0.5 shrink-0 text-bad" size={18} />
        <div className="min-w-0 flex-1">
          <div className="font-medium">Something went wrong</div>
          <p className="mt-1 break-words text-sm text-muted">{ep.error || job?.error || 'unknown error'}</p>
          <div className="mt-4 flex gap-2">
            <Button variant="primary" onClick={() => api.rerun(ep.slug)}><RefreshCw size={15} /> Retry generation</Button>
          </div>
          {job?.log && (
            <details className="mt-4">
              <summary className="cursor-pointer text-xs text-muted">Log</summary>
              <pre className="mt-2 max-h-64 overflow-auto whitespace-pre-wrap rounded-xl bg-bg p-3 text-xs text-muted">{job.log}</pre>
            </details>
          )}
        </div>
      </div>
    </div>
  )
}

function Pipeline({ ep, job }: { ep: Episode; job?: Job }) {
  // the stages the episode's render mode declares; the voice ones only run for a narrated script
  const declared = formatOf(useFormats(), ep.beats)?.mode.stages ?? Object.keys(STAGES)
  const stages = declared.filter((s) => ep.beats?.voice || (s !== 'tts' && s !== 'align'))
  const current = job?.stage ? stages.indexOf(job.stage) : -1
  return (
    <div className="mb-6 rounded-[18px] border border-line bg-panel p-5">
      <div className="mb-4 flex items-center justify-between">
        <div className="font-medium">{job ? (job.status === 'queued' ? 'Waiting in queue' : 'Generating') : 'Starting…'}</div>
        <div className="flex items-center gap-3">
          <span className="tabular text-sm text-muted">{Math.round((job?.progress ?? 0) * 100)}%</span>
          {job && <Button variant="ghost" onClick={() => api.cancel(job.id)}><Square size={14} /> Stop</Button>}
        </div>
      </div>
      <Progress value={job?.progress ?? 0} />
      <div className="mt-4 grid grid-cols-6 gap-2 text-xs">
        {stages.map((s, i) => (
          <div key={s} className={cx('rounded-xl border px-2 py-1.5 text-center', i < current ? 'border-ok/30 text-ok' : i === current ? 'border-accent text-text' : 'border-line text-muted')}>
            {i === current && <Loader2 size={11} className="mr-1 inline animate-spin" />}
            {STAGES[s]}
          </div>
        ))}
      </div>
      {ep.frames.length > 0 && (
        <div className="mt-5 flex gap-2 overflow-x-auto pb-1">
          {ep.frames.map((f) => <img key={f} src={episodeFile(ep, `work/public/frames/${f}`)} className="h-40 rounded-xl" alt="" />)}
        </div>
      )}
      {job?.log && <pre className="mt-4 max-h-40 overflow-auto whitespace-pre-wrap rounded-xl bg-bg p-3 font-mono text-xs text-muted">{job.log.trim().split('\n').slice(-12).join('\n')}</pre>}
    </div>
  )
}

function Review({ ep }: { ep: Episode }) {
  const { compose, refresh } = useApp()
  const b = ep.beats
  const fm = formatOf(useFormats(), b)
  const [caption, setCaption] = useState(ep.caption || '')
  // a new caption starts from the format's caption template, {field} filled from the script
  useEffect(() => {
    if (!ep.caption && b && fm?.format.caption) setCaption((c) => c || fm.format.caption!.replace(/\{(\w+)\}/g, (_, k) => text(b[k])))
  }, [fm?.format.id]) // eslint-disable-line react-hooks/exhaustive-deps -- once the formats load
  const [note, setNote] = useState<{ ok: boolean; text: string } | null>(null)
  const done = ep.status === 'done'
  const finder = navigator.userAgent.includes('Mac') ? 'Finder' : 'Explorer'

  const tell = (ok: boolean, text: string) => {
    setNote({ ok, text })
    setTimeout(() => setNote((n) => (n?.text === text ? null : n)), 2500)
  }
  const act = async (fn: () => Promise<unknown>, said: string) => {
    try { await fn(); if (said) tell(true, said) } catch (e) { tell(false, (e as Error).message) }
  }
  const accept = () => act(async () => { await api.accept(ep.slug, caption); refresh() }, '')

  return (
    <div className="mb-8 grid grid-cols-[minmax(0,1fr)] gap-6 lg:grid-cols-[360px_minmax(0,1fr)]">
      <div>
        {ep.video ? (
          <video key={ep.video_mtime} src={episodeFile(ep, ep.video, ep.video_mtime)} controls className="w-full rounded-[18px] border border-line bg-black" />
        ) : (
          <div className="grid aspect-[9/16] place-items-center rounded-[18px] border border-line text-muted">No video</div>
        )}
      </div>
      <div className="space-y-5">
        <div className="rounded-[18px] border border-line bg-panel p-5">
          {ep.video && (
            <>
              <div className="flex items-center gap-2 text-xs text-muted">
                <Film size={15} className="shrink-0" />
                <span className="min-w-0 truncate font-mono">{ep.video.split('/').pop()}</span>
              </div>
              <div className="mt-3 flex flex-wrap gap-2">
                <Button onClick={() => act(() => api.video(ep.slug, 'copy'), 'Video copied: paste it into any app')}><Copy size={15} /> Copy video</Button>
                <Button onClick={() => act(() => api.video(ep.slug, 'reveal'), '')}><FolderOpen size={15} /> Show in {finder}</Button>
                <Button onClick={() => act(() => api.video(ep.slug, 'open'), '')}><ExternalLink size={15} /> Open</Button>
              </div>
              <div className="my-5 h-px bg-line" />
            </>
          )}
          <div className="mb-1.5 flex items-center justify-between">
            <span className="text-xs font-medium text-muted">Post caption</span>
            <IconButton label="Copy caption" className="-my-2 -mr-2" onClick={() => act(() => navigator.clipboard.writeText(caption), 'Caption copied')}><Copy size={15} /></IconButton>
          </div>
          <textarea value={caption} onChange={(e) => setCaption(e.target.value)} onBlur={() => done && caption !== ep.caption && api.accept(ep.slug, caption)}
            rows={4} aria-label="Post caption" className={cx(inputCls, 'resize-none')} />
          <div className="mt-4 flex min-h-[42px] flex-wrap items-center gap-3">
            {done
              ? <span className="flex min-w-0 items-center gap-1.5 text-sm text-ok"><CircleCheck size={16} className="shrink-0" /> Accepted
                  {ep.exported && <span className="truncate text-muted" title={ep.exported}>· saved to {ep.exported.split(/[\\/]/).slice(-2, -1)[0]}</span>}</span>
              : <Button variant="primary" onClick={accept} disabled={!ep.video}><Check size={15} /> Accept</Button>}
            {note && <span className={cx('text-sm', note.ok ? 'text-muted' : 'text-bad')}>{note.text}</span>}
          </div>
        </div>

        <QualityCheck ep={ep} />

        {ep.beats && fm?.mode.stages.includes('frames') && (
          <div className="rounded-[18px] border border-line bg-panel p-5">
            <div className="mb-3 flex items-center justify-between">
              <span className="eyebrow">Frames by beat</span>
              <Button variant="ghost" className="-my-2 -mr-2" onClick={() => api.rerun(ep.slug)}><RefreshCw size={14} /> Rebuild video</Button>
            </div>
            <div className="flex gap-2 overflow-x-auto pb-1">
              {ep.beats.beats.map((beat, i) => {
                const f = `${pad(i + 1)}-916.png`
                return (
                  <div key={i} className="w-28 shrink-0">
                    {ep.frames.includes(f) ? <img src={episodeFile(ep, `work/public/frames/${f}`)} className="aspect-[9/16] w-full rounded-xl object-cover" alt="" /> : <div className="aspect-[9/16] rounded-xl bg-raised" />}
                    <div className="mt-1 truncate text-xs text-muted">{i + 1}. {text(beat[fm.fields('beat')[0]?.key ?? ''])}</div>
                    <button onClick={() => api.regenerateBeat(ep.slug, i + 1)} className="mt-0.5 flex items-center gap-1 text-xs text-faint transition hover:text-accent">
                      <RefreshCw size={11} /> another take
                    </button>
                  </div>
                )
              })}
            </div>
            <p className="mt-2 text-xs text-muted">A new take of the first frame redoes all frames: the others are edits of it.</p>
          </div>
        )}

        <OtherLanguages ep={ep} />

        <div className="flex items-center justify-between gap-3 rounded-[18px] border border-line bg-panel p-5">
          <div>
            <div className="eyebrow">Continue the series</div>
            <p className="mt-1 text-xs text-muted">A new episode in the same world and style.</p>
          </div>
          <Button onClick={() => compose({ series: ep.series ?? ep.slug, language: ep.language ?? b?.language,
            style: b?.style_prompt ? 'custom' : b?.style, style_prompt: b?.style_prompt })}>
            <Plus size={15} /> Next episode
          </Button>
        </div>
      </div>
    </div>
  )
}

/** Versions of this video in other languages: same frames, new voice and subtitles. */
function OtherLanguages({ ep }: { ep: Episode }) {
  const { episodes, go, refresh } = useApp()
  const [voices, setVoices] = useState<Record<string, Voice>>({})
  const [error, setError] = useState('')
  useEffect(() => { api.voices().then(setVoices).catch(() => {}) }, [])
  const source = ep.translation_of ?? ep.slug
  const versions = episodes.filter((e) => e.slug === source || e.translation_of === source)
  const own = ep.language ?? ep.beats?.language ?? 'en'
  const have = new Set(versions.map((e) => e.language ?? e.beats?.language ?? 'en'))
  const copy = async (code: string) => {
    setError('')
    try {
      const r = await api.translate(source, code)
      refresh()
      go(`/episode/${r.slug}`)
    } catch (e) {
      setError((e as Error).message)
    }
  }
  return (
    <div className="rounded-[18px] border border-line bg-panel p-5">
      <div className="eyebrow mb-3">Other languages</div>
      <div className="flex flex-wrap gap-2">
        {versions.filter((e) => e.slug !== ep.slug).map((e) => (
          <a key={e.slug} href={`#/episode/${encodeURIComponent(e.slug)}`}
            className="inline-flex h-[34px] items-center gap-2 rounded-full border border-line bg-raised px-3.5 text-[13px] font-semibold hover:border-white/20">
            <span className="uppercase">{e.language ?? e.beats?.language ?? 'en'}</span><span className="text-muted">{e.title}</span>
          </a>
        ))}
        {Object.entries(voices).filter(([code]) => code !== own && !have.has(code)).map(([code, v]) => (
          <Button key={code} onClick={() => copy(code)}><Languages size={14} /> {v.name}</Button>
        ))}
      </div>
      {error && <p className="mt-2 text-xs text-bad">{error}</p>}
      <p className="mt-2 text-xs text-muted">Makes a copy with the same frames. Rewrite its texts in the new language (or ask Claude to), then approve: only the voice, subtitles and render run again.</p>
    </div>
  )
}

function ScriptEditor({ ep }: { ep: Episode }) {
  const { refresh } = useApp()
  const [b, setB] = useState<Beats>(ep.beats!)
  const [open, setOpen] = useState(ep.status === 'script' || ep.status === 'failed')
  const [warnings, setWarnings] = useState<string[]>([])
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)
  const dirty = JSON.stringify(b) !== JSON.stringify(ep.beats)
  const total = b.beats.reduce((s, x) => s + x.seconds, 0)

  const setBeat = (i: number, patch: Partial<Beat>) => setB({ ...b, beats: b.beats.map((x, k) => (k === i ? { ...x, ...patch } : x)) })

  const save = async () => {
    setSaving(true)
    setError('')
    try {
      const r = await api.saveBeats(ep.slug, b)
      setWarnings(r.warnings)
      refresh()
      return true
    } catch (e) {
      setError((e as Error).message)
      return false
    } finally {
      setSaving(false)
    }
  }

  const approve = async () => {
    if (dirty && !(await save())) return
    try {
      await api.approve(ep.slug)
      refresh()
    } catch (e) {
      setError((e as Error).message)
    }
  }
  // every field comes from the format: its own and its render mode's (format.yaml `fields`)
  const f = formatOf(useFormats(), b)
  const scriptFields = f?.fields('script') ?? []
  const beatFields = f?.fields('beat') ?? []
  const inline = beatFields.filter((x) => (x.kind ?? 'text') === 'text')
  const block = beatFields.filter((x) => !inline.includes(x))
  const scene = beatFields.find((x) => x.kind === 'svg')
  const addBeat = () => setB({ ...b, beats: [...b.beats, {
    ...Object.fromEntries(beatFields.filter((x) => x.required).map((x) => [x.key, ''])), seconds: 8, ...(b.voice ? { vo: '' } : {}),
  }] })
  const removeBeat = (i: number) => setB({ ...b, beats: b.beats.filter((_, k) => k !== i) })
  const otherMode = f && f.modeId !== Object.keys(f.format.render_modes)[0] ? ` · ${f.mode.title}` : ''

  return (
    <div className="rounded-[18px] border border-line bg-panel">
      <button onClick={() => setOpen(!open)} className="flex w-full items-center justify-between px-5 py-4">
        <div className="text-left">
          <div className="font-display text-xl">Script</div>
          <div className="tabular text-xs text-muted">{b.beats.length} beats · ~{total}s{b.voice ? ' · narrated' : ''}{otherMode}</div>
        </div>
        <ChevronDown size={18} className={cx('text-muted transition', open && 'rotate-180')} />
      </button>
      {open && (
        <div className="space-y-5 border-t border-line p-5">
          <Field label="Title"><input value={b.title ?? ''} onChange={(e) => setB({ ...b, title: e.target.value })} className={inputCls} /></Field>
          <div className="grid gap-4 md:grid-cols-2">
            {scriptFields.map((x) => (
              <div key={x.key} className={(x.kind ?? 'text') === 'text' ? '' : 'md:col-span-2'}>
                <Field label={x.label}><FieldInput spec={x} value={b[x.key]} onChange={(v) => setB({ ...b, [x.key]: v })} /></Field>
              </div>
            ))}
          </div>

          <MusicPicker value={b.music} onChange={(music) => setB({ ...b, music })} />

          <div className="space-y-3">
            {b.beats.map((beat, i) => (
              <div key={i} className="grid gap-3 rounded-xl border border-line bg-bg/40 p-3 md:grid-cols-[96px_minmax(0,1fr)]">
                <div className="relative">
                  {b.beats.length > 3 && (
                    <button onClick={() => removeBeat(i)} title="Remove beat" aria-label="Remove beat"
                      className="absolute right-1 top-1 z-10 rounded-lg bg-black/60 p-1 text-muted hover:text-bad"><Trash2 size={13} /></button>
                  )}
                  {scene && text(beat[scene.key]) ? (
                    <svg viewBox="0 0 1080 1920" className="aspect-[9/16] w-full rounded-xl bg-[#f3ead8]" dangerouslySetInnerHTML={{ __html: thumb(text(beat[scene.key]), i) }} />
                  ) : ep.frames.includes(`${pad(i + 1)}-916.png`) ? (
                    <img src={episodeFile(ep, `work/public/frames/${pad(i + 1)}-916.png`)} className="aspect-[9/16] w-full rounded-xl object-cover" alt="" />
                  ) : (
                    <div className="grid aspect-[9/16] place-items-center rounded-xl bg-raised font-display text-lg text-muted">{i + 1}</div>
                  )}
                </div>
                <div className="space-y-2">
                  <div className="flex flex-wrap gap-2">
                    {inline.map((x, k) => (
                      <FieldInput key={x.key} spec={x} value={beat[x.key]} onChange={(v) => setBeat(i, { [x.key]: v })}
                        className={cx('min-w-[120px] flex-1', k === 0 && 'font-semibold')} />
                    ))}
                    <div className="w-[72px] shrink-0">
                      <input type="number" min={2} max={15} value={beat.seconds} onChange={(e) => setBeat(i, { seconds: +e.target.value })} className={cx(inputCls, 'tabular')} title="Seconds" />
                    </div>
                  </div>
                  {b.voice && (
                    <textarea value={beat.vo ?? ''} onChange={(e) => setBeat(i, { vo: e.target.value })} rows={2} placeholder="Narrator line · [pause 0.6] for a beat of silence · + before a vowel to fix a stress"
                      className={cx(inputCls, 'resize-none')} />
                  )}
                  {block.map((x) => <FieldInput key={x.key} spec={x} value={beat[x.key]} onChange={(v) => setBeat(i, { [x.key]: v })} className="text-xs text-muted" />)}
                  {beat.fact_source && <div className="text-[11px] text-muted">Source: {beat.fact_source}</div>}
                </div>
              </div>
            ))}
            {b.beats.length < 12 && (
              <button onClick={addBeat} className="flex h-11 w-full items-center justify-center gap-2 rounded-xl border border-dashed border-line text-sm text-muted hover:border-muted hover:text-text">
                <Plus size={15} /> Add beat
              </button>
            )}
          </div>

          {warnings.length > 0 && (
            <ul className="space-y-1 rounded-xl border border-warn/30 bg-warn/5 p-3 text-xs text-warn">
              {warnings.map((w) => <li key={w}>{w}</li>)}
            </ul>
          )}
          {error && <p className="text-sm text-bad">{error}</p>}
          <div className="flex flex-wrap gap-2">
            {ep.status === 'script' && (
              <Button variant="primary" onClick={approve} disabled={saving}><Play size={15} /> Approve and generate</Button>
            )}
            <Button onClick={save} disabled={!dirty || saving}><Save size={15} /> Save</Button>
            {(ep.status === 'review' || ep.status === 'done') && (
              <Button variant="ghost" disabled={dirty} onClick={() => api.rerun(ep.slug)} title="Only changed beats are recomputed">
                <RefreshCw size={15} /> Rebuild with edits
              </Button>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

/** One field of the script as the format declares it: a line, a paragraph, or SVG markup. */
function FieldInput({ spec, value, onChange, className }: { spec: FieldSpec; value: unknown; onChange: (v: string) => void; className?: string }) {
  const kind = spec.kind ?? 'text'
  if (kind === 'text') {
    return <input value={text(value)} onChange={(e) => onChange(e.target.value)} placeholder={spec.placeholder} title={spec.label} className={cx(inputCls, className)} />
  }
  return (
    <textarea value={text(value)} onChange={(e) => onChange(e.target.value)} rows={kind === 'svg' ? 3 : 2} spellCheck={kind !== 'svg'}
      placeholder={spec.placeholder} title={spec.label}
      className={cx(inputCls, kind === 'svg' ? 'resize-y font-mono text-[11px] text-muted' : 'resize-none', className)} />
  )
}

// Library tracks are CC0; an empty choice lets the render stage match one by mood.
function MusicPicker({ value, onChange }: { value?: string; onChange: (v: string) => void }) {
  const [tracks, setTracks] = useState<Track[]>([])
  useEffect(() => {
    api.music().then(setTracks).catch(() => setTracks([]))
  }, [])
  const track = tracks.find((t) => t.id === value)
  return (
    <Field label="Music">
      <div className="flex flex-wrap items-center gap-3">
        <select value={track || value === 'none' ? value : ''} onChange={(e) => onChange(e.target.value)} className={cx(inputCls, 'max-w-xs')}>
          <option value="">Match by mood{value && !track && value !== 'none' ? ` (${value})` : ''}</option>
          <option value="none">No music</option>
          {tracks.map((t) => <option key={t.id} value={t.id}>{t.title} · {t.moods.slice(0, 2).join(', ')}</option>)}
        </select>
        {track && <audio key={track.id} src={`${ENGINE}${track.url}`} controls className="h-9" />}
        {track && (
          <a href={track.source} target="_blank" rel="noreferrer" className="flex items-center gap-1 text-[11px] text-muted hover:text-white">
            <Music size={12} /> {track.author} · {track.license}
          </a>
        )}
      </div>
    </Field>
  )
}

type QaCheck = { level: 'error' | 'warn' | 'info'; id: string; message: string; beat?: number }

// out/qa.json from the qa stage: what to fix before posting.
function QualityCheck({ ep }: { ep: Episode }) {
  const [qa, setQa] = useState<{ ok: boolean; checks: QaCheck[] } | null>(null)
  useEffect(() => {
    fetch(episodeFile(ep, 'out/qa.json', ep.video_mtime)).then((r) => (r.ok ? r.json() : null)).then(setQa).catch(() => setQa(null))
  }, [ep])
  if (!qa) return null
  const problems = qa.checks.filter((c) => c.level !== 'info')
  const icon = { error: <CircleX size={14} className="text-bad" />, warn: <TriangleAlert size={14} className="text-warn" />, info: <Info size={14} className="text-muted" /> }
  return (
    <div className="rounded-[18px] border border-line bg-panel p-5">
      <div className="mb-3 flex items-center gap-2">
        <span className="eyebrow">Quality check</span>
        {problems.length === 0 && <span className="flex items-center gap-1 text-xs text-ok"><CircleCheck size={13} /> ready to post</span>}
      </div>
      <ul className="space-y-1.5 text-sm">
        {[...problems, ...qa.checks.filter((c) => c.level === 'info')].map((c, k) => (
          <li key={k} className={cx('flex items-start gap-2', c.level === 'info' && 'text-muted')}>
            <span className="mt-0.5">{icon[c.level]}</span>
            <span>{c.beat ? <span className="tabular text-muted">Beat {c.beat} · </span> : null}{c.message}</span>
          </li>
        ))}
      </ul>
    </div>
  )
}
