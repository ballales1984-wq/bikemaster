/**
 * Verifica della struttura e delle chiavi dei token del design system.
 *
 * Assicura che tutti i gruppi (colori, spaziature, raggi, ombre) e le
 * chiavi siano presenti e invariati rispetto a `tokens.ts`.
 */

import { describe, it, expect } from "vitest";
import { tokens } from "./tokens";

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
});
