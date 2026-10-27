"""Everything between a script line and a finished voice track, engine-agnostic:
`text` cleans the line and reads its markup, `fit` decides how fast a line may be
spoken to fit its beat, `audio` does the ffmpeg work (silence, tempo, joins, loudness)."""
