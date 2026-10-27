# Architecture

Content Factory has three parts: a Python engine that does the work, a Remotion project that renders the video, and
a Tauri desktop app that drives the engine over a local HTTP API. Agents drive the same engine over MCP.

| Folder | Part |
|---|---|
| `engine/` | the Python engine (`engine/src/factory/`) and its tests |
| `formats/` | the formats, one folder each, render template included |
| `render/` | the Remotion project that bundles and renders the templates |
| `app/` | the desktop app |

```
app (Tauri + React)     agent (Claude Code, any MCP client)
        │  HTTP 127.0.0.1:8790        │  stdio
        └──────────────┬──────────────┘
                 engine (FastAPI)
   api → studio → stages → voice / providers → core
                       │
                 render (Remotion, Node)
```

## Engine

| Layer | Path in `engine/src/factory/` | What it does |
|---|---|---|
| core | `core/` | paths, profile, secrets, languages, desktop actions |
| providers | `providers/` | interchangeable back ends: image APIs, TTS, speech-to-text |
| voice | `voice/` | text normalisation, pauses, tempo, audio joins |
| stages | `stages/` | `frames` → `depth` → `transitions` → `tts` → `align` → `render` → `qa` |
| studio | `studio/` | episodes on disk, composing scripts, translation copies, storage |
| api | `api/` | the HTTP API and the job queue handlers |
| mcp | `mcp/` | the MCP server, a thin client of the HTTP API |

Layers import downward only.

### Paths

`ROOT` is the repository (`CF_ROOT`, default the checkout): `engine/`, `formats/`, `render/`. `DATA` is everything
the engine writes (`CF_DATA`, default `data/` in the checkout, ignored by git): episodes, `profile.yaml`, `.env` with API keys, models, tools, the job database, the log, music and the
render workspace. The release app sets `CF_ROOT` to its bundled resources and `CF_DATA` to the app-data folder, so
the code stays read-only.

### Episodes

An episode is a folder `episodes/<slug>/`. `beats.json` is the single source of truth: the script, the style, the
camera and one entry per beat. Stages read it and write their results under `work/`, each next to a `.key` file
holding the hash of its input. Running a stage again with the same input is a no-op; editing one beat rebuilds only
that beat. The finished video is `out/<slug>.mp4` with `out/qa.json` next to it.

### Projects

A project is a channel: `projects/<id>/project.json` in DATA holds its details, its variants and its cast, and
`projects/<id>/cast/<character>/` its characters' reference images (`core/projects.py`). Composing with `project` and
`variant` takes the variant's settings where the call and the script give none, and writes `project` and `cast` (the
characters' ids) into `beats.json`, `project` and `variant` into `meta.json`. The frames stage adds the characters'
looks to every prompt and their first three images to every frame's references.

### Jobs

Long work runs in a queue (`jobs.py`, SQLite). The app subscribes to its event stream; agents wait on a job with
`GET /api/jobs/{id}?wait=55`. Heavy jobs run one at a time, light ones in parallel. A job that was running when the
app closed is marked stopped on the next start.

## Formats

A format is data in `formats/<id>/`; the engine names none of them. `core/formats.py` lists the folders that have a
`format.yaml` and loads one by id. Every `beats.json` carries `"format": "<id>"` (compose writes it); a script
without one, written before formats were named, uses the default format: the `format` in the owner's Settings
when it exists, else the first one found.

- `format.yaml`: what the engine and the app read: title and description, the Remotion composition id
  (`template`), duration limits, the post caption template, the script and beat `fields` (label, kind `text`,
  `textarea` or `svg`, and the flags `required`, `english`, `translate`), the empty-script skeleton, the text limits
  for the quality check, and `render_modes`. Each render mode (the first is the default) declares the stages it
  runs, its own extra fields, and its style choice: the presets of `styles.yaml`, or a fixed list of looks. The
  engine and the app read these declarations; no mode or format is named in code;
- `guide.md`: the rules an author writes by, served to agents by `catalog('format')`; `{languages}`,
  `{language_name}`, `{words_per_second}` and `{schema}` are filled in by the engine;
- `beats.schema.json`: the script schema, checked on every save;
- `prompts/`: image prompt templates for the frames stage (`first_frame.txt`, `next_frame.txt`), with `{style}` and
  the script's fields as `{field}`;
- `styles.yaml` and `previews/`: style presets;
- `template/`: the Remotion composition, `index.ts` exporting `template` (`id`, `component`, `empty`);
- `examples/`: finished scripts; the first is shown to agents as the reference.

`render/` finds every `formats/*/template/index.ts` when it bundles (`render/src/templates.ts`) and `Root.tsx`
registers each by its id; adding a format touches no file in `render/`. The template gets the script's fields, the timing and
the files of the picture stages its render mode runs. Generic checks stay in code: the schema, digits in spoken
lines, voice length against the beat's seconds. `stages.ORDER` is the order stages run in; `stages.plan` picks the
ones the render mode declares, and the voice stages only for a narrated script.

The bundled format is **What if**: one world seen from a locked camera, one axis of change (time, depth, size), a
counter on screen, and a loop back to the hook.

## Frames

The first frame sets the style; every other frame is an edit of it with only the state of the world changed, so the
camera and layout stay pixel-aligned. Depth Anything V2 turns each frame into a parallax layer and RIFE
interpolates between frames for the transitions. The image pool runs several workers per provider in parallel and
retires a worker whose key or quota fails.

## App

`app/` is Tauri 2 with React and Tailwind. `src-tauri/src/lib.rs` starts the engine with `uv run --project engine factory serve`,
stops it on exit, and shows a recovery screen with the log when it cannot start. On first launch the onboarding
installs the components and asks for an image provider key.
