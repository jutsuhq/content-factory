import type { ComponentType } from "react";

/** One format's Remotion composition. The render stage passes `{ timeline }` (timeline.json) as its props; every
 * timeline carries fps and duration, which size the composition. */
export type Template<T extends { fps: number; duration: number }> = {
  id: string; // the composition id the format's format.yaml declares as `template`
  component: ComponentType<{ timeline: T }>;
  empty: T; // props for the Remotion studio before a timeline is loaded
};
