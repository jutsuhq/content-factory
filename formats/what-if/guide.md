Format 'What if': one locked world that changes along one axis (time, depth, speed, scale, steps, count), a big counter on screen, one fact per beat, a loop at the end.

Rules:
- hook: statement or question, readable in 1 second, on screen at frame 0
- steps: 6-12 beats along one axis (time, depth, speed, scale); each beat has one counter value and one fact
- pace: a beat is one short line, 4-7 seconds; the picture cuts every ~2.4 s inside a beat, so long lines feel slow
- objection: one viewer objection mid-video (Wait, doesn't X...?)
- hard_number: at least one checkable figure
- cta: question for the comments
- loop: last line repeats the hook so the video replays

Fields (JSON, schema {schema}):
- language: code ({languages}); hook, title, counter, caption, vo, objection, cta in that language (here {language_name}). caption up to 6 words, hook up to 90 characters.
- axis: {name, unit?}; style: a style id; voice: true for narration; loop: true.
- beats: 3-12 items {counter, caption, state, seconds 2-15, vo?, fact_source?}. vo is spoken: about {words_per_second} words per second of the beat, numbers written as words, [pause] or [pause 0.8] for silence.
- camera: English, one locked composition shared by every frame, room at the top for titles.
- state: English, what the world looks like in this beat, visible changes only, no text in the image.
- focus: optional [x, y], 0..1 of the frame, where the beat's subject is; close-up shots centre on it.
- The last beat's vo repeats the hook so the video loops. Facts must be real; put the source in fact_source.
- music: a track id from the music catalog, 'none', or mood words.

Drawn mode (render_mode: "drawn", no image generation, free): instead of camera and state, every beat has `svg`, the scene drawn by you as SVG markup without the outer <svg> tag, in a 1080x1920 viewBox; style is the paint look: gouache, ink, crayon or clean. Keep the top 600 px calm for the counter and caption and the band from 1300 to 1600 px clear for subtitles. Draw in layers, each a <g> with data-depth from 0 (sky) to 1 (nearest), and bring it to life with data-bob="px", data-sway="deg", data-spin="deg/s", data-pulse="0.05", data-drift="dx,dy" (px/s) or data-flicker="0.5" on wrapper groups that have no transform attribute of their own. Flat shapes, a small palette and bold silhouettes read best on a phone; use paths, gradients and opacity, no text, no external images. Keep one world and change it from beat to beat, like the frames of the states mode.
