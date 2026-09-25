// Per sensor presentation metadata: labels, units, and the comfortable band to
// draw on the range track.
//
// The ideal bands are the same numbers the server scores against
// (server/app/engine/gpss.py). They live here as well because the app draws the
// track before any reading arrives; if you calibrate them for a crop, change
// both.

export const IDEAL_SOIL_MOISTURE: [number, number] = [45, 70]; // %
export const IDEAL_TEMPERATURE: [number, number] = [18, 28]; // °C
export const IDEAL_HUMIDITY: [number, number] = [50, 75]; // %
export const IDEAL_LIGHT: [number, number] = [400, 800]; // lux

export type MetricKey = 'soil_moisture' | 'temperature' | 'humidity' | 'light';

export interface MetricMeta {
  key: MetricKey;
  label: string;
  short: string;
  unit: string;
  symbol: string;
  min: number;
  max: number;
  ideal: [number, number];
  decimals: number;
  step: number;
  tint: string;
}

export const METRICS: Record<MetricKey, MetricMeta> = {
  soil_moisture: {
    key: 'soil_moisture',
    label: 'Soil moisture',
    short: 'Soil',
    unit: '%',
    symbol: 'drop.fill',
    min: 0,
    max: 100,
    ideal: IDEAL_SOIL_MOISTURE,
    decimals: 0,
    step: 1,
    tint: '#38BDF8',
  },
  temperature: {
    key: 'temperature',
    label: 'Temperature',
    short: 'Temp',
    unit: '°C',
    symbol: 'thermometer.medium',
    min: -5,
    max: 45,
    ideal: IDEAL_TEMPERATURE,
    decimals: 1,
    step: 0.5,
    tint: '#FB923C',
  },
  humidity: {
    key: 'humidity',
    label: 'Humidity',
    short: 'Humidity',
    unit: '%',
    symbol: 'humidity.fill',
    min: 0,
    max: 100,
    ideal: IDEAL_HUMIDITY,
    decimals: 0,
    step: 1,
    tint: '#34D399',
  },
  light: {
    key: 'light',
    label: 'Light',
    short: 'Light',
    unit: 'lux',
    symbol: 'sun.max.fill',
    min: 0,
    max: 1500,
    ideal: IDEAL_LIGHT,
    decimals: 0,
    step: 10,
    tint: '#FACC15',
  },
};

export function inIdealRange(key: MetricKey, value: number): boolean {
  const [low, high] = METRICS[key].ideal;
  return value >= low && value <= high;
}

export const METRIC_KEYS: MetricKey[] = [
  'soil_moisture',
  'temperature',
  'humidity',
  'light',
];
