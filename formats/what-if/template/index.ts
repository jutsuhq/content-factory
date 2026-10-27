import { WhatIf, type Timeline } from "./WhatIf";

const empty: Timeline = { fps: 30, duration: 1, hook: "", beats: [] };

// `id` is what ../format.yaml names as its template; `empty` is the props the Remotion studio starts with.
export const template = { id: "WhatIf", component: WhatIf, empty };
