import {
  Droplet,
  Droplets,
  Thermometer,
  Sun,
  Wind,
  Lightbulb,
  AlertTriangle,
  Eye,
  type LucideIcon,
} from 'lucide-react';
import type { Actuator, Capture, DecisionCode } from '../types';
import { METRICS, RISK_COLOR } from '../constants';
import { useT } from '../i18n';
import { withAlpha, RiskBadge } from './visuals';
import { AuthImage } from './AuthImage';
import { timeAgo } from '../format';

const METRIC_ICON: Record<string, LucideIcon> = {
  soil_moisture: Droplet,
  temperature: Thermometer,
  humidity: Droplets,
  light: Sun,
};

const DECISION_ICON: Record<DecisionCode, LucideIcon> = {
  MONITORING: Eye,
  IRRIGATION_ON: Droplet,
  VENTILATION_ON: Wind,
  SUPPLEMENTAL_LIGHT_ON: Lightbulb,
  ALERT_AGRONOMIST: AlertTriangle,
};

export function SensorCard({
  metricKey,
  value,
}: {
  metricKey: (typeof METRICS)[number]['key'];
  /** null when this probe is not wired on the greenhouse node. */
  value: number | null;
}) {
  const { t, tMetric } = useT();
  const m = METRICS.find((x) => x.key === metricKey)!;
  const Icon = METRIC_ICON[m.key];

  if (value == null) {
    return (
      <div className="card" style={{ opacity: 0.55 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span className="sensor-icon" style={{ background: withAlpha('#6c8579', 0.14) }}>
            <Icon size={16} color="var(--text-muted)" />
          </span>
          <span className="t2" style={{ fontSize: 12.5 }}>{tMetric(m.key)}</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'baseline', gap: 3, marginTop: 12 }}>
          <span className="num" style={{ fontSize: 28, color: 'var(--text-muted)' }}>--</span>
        </div>
        <div className="muted" style={{ fontSize: 11.5, marginTop: 10 }}>{t('sensor.notWired')}</div>
      </div>
    );
  }

  const ok = value >= m.ideal[0] && value <= m.ideal[1];
  const span = m.max - m.min;
  const pos = Math.max(0, Math.min(1, (value - m.min) / span));
  const idealStart = Math.max(0, Math.min(1, (m.ideal[0] - m.min) / span));
  const idealWidth = Math.max(0, Math.min(1, (m.ideal[1] - m.min) / span)) - idealStart;
  const marker = ok ? '#10b981' : '#d97706';

  return (
    <div className="card">
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <span className="sensor-icon" style={{ background: withAlpha(m.tint, 0.16) }}>
          <Icon size={16} color={m.tint} />
        </span>
        <span className="t2" style={{ fontSize: 12.5 }}>{tMetric(m.key)}</span>
      </div>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 3, marginTop: 12 }}>
        <span className="num" style={{ fontSize: 28 }}>{value.toFixed(m.decimals)}</span>
        <span className="muted" style={{ fontSize: 12.5 }}>{m.unit}</span>
      </div>
      <div className="range-track">
        <span className="range-ideal" style={{ left: `${idealStart * 100}%`, width: `${idealWidth * 100}%` }} />
      </div>
      <div style={{ position: 'relative', height: 0 }}>
        <span className="range-marker" style={{ left: `${pos * 100}%`, top: -10, background: marker, boxShadow: `0 0 8px ${marker}` }} />
      </div>
    </div>
  );
}

export function DecisionCard({
  decision,
  actuator,
  reason,
  notify,
  leafFinding,
}: {
  decision: DecisionCode;
  actuator: Actuator;
  reason: string;
  notify: boolean;
  /** The leaf model found a disease: the farmer was told about the leaf, not a critical score. */
  leafFinding?: boolean;
}) {
  const { t, tDecision, tActuator } = useT();
  const active = actuator !== 'NONE';
  const alert = decision === 'ALERT_AGRONOMIST';
  const accent = alert ? '#d97706' : active ? '#10b981' : '#6c8579';
  const Icon = DECISION_ICON[decision];

  return (
    <div className={`card${active ? ' glow' : ''}`} style={{ borderColor: active ? withAlpha(accent, 0.3) : 'var(--border)' }}>
      <span className="overline">{t('decision.title')}</span>
      <div style={{ display: 'flex', alignItems: 'center', gap: 14, marginTop: 14 }}>
        <span className="dec-icon" style={{ background: withAlpha(accent, 0.16), borderColor: withAlpha(accent, 0.3), color: accent }}>
          <Icon size={24} />
        </span>
        <div style={{ flex: 1 }}>
          <div style={{ fontWeight: 600, fontSize: 18 }}>{tDecision(decision)}</div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 4 }}>
            <span style={{ width: 7, height: 7, borderRadius: 99, background: active ? '#10b981' : '#6c8579', boxShadow: active ? '0 0 8px #10b981' : undefined }} />
            <span style={{ fontSize: 12.5, color: active ? '#10b981' : 'var(--text-muted)' }}>
              {active ? t('decision.on', { actuator: tActuator(actuator) }) : t('decision.none')}
            </span>
          </div>
        </div>
      </div>
      <p className="t2" style={{ marginTop: 14, fontSize: 14.5, lineHeight: 1.5 }}>{reason}</p>
      {notify ? (
        <div className="error-banner" style={{ marginTop: 14, background: withAlpha('#d97706', 0.12), borderColor: withAlpha('#d97706', 0.3), color: '#d97706' }}>
          <AlertTriangle size={15} />
          {t(leafFinding ? 'decision.notifiedLeaf' : 'decision.notified')}
        </div>
      ) : null}
    </div>
  );
}

export function PhotoCard({ record, onClick }: { record: Capture; onClick: () => void }) {
  const { t, tStress, tDisease } = useT();
  return (
    <div className="photo-card fade-up" onClick={onClick}>
      <div style={{ position: 'relative' }}>
        <AuthImage path={record.image_url} alt="Leaf scan" className="photo-img" />
        <div style={{ position: 'absolute', top: 10, left: 10 }}>
          <RiskBadge level={record.gpss_risk_level} />
        </div>
        <div style={{ position: 'absolute', bottom: 10, right: 12, fontFamily: 'var(--font-display)', fontWeight: 600, fontSize: 26, color: '#fff', textShadow: '0 2px 10px rgba(0,0,0,0.6)' }}>
          {record.gpss_score}
        </div>
      </div>
      <div className="photo-meta">
        <div style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
          <span style={{ width: 8, height: 8, borderRadius: 99, background: RISK_COLOR[record.gpss_risk_level] }} />
          <span style={{ fontWeight: 500, fontSize: 14 }}>
            {record.diagnosis?.disease_found ? tDisease(record.diagnosis.code) : tStress(record.stress_type)}
          </span>
        </div>
        <span className="muted" style={{ fontSize: 12 }}>
          {t(record.source === 'phone' ? 'src.phone' : 'src.node')} · {timeAgo(record.captured_at)}
        </span>
      </div>
    </div>
  );
}
