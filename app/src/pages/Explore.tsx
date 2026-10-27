import { ImagePlus, Loader2 } from '../icons'
import { useEffect, useState } from 'react'
import { api, file, type Style } from '../api'
import { useApp } from '../App'
import { Button } from '../ui'

// Gradient stand-ins until a style has a generated preview.
const GRADIENTS = [
  'from-orange-500/40 via-rose-500/20 to-indigo-900/40',
  'from-sky-400/40 via-teal-500/20 to-slate-900/40',
  'from-fuchsia-500/40 via-violet-600/20 to-black/40',
  'from-stone-300/30 via-zinc-500/20 to-zinc-900/40',
  'from-lime-300/30 via-emerald-500/20 to-cyan-900/40',
  'from-indigo-400/40 via-purple-700/20 to-black/40',
]

export function Explore() {
  const { compose, jobs } = useApp()
  const [styles, setStyles] = useState<Style[]>([])

  const previewJobs = jobs.filter((j) => j.kind === 'style_preview' && (j.status === 'running' || j.status === 'queued'))
  const doneCount = jobs.filter((j) => j.kind === 'style_preview' && j.status === 'done').length
  const missing = styles.filter((s) => !s.preview && !previewJobs.some((j) => j.params.style === s.id))

  useEffect(() => { api.styles().then(setStyles) }, [doneCount])

  return (
    <div className="mx-auto max-w-7xl px-8 py-8">
      <h1 className="mb-6 font-display text-[40px]">Explore</h1>

      <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="mb-1 font-display text-[28px]">Styles</h2>
          <p className="text-sm text-muted">Built-in presets. Each preview is one image from your image provider.</p>
        </div>
        {missing.length > 0 && (
          <Button onClick={() => missing.forEach((s) => api.stylePreview(s.id))} disabled={previewJobs.length > 0}>
            {previewJobs.length > 0 ? <Loader2 size={15} className="animate-spin" /> : <ImagePlus size={15} />}
            {previewJobs.length > 0 ? `Making ${previewJobs.length} preview${previewJobs.length > 1 ? 's' : ''}` : `Make ${missing.length} missing preview${missing.length > 1 ? 's' : ''}`}
          </Button>
        )}
      </div>
      <div className="mb-12 grid grid-cols-2 gap-4 md:grid-cols-3 xl:grid-cols-6">
        {styles.map((s, i) => {
          const busy = previewJobs.some((j) => j.params.style === s.id)
          return (
            <div key={s.id} className="group overflow-hidden rounded-[18px] border border-line bg-panel transition hover:-translate-y-0.5 hover:border-muted/60">
              <button className="relative block aspect-[9/16] w-full" onClick={() => compose({ style: s.id })}>
                {s.preview ? (
                  <img src={file(s.preview, doneCount + 1)} className="size-full object-cover" alt="" />
                ) : (
                  <div className={`size-full bg-gradient-to-br ${GRADIENTS[i % GRADIENTS.length]}`} />
                )}
                <div className="absolute inset-0 flex items-end bg-gradient-to-t from-black/80 via-transparent p-3 text-left">
                  <div>
                    <div className="font-display text-lg">{s.title}</div>
                    <div className="mt-0.5 line-clamp-2 text-[11px] text-white/70">{s.tags.join(' · ')}</div>
                  </div>
                </div>
              </button>
              <div className="flex items-center justify-between px-2 py-1.5">
                <Button variant="ghost" className="h-7 px-2 text-xs" onClick={() => compose({ style: s.id })}>Create</Button>
                <Button variant="ghost" className="h-7 px-2 text-xs" disabled={busy} onClick={() => api.stylePreview(s.id)} title="Generate preview">
                  {busy ? <Loader2 size={13} className="animate-spin" /> : <ImagePlus size={13} />}
                </Button>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
