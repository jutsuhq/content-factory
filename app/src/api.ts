// Client for the local engine (`factory serve`, 127.0.0.1:8790).
export const ENGINE = 'http://127.0.0.1:8790'

export type Status = 'draft' | 'script' | 'approved' | 'generating' | 'review' | 'done' | 'failed'

// A script is the format's fields (format.yaml `fields`, and the render mode's) plus what every format has.
export type Beat = {
  seconds: number
  vo?: string // spoken line, when the script has voice
  fact_source?: string
  [field: string]: unknown
}

export type Beats = {
  format?: string // folder under formats/; scripts without one use the default format
  render_mode?: string // one of the format's render_modes; none means its first
  title?: string
  language?: string
  style: string
  style_prompt?: string
  voice: boolean
  beats: Beat[]
  music?: string
  [field: string]: unknown
}

export type Episode = {
  slug: string
  status: Status
  title: string
  topic?: string
  series?: string
  episode_index?: number
  duration?: number
  created?: number
  updated?: number
  error?: string | null
  caption?: string
  exported?: string | null // where Accept copied the video
  sent?: number
  language?: string
  translation_of?: string
  beats: Beats | null
  frames: string[]
  video: string | null
  video_mtime: number | null
  thumb: string | null
}

export type Voice = { name: string; engine: string; model: string; speaker: string | number }

export type Track = { id: string; title: string; author: string; source: string; license: string; moods: string[]; url: string; default?: boolean }
export type Style = { id: string; title: string; tags: string[]; prompt: string; preview: string | null }
/** A field the script editor shows; required ones must be filled before generating. */
export type FieldSpec = {
  key: string
  label: string
  kind?: 'text' | 'textarea' | 'svg' // text by default
  placeholder?: string
  required?: boolean
  english?: boolean // an image prompt
  translate?: boolean
}
export type FieldSet = { script?: FieldSpec[]; beat?: FieldSpec[] }
export type RenderMode = {
  title: string
  hint: string
  icon?: string
  stages: string[] // the pipeline stages this mode runs, in order
  style: 'presets' | { looks: { id: string; hint: string }[] } // a style preset of the format, or one of fixed looks
  fields?: FieldSet
}
export type Format = {
  id: string
  title: string
  description: string
  template: string
  render_modes: Record<string, RenderMode> // the first is the default
  fields?: FieldSet // shared by every render mode
  duration_seconds: { min: number; default: number; max: number }
  caption?: string // post caption, {field} filled from the script
}

/** The format a script uses (the default one, listed first, when it names none), its render mode and fields. */
export function formatOf(formats: Format[], b: { format?: string; render_mode?: string } | null) {
  const format = formats.find((f) => f.id === b?.format) ?? formats[0]
  if (!format) return null
  const modeId = b?.render_mode && format.render_modes[b.render_mode] ? b.render_mode : Object.keys(format.render_modes)[0]
  const mode = format.render_modes[modeId]
  const fields = (level: 'script' | 'beat') => [...(format.fields?.[level] ?? []), ...(mode.fields?.[level] ?? [])]
  return { format, modeId, mode, fields }
}

export type Job = {
  id: number
  kind: string
  slug: string | null
  params: Record<string, unknown>
  status: 'queued' | 'running' | 'done' | 'failed' | 'cancelled'
  stage: string | null
  progress: number
  log: string
  error: string | null
  created: number
  started: number | null
  finished: number | null
}

export type ComposeIn = {
  topic: string
  duration?: number
  style?: string
  style_prompt?: string | null
  voice?: boolean
  language?: string
  series?: string | null
  format?: string
  render_mode?: string
}

export type Defaults = { language: string; format: string; style: string; duration: number; voice: boolean }
export type Settings = {
  defaults: Defaults
  languages: Record<string, string>
  mcp: string
  music: number
  onboarded: boolean
}
export type Component = {
  id: string
  title: string
  detail: string
  ok: boolean
  install?: boolean // the engine fetches it itself
  command?: string // otherwise the user runs this once
  needs?: string
  optional?: boolean // only for some languages; not part of "install all"
}
export type ImageProvider = {
  id: string
  title: string
  key: string | null // env name of its API key; null for a local worker
  signup: string | null
  price: number | null // approx USD per image
  workers: number // parallel requests when enabled
  edits: boolean
  note: string
  key_set: boolean
  enabled: number // workers in the profile, 0 = off
  private?: boolean // a local worker, not part of the public build
}
export type Usage = { videos: number; frames: number; cache: number; other: number; trash: number; free: number }
export type Storage = {
  export_dir: string
  export_shown: string // with ~ for the home folder
  copy_on_accept: boolean
  clean_after_accept: boolean
  episodes_dir: string
  usage: Usage
}
export type SettingsIn = { defaults?: Partial<Defaults>; onboarded?: boolean }

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  const r = await fetch(ENGINE + path, {
    ...init,
    // X-Factory marks requests from the app; the engine refuses writes without it (see factory/api/app.py).
    headers: {
      'X-Factory': '1',
      ...(init?.body && !(init.body instanceof FormData) ? { 'Content-Type': 'application/json' } : {}),
    },
  })
  if (!r.ok) {
    const body = await r.json().catch(() => ({}))
    throw new Error(typeof body.detail === 'string' ? body.detail : `${r.status} ${r.statusText}`)
  }
  return r.json()
}

const post = <T,>(path: string, body?: unknown) => call<T>(path, { method: 'POST', body: body === undefined ? undefined : JSON.stringify(body) })
const put = <T,>(path: string, body: unknown) => call<T>(path, { method: 'PUT', body: JSON.stringify(body) })

let formatsOnce: Promise<Format[]> | null = null

export const api = {
  health: () => call<{ ok: boolean; root: string; version: string }>('/api/health'),
  episodes: () => call<Episode[]>('/api/episodes'),
  episode: (slug: string) => call<Episode>(`/api/episodes/${slug}`),
  /** Every format, the default one first. Formats are files shipped with the engine, so one fetch serves the session. */
  formats: () => (formatsOnce ??= call<Format[]>('/api/formats').catch((e) => { formatsOnce = null; throw e })),
  styles: (format?: string) => call<Style[]>(`/api/styles${format ? `?format=${encodeURIComponent(format)}` : ''}`),
  music: () => call<Track[]>('/api/music'),
  stylePreview: (id: string, format?: string) => post<{ job: number }>(`/api/styles/${id}/preview${format ? `?format=${encodeURIComponent(format)}` : ''}`),
  compose: (body: ComposeIn) => post<{ slug: string; warnings: string[] }>('/api/compose', body),
  saveBeats: (slug: string, beats: Beats) => put<{ warnings: string[] }>(`/api/episodes/${slug}/beats`, beats),
  approve: (slug: string) => post<{ job: number }>(`/api/episodes/${slug}/approve`),
  rerun: (slug: string, stages?: string[]) => post<{ job: number }>(`/api/episodes/${slug}/rerun`, stages ?? null),
  regenerateBeat: (slug: string, n: number) => post<{ job: number }>(`/api/episodes/${slug}/beats/${n}/regenerate`),
  accept: (slug: string, caption: string) => post<{ video: string; exported: string | null }>(`/api/episodes/${slug}/accept`, { caption }),
  /** Show the finished video in Finder or Explorer, open it in the player, or copy the file itself. */
  video: (slug: string, action: 'reveal' | 'open' | 'copy') => post<{ ok: boolean }>(`/api/episodes/${slug}/video/${action}`),
  translate: (slug: string, language: string) => post<{ slug: string }>(`/api/episodes/${slug}/translate`, { language }),
  voices: () => call<Record<string, Voice>>('/api/voices'),
  remove: (slug: string) => call<{ ok: boolean }>(`/api/episodes/${slug}`, { method: 'DELETE' }),
  jobs: () => call<Job[]>('/api/jobs'),
  cancel: (id: number) => post<{ ok: boolean }>(`/api/jobs/${id}/cancel`),
  clearJobs: () => call<{ removed: number }>('/api/jobs', { method: 'DELETE' }),
  say: (text: string, language: string) => post<{ spoken: string; audio: string }>('/api/voice/say', { text, language }),
  profile: () => call<Record<string, unknown>>('/api/profile'),
  doctor: () => post<Record<string, unknown>>('/api/doctor'),
  settings: () => call<Settings>('/api/settings'),
  saveSettings: (body: SettingsIn) => put<Settings>('/api/settings', body),
  setup: () => call<{ ready: boolean; components: Component[] }>('/api/setup'),
  install: (components?: string[]) => post<{ job: number }>('/api/setup', { components: components ?? null }),
  images: () => call<ImageProvider[]>('/api/images'),
  saveImages: (body: { keys?: Record<string, string>; workers?: Record<string, number> }) => put<ImageProvider[]>('/api/images', body),
  checkImages: (id: string) => post<{ message: string }>(`/api/images/${id}/check`),
  storage: () => call<Storage>('/api/storage'),
  saveStorage: (body: Partial<Pick<Storage, 'export_dir' | 'copy_on_accept' | 'clean_after_accept'>>) => put<Storage>('/api/storage', body),
  chooseFolder: () => post<Storage>('/api/storage/choose-folder'),
  clearCache: () => post<Storage & { freed: number }>('/api/storage/clear-cache'),
  emptyTrash: () => post<Storage & { freed: number }>('/api/storage/empty-trash'),
  openFolder: (which: 'episodes' | 'export') => post<{ ok: boolean }>(`/api/storage/open/${which}`),
}

/** URL of a file served by the engine: episode media, style previews, voice samples. */
export const file = (path: string, bust?: number | null) => `${ENGINE}/files/${path}${bust ? `?v=${Math.round(bust)}` : ''}`

export const episodeFile = (e: Episode, path: string, bust?: number | null) => file(`episodes/${e.slug}/${path}`, bust ?? e.updated)

/** Live job list over server-sent events; reconnects on its own. */
export function subscribeJobs(onJobs: (jobs: Job[]) => void): () => void {
  const es = new EventSource(`${ENGINE}/api/events`)
  es.onmessage = (ev) => onJobs(JSON.parse(ev.data).jobs)
  return () => es.close()
}
