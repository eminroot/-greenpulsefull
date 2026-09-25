// Presentation helpers shared by several screens.
//
// The scoring itself lives on the server now (server/app/engine/), so the app
// only needs to know how to draw what comes back.

export * from './metrics';

import type { RiskLevel, StressType } from '@/api/types';

export const RISK_ORDER: RiskLevel[] = ['Low', 'Medium', 'High', 'Critical'];

export const STRESS_SYMBOL: Record<StressType, string> = {
  Healthy: 'checkmark.seal.fill',
  'Water Stress': 'drop.fill',
  'Heat Stress': 'thermometer.sun.fill',
  'Light Stress': 'sun.max.fill',
  'Tissue Damage': 'exclamationmark.triangle.fill',
};
