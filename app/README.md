# App

The desktop app: Tauri 2 with React and Tailwind. It starts the engine next to the window and talks to it over
`http://127.0.0.1:8790`; it holds no pipeline logic of its own.

- `src/pages/` one file per screen: Composer, Episode, Library, Queue, Explore, Voice, Settings, Setup.
- `src/api.ts` the typed client of the engine's HTTP API.
- `src-tauri/src/lib.rs` starts and stops the engine (`uv run --project engine factory serve`) and shows a recovery
  screen with its log when it cannot start. A release build bundles `engine/`, `formats/` and `render/` as resources.

```bash
npm install
npx tauri dev                      # runs the engine from this checkout
npx tauri build --bundles app      # a release .app
```
