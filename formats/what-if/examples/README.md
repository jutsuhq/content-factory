# Examples

Finished scripts of the three demo videos. Each is a `beats.json` for the *What if* format, the same file the app
and the MCP server write.

| Script | Mode | Needs |
|---|---|---|
| [what-if-every-human-vanished](what-if-every-human-vanished.beats.json) | AI frames, Low-poly City | an image provider key, about $0.30 |
| [what-if-the-sun-went-out](what-if-the-sun-went-out.beats.json) | Drawn, gouache | nothing, free |
| [what-if-you-fell-into-jupiter](what-if-you-fell-into-jupiter.beats.json) | AI frames, Space Epic | an image provider key, about $0.30 |

To render one from the command line:

```bash
cd engine
uv run factory create "What if the Sun went out?" --script ../formats/what-if/examples/what-if-the-sun-went-out.beats.json
uv run factory run <slug> approve
```

`create` prints the new episode's slug; `run` waits for the job and prints where the video is. The episode shows up
in the app too, where you can edit the script and rebuild single beats.
