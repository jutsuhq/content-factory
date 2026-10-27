import { Clapperboard, Film, Plus } from '../icons'
import { useState } from 'react'
import { episodeFile, type Episode, type Project, type Status } from '../api'
import { useApp } from '../App'
import { Button, Empty, Progress, STAGES, StatusBadge, activeJob, ago, cx } from '../ui'

const FILTERS: { id: string; label: string; match: (s: Status) => boolean }[] = [
  { id: 'all', label: 'All', match: () => true },
  { id: 'todo', label: 'Needs me', match: (s) => s === 'script' || s === 'review' },
  { id: 'work', label: 'In progress', match: (s) => s === 'draft' || s === 'approved' || s === 'generating' },
  { id: 'done', label: 'Done', match: (s) => s === 'done' },
  { id: 'failed', label: 'Failed', match: (s) => s === 'failed' },
]

const GRID = 'grid grid-cols-2 gap-4 md:grid-cols-3 xl:grid-cols-5'

const heading = (group: Episode[]) => {
  const originals = group.filter((e) => !e.translation_of).length
  return originals > 1 ? `Series · ${originals} episodes` : `One video · ${group.length} languages`
}

/** Every video, or one channel's when `project` is given (inside its page, so without a heading of its own). */
export function Library({ project }: { project?: Project }) {
  const { episodes: all, compose, projects } = useApp()
  const episodes = project ? all.filter((e) => e.project === project.id) : all
  const newVideo = () => compose(project ? { project: project.id } : undefined)
  const [filter, setFilter] = useState('all')
  const f = FILTERS.find((x) => x.id === filter)!
  const shown = episodes.filter((e) => f.match(e.status))
  const channel = (e: Episode) => (project ? undefined : projects.find((p) => p.id === e.project))

  // Group episodes of one series under its first episode's title.
  const series = new Map<string, Episode[]>()
  for (const e of shown) series.set(e.series ?? e.slug, [...(series.get(e.series ?? e.slug) ?? []), e])
  const groups = [...series.values()].filter((g) => g.length > 1)
  const singles = [...series.values()].filter((g) => g.length === 1).flat()

  return (
    <div className={project ? '' : 'mx-auto max-w-7xl px-8 py-8'}>
      {!project && (
        <div className="mb-6 flex items-center justify-between">
          <h1 className="font-display text-[40px]">All videos</h1>
          <Button variant="primary" onClick={newVideo}><Plus size={16} /> New video</Button>
        </div>
      )}
      <div className="mb-6 flex gap-1.5">
        {FILTERS.map((x) => {
          const n = episodes.filter((e) => x.match(e.status)).length
          return (
            <button key={x.id} onClick={() => setFilter(x.id)}
              className={cx('h-8 rounded-full border px-3 text-sm', filter === x.id ? 'border-accent bg-accent/10 text-text' : 'border-line text-muted hover:text-text')}>
              {x.label} <span className="tabular ml-1 text-muted">{n}</span>
            </button>
          )
        })}
      </div>
      {!shown.length ? (
        <Empty icon={<Clapperboard />} title="Nothing here yet" text="Type a topic and a script will be ready for review in a couple of minutes." action={<Button variant="primary" onClick={newVideo}>New video</Button>} />
      ) : (
        <div className="space-y-10">
          {singles.length > 0 && <div className={GRID}>{singles.map((e) => <Card key={e.slug} e={e} channel={channel(e)} />)}</div>}
          {groups.map((group) => (
            <section key={group[0].series ?? group[0].slug}>
              <h2 className="eyebrow mb-3">{heading(group)}</h2>
              <div className={GRID}>
                {[...group].sort((a, b) => (a.episode_index ?? 1) - (b.episode_index ?? 1)).map((e) => <Card key={e.slug} e={e} channel={channel(e)} />)}
              </div>
            </section>
          ))}
        </div>
      )}
    </div>
  )
}

function Card({ e, channel }: { e: Episode; channel?: Project }) {
  const { jobs } = useApp()
  const job = activeJob(jobs, e.slug)
  return (
    <a href={`#/episode/${encodeURIComponent(e.slug)}`} className="group overflow-hidden rounded-[18px] border border-line bg-panel transition hover:-translate-y-0.5 hover:border-muted/60">
      <div className="relative aspect-[9/16] bg-raised">
        {e.thumb ? (
          <img src={episodeFile(e, e.thumb)} className="size-full object-cover" alt="" loading="lazy" />
        ) : (
          <div className="grid size-full place-items-center text-muted"><Film /></div>
        )}
        <div className="absolute left-2 top-2"><StatusBadge status={e.status} /></div>
        {e.translation_of && (
          <div className="absolute bottom-2 right-2 rounded-full bg-black/60 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.06em]">{e.language}</div>
        )}
        {!e.translation_of && ((e.episode_index ?? 1) > 1 || e.series !== e.slug) ? (
          <div className="absolute right-2 top-2 rounded-full bg-black/60 px-2 py-0.5 text-xs">ep. {e.episode_index ?? 1}</div>
        ) : null}
        {job && (
          <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/90 p-3">
            <div className="mb-1.5 flex justify-between text-xs">
              <span>{job.kind === 'script' ? 'Script' : STAGES[job.stage ?? ''] ?? 'Queued'}</span>
              <span className="tabular">{Math.round(job.progress * 100)}%</span>
            </div>
            <Progress value={job.kind === 'script' ? 0.5 : job.progress} />
          </div>
        )}
      </div>
      <div className="px-3 py-2.5">
        <div className="line-clamp-2 text-sm font-medium leading-snug">{e.title}</div>
        <div className="mt-1 flex items-center gap-1.5 text-xs text-muted">
          {channel && <><span className="size-2 shrink-0 rounded-full" style={{ background: channel.color }} /><span className="truncate">{channel.name}</span>·</>}
          <span className="shrink-0">{ago(e.updated ?? e.created)}</span>
        </div>
      </div>
    </a>
  )
}
