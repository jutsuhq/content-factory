# Render

The Remotion project that turns an episode's `timeline.json` into a video. It holds no format of its own:
`src/templates.ts` finds every `formats/*/template/index.ts` when Remotion bundles, and `src/Root.tsx` registers each
as a 1080×1920 composition sized by its timeline.

- `remotion.config.ts` points the bundle at the formats folder (`CF_FORMATS`, default `../formats`) and resolves the
  templates' imports from this package.
- The engine's render stage runs `npx remotion render` here with the episode's `work/public` as the public folder.
- `npm run studio` opens the Remotion studio with every template; `npx tsc` checks this package and the templates.

Packages are installed by `factory setup render` (or `npm install`). Remotion has its own license.
