/**
 * Verifica della struttura e delle chiavi dei token del design system.
 *
 * Assicura che tutti i gruppi (colori, spaziature, raggi, ombre) e le
 * chiavi siano presenti e invariati rispetto a `tokens.ts`.
 */

import { describe, it, expect } from "vitest";
import { tokens } from "./tokens";

function hexToRgb(hex: string): { r: number; g: number; b: number } | null {
  const m = hex
    .replace("#", "")
    .match(/^([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i);
  return m
    ? { r: parseInt(m[1], 16), g: parseInt(m[2], 16), b: parseInt(m[3], 16) }
    : null;
}

function luminance(r: number, g: number, b: number): number {
  const [rs, gs, bs] = [r, g, b].map((c) => {
    c = c / 255;
    return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * rs + 0.7152 * gs + 0.0722 * bs;
}

function contrastRatio(hex1: string, hex2: string): number {
  const a = hexToRgb(hex1);
  const b = hexToRgb(hex2);
  if (!a || !b) return 0;
  const l1 = luminance(a.r, a.g, a.b);
  const l2 = luminance(b.r, b.g, b.b);
  const lighter = Math.max(l1, l2);
  const darker = Math.min(l1, l2);
  return (lighter + 0.05) / (darker + 0.05);
}

describe("tokens module", () => {
  const expectedGroups = [
    "color",
    "font",
    "glassBlur",
    "radius",
    "shadow",
    "space",
    "transition",
  ];

  it("exports the expected top-level groups", () => {
    const actual = Object.keys(tokens).sort();
    expect(actual).toEqual(expectedGroups);
  });

  it("has the expected color keys", () => {
    const expected = [
      "primary",
      "secondary",
      "tertiary",
      "textPrimary",
      "textSecondary",
      "textMuted",
      "accent",
      "accentHover",
      "accentSecondary",
      "accentGradient",
      "border",
      "borderLight",
      "error",
      "warning",
      "success",
      "performance",
      "endurance",
      "efficiency",
      "recovery",
      "alert",
      "alertBg",
      "alertBorder",
      "calendar1",
      "calendar2",
      "calendar3",
      "panelBorder",
      "panelBorderHover",
      "panelBg",
      "legendEndurance",
      "legendThreshold",
      "legendSweetspot",
      "legendRecovery",
      "legendRace",
      "successStrong",
      "successText",
      "errorText",
    ].sort();

    const actual = Object.keys(tokens.color).sort();
    expect(actual).toEqual(expected);
  });

  it("has the expected space keys", () => {
    const expected = ["xs", "sm", "md", "lg", "xl", "xxl"].sort();
    const actual = Object.keys(tokens.space).sort();
    expect(actual).toEqual(expected);
  });

  it("has the expected radius keys", () => {
    const expected = ["default", "sm"];
    const actual = Object.keys(tokens.radius).sort();
    expect(actual).toEqual(expected);
  });

  it("has the expected shadow keys", () => {
    const expected = ["lg", "sm"];
    const actual = Object.keys(tokens.shadow).sort();
    expect(actual).toEqual(expected);
  });

  it("exposes glassBlur and transition as scalar values", () => {
    expect(tokens.glassBlur).toBe("12px");
    expect(tokens.transition).toBe("0.3s cubic-bezier(0.25, 0.8, 0.25, 1)");
  });

  it("meets WCAG AA contrast for primary text on primary background", () => {
    const ratio = contrastRatio(tokens.color.textPrimary, tokens.color.primary);
    expect(ratio).toBeGreaterThanOrEqual(4.5);
  });

  it("meets WCAG AA contrast for secondary text on primary background", () => {
    const ratio = contrastRatio(
      tokens.color.textSecondary,
      tokens.color.primary,
    );
    expect(ratio).toBeGreaterThanOrEqual(4.5);
  });

  it("meets WCAG AA contrast for accent on primary background", () => {
    const ratio = contrastRatio(tokens.color.accent, tokens.color.primary);
    expect(ratio).toBeGreaterThanOrEqual(4.5);
  });

  it("meets WCAG AA contrast for error text on primary background", () => {
    const ratio = contrastRatio(tokens.color.error, tokens.color.primary);
    expect(ratio).toBeGreaterThanOrEqual(4.5);
  });
});
