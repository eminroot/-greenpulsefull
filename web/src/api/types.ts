// Shapes the server returns. These mirror server/app/schemas.py, and match the
// mobile app's src/api/types.ts, because the panel and the phone read exactly
// the same data. If you change one, change all three.

export type RiskLevel = 'Low' | 'Medium' | 'High' | 'Critical';

export type StressType =
  | 'Healthy'
  | 'Water Stress'
  | 'Heat Stress'
  | 'Light Stress'
  | 'Tissue Damage';

export type DecisionCode =
  | 'MONITORING'
  | 'IRRIGATION_ON'
  | 'VENTILATION_ON'
  | 'SUPPLEMENTAL_LIGHT_ON'
  | 'ALERT_AGRONOMIST';

export type Actuator = 'NONE' | 'WATER_PUMP' | 'FAN' | 'GROW_LIGHT';

export type MetricKey = 'soil_moisture' | 'temperature' | 'humidity' | 'light';

export interface User {
  id: string;
  email: string;
  display_name: string | null;
  created_at: string;
}

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  expires_in: number;
  token_type: string;
  user: User;
}

export interface Site {
  id: string;
  name: string;
  slug: string;
  crop: string | null;
  created_at: string;
  device_count: number;
  online: boolean;
  last_capture_at: string | null;
}

export interface DeviceStatus {
  id: string;
  name: string;
  online: boolean;
  last_seen_at: string | null;
  model_version: string | null;
}

// A probe that is not wired reads null, never 0.
export interface Reading {
  recorded_at: string;
  soil_moisture: number | null;
  temperature: number | null;
  humidity: number | null;
  light: number | null;
  soil_raw: number | null;
}

export interface SubScores {
  damage_score: number | null;
  water_score: number | null;
  thermal_score: number | null;
  light_score: number | null;
}

// Which inputs the score was actually computed from.
export interface Signals {
  damage: boolean;
  water: boolean;
  thermal: boolean;
  light: boolean;
  humidity: boolean;
}

export interface DiagnosisAlternative {
  code: string;
  p: number;
}

// The leaf model's verdict, as codes; the panel owns the wording.
// status 'ok': code is a disease or 'healthy'. 'uncertain' means below the line
// where it counts as a finding. status 'unreadable': reason says why the photo
// could not be read (too_dark, overexposed, no_leaf, too_small).
export interface Diagnosis {
  status: 'ok' | 'unreadable';
  crop: string | null;
  code: string | null;
  confidence: number | null;
  healthy: boolean | null;
  uncertain: boolean;
  disease_found: boolean;
  reason: string | null;
  alternatives: DiagnosisAlternative[];
  model: string | null;
}

export interface Capture {
  id: string;
  site_id: string;
  node_capture_id: string;
  captured_at: string;
  received_at: string;
  source: 'node' | 'phone';

  // null when the node could not read the photo (night, no leaf in view)
  risk_score: number | null;
  risk_level: string | null;
  label: string | null;
  confidence: number | null;
  model_version: string | null;
  inference_ms: number | null;
  diagnosis: Diagnosis | null;

  gpss_score: number;
  gpss_risk_level: RiskLevel;
  stress_type: StressType;
  sub_scores: SubScores;
  signals: Signals;
  decision: DecisionCode;
  actuator: Actuator;
  notify_farmer: boolean;
  decision_reason: string;

  reading: Reading | null;
  image_url: string | null;
  image_width: number | null;
  image_height: number | null;
}

export interface Live {
  site: Site;
  capture: Capture | null;
  // Set only when the newest capture has no leaf verdict: the last one that did.
  last_leaf_capture: Capture | null;
  reading: Reading | null;
  devices: DeviceStatus[];
  online: boolean;
  stale: boolean;
  seconds_since_reading: number | null;
  server_time: string;
}

export interface Sustainability {
  irrigation_events: number;
  ventilation_events: number;
  light_events: number;
  autonomous_actions: number;
  alerts: number;
  captures: number;
  water_saved_pct: number;
  energy_saved_pct: number;
  cost_reduction: number;
  co2_kg: number;
  water_liters: number;
  yield_protected_pct: number;
  disease_risk_pct: number;
  manual_checks: number;
  labor_hours: number;
  fertilizer_saved_pct: number;
  since: string | null;
}

// The twin's what-if result. Same engine as a real reading.
export interface ScorePreview {
  gpss_score: number;
  risk_level: RiskLevel;
  stress_type: StressType;
  sub_scores: SubScores;
  signals: Signals;
  decision: DecisionCode;
  actuator: Actuator;
  notify_farmer: boolean;
  decision_reason: string;
}

// "Take a photo now": the greenhouse camera photographs the leaf off its
// schedule. kind 'photo' is a leaf photo taken with the phone app.
export type ScanKind = 'photo' | 'camera';

export interface ScanSubmitted {
  job_id: string;
  kind: ScanKind;
  status: string;
  queued_at: string;
  node_online: boolean;
  message: string | null;
}

export interface ScanStatus {
  job_id: string;
  kind: ScanKind;
  status: 'pending' | 'claimed' | 'done' | 'failed' | 'expired';
  capture: Capture | null;
  error: string | null;
}

export type StreamEvent =
  | { type: 'ready'; site_id: string; at: string }
  | { type: 'ping'; at: string }
  | { type: 'capture'; capture: Capture };
