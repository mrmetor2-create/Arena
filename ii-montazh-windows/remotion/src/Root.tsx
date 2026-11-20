import React from "react";
import { Composition, staticFile } from "remotion";
import { Main } from "./Main";
import type { MainProps, Project } from "./types";

export const Root: React.FC = () => (
  <Composition
    id="Main"
    component={Main}
    width={1080}
    height={1920}
    fps={30}
    durationInFrames={90}
    defaultProps={{ project: null, showGuides: false } as MainProps}
    calculateMetadata={async ({ props }) => {
      try {
        const res = await fetch(staticFile("current/project.json"), { cache: "no-store" });
        if (!res.ok) throw new Error(String(res.status));
        const project = (await res.json()) as Project;
        return {
          durationInFrames: project.durationInFrames,
          fps: project.fps,
          width: project.width,
          height: project.height,
          props: { ...props, project },
        };
      } catch {
        return { props: { ...props, project: null } };
      }
    }}
  />
);
