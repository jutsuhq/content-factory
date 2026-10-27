import { Loader2, Play } from '../icons'
import { useEffect, useState } from 'react'
import { api, file, type Voice } from '../api'
import { Button, Field, cx, inputCls } from '../ui'

export function VoicePage() {
  const [text, setText] = useState('')
  const [language, setLanguage] = useState('en')
  const [voices, setVoices] = useState<Record<string, Voice>>({})
  const [result, setResult] = useState<{ spoken: string; audio: string } | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    api.settings().then((s) => setLanguage(s.defaults.language))
    api.voices().then(setVoices)
  }, [])

  const say = async () => {
    setBusy(true)
    setError('')
    try {
      setResult(await api.say(text, language))
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="mx-auto max-w-5xl px-8 py-8">
      <h1 className="mb-1 font-display text-[40px]">Voice</h1>
      <p className="mb-6 text-sm text-muted">Every line goes through the same path as a video: numbers to words, pauses, trimmed edges, the voice set for its language.</p>

      <div className="rounded-[18px] border border-line bg-panel p-5">
        <div className="grid gap-4 md:grid-cols-[minmax(0,1fr)_220px]">
          <Field label="Text">
            <textarea value={text} onChange={(e) => setText(e.target.value)} rows={3} placeholder="Type a line in the selected language to hear it" className={cx(inputCls, 'resize-none')} />
          </Field>
          <Field label="Language">
            <select value={language} onChange={(e) => setLanguage(e.target.value)} className={inputCls}>
              {Object.entries(voices).map(([code, v]) => <option key={code} value={code}>{v.name} · {v.engine}</option>)}
            </select>
          </Field>
        </div>
        <p className="mt-3 text-xs text-muted">
          Markup: <code className="font-mono text-text">[pause]</code> or <code className="font-mono text-text">[pause 0.8]</code> for silence.
        </p>
        <Button variant="primary" className="mt-4" onClick={say} disabled={busy || !text.trim()}>
          {busy ? <Loader2 size={15} className="animate-spin" /> : <Play size={15} />} Speak
        </Button>
        {result && (
          <div className="mt-5 space-y-3 rounded-xl bg-bg/60 p-4">
            <p className="text-lg leading-relaxed">{result.spoken}</p>
            <audio key={result.audio} src={file(result.audio)} controls autoPlay className="w-full" />
          </div>
        )}
        {error && <p className="mt-3 text-sm text-bad">{error}</p>}
      </div>
    </div>
  )
}
