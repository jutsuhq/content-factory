import { ImagePlus, Loader2, Mic, MicOff, PenNib, Sparkles } from '../icons'
import { useEffect, useState } from 'react'
import { api, type ComposeIn, type Format, type ImageProvider, type Settings, type Style, type Variant, type Voice } from '../api'
import { useApp } from '../App'
import { Button, Field, Modal, cx, inputCls } from '../ui'
import { Avatar, CastPick } from './Project'

// icons a format's render mode may name (format.yaml `render_modes.<mode>.icon`)
const ICONS: Record<string, typeof ImagePlus> = { image: ImagePlus, pen: PenNib }

/** "New video": channel and variant, format, topic, style, language, length, narration, who is in it. It opens the
 * episode with an empty script to fill in; Claude can write one instead over MCP. */
export function Composer({ prefill, onClose }: { prefill: Partial<ComposeIn>; onClose: () => void }) {
  const { go, refresh, episodes, projects, project: picked } = useApp()
  // the channel the sidebar has picked, unless the caller names one (or none, with null)
  const [projectId, setProjectId] = useState(prefill.project !== undefined ? prefill.project ?? '' : picked?.id ?? '')
  const project = projects.find((p) => p.id === projectId) ?? null
  const [variant, setVariant] = useState(prefill.variant ?? '')
  const [cast, setCast] = useState<string[]>(prefill.cast ?? [])
  const [formats, setFormats] = useState<Format[]>([])
  const [format, setFormat] = useState(prefill.format ?? '')
  const [styles, setStyles] = useState<Style[]>([])
  const [topic, setTopic] = useState(prefill.topic ?? '')
  const [style, setStyle] = useState(prefill.style ?? '')
  const [stylePrompt, setStylePrompt] = useState(prefill.style_prompt ?? '')
  const [duration, setDuration] = useState(prefill.duration ?? 60)
  const [voice, setVoice] = useState(prefill.voice ?? true)
  const [language, setLanguage] = useState(prefill.language ?? '')
  const [mode, setMode] = useState(prefill.render_mode ?? '')
  const [look, setLook] = useState('')
  const [settings, setSettings] = useState<Settings | null>(null)
  const [voices, setVoices] = useState<Record<string, Voice>>({})
  const [images, setImages] = useState<ImageProvider[]>([])
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const series = prefill.series ? episodes.find((e) => e.series === prefill.series) : null

  useEffect(() => {
    api.formats().then((fs) => {
      setFormats(fs)
      setFormat((v) => v || fs[0]?.id || '')
    })
    api.voices().then(setVoices)
    api.images().then(setImages)
    // the owner's defaults from Settings fill whatever the prefill (a series, a trend) did not set
    api.settings().then((s) => {
      setSettings(s)
      const d = s.defaults
      setLanguage((v) => v || d.language)
      if (prefill.duration === undefined) setDuration(d.duration)
      if (prefill.voice === undefined) setVoice(d.voice)
      // a channel's variant fills in over the defaults; a series continued keeps its own settings
      const v = project?.variants.find((x) => x.id === prefill.variant) ?? project?.variants[0]
      if (v && !prefill.series) apply(v)
    })
  }, []) // eslint-disable-line react-hooks/exhaustive-deps -- once per open
  const apply = (v: Variant) => {
    setVariant(v.id)
    if (v.format) setFormat(v.format)
    if (v.render_mode) setMode(v.render_mode)
    if (v.style_prompt) { setStyle('custom'); setStylePrompt(v.style_prompt) } else if (v.style) { setStyle(v.style); setLook(v.style) }
    if (v.language) setLanguage(v.language)
    if (v.duration) setDuration(v.duration)
    if (v.voice !== undefined) setVoice(v.voice)
    setCast(v.cast ?? [])
  }
  const pickProject = (id: string) => {
    setProjectId(id)
    const p = projects.find((x) => x.id === id)
    if (p) apply(p.variants[0])
    else { setVariant(''); setCast([]) }
  }
  const fmt = formats.find((f) => f.id === format)
  const m = fmt?.render_modes[mode]
  const looks = m && typeof m.style === 'object' ? m.style.looks : null // a fixed list instead of the style presets
  // styles belong to a format: switching it loads its own and keeps the chosen style only if that format has it
  useEffect(() => {
    if (!format || !settings) return
    api.styles(format).then((list) => {
      setStyles(list)
      const has = (id: string) => id === 'custom' || list.some((s) => s.id === id)
      setStyle((v) => (has(v) ? v : has(settings.defaults.style) ? settings.defaults.style : list[0]?.id ?? ''))
    })
  }, [format, settings])
  useEffect(() => {
    if (!fmt) return
    setMode((v) => (fmt.render_modes[v] ? v : Object.keys(fmt.render_modes)[0]))
    const { min, max } = fmt.duration_seconds
    setDuration((v) => Math.min(max, Math.max(min, v)))
  }, [fmt])
  useEffect(() => {
    if (looks) setLook((v) => (looks.some((l) => l.id === v) ? v : looks[0]?.id ?? ''))
  }, [looks])
  const noVoice = voice && language !== '' && Object.keys(voices).length > 0 && !voices[language]

  const beats = Math.max(4, Math.min(12, Math.round(duration / 6)))
  const frames = m?.stages.includes('frames') ? beats : 0 // the frames stage makes one image per beat
  const noProvider = frames > 0 && !images.some((p) => p.enabled > 0)

  const submit = async () => {
    setBusy(true)
    setError('')
    try {
      const custom = style === 'custom'
      const res = await api.compose({
        topic: topic.trim(),
        duration,
        format,
        style: looks ? look : custom ? styles[0]?.id ?? '' : style,
        style_prompt: !looks && custom ? stylePrompt.trim() : null,
        render_mode: mode,
        voice,
        language,
        series: prefill.series ?? null,
        project: project?.id ?? null,
        variant: project ? variant || null : null,
        cast: project ? cast : null,
      })
      refresh()
      onClose()
      go(`/episode/${res.slug}`)
    } catch (e) {
      setError(String((e as Error).message))
    } finally {
      setBusy(false)
    }
  }

  return (
    <Modal open onClose={onClose} title={series ? `Next episode: ${series.title}` : 'New video'} wide>
      <div className="grid grid-cols-[minmax(0,1fr)] gap-6 lg:grid-cols-[minmax(0,1fr)_300px]">
        <div className="space-y-5">
          {projects.length > 0 && !series && (
            <div className="flex flex-wrap items-center gap-2">
              {project && <Avatar p={project} size={28} />}
              <select value={projectId} onChange={(e) => pickProject(e.target.value)} aria-label="Channel"
                className="h-8 rounded-full border border-line bg-raised px-3 text-sm outline-none">
                <option value="">No channel</option>
                {projects.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
              </select>
              {project && project.variants.length > 1 && project.variants.map((v) => (
                <button key={v.id} type="button" onClick={() => apply(v)}
                  className={cx('h-8 rounded-full border px-3 text-sm transition', variant === v.id ? 'border-accent bg-accent/10 text-text' : 'border-line text-muted hover:text-text')}>
                  {v.name}
                </button>
              ))}
            </div>
          )}
          <Field label="Topic or title" hint={<span className="tabular">{topic.length}/2000</span>}>
            <textarea
              autoFocus
              value={topic}
              maxLength={2000}
              onChange={(e) => setTopic(e.target.value)}
              rows={4}
              placeholder="What if the Moon disappeared? Tides, nights and animals after a day, a year, a thousand years."
              className={cx(inputCls, 'resize-none text-base')}
            />
          </Field>

          {project && project.cast.length > 0 && (
            <div className="space-y-1.5">
              <div className="text-xs font-medium text-muted">Who is in it: their looks and images go with every frame</div>
              <CastPick cast={project.cast} value={cast} onChange={setCast} />
            </div>
          )}

          {formats.length > 1 ? (
            <Field label="Format">
              <div className="grid grid-cols-2 gap-2">
                {formats.map((f) => (
                  <button key={f.id} type="button" onClick={() => setFormat(f.id)} title={f.description}
                    className={cx('rounded-xl border px-3 py-2.5 text-left text-xs transition', format === f.id ? 'border-accent bg-accent/10' : 'border-line hover:border-muted')}>
                    <span className="block font-medium text-text">{f.title}</span>
                    <span className="line-clamp-2 text-muted">{f.description}</span>
                  </button>
                ))}
              </div>
            </Field>
          ) : fmt && <p className="text-xs text-muted"><span className="font-medium text-text">{fmt.title}</span> · {fmt.description}</p>}

          {fmt && Object.keys(fmt.render_modes).length > 1 && (
          <Field label="Picture">
            <div className="grid grid-cols-2 gap-2">
              {Object.entries(fmt.render_modes).map(([id, r]) => {
                const Icon = ICONS[r.icon ?? ''] ?? ImagePlus
                return (
                  <button key={id} type="button" onClick={() => setMode(id)}
                    className={cx('flex items-start gap-2.5 rounded-xl border px-3 py-2.5 text-left text-xs transition', mode === id ? 'border-accent bg-accent/10' : 'border-line hover:border-muted')}>
                    <Icon size={16} className="mt-0.5 shrink-0 text-muted" />
                    <span><span className="block font-medium text-text">{r.title}</span><span className="text-muted">{r.hint}</span></span>
                  </button>
                )
              })}
            </div>
          </Field>
          )}

          {looks ? (
          <Field label="Look">
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
              {looks.map(({ id, hint }) => (
                <button key={id} type="button" onClick={() => setLook(id)}
                  className={cx('rounded-xl border px-2.5 py-2 text-left text-xs transition', look === id ? 'border-accent bg-accent/10' : 'border-line hover:border-muted')}>
                  <div className="font-medium capitalize text-text">{id}</div>
                  <div className="mt-0.5 truncate text-muted">{hint}</div>
                </button>
              ))}
            </div>
          </Field>
          ) : (
          <Field label="Style">
            <div className="grid grid-cols-3 gap-2 sm:grid-cols-4">
              {styles.map((s) => (
                <button
                  key={s.id}
                  type="button"
                  onClick={() => setStyle(s.id)}
                  className={cx('rounded-xl border px-2.5 py-2 text-left text-xs transition', style === s.id ? 'border-accent bg-accent/10' : 'border-line hover:border-muted')}
                >
                  <div className="font-medium text-text">{s.title}</div>
                  <div className="mt-0.5 truncate text-muted">{s.tags[0]}</div>
                </button>
              ))}
              <button
                type="button"
                onClick={() => setStyle('custom')}
                className={cx('rounded-xl border px-2.5 py-2 text-left text-xs transition', style === 'custom' ? 'border-accent bg-accent/10' : 'border-line hover:border-muted')}
              >
                <div className="font-medium text-text">Custom</div>
                <div className="mt-0.5 text-muted">describe in words</div>
              </button>
            </div>
          </Field>
          )}
          {!looks && style === 'custom' && (
            <Field label="Style description (for the image model)">
              <textarea value={stylePrompt} onChange={(e) => setStylePrompt(e.target.value)} rows={2} className={cx(inputCls, 'resize-none')}
                placeholder="Hazy grey city streets, big countdown timers, flying debris" />
            </Field>
          )}
        </div>

        <div className="space-y-5 rounded-xl border border-line bg-bg/50 p-4">
          <Field label="Length" hint={<span className="tabular text-text">{duration}s</span>}>
            <input type="range" min={fmt?.duration_seconds.min ?? 15} max={fmt?.duration_seconds.max ?? 300} step={5} value={duration} onChange={(e) => setDuration(+e.target.value)} className="w-full accent-[var(--color-accent)]" />
          </Field>
          <Field label="Language">
            <select value={language} onChange={(e) => setLanguage(e.target.value)} className={inputCls}>
              {Object.entries(settings?.languages ?? {}).map(([code, name]) => <option key={code} value={code}>{name}</option>)}
            </select>
            {noVoice && <p className="text-xs text-warn">No voice for this language yet: pick on-screen text only.</p>}
          </Field>
          <Field label="Narration">
            <button type="button" onClick={() => setVoice(!voice)}
              className={cx('flex h-9 w-full items-center gap-2 rounded-xl border px-3 text-sm', voice ? 'border-accent bg-accent/10' : 'border-line text-muted')}>
              {voice ? <Mic size={15} /> : <MicOff size={15} />}
              {voice ? 'Voice + subtitles' : 'On-screen text only'}
            </button>
          </Field>
          <div className="space-y-1 rounded-xl bg-raised/60 p-3 text-xs text-muted">
            <div className="flex justify-between"><span>Beats per episode</span><span className="tabular text-text">~{beats}</span></div>
            <div className="flex justify-between"><span>Frames to generate</span><span className="tabular text-text">{frames}</span></div>
            <div className="flex justify-between"><span>Time</span><span className="tabular text-text">~{Math.ceil(beats / 4) * 3 + 4} min</span></div>
            {noProvider && <div className="text-warn">Turn on an image provider in Settings to make the frames.</div>}
          </div>
          {error && <p className="text-sm text-bad">{error}</p>}
          <Button variant="primary" className="w-full" disabled={busy || !topic.trim() || !language || !format || noVoice || (!looks && style === 'custom' && !stylePrompt.trim())} onClick={submit}>
            {busy ? <Loader2 size={17} className="animate-spin" /> : <Sparkles size={17} />}
            Start the script
          </Button>
          <p className="text-xs text-muted">
            Opens an empty script with ~{beats} beats to fill in, or ask Claude to write it for you (Settings › Claude).
            {frames ? ' Frames start only after you approve it.' : ` ${m?.hint ?? ''}.`}
          </p>
        </div>
      </div>
    </Modal>
  )
}
