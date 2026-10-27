// "Drawn" render mode: every beat is an SVG scene the script's author wrote (viewBox 0 0 1080 1920), so no image
// is generated and the frame costs nothing. Groups move by data attributes, the camera cuts between framings
// (shots.ts) and a paint filter makes the lines "boil" at 12 drawings per second, like hand animation.
//
// Data attributes on a <g> (put them on a wrapper without its own transform attribute):
//   data-depth="0..1"   parallax: 0 is the far background, 1 the nearest layer
//   data-bob="px"       floats up and down        data-sway="deg"   rocks around its centre
//   data-spin="deg/s"   turns around its centre   data-pulse="0.1"  breathes in scale
//   data-drift="dx,dy"  moves in px per second     data-flicker="0.5" opacity flickers by this much
import { useLayoutEffect, useRef } from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";
import { offset, shotAt, shots } from "./shots";
import type { Beat, Timeline } from "./WhatIf";

export type Look = "gouache" | "ink" | "crayon" | "clean";

// displacement strength and grain of each look
const LOOKS: Record<Look, { boil: number; freq: number; grain: number; filter: string }> = {
  gouache: { boil: 5, freq: 0.012, grain: 0.22, filter: "saturate(1.05)" },
  ink: { boil: 3, freq: 0.02, grain: 0.3, filter: "contrast(1.15)" },
  crayon: { boil: 8, freq: 0.035, grain: 0.4, filter: "saturate(0.9)" },
  clean: { boil: 0, freq: 0.01, grain: 0, filter: "none" },
};

const W = 1080;
const H = 1920;
const STEP = 1 / 12; // drawings per second on screen: motion and boil change on twos

const num = (el: Element, name: string) => Number(el.getAttribute(name) ?? 0);

/** Writes each animated group's transform for time t; the camera parallax shifts layers by their depth. */
const animate = (root: SVGGElement, t: number, cam: { x: number; y: number }) => {
  root.querySelectorAll<SVGGElement>("[data-depth],[data-bob],[data-sway],[data-spin],[data-pulse],[data-drift],[data-flicker]").forEach((el, k) => {
    const depth = num(el, "data-depth");
    const [dx, dy] = (el.getAttribute("data-drift") ?? "0,0").split(",").map(Number);
    const phase = k * 1.7; // neighbours do not move in step
    const x = cam.x * depth * 90 + (dx || 0) * t;
    const y = cam.y * depth * 60 + (dy || 0) * t + Math.sin(t * 2.2 + phase) * num(el, "data-bob");
    const rot = num(el, "data-spin") * t + Math.sin(t * 1.6 + phase) * num(el, "data-sway");
    const scale = 1 + Math.sin(t * 2.8 + phase) * num(el, "data-pulse");
    el.style.transformBox = "fill-box";
    el.style.transformOrigin = "center";
    el.style.transform = `translate(${x}px, ${y}px) rotate(${rot}deg) scale(${scale})`;
    const flicker = num(el, "data-flicker");
    if (flicker) el.style.opacity = String(1 - flicker * (0.5 + 0.5 * Math.sin(t * 19 + phase * 3)));
  });
};

// Two scenes share the page during a dissolve: suffix the ids inside each so url(#sky) finds its own gradient.
// Scripts and on* handlers are dropped: the markup comes from a file an agent wrote.
const scoped = (svg: string, k: number) => svg.replace(/<script[\s\S]*?<\/script>/gi, "").replace(/\son\w+="[^"]*"/gi, "").replace(/id="([^"]+)"/g, `id="$1-${k}"`).replace(/url\(#([^)]+)\)/g, `url(#$1-${k})`);

const Scene = ({ beat, index, local, look, seed }: { beat: Beat; index: number; local: number; look: Look; seed: number }) => {
  const ref = useRef<SVGGElement>(null);
  const shot = shotAt(shots(index, beat.duration, beat.focus), local);
  const p = (local - shot.start) / (shot.end - shot.start);
  const zoom = shot.zoom * (1 + 0.05 * p); // slow push inside every shot
  const o = offset({ ...shot, zoom });
  const cam = { x: Math.sin(local * 0.7) * 0.6 + o.x * 2, y: o.y };
  const t = Math.floor(local / STEP) * STEP;
  useLayoutEffect(() => {
    if (ref.current) animate(ref.current, t, cam);
  });
  const L = LOOKS[look];
  return (
    <svg viewBox={`0 0 ${W} ${H}`} width={W} height={H} style={{ position: "absolute", inset: 0, filter: L.filter }}>
      <defs>
        <filter id={`boil-${index}`} x="-5%" y="-5%" width="110%" height="110%">
          <feTurbulence type="fractalNoise" baseFrequency={L.freq} numOctaves={2} seed={seed} />
          <feDisplacementMap in="SourceGraphic" scale={L.boil} xChannelSelector="R" yChannelSelector="G" />
        </filter>
      </defs>
      <g transform={`translate(${W / 2} ${H / 2}) scale(${zoom}) translate(${-W / 2 - o.x * W} ${-H / 2 - o.y * H})`}>
        <g filter={L.boil ? `url(#boil-${index})` : undefined}>
          <g ref={ref} dangerouslySetInnerHTML={{ __html: scoped(beat.svg ?? "", index) }} />
        </g>
      </g>
    </svg>
  );
};

// Paint on paper, laid over the whole frame and fixed to it: a lit paper relief multiplied in, and broad uneven
// washes in soft light so flat fills look brushed rather than vector.
const Paper = ({ amount }: { amount: number }) =>
  amount ? (
    <>
      <svg viewBox={`0 0 ${W} ${H}`} width={W} height={H} style={{ position: "absolute", inset: 0, mixBlendMode: "multiply", opacity: amount * 2 }}>
        <filter id="paper" x="0" y="0" width="100%" height="100%">
          <feTurbulence type="fractalNoise" baseFrequency={0.04} numOctaves={5} seed={7} result="n" />
          <feDiffuseLighting in="n" lightingColor="#fff" surfaceScale={2.2}>
            <feDistantLight azimuth={45} elevation={60} />
          </feDiffuseLighting>
        </filter>
        <rect width={W} height={H} filter="url(#paper)" />
      </svg>
      <svg viewBox={`0 0 ${W} ${H}`} width={W} height={H} style={{ position: "absolute", inset: 0, mixBlendMode: "soft-light", opacity: amount * 2.5 }}>
        <filter id="wash" x="0" y="0" width="100%" height="100%">
          <feTurbulence type="fractalNoise" baseFrequency={0.006} numOctaves={3} seed={3} />
          <feColorMatrix type="saturate" values="0" />
        </filter>
        <rect width={W} height={H} filter="url(#wash)" />
      </svg>
    </>
  ) : null;

const FADE = 0.45; // seconds of cross-dissolve into the next beat

export const DrawnWorld = ({ tl, t }: { tl: Timeline; t: number }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const look: Look = tl.style && tl.style in LOOKS ? (tl.style as Look) : "gouache"; // the script's style is the look in drawn mode
  const seed = Math.floor(frame / (fps * STEP)); // the boil changes on twos
  const i = Math.max(0, tl.beats.findLastIndex((b) => b.start <= t));
  const b = tl.beats[i];
  const local = t - b.start;
  const next = tl.beats[i + 1];
  const fade = next ? Math.max(0, Math.min(1, (local - (b.duration - FADE)) / FADE)) : 0;
  return (
    <AbsoluteFill style={{ background: "#f3ead8" }}>
      <Scene beat={b} index={i} local={local} look={look} seed={seed} />
      {fade > 0 && (
        <AbsoluteFill style={{ opacity: fade }}>
          <Scene beat={next} index={i + 1} local={0} look={look} seed={seed} />
        </AbsoluteFill>
      )}
      <Paper amount={LOOKS[look].grain} />
    </AbsoluteFill>
  );
};
