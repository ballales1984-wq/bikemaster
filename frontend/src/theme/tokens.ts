/**
 * Token del design system.
 *
 * Specchia le custom property CSS in `src/styles/tokens.css` per
 * consentire riferimenti tipizzati da TypeScript senza stringhe magiche.
 */

export const tokens = {
  font: {
    family:
      "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
  },
  color: {
    primary: "#0a0b10",
    secondary: "rgba(22, 27, 40, 0.65)",
    tertiary: "rgba(30, 36, 51, 0.85)",
    textPrimary: "#f8f9fa",
    textSecondary: "#b0b5c1",
    textMuted: "#6e7687",
    accent: "#00ffcc",
    accentHover: "#00d6aa",
    accentSecondary: "#ff3366",
    accentGradient: "linear-gradient(135deg, #00ffcc 0%, #0088ff 100%)",
    border: "rgba(255, 255, 255, 0.08)",
    borderLight: "rgba(255, 255, 255, 0.15)",
    error: "#ff3366",
    warning: "#ffb800",
    success: "#00ffcc",
    performance: "#00ffcc",
    endurance: "#0088ff",
    efficiency: "#ff6b35",
    recovery: "#a855f7",
    alert: "#ff3366",
    alertBg: "rgba(255, 51, 102, 0.15)",
    alertBorder: "rgba(255, 51, 102, 0.4)",
    calendar1: "#1e2a4a",
    calendar2: "#111528",
    calendar3: "#1a2a3a",
    panelBorder: "rgba(0, 255, 204, 0.2)",
    panelBorderHover: "rgba(0, 255, 204, 0.25)",
    panelBg: "rgba(0, 255, 204, 0.08)",
    legendEndurance: "#3498db",
    legendThreshold: "#e74c3c",
    legendSweetspot: "#9b59b6",
    legendRecovery: "#2ecc71",
    legendRace: "#f39c12",
    successStrong: "#22c55e",
    successText: "#166534",
    errorText: "#991b1b",
  },
  space: {
    xs: "4px",
    sm: "8px",
    md: "12px",
    lg: "16px",
    xl: "20px",
    xxl: "24px",
  },
  radius: {
    default: "16px",
    sm: "8px",
  },
  shadow: {
    sm: "0 4px 12px rgba(0,0,0,0.2)",
    lg: "0 12px 32px rgba(0, 10, 20, 0.5)",
  },
  glassBlur: "12px",
  transition: "0.3s cubic-bezier(0.25, 0.8, 0.25, 1)",
} as const;

export type Tokens = typeof tokens;
export type TokenValue = Tokens[keyof Tokens];
