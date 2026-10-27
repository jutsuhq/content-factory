import { NavExplore, NavQueue, NavSettings, NavVideos, NavVoice, Plus, WifiOff } from './icons'
import { EngineDown, Onboarding } from './pages/Setup'
import { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react'
import { api, subscribeJobs, type ComposeIn, type Episode, type Job, type Settings } from './api'
import { Composer } from './pages/Composer'
import { EpisodePage } from './pages/Episode'
import { Explore } from './pages/Explore'
import { Library } from './pages/Library'
import { Queue } from './pages/Queue'
import { SettingsPage } from './pages/Settings'
import { VoicePage } from './pages/Voice'
import { Button, cx } from './ui'

type Ctx = {
  episodes: Episode[]
  jobs: Job[]
  refresh: () => void
  go: (route: string) => void
  compose: (prefill?: Partial<ComposeIn>) => void
}
const AppCtx = createContext<Ctx>(null!)
export const useApp = () => useContext(AppCtx)

const useHash = () => {
  const [hash, setHash] = useState(() => window.location.hash.slice(1) || '/explore')
  useEffect(() => {
    const on = () => setHash(window.location.hash.slice(1) || '/explore')
    window.addEventListener('hashchange', on)
    return () => window.removeEventListener('hashchange', on)
  }, [])
  return hash
}

const NAV = [
  { to: '/explore', label: 'Explore', icon: NavExplore },
  { to: '/videos', label: 'My videos', icon: NavVideos },
  { to: '/queue', label: 'Queue', icon: NavQueue },
  { to: '/voice', label: 'Voice', icon: NavVoice },
  { to: '/settings', label: 'Settings', icon: NavSettings },
]

export default function App() {
  const route = useHash()
  const [episodes, setEpisodes] = useState<Episode[]>([])
  const [jobs, setJobs] = useState<Job[]>([])
  const [online, setOnline] = useState<boolean | null>(null)
  const [composer, setComposer] = useState<Partial<ComposeIn> | null>(null)
  const [settings, setSettings] = useState<Settings | null>(null)
  const timer = useRef<number | undefined>(undefined)

  const refresh = useCallback(() => {
    api.episodes().then((e) => { setEpisodes(e); setOnline(true) }).catch(() => setOnline(false))
  }, [])

  // The engine may still be starting when the window opens: retry until it answers.
  useEffect(() => {
    refresh()
    const id = window.setInterval(() => online !== true && refresh(), 2000)
    return () => window.clearInterval(id)
  }, [refresh, online])

  useEffect(() => { if (online) api.settings().then(setSettings) }, [online])

  useEffect(() => {
    if (!online) return
    return subscribeJobs((j) => {
      setJobs(j)
      window.clearTimeout(timer.current)
      timer.current = window.setTimeout(refresh, 300) // a job moved: statuses and frames may have changed
    })
  }, [online, refresh])

  const go = (to: string) => { window.location.hash = to }
  const running = jobs.filter((j) => j.status === 'running' || j.status === 'queued').length

  let page
  if (route.startsWith('/episode/')) page = <EpisodePage slug={decodeURIComponent(route.slice(9))} />
  else if (route === '/videos') page = <Library />
  else if (route === '/queue') page = <Queue />
  else if (route === '/voice') page = <VoicePage />
  else if (route === '/settings') page = <SettingsPage />
  else page = <Explore />

  return (
    <AppCtx.Provider value={{ episodes, jobs, refresh, go, compose: (p) => setComposer(p ?? {}) }}>
      <div className="flex h-full">
        <aside className="flex w-60 shrink-0 flex-col border-r border-line bg-white/[0.025] px-3 py-5">
          <a href="#/explore" className="mb-7 flex items-center gap-2.5 px-1.5">
            <img src="/logo.png" className="size-8 rounded-[8px]" alt="" />
            <div className="leading-tight">
              <div className="font-display text-[17px] tracking-[0.02em]">Content Factory</div>
              <div className="eyebrow !text-[10px] !tracking-[0.12em]">local · open source</div>
            </div>
          </a>
          <Button variant="primary" className="mb-5 w-full" onClick={() => setComposer({})}>
            <Plus size={16} /> New video
          </Button>
          <nav className="space-y-0.5">
            {NAV.map(({ to, label, icon: Icon }) => {
              const active = route === to || (to === '/videos' && route.startsWith('/episode/'))
              return (
                <a
                  key={to}
                  href={`#${to}`}
                  className={cx(
                    'flex h-9 items-center gap-2.5 rounded-[9px] px-2.5 text-[13px] font-medium transition',
                    active ? 'bg-white/10 text-text' : 'text-muted hover:bg-white/5 hover:text-text',
                  )}
                >
                  <Icon size={18} className={active ? 'nav-active' : undefined} />
                  <span className="flex-1">{label}</span>
                  {to === '/queue' && running > 0 && (
                    <span className="tabular rounded-full bg-accent/15 px-1.5 text-xs text-accent">{running}</span>
                  )}
                </a>
              )
            })}
          </nav>
          <div className="eyebrow mt-auto px-2 !normal-case !tracking-normal">
            {online === false ? (
              <span className="flex items-center gap-1.5 text-bad"><WifiOff size={13} /> engine offline</span>
            ) : (
              <span className="flex items-center gap-1.5"><span className="size-1.5 rounded-full bg-ok shadow-[0_0_8px] shadow-ok" /> engine running</span>
            )}
          </div>
        </aside>
        <main className="min-w-0 flex-1 overflow-y-auto">
          {online === false ? (
            <EngineDown />
          ) : settings && !settings.onboarded ? (
            <Onboarding settings={settings} onDone={() => api.settings().then(setSettings)} />
          ) : (
            page
          )}
        </main>
      </div>
      {composer && <Composer prefill={composer} onClose={() => setComposer(null)} />}
    </AppCtx.Provider>
  )
}
