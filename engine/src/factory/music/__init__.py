"""Background music from a local library of tracks the owner may use freely (CC0 by default).

music/library.yaml lists every track: id, file, title, author, source, license, moods. `library` reads it and picks
a track for an episode; `fetch` imports CC0 tracks from OpenGameArt and levels them so one mix gain fits all.
Mixing under the voice (with ducking) happens in voice.audio.mix_music during the render stage."""
