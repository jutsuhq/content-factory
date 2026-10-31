# The faceless video playbook

What makes a faceless short travel, and how to make one with Content Factory that a platform treats as original
work. The rules come from posting and from building the factory. Platforms change their rules and never publish
their formulas: read this as practice, not as law, and check each platform's own creator pages before relying on it.

## 1. The idea decides, not the look

Two videos in the same style on the same channel can be 50 times apart in views. What separates them is the premise.
Spend most of the time choosing the idea, then build it well.

**The one-line test.** Say the idea out loud in one sentence. If a friend asks "wait, then what happens?", it is a
video. If they say "huh", it is not. A premise that needs a second sentence is too complicated.

What an idea that travels has:

| Rule | Why | Example |
|---|---|---|
| Change one everyday thing | Everyone has felt friction, heat, water, gravity; the change needs no explaining | "What if friction disappeared for 5 seconds?" |
| For a short time | Short enough to imagine, long enough to wreck something | 5 seconds, one minute, one day |
| Somewhere bright, busy and known | A crowded, sunny, famous place gives the disaster something to hit; dark scenes give the eye nothing to hold | a beach, a stadium, a city square at noon |
| The viewer is the main character | "You" choose, survive or own the result | "What if you jumped through the Earth?" |
| A payoff worth arguing about | The ending is what the comments are about | "Would you jump?" |

Space, night and deep underground are fine as one beat, not as the whole video: keep returning to daylight and people.

**Where ideas come from.** The best source is your own comments: a video someone asked for starts with an audience
waiting for it. Second, trends in your niche (a question a growing sound or tag keeps asking). Copying a competitor's
fresh hit is the weakest source: by the time yours is out, theirs has used up the audience.

## 2. The script

A format's guide (`catalog('format', format=...)`, or `formats/<id>/guide.md`) has its fields and limits. On top of it:

- **Hook at frame 0.** A question or a statement readable in one second. It is on screen before anything moves.
- **Something new every 2-3 seconds.** One consequence per beat, a picture change inside long beats, and a number on
  screen that keeps moving (a counter: seconds since, degrees, kilometres, day 1, day 2). The counter is a reason to
  see the next second.
- **A ladder, not a list.** Each beat is bigger than the one before, so the viewer wants to see the top.
- **One objection mid-video.** "Wait, wouldn't you burn up?" It answers the comment before it is written.
- **Real, checkable facts.** At least three hard numbers, each with a source in `fact_source`.
- **A loop or a question at the end.** The last line repeats the hook, or asks the viewer to pick a side.
- **A running line for the channel.** One recurring phrase or ending that regulars wait for turns viewers into a
  community. Vary how it lands; never repeat the whole video around it.

**Write for one country.** Pick the channel's audience and write for it: places they know, their units (miles and
°F for the US, kilometres and °C elsewhere), their money. Who watches decides how much a view is worth, and a mixed
audience is worth less than a focused one.

**Write for the voice.** Numbers as words, rounded so they read aloud easily ("nearly thirteen thousand kilometres",
not "twelve thousand seven hundred and forty-two"). Short sentences. A line the speech check hears badly (the QA
report lists it) is usually a number or a name: rewrite it rather than rebuild.

## 3. Length

Many creator programmes pay only for videos **longer than one minute**. A hit at 52 seconds can earn nothing.

- Plan **61-80 seconds** from the first draft. The extra time is story (one more beat on the ladder), never silence at
  the end.
- The voice sets the real length: each beat lasts as long as its line. Count the words: the format's guide gives the
  words per second. A 65-second video needs about 65 seconds of spoken lines.
- After the render, check the length in `episode(slug)`. Under 61 seconds: add a beat or lengthen lines, then rebuild.

## 4. Originality

Platforms reward original work and keep getting better at spotting the rest. A video can be flagged as
"non-original" or "repurposed", and a few flags in a month can take a channel out of monetisation. The flags stay on
record even if the video is deleted.

- **Your own script, every word.** Copy a format, its pacing and its energy; never another creator's words.
  Platforms compare the words and the voice, not only the pictures.
- **New next to your own videos too.** Every video gets a new place, a new opening shot and a new camera. A channel
  whose videos share a set, an opening and an ending can be flagged for repeating itself.
- **Never reuse frames.** The factory caches frames per episode; a remake or a copy of an episode starts from them.
  For a new video on the same subject, write new scenes.
- **Vary the sound.** A popular free track that thousands of videos use can make yours look repurposed. Do not use
  the same track twice in a row on a channel, and consider narration and sound alone with no music bed.
- **One file, one post.** Never upload the same file twice (a stuck upload: check the profile first) and never post
  one file on two channels. A duplicate can take down the original with it.
- **One channel, one identity.** Each channel its own name, handle, picture and bio. Never split one series across two
  channels.

## 5. Characters and look

- A recurring character is a **project's cast**: its looks text and reference images go into every frame by
  themselves. Name the character by role in the script ("the kid"); never describe the look again in a beat.
- Check the frame sheet (`episode(slug, frames=True)`): the same face, hair and clothes in every frame. Redo one frame
  (`run(slug, 'redo_frame', beat=n)`) rather than the whole video.
- Keep the top 20% of every frame free for titles, and no text inside the pictures: the template draws all text.
- The look is never the edge, since many channels share a style. Make it recognisable (a colour, a sticker, a counter
  design) but put the effort into the premise.

## 6. Before you post

Five questions, every time:

- [ ] Is it longer than 61 seconds?
- [ ] Is every word of the script ours?
- [ ] New place, new opening, new camera, compared with this channel's last videos?
- [ ] Has this file ever been posted anywhere?
- [ ] Does this channel look like nobody else?

Then the caption: the hook, one or two emoji, a handful of live hashtags (two or three broad, one or two of the niche).

## 7. After you post

- **Judge after 24 hours, not 3.** Big videos often take a day or more to start; at hour three most look like flops.
- Read **views per hour** and the **like rate**. A like rate well under 4% says the idea did not land; over 5% says
  make more like it.
- A flagged video: appeal, and do not delete it while the appeal runs.
- Read the comments for the next idea and for the running line the audience has picked up.

## Formats that fit this

| Format | Shape | In the factory |
|---|---|---|
| What if | one everyday change, consequences stacking up, a live counter, an ending to argue about | `what-if`, states or scenes |
| How it's built | a cutaway from an empty plot to the finished thing (a pool, a bunker), each beat further along, a reveal at the end | one locked world that changes: `states` mode |
| Survival story | day one of an outbreak or a disaster, one place, a choice per scene with a cost, a day counter, ends on the next day for part 2 | a new scene per beat: `scenes` mode, with a cast |
| Long form | the same question told as a 5-8 minute journey, a ladder of bigger steps, a clock on screen | a format of its own (16:9) |

A format the factory does not have yet is made with `save_format` (see `formats/README.md`); it is usable at once.
