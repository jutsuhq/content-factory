# Engine

The Python engine: it runs the pipeline, keeps the job queue and serves the HTTP API the app, the MCP server and the
`factory` command use. Everything is in `src/factory/`; layers import downward only.

| Folder | What it does |
|---|---|
| `core/` | paths, profile, secrets, languages, the format registry |
| `providers/` | interchangeable back ends: image APIs, TTS, speech-to-text |
| `voice/` | text normalisation, pauses, tempo, audio joins |
| `stages/` | `frames` → `depth` → `transitions` → `tts` → `align` → `render` → `qa`, each cached by its input |
| `studio/` | episodes on disk, composing scripts, translation copies, storage |
| `api/` | the HTTP API and the job handlers |
| `mcp/` | the MCP server, a client of the HTTP API |
| `music/` | the CC0 music library and the starter list |

`cli.py` is the `factory` command, `jobs.py` the queue, `setup.py` and `doctor.py` prepare the machine.

```bash
uv sync                    # MLX voices come along on Apple silicon; --extra vosk adds the Russian voice
uv run factory --help
uv run pytest -q tests
```

See [docs/architecture.md](../docs/architecture.md) for how the parts fit together.
