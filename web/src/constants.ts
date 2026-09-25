import type {
  Actuator,
  DecisionCode,
  RiskLevel,
  StressType,
  SubScores,
} from './types';

export const IDEAL = {
  soil_moisture: [45, 70] as [number, number],
  temperature: [18, 28] as [number, number],
  humidity: [50, 75] as [number, number],
  light: [400, 800] as [number, number],
};

// Saturated enough to stay readable as text on BOTH the dark and light themes.
export const RISK_COLOR: Record<RiskLevel, string> = {
  Low: '#10b981',
  Medium: '#d97706',
  High: '#ea580c',
  Critical: '#dc2626',
};

export const RISK_GRADIENT: Record<RiskLevel, [string, string]> = {
  Low: ['#10B981', '#34D399'],
  Medium: ['#F59E0B', '#FBBF24'],
  High: ['#F97316', '#FB923C'],
  Critical: ['#DC2626', '#F87171'],
};

export const STRESS_LABEL: Record<StressType, string> = {
  Healthy: 'Healthy',
  'Water Stress': 'Water stress',
  'Heat Stress': 'Heat stress',
  'Light Stress': 'Light stress',
  'Tissue Damage': 'Tissue damage',
};

export const DECISION_LABEL: Record<DecisionCode, string> = {
  MONITORING: 'Monitoring',
  IRRIGATION_ON: 'Irrigation on',
  VENTILATION_ON: 'Ventilation on',
  SUPPLEMENTAL_LIGHT_ON: 'Grow light on',
  ALERT_AGRONOMIST: 'Alert agronomist',
};

export const ACTUATOR_LABEL: Record<Actuator, string> = {
  NONE: 'None',
  WATER_PUMP: 'Water pump',
  FAN: 'Ventilation fan',
  GROW_LIGHT: 'Grow light',
};

export const METRICS: {
  key: 'soil_moisture' | 'temperature' | 'humidity' | 'light';
  label: string;
  unit: string;
  min: number;
  max: number;
  ideal: [number, number];
  decimals: number;
  tint: string;
}[] = [
  { key: 'soil_moisture', label: 'Soil moisture', unit: '%', min: 0, max: 100, ideal: IDEAL.soil_moisture, decimals: 0, tint: '#38BDF8' },
  { key: 'temperature', label: 'Temperature', unit: '°C', min: -5, max: 45, ideal: IDEAL.temperature, decimals: 1, tint: '#FB923C' },
  { key: 'humidity', label: 'Humidity', unit: '%', min: 0, max: 100, ideal: IDEAL.humidity, decimals: 0, tint: '#34D399' },
  { key: 'light', label: 'Light', unit: 'lux', min: 0, max: 1500, ideal: IDEAL.light, decimals: 0, tint: '#FACC15' },
];

export const SUB_META: { key: keyof SubScores; label: string; weight: string; color: string }[] = [
  { key: 'damage_score', label: 'Leaf damage', weight: '40%', color: '#F87171' },
  { key: 'water_score', label: 'Water stress', weight: '30%', color: '#38BDF8' },
  { key: 'thermal_score', label: 'Heat stress', weight: '15%', color: '#FB923C' },
  { key: 'light_score', label: 'Light stress', weight: '15%', color: '#FACC15' },
];

export function reasonFor(decision: DecisionCode, score: number): string {
  switch (decision) {
    case 'IRRIGATION_ON':
      return `Soil moisture deficit detected (score ${score}).`;
    case 'VENTILATION_ON':
      return `Thermal stress detected (score ${score}).`;
    case 'SUPPLEMENTAL_LIGHT_ON':
      return `Light shortfall detected (score ${score}).`;
    case 'ALERT_AGRONOMIST':
      return `Visible tissue damage detected (score ${score}). Human inspection needed.`;
    default:
      return `Stress score ${score} is within a healthy range.`;
  }
}
