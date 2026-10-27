// Cuts inside a beat. One still held for 8 seconds feels slow on a phone, so every beat is split into shots of
// about SHOT seconds, each a different framing of the same picture: punch-ins on the beat's focus point and a
// wide shot. The last shot of a beat is always wide, so the transition into the next beat happens wide.

export type Framing = { zoom: number; fx: number; fy: number }; // fx, fy: point to centre on, 0..1 of the frame
export type Shot = Framing & { start: number; end: number }; // seconds from the beat start

export const SHOT = 2.4;
const WIDE: Framing = { zoom: 1, fx: 0.5, fy: 0.5 };

export const shots = (beatIndex: number, duration: number, focus: [number, number] = [0.5, 0.55]): Shot[] => {
  const n = Math.max(1, Math.floor(duration / SHOT));
  const [fx, fy] = focus;
  const close: Framing[] = [
    { zoom: 1.3, fx, fy },
    { zoom: 1.65, fx, fy },
    { zoom: 1.2, fx: 1 - fx, fy: Math.min(0.75, fy + 0.12) }, // the other side of the frame
  ];
  const len = duration / n;
  return Array.from({ length: n }, (_, k) => {
    const wide = k === n - 1 || (beatIndex === 0 && k === 0); // the hook opens wide
    return { ...(wide ? WIDE : close[(beatIndex + k) % close.length]), start: k * len, end: (k + 1) * len };
  });
};

export const shotAt = (list: Shot[], local: number): Shot => list.find((s) => local < s.end) ?? list[list.length - 1];

/** How far the frame is moved so that the focus point is centred, clamped so the picture still fills the frame. */
export const offset = (f: Framing) => {
  const room = (1 - 1 / f.zoom) / 2; // how far the centre may move, as a fraction of the frame
  const clamp = (v: number) => Math.max(-room, Math.min(room, v));
  return { x: clamp(f.fx - 0.5), y: clamp(f.fy - 0.5) };
};
