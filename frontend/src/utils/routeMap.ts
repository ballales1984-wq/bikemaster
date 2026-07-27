/**
 * Utility for route map and risk segment coloring.
 *
 * `buildRidePolylines` raggruppa i segmenti per colore; `riskColor`,
 * `gradeRiskPercent`, `weatherRiskPercent` e `speedRiskPercent` mappano rischio
 * (gradient/conditions/speed) as percentage and color. `speedColor` colors
 * based on speed relative to the ride range; `escapeHtml` and
 * `formatDistance` sono helper di formattazione.
 */

import type { GpsPoint, RideSegment, EnrichedRide } from "../types/index";
import { RISK_COLORS, GRADE_COLORS, SPEED_COLORS } from "../constants";

export function buildRidePolylines(ride: {
  segments: RideSegment[];
}): { color: string; points: [number, number][] }[] {
  const groups: { color: string; points: [number, number][] }[] = [];
  let current: { color: string; points: [number, number][] } | null = null;

  for (const segment of ride.segments || []) {
    if (!current || current.color !== segment.color) {
      current = {
        color: segment.color,
        points: [segment.start],
      };
      groups.push(current);
    }
    current.points.push(segment.end);
  }

  return groups;
}

export function escapeHtml(value: unknown): string {
  return String(value ?? "").replace(
    /[&<>"']/g,
    (char) =>
      ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;",
      })[char] as string,
  );
}

export function riskColor(risk: number): string {
  if (risk < 25) return RISK_COLORS.LOW;
  if (risk < 50) return RISK_COLORS.MEDIUM;
  if (risk < 75) return RISK_COLORS.HIGH;
  return RISK_COLORS.SEVERE;
}

export function gradeRiskPercent(grade: number): number {
  const absGrade = Math.abs(grade);
  if (absGrade < 3) return 15;
  if (absGrade < 6) return 35;
  if (absGrade < 10) return 65;
  return 90;
}

export function weatherRiskPercent(score: number): number {
  if (!Number.isFinite(score)) return 50;
  if (score >= 8) return 10;
  if (score >= 5) return 45;
  return 85;
}

export function speedRiskPercent(speed: number | string): number {
  const spd = Number(speed) || 0;
  if (spd >= 25) return 15;
  if (spd >= 15) return 45;
  return 85;
}

export function formatDistance(meters: number = 0): string {
  return `${(meters / 1000).toFixed(2)} km`;
}

export function speedColor(ride: EnrichedRide, index: number): string {
  const points = ride.gps_points || [];
  if (index < points.length) {
    const speed = points[index].speed ?? null;
    if (speed === null) return "#4488ff";
    const speeds = points
      .map((p) => p.speed)
      .filter((s): s is number => s !== null && s !== undefined);
    if (!speeds.length) return "#4488ff";
    const minSpd = Math.min(...speeds);
    const maxSpd = Math.max(...speeds);
    if (maxSpd === minSpd) return "#ffff00";
    const ratio = (speed - minSpd) / (maxSpd - minSpd);
    if (ratio < 0.5) {
      const r = 255;
      const g = Math.round(255 * ratio * 2);
      return `#${r.toString(16).padStart(2, "0")}${g.toString(16).padStart(2, "0")}00`;
    }
    const r = Math.round(255 * (1 - (ratio - 0.5) * 2));
    const g = 255;
    return `#${r.toString(16).padStart(2, "0")}${g.toString(16).padStart(2, "0")}00`;
  }
  return "#4488ff";
}
