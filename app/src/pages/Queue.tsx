import { ListTodo, Square, Trash2 } from '../icons'
import { Fragment, useEffect, useState } from 'react'
import { api, type Style } from '../api'
import { useApp } from '../App'
import { Button, Empty, JOB_KIND, Progress, STAGES, ago, cx } from '../ui'

const TONE: Record<string, string> = {
  queued: 'text-muted',
  running: 'text-accent',
  done: 'text-ok',
  failed: 'text-bad',
  cancelled: 'text-muted',
}
const LABEL: Record<string, string> = { queued: 'queued', running: 'running', done: 'done', failed: 'failed', cancelled: 'cancelled' }

export function Queue() {
  const { jobs, episodes } = useApp()
  const [open, setOpen] = useState<number | null>(null)
  const [styles, setStyles] = useState<Style[]>([])
  useEffect(() => { api.styles().then(setStyles) }, [])
  const title = (slug: string | null) => (slug ? episodes.find((e) => e.slug === slug)?.title ?? slug : '—')
  const style = (id: unknown) => styles.find((s) => s.id === id)?.title ?? String(id ?? '—')
  const finished = jobs.filter((j) => j.status !== 'running' && j.status !== 'queued').length

  return (
    <div className="mx-auto max-w-6xl px-8 py-8">
      <div className="mb-6 flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="mb-1 font-display text-[40px]">Queue</h1>
          <p className="text-sm text-muted">Heavy jobs (frames, render) run one at a time; style previews run right away.</p>
        </div>
        {finished > 0 && <Button variant="ghost" onClick={() => api.clearJobs()}><Trash2 size={15} /> Clear finished</Button>}
      </div>
      {!jobs.length ? (
        <Empty icon={<ListTodo />} title="No jobs" text="Generations and rebuilds show up here." />
      ) : (
        <div className="overflow-x-auto rounded-[18px] border border-line">
          <table className="w-full whitespace-nowrap text-sm">
            <thead className="eyebrow bg-panel text-left">
              <tr>
                <th className="px-4 py-2.5 font-medium">Job</th>
                <th className="px-4 py-2.5 font-medium">Episode</th>
                <th className="px-4 py-2.5 font-medium">Stage</th>
                <th className="w-48 px-4 py-2.5 font-medium">Progress</th>
                <th className="px-4 py-2.5 font-medium">Status</th>
                <th className="px-4 py-2.5 font-medium">When</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {jobs.map((j) => (
                <Fragment key={j.id}>
                  <tr onClick={() => setOpen(open === j.id ? null : j.id)} className="cursor-pointer border-t border-line hover:bg-panel/60">
                    <td className="px-4 py-2.5">{JOB_KIND[j.kind] ?? j.kind}</td>
                    <td className="max-w-64 truncate px-4 py-2.5">
                      {j.slug ? <a href={`#/episode/${encodeURIComponent(j.slug)}`} onClick={(e) => e.stopPropagation()} className="hover:text-accent">{title(j.slug)}</a> : <span className="text-muted">{style(j.params.style)}</span>}
                    </td>
                    <td className="px-4 py-2.5 text-muted">{j.stage ? STAGES[j.stage] ?? j.stage : '—'}</td>
                    <td className="max-w-48 px-4 py-2.5">
                      {j.status === 'failed' || j.status === 'cancelled'
                        ? <span className="block truncate text-xs text-muted" title={j.error ?? ''}>{j.error ?? '—'}</span>
                        : <div className="flex items-center gap-2"><Progress value={j.progress} className="flex-1" /><span className="tabular w-9 text-right text-xs text-muted">{Math.round(j.progress * 100)}%</span></div>}
                    </td>
                    <td className={cx('px-4 py-2.5', TONE[j.status])}>{LABEL[j.status]}</td>
                    <td className="px-4 py-2.5 text-muted">{ago(j.started ?? j.created)}</td>
                    <td className="px-2">
                      {(j.status === 'running' || j.status === 'queued') && (
                        <Button variant="ghost" className="h-7 px-2" onClick={(e) => { e.stopPropagation(); api.cancel(j.id) }} title="Stop"><Square size={13} /></Button>
                      )}
                    </td>
                  </tr>
                  {open === j.id && (
                    <tr className="border-t border-line bg-bg">
                      <td colSpan={7} className="px-4 py-3">
                        {j.error && <p className="mb-2 text-xs text-bad">{j.error}</p>}
                        <pre className="max-h-72 overflow-auto whitespace-pre-wrap font-mono text-xs text-muted">{j.log || 'empty log'}</pre>
                      </td>
                    </tr>
                  )}
                </Fragment>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
