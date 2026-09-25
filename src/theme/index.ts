// GreenPulse design tokens. Emerald canopy palette with a lime "pulse" accent.
// Supports a dark (default) and a clean light theme. Because React Native can't
// swap a static import at runtime, `colors` / `riskColor` are Proxies that read
// from the active palette; the ThemeProvider swaps it and re-renders consumers.

import type { RiskLevel } from '@/api/types';

export type Mode = 'dark' | 'light';

const dark = {
  // Canvas
  bg: '#08120D',
  bgElev: '#0C1812',
  surface: '#10211A',
  surface2: '#16291F',
  surfaceHi: '#1C3327',

  // Lines
  border: 'rgba(214, 248, 228, 0.08)',
  borderStrong: 'rgba(163, 230, 53, 0.28)',
  hairline: 'rgba(214, 248, 228, 0.06)',

  // Text
  text: '#EAF7EF',
  textSecondary: '#9FB7AB',
  textMuted: '#6C8579',
  textInverse: '#06120C',

  // Brand
  primary: '#10B981',
  primaryDeep: '#059669',
  accent: '#A3E635', // decorative lime (fills, gradients)
  accentSoft: '#BEF264',
  accentText: '#A3E635', // lime as text/icon (readable on dark)
  mint: '#34D399',

  // Risk scale
  riskLow: '#34D399',
  riskMedium: '#FBBF24',
  riskHigh: '#FB923C',
  riskCritical: '#F87171',

  // Utility
  danger: '#F87171',
  warning: '#FBBF24',
  white: '#FFFFFF',
  overlay: 'rgba(4, 9, 6, 0.72)',
  glassTint: 'rgba(18, 34, 26, 0.62)',
};

export type ThemeColors = typeof dark;

const light: ThemeColors = {
  bg: '#EEF3EF',
  bgElev: '#FFFFFF',
  surface: '#FFFFFF',
  surface2: '#F1F5F2',
  surfaceHi: '#E3EAE5',

  border: 'rgba(6, 40, 27, 0.12)',
  borderStrong: 'rgba(22, 101, 52, 0.32)',
  hairline: 'rgba(6, 40, 27, 0.08)',

  text: '#0E1F17',
  textSecondary: '#3C5249',
  textMuted: '#647A6E',
  textInverse: '#06120C',

  primary: '#10B981',
  primaryDeep: '#059669',
  accent: '#A3E635',
  accentSoft: '#BEF264',
  accentText: '#2F6D12', // dark green, readable on white
  mint: '#10B981',

  riskLow: '#10B981',
  riskMedium: '#D97706',
  riskHigh: '#EA580C',
  riskCritical: '#DC2626',

  danger: '#DC2626',
  warning: '#D97706',
  white: '#FFFFFF',
  overlay: 'rgba(18, 30, 24, 0.5)',
  glassTint: 'rgba(255, 255, 255, 0.72)',
};

const palettes: Record<Mode, ThemeColors> = { dark, light };
let active: ThemeColors = dark;

export function setThemeMode(mode: Mode) {
  active = palettes[mode];
}

// Runtime-swappable color access. `colors.text` resolves against the active
// palette at read time, so a re-render after a theme change yields new values.
export const colors = new Proxy({} as ThemeColors, {
  get: (_t, key: string) => (active as Record<string, string>)[key],
}) as ThemeColors;

const RISK_KEY: Record<RiskLevel, keyof ThemeColors> = {
  Low: 'riskLow',
  Medium: 'riskMedium',
  High: 'riskHigh',
  Critical: 'riskCritical',
};

export const riskColor = new Proxy({} as Record<RiskLevel, string>, {
  get: (_t, key: string) => active[RISK_KEY[key as RiskLevel]],
}) as Record<RiskLevel, string>;

// Brand gradients are vibrant on both themes, so they are not theme-swapped.
export const gradients = {
  brand: ['#10B981', '#A3E635'] as readonly [string, string],
  brandDeep: ['#0B3D2E', '#10B981'] as readonly [string, string],
  emerald: ['#059669', '#34D399'] as readonly [string, string],
  field: ['#0B1A13', '#08120D'] as readonly [string, string],
  pulse: ['#A3E635', '#34D399'] as readonly [string, string],
  riskLow: ['#10B981', '#34D399'] as readonly [string, string],
  riskMedium: ['#F59E0B', '#FBBF24'] as readonly [string, string],
  riskHigh: ['#F97316', '#FB923C'] as readonly [string, string],
  riskCritical: ['#DC2626', '#F87171'] as readonly [string, string],
};

export const riskGradient: Record<RiskLevel, readonly [string, string]> = {
  Low: gradients.riskLow,
  Medium: gradients.riskMedium,
  High: gradients.riskHigh,
  Critical: gradients.riskCritical,
};

export const spacing = {
  xs: 4,
  sm: 8,
  md: 12,
  lg: 16,
  xl: 24,
  xxl: 32,
  xxxl: 48,
} as const;

export const radius = {
  sm: 10,
  md: 16,
  lg: 22,
  xl: 28,
  pill: 999,
} as const;

export const font = {
  display: 'SpaceGrotesk_700Bold',
  displayMedium: 'SpaceGrotesk_600SemiBold',
  heading: 'SpaceGrotesk_500Medium',
  body: 'Inter_400Regular',
  bodyMedium: 'Inter_500Medium',
  bodySemibold: 'Inter_600SemiBold',
  bodyBold: 'Inter_700Bold',
  numeric: 'SpaceGrotesk_600SemiBold',
} as const;

export const shadow = {
  card: '0 18px 40px rgba(0, 0, 0, 0.45)',
  glow: '0 0 28px rgba(16, 185, 129, 0.35)',
  accentGlow: '0 0 32px rgba(163, 230, 53, 0.4)',
  soft: '0 6px 18px rgba(0, 0, 0, 0.3)',
} as const;
