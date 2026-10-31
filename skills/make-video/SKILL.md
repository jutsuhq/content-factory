---
name: make-video
description: Make a faceless short video with Content Factory (the content-factory MCP server), from idea to a file ready to post. Use when the owner asks for a video, a series, an idea for a channel, a script, or a new format; when they say "сделай ролик", "make a what-if about…", "ideas for my channel", or name a project/channel. Covers picking the idea, writing the script by the format's guide, the length and originality rules that keep a channel monetised, checking the result, and the pre-post checklist.
---

# Make a video with Content Factory

The factory renders; you write. It never writes scripts. Everything goes through the `content-factory` MCP tools:
`status`, `catalog`, `create`, `edit_script`, `run`, `job`, `episode`, `episodes`, `accept`, `format_source`,
`save_format`. The reasoning behind every rule here is in `docs/playbook.md` of the repository.

## 1. Context first

1. `status` — the engine is up and an image provider is on. If not, tell the owner what is missing and stop.
2. `catalog('projects')` — the channel: its brief, audience country, variants and cast. The video belongs to one.
   No project fits: ask which channel, or make the video without one if the owner says so.
3. `episodes(project=<id>)` — the channel's last videos. You need them for originality (step 3).
4. `catalog('format', format=<id>)` — the format's guide, fields and a finished example. Read it before the first
   `create` in a session. No format fits the idea: go to "A new format" below.

## 2. The idea

Unless the owner gave one, propose three ideas in one line each and let them pick. Each must pass:

- **One line.** One everyday thing changes (friction, heat, water, gravity), for a short time, or the viewer
  survives/builds/owns something. If it needs a second sentence, drop it.
- **Bright, busy, known place** for most beats. Space, night or underground only as single beats.
- **The viewer is the main character** ("you").
- **An ending to argue about** in the comments.
- **New for this channel**: not a topic, place or opening its last videos already used.

Good sources, best first: the owner's comments and requests, a rising trend in the niche, the owner's brief.
Never a competitor's fresh hit copied.

## 3. The script

Write the whole `beats.json` by the format's guide, then check it against this list before `create`:

- [ ] **Length 61-80 s of speech.** Count the words of all `vo` lines against the guide's words per second. The voice
      sets the length, so a script with 45 s of words renders at 45 s whatever `seconds` says. Short: add a beat on
      the ladder, never pad.
- [ ] **Hook** readable in one second, on screen at frame 0.
- [ ] **Something new every 2-3 s**: one consequence per beat, a counter that changes every beat, each beat bigger
      than the last.
- [ ] **One objection** mid-video; **at least three real numbers**, each with `fact_source`.
- [ ] **Units and places of the channel's country** (miles and °F for a US channel).
- [ ] **Numbers as words, rounded to read aloud** ("nearly thirteen thousand"), short sentences.
- [ ] **Ending**: the hook again (loop) or a question that makes people pick a side; the channel's running line if it
      has one, landed differently than last time.
- [ ] **Originality**: every word yours; a place, opening shot and camera that differ from the channel's last videos.
- [ ] **Pictures**: image fields in English, no text in the images, top 20% free; cast members named by role only
      ("the kid"), never described.

Then `create(topic, script, format, project, variant, cast)`. Show the owner the hook, the beat list (counter +
caption + one line each) and the length estimate. Apply feedback with `edit_script`. Generate only after their go:
`run(slug, 'approve')`, then `job(id)` until done (it waits up to 50 s per call; never poll faster).

## 4. Check the result

`episode(slug, frames=True)` gives the video path, the QA report and a frame sheet. Look at the sheet once:

- the cast looks the same in every frame (face, hair, clothes); hands and bodies are whole;
- no text or logos drawn into the pictures; titles are readable over the frames;
- the length is over 61 s;
- the QA report: a line the speech check heard badly is usually a number or a name — rewrite that `vo`, then
  `run(slug, 'rebuild', stages=['tts','align','render','qa'])`.

One bad frame: `run(slug, 'redo_frame', beat=n)`. A wrong scene: `edit_script` the beat's picture field, then
`rebuild`. Never remake a whole video for one frame.

Send the owner the video path and what you checked, with anything that still looks off. Do not call it done before
they have seen it.

## 5. Before posting

When the owner is happy, go through these with them and say which one fails, if any:

- [ ] Longer than 61 seconds?
- [ ] Every word of the script ours?
- [ ] New place, opening and camera next to the channel's last videos?
- [ ] This file never posted anywhere, and only to this one channel?
- [ ] Music not the same track as the channel's last video (or no music bed)?

Then `accept(slug, caption)` with a caption: the hook as one short line, one or two emoji, four to six live hashtags
(two or three broad, one or two of the niche; never invented ones). Give the owner the file path. Posting is theirs.

## A series

Several videos on one subject: `create` each with the same `series`. Each gets its own place and opening; the
survival-story shape ends each one on the next day so part 2 has a reason to exist.

## A new format

When no format fits (a new shape seen in a trend, a reference video the owner sends):

1. `catalog('new_format')` for how a format is built; `format_source(<closest format>)` for files to start from.
2. Write the format whole: `format.yaml` (fields, render modes, length 61 s or more by default), `beats.schema.json`,
   `guide.md` (the rules above, specific to the shape), prompts, `styles.yaml`, the Remotion `template/`, and one
   finished example script in `examples/`.
3. `save_format(id, files)`. The engine checks it and refuses a broken one with the reasons; fix and save again. It is
   usable at once, in the app too.
4. Make the first video in it with this skill.

Reuse what the engine already offers (render modes `states`, `scenes`, `drawn`; style `props` such as sticker text)
before asking for engine changes.
