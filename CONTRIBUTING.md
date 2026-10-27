# Contributing

Issues and pull requests are welcome. For anything bigger than a fix, open an issue first so we can agree on the
shape before you write the code.

## Where things are

| Folder | Change it to | Guide |
|---|---|---|
| `engine/` | add a stage, a voice or image provider, an API route, an MCP tool or a command | [engine/README.md](engine/README.md) |
| `formats/` | add or improve a video format, its styles, prompts or template | [formats/README.md](formats/README.md) |
| `render/` | change how every template is bundled and rendered | [render/README.md](render/README.md) |
| `app/` | change the desktop app | [app/README.md](app/README.md) |

A pull request that stays inside one module is the easiest to review.

## Setup

You need [uv](https://docs.astral.sh/uv/), Node.js 20 or later, FFmpeg and, for the desktop app, Rust.

```bash
cd engine
uv sync                        # MLX voices come along on Apple Silicon; --extra vosk for Russian
uv run factory doctor          # writes profile.yaml for this machine
uv run factory setup all       # renderer packages, RIFE, depth model, starter music
cd ../app && npm install && npx tauri dev
```

A debug build of the app runs the engine from your checkout and keeps episodes, keys and models in `data/`, which
git ignores.

## Checks

Run these before you open a pull request; CI runs the same:

```bash
cd engine
uv run pytest -q tests
uvx ruff check src tests          # lint rules are in pyproject.toml
uvx ruff format src tests         # the formatter decides the layout, 120 columns
uvx pyright                       # types, against the project's .venv
cd ../render && npx tsc           # the renderer and every format's template
cd ../app && npx tsc -p tsconfig.app.json --noEmit
```

## Code rules

- The engine is Python and the renderer is Node. No shell scripts in the engine: everything has to run on Windows too.
- Layers import downward only: `api` → `studio` → `stages` → `voice` / `providers` → `core`.
- A format is data. A new format is a folder in `formats/`, not new branches in the engine
  ([formats/README.md](formats/README.md)).
- A stage is a function with a cache keyed by the hash of its input. Changing one beat must rebuild only that beat.
- The factory does not write scripts. People write them in the app, or an agent writes them over MCP.
- Everything the engine writes goes under `DATA` (`core.paths`), never next to the code.
- Keep comments for what the code cannot say: why, limits, sources of numbers.

## Adding an image provider

Image providers live in `engine/src/factory/providers/image/`. A worker class takes `(n)`, has `name`,
`generate(job)` and `close()`, and raises in the constructor when its key is missing. Register it in `pool.WORKERS` and describe it in
`catalog.PROVIDERS` with its key name, sign-up link and a free key check. See `fal.py` for a small
example.

## Licenses

Code you contribute is released under the [MIT License](LICENSE). Music, models and other assets must be CC0 or
under a license that allows redistribution; note the source next to them.
