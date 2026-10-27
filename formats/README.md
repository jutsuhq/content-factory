# Formats

A format is a kind of video with a fixed structure and a new topic every time. Each folder here is one format, and
everything about it lives in that folder: the script schema, the guide an author or agent writes by, image prompts,
style presets, the Remotion template and finished example scripts. The engine, the app, the MCP server and the
renderer read whatever formats are here; none of them names a format in code.

```
what-if/
├── format.yaml          fields, render modes, limits: what the engine and the app read
├── beats.schema.json    the script schema, checked on every save
├── guide.md             the rules an author writes by, served to agents by catalog('format')
├── styles.yaml          style presets, with previews/ showing each
├── prompts/             image prompts for the frames stage
├── template/            the Remotion composition that renders the video
└── examples/            finished scripts; the first is shown to agents as the reference
```

## Adding a format

Copy `what-if/` and rename it; the folder name is the format id.

- `format.yaml`: `title`, `description`, `template` (the composition id), `duration_seconds`, `caption`, `fields`,
  `blank`, `text_limits` and `render_modes`, each mode with `title`, `hint`, `icon`, `stages`, `style` (`presets` or
  `looks`) and its own `fields`. The bundled one comments each key. The app's script editor and the engine's checks
  are built from these declarations.
- `guide.md`: the rules and fields an agent writes by. `{languages}`, `{language_name}`, `{words_per_second}` and
  `{schema}` are filled in by the engine.
- `beats.schema.json`, with a `format` property.
- `styles.yaml` with at least one style, and `prompts/first_frame.txt` and `next_frame.txt` when a render mode runs
  the frames stage.
- `template/index.ts` exporting `template`: `id` (the composition id), `component` (gets `{ timeline }`, the script's
  fields with the timing and stage outputs) and `empty` (props for the Remotion studio). The renderer finds it when it
  bundles; nothing has to be registered.
- `examples/` with at least one finished script that passes the schema.

Prompts may differ per render mode: `prompts/<mode>/first_frame.txt` wins over `prompts/first_frame.txt`. A style
preset may carry `props`, which go to the template as they are (the bundled one uses `text: sticker`).

## A format from Claude

The formats in this folder ship with the factory and are read-only. Anything else is the owner's own format, kept in
the data folder (`data/formats/<id>/` in a checkout, the application-data folder in the app), and an agent adds one
without touching the code:

1. `catalog('new_format')` returns this file; `format_source(<id>)` returns every text file of the closest format.
2. Write the new folder's files: change the schema, guide, prompts, styles and template for the new kind of video.
3. `save_format(<id>, files)` sends the whole folder. The engine checks format.yaml and the stages each render mode
   names, the schema, the guide, `template/index.ts` and every example against the schema; it keeps nothing when a
   check fails, and a working earlier version stays in place.
4. `create(..., format=<id>)` works at once, and the app lists the format in New video.

From a terminal: `factory format show what-if my-folder/`, edit, then `factory format save my-show my-folder/`.
A template may import only from its own `template/` folder and the renderer's packages (remotion, react, three,
@remotion/three, @react-three/fiber): the render stage bundles the episode's format's `template/` on its own.

Nothing outside the format's folder may name it. `engine/tests/test_formats.py` checks that and runs every format
through blank, check and compose. To preview the template, run `npm run studio` in `render/`.
