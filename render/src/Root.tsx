import { Composition } from "remotion";
import { templates } from "./templates";

export const Root = () => (
  <>
    {templates.map(({ id, component, empty }) => (
      <Composition
        key={id}
        id={id}
        component={component}
        width={1080}
        height={1920}
        fps={30}
        durationInFrames={30}
        defaultProps={{ timeline: empty }}
        calculateMetadata={({ props }) => ({
          fps: props.timeline.fps,
          durationInFrames: Math.max(1, Math.round(props.timeline.duration * props.timeline.fps)),
        })}
      />
    ))}
  </>
);
