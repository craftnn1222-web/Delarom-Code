// Delarom mobile design tokens — a dark-fantasy palette that mirrors the web
// brand (candlelit gold on near-black, arcane violet for roleplay/magic, rose
// for danger). One cohesive system shared across every screen.

export const colors = {
  bg: "#0B0B0F",
  bgElevated: "#12121A",
  surface: "#181824",
  surfaceAlt: "#20202E",
  surfaceHover: "#262636",
  border: "#2C2C3C",
  borderStrong: "#3B3B50",

  textPrimary: "#F4F0E6",
  textSecondary: "#ADA9BC",
  textMuted: "#6F6C80",

  gold: "#E0A94F",
  goldSoft: "#F2CE84",
  goldDim: "rgba(224,169,79,0.14)",
  goldBorder: "rgba(224,169,79,0.35)",

  violet: "#A855F7",
  violetSoft: "#CBA2FF",
  violetDim: "rgba(168,85,247,0.14)",
  violetBorder: "rgba(168,85,247,0.35)",

  rose: "#E5484D",
  roseDim: "rgba(229,72,77,0.14)",
  green: "#3DD68C",
  greenDim: "rgba(61,214,140,0.14)",

  black: "#000000",
  white: "#FFFFFF",
  overlay: "rgba(0,0,0,0.6)",
};

export const spacing = {
  xs: 4,
  sm: 8,
  md: 16,
  lg: 24,
  xl: 32,
  xxl: 48,
};

export const radius = {
  sm: 8,
  md: 12,
  lg: 16,
  xl: 24,
  pill: 999,
};

export const typography = {
  display: { fontSize: 30, fontWeight: "800" as const, letterSpacing: 0.3 },
  h1: { fontSize: 24, fontWeight: "800" as const, letterSpacing: 0.3 },
  h2: { fontSize: 19, fontWeight: "700" as const, letterSpacing: 0.2 },
  h3: { fontSize: 16, fontWeight: "700" as const },
  body: { fontSize: 15, fontWeight: "400" as const },
  bodyStrong: { fontSize: 15, fontWeight: "600" as const },
  small: { fontSize: 13, fontWeight: "400" as const },
  tiny: { fontSize: 11, fontWeight: "600" as const, letterSpacing: 0.6 },
};

export const theme = { colors, spacing, radius, typography };
export type Theme = typeof theme;
