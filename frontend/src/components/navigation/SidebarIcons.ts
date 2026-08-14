import { h, type VNode } from "vue";

export function IconRides(): VNode {
  return h(
    "svg",
    {
      viewBox: "0 0 24 24",
      width: "18",
      height: "18",
      fill: "none",
      stroke: "currentColor",
      "stroke-width": "2",
      "stroke-linecap": "round",
      "stroke-linejoin": "round",
    },
    [
      h("circle", { cx: "5.5", cy: "17.5", r: "3.5" }),
      h("circle", { cx: "18.5", cy: "17.5", r: "3.5" }),
      h("path", {
        d: "M15 6a1 1 0 1 0 0-2 1 1 0 0 0 0 2zm-3 11.5V14l-3-3 4-3 2 3h3",
      }),
    ],
  );
}

export function IconDashboard(): VNode {
  return h(
    "svg",
    {
      viewBox: "0 0 24 24",
      width: "18",
      height: "18",
      fill: "none",
      stroke: "currentColor",
      "stroke-width": "2",
      "stroke-linecap": "round",
      "stroke-linejoin": "round",
    },
    [
      h("rect", { x: "3", y: "3", width: "7", height: "7" }),
      h("rect", { x: "14", y: "3", width: "7", height: "7" }),
      h("rect", { x: "14", y: "14", width: "7", height: "7" }),
      h("rect", { x: "3", y: "14", width: "7", height: "7" }),
    ],
  );
}

export function IconCalendar(): VNode {
  return h(
    "svg",
    {
      viewBox: "0 0 24 24",
      width: "18",
      height: "18",
      fill: "none",
      stroke: "currentColor",
      "stroke-width": "2",
      "stroke-linecap": "round",
      "stroke-linejoin": "round",
    },
    [
      h("rect", {
        x: "3",
        y: "4",
        width: "18",
        height: "18",
        rx: "2",
        ry: "2",
      }),
      h("line", { x1: "16", y1: "2", x2: "16", y2: "6" }),
      h("line", { x1: "8", y1: "2", x2: "8", y2: "6" }),
      h("line", { x1: "3", y1: "10", x2: "21", y2: "10" }),
    ],
  );
}

export function IconImport(): VNode {
  return h(
    "svg",
    {
      viewBox: "0 0 24 24",
      width: "18",
      height: "18",
      fill: "none",
      stroke: "currentColor",
      "stroke-width": "2",
      "stroke-linecap": "round",
      "stroke-linejoin": "round",
    },
    [
      h("path", { d: "M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" }),
      h("polyline", { points: "17 8 12 3 7 8" }),
      h("line", { x1: "12", y1: "3", x2: "12", y2: "15" }),
    ],
  );
}

export function IconTrack(): VNode {
  return h(
    "svg",
    {
      viewBox: "0 0 24 24",
      width: "18",
      height: "18",
      fill: "none",
      stroke: "currentColor",
      "stroke-width": "2",
      "stroke-linecap": "round",
      "stroke-linejoin": "round",
    },
    [
      h("path", { d: "M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0Z" }),
      h("circle", { cx: "12", cy: "10", r: "3" }),
    ],
  );
}

export function IconHr24h(): VNode {
  return h(
    "svg",
    {
      viewBox: "0 0 24 24",
      width: "18",
      height: "18",
      fill: "none",
      stroke: "currentColor",
      "stroke-width": "2",
      "stroke-linecap": "round",
      "stroke-linejoin": "round",
    },
    [
      h("path", {
        d: "M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.3 1.51 4.04 3 5.5l7 7Z",
      }),
    ],
  );
}

export function IconAthlete(): VNode {
  return h(
    "svg",
    {
      viewBox: "0 0 24 24",
      width: "18",
      height: "18",
      fill: "none",
      stroke: "currentColor",
      "stroke-width": "2",
      "stroke-linecap": "round",
      "stroke-linejoin": "round",
    },
    [
      h("path", { d: "M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2" }),
      h("circle", { cx: "12", cy: "7", r: "4" }),
    ],
  );
}

export function IconAvatar(): VNode {
  return h(
    "svg",
    {
      viewBox: "0 0 24 24",
      width: "18",
      height: "18",
      fill: "none",
      stroke: "currentColor",
      "stroke-width": "2",
      "stroke-linecap": "round",
      "stroke-linejoin": "round",
    },
    [
      h("rect", { x: "2", y: "4", width: "20", height: "16", rx: "2" }),
      h("circle", { cx: "8", cy: "10", r: "1.5", fill: "currentColor" }),
      h("path", { d: "M14 9h4" }),
      h("path", { d: "M14 13h2" }),
      h("path", { d: "M14 17h4" }),
    ],
  );
}

export function IconCoach(): VNode {
  return h(
    "svg",
    {
      viewBox: "0 0 24 24",
      width: "18",
      height: "18",
      fill: "none",
      stroke: "currentColor",
      "stroke-width": "2",
      "stroke-linecap": "round",
      "stroke-linejoin": "round",
    },
    [
      h("path", {
        d: "M9.5 18A2.5 2.5 0 0 1 7 15.5V11a2.5 2.5 0 0 1 5 0v4.5a2.5 2.5 0 0 1-2.5 2.5z",
      }),
      h("path", {
        d: "M14.5 18A2.5 2.5 0 0 1 12 15.5V11a2.5 2.5 0 0 1 5 0v4.5a2.5 2.5 0 0 1-2.5 2.5z",
      }),
      h("path", {
        d: "M17.5 9.5A2.5 2.5 0 0 1 20 7V4.5a2.5 2.5 0 0 1-5 0V7a2.5 2.5 0 0 1 2.5 2.5z",
      }),
      h("path", {
        d: "M6.5 9.5A2.5 2.5 0 0 1 9 7V4.5a2.5 2.5 0 0 1-5 0V7a2.5 2.5 0 0 1 2.5 2.5z",
      }),
    ],
  );
}

export function IconKnowledge(): VNode {
  return h(
    "svg",
    {
      viewBox: "0 0 24 24",
      width: "18",
      height: "18",
      fill: "none",
      stroke: "currentColor",
      "stroke-width": "2",
      "stroke-linecap": "round",
      "stroke-linejoin": "round",
    },
    [
      h("path", {
        d: "M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H19a1 1 0 0 1 1 1v18a1 1 0 0 1-1 1H6.5a2.5 2.5 0 0 1 0-5H20",
      }),
    ],
  );
}

export function IconBm2(): VNode {
  return h(
    "svg",
    {
      viewBox: "0 0 24 24",
      width: "18",
      height: "18",
      fill: "none",
      stroke: "currentColor",
      "stroke-width": "2",
      "stroke-linecap": "round",
      "stroke-linejoin": "round",
    },
    [h("polygon", { points: "13 2 3 14 12 14 11 22 21 10 12 10 13 2" })],
  );
}

export function IconPerformance(): VNode {
  return h(
    "svg",
    {
      viewBox: "0 0 24 24",
      width: "18",
      height: "18",
      fill: "none",
      stroke: "currentColor",
      "stroke-width": "2",
      "stroke-linecap": "round",
      "stroke-linejoin": "round",
    },
    [h("path", { d: "M3 3v18h18" }), h("path", { d: "M7 16l4-4 4 4 6-6" })],
  );
}

export function IconMap(): VNode {
  return h(
    "svg",
    {
      viewBox: "0 0 24 24",
      width: "18",
      height: "18",
      fill: "none",
      stroke: "currentColor",
      "stroke-width": "2",
      "stroke-linecap": "round",
      "stroke-linejoin": "round",
    },
    [
      h("polygon", { points: "1 6 1 22 8 18 16 22 21 18 21 2 16 6 8 2 1 6" }),
      h("line", { x1: "16", y1: "6", x2: "16", y2: "22" }),
      h("line", { x1: "8", y1: "2", x2: "8", y2: "18" }),
    ],
  );
}

export function IconAetherMap(): VNode {
  return h(
    "svg",
    {
      viewBox: "0 0 24 24",
      width: "18",
      height: "18",
      fill: "none",
      stroke: "currentColor",
      "stroke-width": "2",
      "stroke-linecap": "round",
      "stroke-linejoin": "round",
    },
    [
      h("circle", { cx: "12", cy: "12", r: "10" }),
      h("path", { d: "M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20" }),
      h("path", { d: "M2 12h20" }),
    ],
  );
}

export function IconPois(): VNode {
  return h(
    "svg",
    {
      viewBox: "0 0 24 24",
      width: "18",
      height: "18",
      fill: "none",
      stroke: "currentColor",
      "stroke-width": "2",
      "stroke-linecap": "round",
      "stroke-linejoin": "round",
    },
    [
      h("path", { d: "M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0Z" }),
      h("circle", { cx: "12", cy: "10", r: "3" }),
    ],
  );
}

export function IconItinerary(): VNode {
  return h(
    "svg",
    {
      viewBox: "0 0 24 24",
      width: "18",
      height: "18",
      fill: "none",
      stroke: "currentColor",
      "stroke-width": "2",
      "stroke-linecap": "round",
      "stroke-linejoin": "round",
    },
    [
      h("path", { d: "M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0z" }),
      h("circle", { cx: "12", cy: "10", r: "3" }),
    ],
  );
}

export function IconHeatmap(): VNode {
  return h(
    "svg",
    {
      viewBox: "0 0 24 24",
      width: "18",
      height: "18",
      fill: "none",
      stroke: "currentColor",
      "stroke-width": "2",
      "stroke-linecap": "round",
      "stroke-linejoin": "round",
    },
    [
      h("path", {
        d: "M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83",
      }),
    ],
  );
}

export function IconMetabolism(): VNode {
  return h(
    "svg",
    {
      viewBox: "0 0 24 24",
      width: "18",
      height: "18",
      fill: "none",
      stroke: "currentColor",
      "stroke-width": "2",
      "stroke-linecap": "round",
      "stroke-linejoin": "round",
    },
    [
      h("path", {
        d: "M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.3 1.51 4.04 3 5.5l7 7z",
      }),
    ],
  );
}

export function IconGranfondo(): VNode {
  return h(
    "svg",
    {
      viewBox: "0 0 24 24",
      width: "18",
      height: "18",
      fill: "none",
      stroke: "currentColor",
      "stroke-width": "2",
      "stroke-linecap": "round",
      "stroke-linejoin": "round",
    },
    [
      h("path", {
        d: "M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z",
      }),
      h("line", { x1: "4", y1: "22", x2: "4", y2: "15" }),
    ],
  );
}

export function IconZones(): VNode {
  return h(
    "svg",
    {
      viewBox: "0 0 24 24",
      width: "18",
      height: "18",
      fill: "none",
      stroke: "currentColor",
      "stroke-width": "2",
      "stroke-linecap": "round",
      "stroke-linejoin": "round",
    },
    [
      h("circle", { cx: "12", cy: "12", r: "10" }),
      h("path", { d: "M12 6v6l4 2" }),
    ],
  );
}

export function IconWeather(): VNode {
  return h(
    "svg",
    {
      viewBox: "0 0 24 24",
      width: "18",
      height: "18",
      fill: "none",
      stroke: "currentColor",
      "stroke-width": "2",
      "stroke-linecap": "round",
      "stroke-linejoin": "round",
    },
    [h("path", { d: "M17.5 19H9a7 7 0 1 1 6.71-9h1.79a4.5 4.5 0 1 1 0 9z" })],
  );
}

export function IconComparison(): VNode {
  return h(
    "svg",
    {
      viewBox: "0 0 24 24",
      width: "18",
      height: "18",
      fill: "none",
      stroke: "currentColor",
      "stroke-width": "2",
      "stroke-linecap": "round",
      "stroke-linejoin": "round",
    },
    [
      h("path", { d: "m16 16 3-8 3 8c-.87.65-1.92 1-3 1s-2.13-.35-3-1Z" }),
      h("path", { d: "m2 16 3-8 3 8c-.87.65-1.92 1-3 1s-2.13-.35-3-1Z" }),
      h("path", { d: "M7 21h10" }),
      h("path", { d: "M12 3v18" }),
      h("path", { d: "M3 7h2v2H3z" }),
      h("path", { d: "M19 7h2v2h-2z" }),
    ],
  );
}

export function IconBadges(): VNode {
  return h(
    "svg",
    {
      viewBox: "0 0 24 24",
      width: "18",
      height: "18",
      fill: "none",
      stroke: "currentColor",
      "stroke-width": "2",
      "stroke-linecap": "round",
      "stroke-linejoin": "round",
    },
    [
      h("circle", { cx: "12", cy: "8", r: "7" }),
      h("polyline", { points: "10.5 21 12 17 13.5 21" }),
      h("polyline", { points: "7 12 9 8 11 12" }),
      h("polyline", { points: "13 12 15 8 17 12" }),
    ],
  );
}
