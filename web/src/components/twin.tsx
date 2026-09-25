import { useEffect, useRef, useState } from 'react';
import {
  Droplet,
  Droplets,
  Fan,
  Lightbulb,
  Sparkles,
  Zap,
  Coins,
  Cloud,
  Activity,
  Leaf,
  Sprout,
  ShieldCheck,
  CheckCircle2,
  Clock,
  FlaskConical,
  TrendingUp,
  type LucideIcon,
} from 'lucide-react';
import type { Sustainability } from '../types';
import { useT } from '../i18n';
import { withAlpha } from './visuals';
import { AnimatedNumber } from './anim';

// ---------- slider ----------
export function SliderControl({
  label,
  value,
  unit,
  min,
  max,
  step,
  ideal,
  tint,
  onChange,
}: {
  label: string;
  value: number;
  unit: string;
  min: number;
  max: number;
  step: number;
  ideal: [number, number];
  tint: string;
  onChange: (v: number) => void;
}) {
  const { t } = useT();
  const pct = ((value - min) / (max - min)) * 100;
  const ok = value >= ideal[0] && value <= ideal[1];

  return (
    <div className="twin-control">
      <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between' }}>
        <span className="t2" style={{ fontSize: 13.5, fontWeight: 500 }}>{label}</span>
        <span className="num" style={{ fontSize: 20, color: ok ? 'var(--text)' : '#fbbf24' }}>
          {value}
          <span className="muted" style={{ fontSize: 12.5, marginLeft: 3 }}>{unit}</span>
        </span>
      </div>
      <input
        className="twin-slider"
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        style={{ background: `linear-gradient(90deg, ${tint} ${pct}%, var(--surface-hi) ${pct}%)` }}
      />
      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
        <span className="muted" style={{ fontSize: 11 }}>{min}{unit}</span>
        <span className="muted" style={{ fontSize: 11 }}>{t('twin.ideal', { lo: ideal[0], hi: ideal[1], unit })}</span>
        <span className="muted" style={{ fontSize: 11 }}>{max}{unit}</span>
      </div>
    </div>
  );
}

// ---------- actuator matrix ----------
function ActuatorTile({
  name,
  hint,
  on,
  Icon,
}: {
  name: string;
  hint: string;
  on: boolean;
  Icon: LucideIcon;
}) {
  const { t } = useT();
  const color = on ? '#10b981' : '#dc2626';
  return (
    <div className={`actuator-tile${on ? ' on' : ''}`}>
      <span
        className="actuator-icon"
        style={{
          background: withAlpha(color, on ? 0.18 : 0.12),
          color,
          border: `1px solid ${withAlpha(color, 0.3)}`,
        }}
      >
        <Icon size={24} className={on ? 'spin-fan' : ''} />
      </span>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontWeight: 600, fontSize: 15.5 }}>{name}</div>
        <div className="muted" style={{ fontSize: 12 }}>{hint}</div>
      </div>
      <span style={{ fontSize: 11, fontWeight: 700, letterSpacing: 0.4, color }}>
        {on ? t('twin.on') : t('twin.off')}
      </span>
    </div>
  );
}

export function ActuatorMatrix({
  irrigation,
  ventilation,
  light,
}: {
  irrigation: boolean;
  ventilation: boolean;
  light: boolean;
}) {
  const { t } = useT();
  return (
    <div className="card">
      <span className="overline">{t('twin.actuatorMatrix')}</span>
      <p className="muted" style={{ fontSize: 12.5, marginTop: 6, lineHeight: 1.5 }}>
        {t('twin.actuatorProjected')}
      </p>
      <div className="grid grid-3" style={{ marginTop: 14 }}>
        <ActuatorTile name={t('twin.irrigationValve')} hint={t('twin.irrigationHint')} on={irrigation} Icon={Droplet} />
        <ActuatorTile name={t('twin.ventilationFan')} hint={t('twin.ventilationHint')} on={ventilation} Icon={Fan} />
        <ActuatorTile name={t('twin.growLight')} hint={t('twin.growLightHint')} on={light} Icon={Lightbulb} />
      </div>
    </div>
  );
}

// ---------- recommendations ----------
export function Recommendations({ items }: { items: string[] }) {
  const { t } = useT();
  return (
    <div className="card">
      <span className="overline">{t('twin.recommendations')}</span>
      <div className="col" style={{ gap: 10, marginTop: 14 }}>
        {items.map((key) => (
          <div key={key} style={{ display: 'flex', alignItems: 'flex-start', gap: 10 }}>
            <span style={{ color: 'var(--accent-text)', marginTop: 1 }}><Sparkles size={15} /></span>
            <span className="t2" style={{ fontSize: 14, lineHeight: 1.45 }}>{t(key)}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ---------- sustainability ----------
function MetricTile({
  Icon,
  label,
  value,
  color,
  format,
  decimals,
}: {
  Icon: LucideIcon;
  label: string;
  value: number;
  color: string;
  format?: (n: number) => string;
  decimals?: number;
}) {
  const prev = useRef(value);
  const [bump, setBump] = useState(false);
  useEffect(() => {
    if (value > prev.current) {
      setBump(true);
      const id = setTimeout(() => setBump(false), 720);
      prev.current = value;
      return () => clearTimeout(id);
    }
    prev.current = value;
  }, [value]);

  return (
    <div className={`metric-tile fade-up${bump ? ' bump' : ''}`}>
      <span className="metric-ico" style={{ background: withAlpha(color, 0.14), color }}>
        <Icon size={16} />
      </span>
      <div>
        <div className="num metric-value">
          <AnimatedNumber value={value} format={format} decimals={decimals} />
        </div>
        <div className="overline" style={{ fontSize: 9.5 }}>{label}</div>
      </div>
    </div>
  );
}

function SaveBar({ label, greenpulse, color }: { label: string; greenpulse: number; color: string }) {
  const { t } = useT();
  const [w, setW] = useState(0);
  useEffect(() => {
    const id = requestAnimationFrame(() => setW(greenpulse));
    return () => cancelAnimationFrame(id);
  }, [greenpulse]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
      <span className="t2" style={{ fontSize: 13 }}>{label}</span>
      <div className="compare-row">
        <span className="muted" style={{ width: 80, fontSize: 11.5 }}>{t('sus.traditional')}</span>
        <div className="bar" style={{ flex: 1 }}><span style={{ width: '2%', background: 'var(--surface-hi)' }} /></div>
        <span className="num" style={{ width: 44, textAlign: 'right', fontSize: 13, color: 'var(--text-muted)' }}>0%</span>
      </div>
      <div className="compare-row">
        <span style={{ width: 80, fontSize: 11.5, color, fontWeight: 600 }}>{t('sus.greenpulse')}</span>
        <div className="bar" style={{ flex: 1 }}>
          <span className="save-fill" style={{ width: `${w}%`, background: `linear-gradient(90deg, var(--primary), ${color})` }} />
        </div>
        <span className="num" style={{ width: 44, textAlign: 'right', fontSize: 13, color }}>
          <AnimatedNumber value={greenpulse} format={(n) => `${Math.round(n)}%`} />
        </span>
      </div>
    </div>
  );
}

export function SustainabilityPanel({ sus }: { sus: Sustainability }) {
  const { t } = useT();
  return (
    <div className="col">
      {/* head-to-head */}
      <div className="grid grid-2">
        <div className="card">
          <span className="overline">{t('sus.tradLabel')}</span>
          <div className="num" style={{ fontSize: 40, marginTop: 10, color: 'var(--text-muted)' }}>0%</div>
          <p className="muted" style={{ fontSize: 12.5, marginTop: 4 }}>{t('sus.tradDesc')}</p>
        </div>
        <div className="card glow" style={{ borderColor: 'var(--border-strong)' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span className="overline" style={{ color: 'var(--accent-text)' }}>{t('sus.gpLabel')}</span>
            <Leaf size={15} color="var(--accent-text)" />
          </div>
          <div style={{ display: 'flex', gap: 22, marginTop: 10, flexWrap: 'wrap' }}>
            <div>
              <div className="num" style={{ fontSize: 40, color: '#0ea5e9' }}>
                <AnimatedNumber value={sus.water_saved_pct} format={(n) => `${Math.round(n)}%`} />
              </div>
              <div className="overline" style={{ fontSize: 9.5 }}>{t('sus.waterSaved')}</div>
            </div>
            <div>
              <div className="num" style={{ fontSize: 40, color: '#65a30d' }}>
                <AnimatedNumber value={sus.energy_saved_pct} format={(n) => `${Math.round(n)}%`} />
              </div>
              <div className="overline" style={{ fontSize: 9.5 }}>{t('sus.energySaved')}</div>
            </div>
          </div>
          <p className="muted" style={{ fontSize: 12.5, marginTop: 6 }}>{t('sus.gpDesc')}</p>
        </div>
      </div>

      {/* bars */}
      <div className="card">
        <span className="overline">{t('sus.compare')}</span>
        <div className="col" style={{ gap: 16, marginTop: 16 }}>
          <SaveBar label={t('sus.waterSaved')} greenpulse={sus.water_saved_pct} color="#0ea5e9" />
          <SaveBar label={t('sus.energySaved')} greenpulse={sus.energy_saved_pct} color="#65a30d" />
        </div>
      </div>

      {/* metric grid */}
      <div className="grid grid-3 metric-grid">
        <MetricTile Icon={Droplet} label={t('sus.waterSaved')} value={sus.water_saved_pct} color="#0ea5e9" format={(n) => `${Math.round(n)}%`} />
        <MetricTile Icon={Zap} label={t('sus.energySaved')} value={sus.energy_saved_pct} color="#65a30d" format={(n) => `${Math.round(n)}%`} />
        <MetricTile Icon={Activity} label={t('sus.irrigationEvents')} value={sus.irrigation_events} color="#10b981" />
        <MetricTile Icon={TrendingUp} label={t('sus.autonomousActions')} value={sus.autonomous_actions} color="#d97706" />
        <MetricTile Icon={Coins} label={t('sus.costReduction')} value={sus.cost_reduction} color="#ea580c" format={(n) => `₺${Math.round(n).toLocaleString()}`} />
        <MetricTile Icon={Cloud} label={t('sus.co2')} value={sus.co2_kg} color="#10b981" format={(n) => `${Math.round(n)} kg`} />
        <MetricTile Icon={Droplets} label={t('sus.waterLiters')} value={sus.water_liters} color="#0ea5e9" format={(n) => `${Math.round(n).toLocaleString()} L`} />
        <MetricTile Icon={Sprout} label={t('sus.yield')} value={sus.yield_protected_pct} color="#16a34a" format={(n) => `${Math.round(n)}%`} />
        <MetricTile Icon={ShieldCheck} label={t('sus.disease')} value={sus.disease_risk_pct} color="#14b8a6" format={(n) => `${Math.round(n)}%`} />
        <MetricTile Icon={CheckCircle2} label={t('sus.manualChecks')} value={sus.manual_checks} color="#8b5cf6" />
        <MetricTile Icon={Clock} label={t('sus.labor')} value={sus.labor_hours} color="#d97706" format={(n) => `${Math.round(n)} h`} />
        <MetricTile Icon={FlaskConical} label={t('sus.fertilizer')} value={sus.fertilizer_saved_pct} color="#65a30d" format={(n) => `${Math.round(n)}%`} />
      </div>
    </div>
  );
}
