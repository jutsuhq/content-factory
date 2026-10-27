// Template of the bundled What-if format (formats/what-if). In "states" mode: one locked world per beat with depth
// parallax, RIFE morphs between beats and camera cuts inside each beat (shots.ts).
// In "drawn" mode: SVG scenes from the script (Drawn.tsx). Both get the HUD counter and caption, word-by-word
// subtitles and voice per beat.
// Music is mixed in afterwards by the render stage (ffmpeg ducking under the voice).
// Everything comes from timeline.json, which the render stage writes into the episode's public dir.
import { useLayoutEffect, useMemo, useState } from "react";
import { AbsoluteFill, Audio, Sequence, continueRender, delayRender, interpolate, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { ThreeCanvas } from "@remotion/three";
import { useThree } from "@react-three/fiber";
import * as THREE from "three";
import { DrawnWorld } from "./Drawn";
import { offset, shotAt, shots } from "./shots";

type Word = { word: string; start: number; end: number };
export type Beat = {
  start: number; // seconds
  duration: number;
  counter: string;
  caption: string;
  image?: string; // states mode
  depth?: string;
  svg?: string; // drawn mode
  focus?: [number, number]; // where punch-in shots centre, 0..1 of the frame
  voice?: string;
  words: Word[]; // seconds from the beat start
  morph?: { dir: string; count: number; seconds: number }; // into the next beat, at the end of this one
};
// timeline.json: the style preset's props, the script's own fields plus timing; mode is the render mode, style the
// preset or look, text the look of the counter and subtitles ("sticker": bold outlined, else plain with a shadow)
export type Timeline = { fps: number; duration: number; hook: string; mode?: string; style?: string; text?: string; beats: Beat[] };

const frameName = (n: number) => `${String(n).padStart(8, "0")}.jpg`;

// What to draw at a time: an image and a blend between the depth maps of two beats.
const pick = (tl: Timeline, t: number) => {
  const i = Math.max(0, tl.beats.findLastIndex((b) => b.start <= t));
  const b = tl.beats[i];
  const local = t - b.start;
  const m = b.morph;
  if (!m || local < b.duration - m.seconds || i === tl.beats.length - 1) {
    return { i, image: b.image!, depthA: b.depth!, depthB: b.depth!, mix: 0 };
  }
  const p = Math.min(1, (local - (b.duration - m.seconds)) / m.seconds);
  const n = Math.min(m.count, Math.max(1, Math.round(p * (m.count - 1)) + 1));
  return { i, image: `${m.dir}/${frameName(n)}`, depthA: b.depth!, depthB: tl.beats[i + 1].depth!, mix: p };
};

// Texture cache. With frameloop "never" R3F draws only when Remotion advances it, so a texture that
// arrives after the frame was drawn would leave the frame black: hold the frame, then advance by hand.
type Entry = { tex: THREE.Texture | null; handle: number | null };
const cache = new Map<string, Entry>();
const loader = new THREE.TextureLoader();
const MAX_TEXTURES = 48;

const evict = (keep: Set<string>) => {
  for (const [url, e] of cache) {
    if (cache.size <= MAX_TEXTURES) break;
    if (e.tex && !keep.has(url)) {
      e.tex.dispose();
      cache.delete(url);
    }
  }
};

const useTextures = (urls: string[]) => {
  const advance = useThree((s) => s.advance);
  const [, rerender] = useState(0);
  for (const url of urls) {
    if (!cache.has(url)) {
      const entry: Entry = { tex: null, handle: delayRender(`texture ${url}`) };
      cache.set(url, entry);
      loader.load(staticFile(url), (t) => {
        entry.tex = t;
        rerender((n) => n + 1);
      });
    }
  }
  const entries = urls.map((u) => cache.get(u)!);
  useLayoutEffect(() => {
    if (entries.some((e) => !e.tex)) return;
    // the same url can come twice (both depth maps outside a morph): release each handle once
    const waiting = [...new Set(entries)].filter((e) => e.handle !== null);
    if (waiting.length) {
      advance(performance.now());
      waiting.forEach((e) => {
        continueRender(e.handle!);
        e.handle = null;
      });
    }
    evict(new Set(urls));
  });
  return entries.map((e) => e.tex);
};

const vertex = /* glsl */ `
  uniform sampler2D depthA; uniform sampler2D depthB; uniform float mixAB; uniform float strength;
  varying vec2 vUv;
  void main() {
    vUv = uv;
    float d = mix(texture2D(depthA, uv).r, texture2D(depthB, uv).r, mixAB);
    gl_Position = projectionMatrix * modelViewMatrix * vec4(position + vec3(0.0, 0.0, d * strength), 1.0);
  }`;
// Texels go out as they are (no colour-space conversion), so the frame keeps the source colours.
const fragment = /* glsl */ `
  uniform sampler2D image; varying vec2 vUv;
  void main() { gl_FragColor = texture2D(image, vUv); }`;

const World = ({ tl, t }: { tl: Timeline; t: number }) => {
  const s = pick(tl, t);
  const [image, depthA, depthB] = useTextures([s.image, s.depthA, s.depthB]);
  const material = useMemo(
    () =>
      new THREE.ShaderMaterial({
        vertexShader: vertex,
        fragmentShader: fragment,
        uniforms: { image: { value: null }, depthA: { value: null }, depthB: { value: null }, mixAB: { value: 0 }, strength: { value: 1.2 } },
      }),
    [],
  );
  const camera = useThree((st) => st.camera);
  // A cut to a new framing every few seconds, a slow push inside each shot and a sideways drift over the whole
  // episode: parallax comes from the camera. The plane is 9.9 x 17.6 units and fills the frame from z 17.4.
  const beat = tl.beats[s.i];
  const local = t - beat.start;
  const shot = shotAt(shots(s.i, beat.duration, beat.focus), local);
  const push = 1 + 0.05 * ((local - shot.start) / (shot.end - shot.start));
  const o = offset({ ...shot, zoom: shot.zoom * push });
  const p = t / tl.duration;
  const x = o.x * 9.9 + Math.sin(p * Math.PI * 4) * 0.35;
  const y = -o.y * 17.6 + 0.15;
  camera.position.set(x, y, interpolate(p, [0, 1], [17.4, 16.4]) / (shot.zoom * push));
  camera.lookAt(x, y - 0.15, 0);
  if (!image || !depthA || !depthB) return null;
  Object.assign(material.uniforms.image, { value: image });
  Object.assign(material.uniforms.depthA, { value: depthA });
  Object.assign(material.uniforms.depthB, { value: depthB });
  material.uniforms.mixAB.value = s.mix;
  return (
    <mesh material={material} scale={1.1}>
      <planeGeometry args={[9, 16, 256, 256]} />
    </mesh>
  );
};

const shadow = "0 4px 18px rgba(0,0,0,.65), 0 0 4px rgba(0,0,0,.5)";

// Sticker text: a heavy rounded face with a thick dark outline drawn under the fill.
const STICKER = { fontFamily: '"Arial Rounded MT Bold", "Arial Black", sans-serif', fontWeight: 900, WebkitTextStroke: "14px #111", paintOrder: "stroke fill", textTransform: "uppercase" } as const;
const YELLOW = "#ffd84d";

const StickerHud = ({ beat, t, hook }: { beat: Beat; t: number; hook: string }) => {
  const pop = interpolate(t - beat.start, [0, 0.18, 0.3], [0.6, 1.08, 1], { extrapolateRight: "clamp" });
  return (
    <AbsoluteFill style={{ alignItems: "center", textAlign: "center" }}>
      {t < 2.5 ? (
        <div style={{ ...STICKER, position: "absolute", top: 150, padding: "0 70px", fontSize: 96, lineHeight: 1.05, color: YELLOW }}>{hook}</div>
      ) : (
        <div style={{ position: "absolute", top: 150, display: "flex", flexDirection: "column", alignItems: "center", gap: 18, transform: `scale(${pop})` }}>
          <div style={{ background: "white", border: "8px solid #111", borderRadius: 28, padding: "10px 44px", boxShadow: "0 10px 0 rgba(0,0,0,.35)" }}>
            <div style={{ ...STICKER, WebkitTextStroke: "10px #111", fontSize: Math.min(120, 1300 / Math.max(1, beat.counter.length)), color: YELLOW, whiteSpace: "nowrap" }}>{beat.counter}</div>
          </div>
          <div style={{ ...STICKER, WebkitTextStroke: "10px #111", fontSize: 50, color: "white", padding: "0 80px" }}>{beat.caption}</div>
        </div>
      )}
    </AbsoluteFill>
  );
};

// Two words at a time, the spoken one yellow, each popping in as it is said.
const StickerSubtitles = ({ words, t }: { words: Word[]; t: number }) => {
  const i = words.findLastIndex((w) => w.start <= t);
  if (i < 0 || t > words[words.length - 1].end + 0.4) return null;
  const from = Math.floor(i / 2) * 2;
  return (
    <AbsoluteFill style={{ justifyContent: "flex-end", alignItems: "center", paddingBottom: 360 }}>
      <div style={{ ...STICKER, fontSize: 104, textAlign: "center", padding: "0 60px", lineHeight: 1.1 }}>
        {words.slice(from, from + 2).map((w, k) => {
          const pop = interpolate(t - w.start, [0, 0.12, 0.22], [0.5, 1.12, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
          return (
            <span key={k} style={{ display: "inline-block", margin: "0 14px", color: from + k === i ? YELLOW : "white", transform: `scale(${from + k <= i ? pop : 1})` }}>
              {w.word.replace(/[.,!?;:]+$/, "")}
            </span>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};

const Hud = ({ beat, t, hook }: { beat: Beat; t: number; hook: string }) => (
  <AbsoluteFill style={{ fontFamily: "Helvetica Neue, Arial, sans-serif", color: "white", textShadow: shadow, textAlign: "center" }}>
    {/* a long counter ("MILLIONS OF YEARS") shrinks to stay on one line above the caption */}
    <div style={{ position: "absolute", top: 170, width: "100%", fontSize: Math.min(128, 1500 / Math.max(1, beat.counter.length)), fontWeight: 800, letterSpacing: 4, whiteSpace: "nowrap" }}>{beat.counter}</div>
    <div style={{ position: "absolute", top: 330, width: "100%", padding: "0 90px", boxSizing: "border-box", fontSize: 54, fontWeight: 700 }}>
      {t < 2.5 ? hook : beat.caption}
    </div>
  </AbsoluteFill>
);

// Up to four words on screen, the spoken one highlighted.
const Subtitles = ({ words, t }: { words: Word[]; t: number }) => {
  const i = words.findLastIndex((w) => w.start <= t);
  if (i < 0 || t > words[words.length - 1].end + 0.4) return null;
  const from = Math.floor(i / 4) * 4;
  return (
    <AbsoluteFill style={{ justifyContent: "flex-end", alignItems: "center", paddingBottom: 430 }}>
      <div style={{ fontFamily: "Helvetica Neue, Arial, sans-serif", fontSize: 72, fontWeight: 800, textAlign: "center", padding: "0 80px", textShadow: shadow }}>
        {words.slice(from, from + 4).map((w, k) => (
          <span key={k} style={{ color: from + k === i ? "#ffd84d" : "white" }}>
            {w.word}{" "}
          </span>
        ))}
      </div>
    </AbsoluteFill>
  );
};

export const WhatIf = ({ timeline: tl }: { timeline: Timeline }) => {
  const frame = useCurrentFrame();
  const { width, height, fps } = useVideoConfig();
  const t = frame / fps;
  const s = tl.mode === "drawn" ? { i: Math.max(0, tl.beats.findLastIndex((b) => b.start <= t)), mix: 0 } : pick(tl, t);
  const beat = tl.beats[s.i];
  const hudBeat = tl.beats[s.mix >= 0.5 ? s.i + 1 : s.i]; // the counter flips halfway through a morph
  return (
    <AbsoluteFill style={{ background: "black" }}>
      {tl.mode === "drawn" ? (
        <DrawnWorld tl={tl} t={t} />
      ) : (
        <ThreeCanvas width={width} height={height} camera={{ fov: 50, position: [0, 0, 17], near: 0.1, far: 100 }}>
          <World tl={tl} t={t} />
        </ThreeCanvas>
      )}
      {tl.text === "sticker" ? (
        <>
          <StickerHud beat={hudBeat} t={t} hook={tl.hook} />
          <StickerSubtitles words={beat.words} t={t - beat.start} />
        </>
      ) : (
        <>
          <Hud beat={hudBeat} t={t} hook={tl.hook} />
          <Subtitles words={beat.words} t={t - beat.start} />
        </>
      )}
      {tl.beats.map((b, k) =>
        b.voice ? (
          <Sequence key={k} from={Math.round(b.start * fps)} durationInFrames={Math.round(b.duration * fps)}>
            <Audio src={staticFile(b.voice)} />
          </Sequence>
        ) : null,
      )}
    </AbsoluteFill>
  );
};
