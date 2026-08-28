// tiny inline SVG icon set (no emoji, no runtime icon fetch)
import { h } from "vue";

const svg = (paths: any[], props: Record<string, any> = {}) =>
  h(
    "svg",
    { viewBox: "0 0 24 24", fill: "none", stroke: "currentColor",
      "stroke-width": 1.7, "stroke-linecap": "round", "stroke-linejoin": "round",
      width: "1em", height: "1em", ...props },
    paths,
  );

export const IconNode = () =>
  svg([
    h("path", { d: "M12 2 3 7v10l9 5 9-5V7z" }),
    h("path", { d: "M12 22V12" }),
    h("path", { d: "m3 7 9 5 9-5" }),
  ]);
export const IconGear = () =>
  svg([
    h("circle", { cx: 12, cy: 12, r: 3 }),
    h("path", { d: "M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" }),
  ]);
export const IconPlay = () => svg([h("path", { d: "m6 4 14 8-14 8z", fill: "currentColor", stroke: "none" })]);
export const IconClose = () => svg([h("path", { d: "M18 6 6 18M6 6l12 12" })]);
export const IconChevron = () => svg([h("path", { d: "m9 18 6-6-6-6" })]);
export const IconCheck = () => svg([h("path", { d: "M20 6 9 17l-5-5" })]);
export const IconAlert = () =>
  svg([h("path", { d: "M12 9v4M12 17h.01M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z" })]);
