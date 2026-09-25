import type { RiskLevel, StressType } from '../types';
import { RISK_COLOR, RISK_GRADIENT } from '../constants';
import { useT } from '../i18n';

export function withAlpha(hex: string, a: number): string {
  const n = parseInt(hex.slice(1), 16);
  return `rgba(${(n >> 16) & 255}, ${(n >> 8) & 255}, ${n & 255}, ${a})`;
}

export function LogoMark({ size = 40 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 100 100">
      <defs>
        <linearGradient id="leafGrad" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#A3E635" />
          <stop offset="1" stopColor="#10B981" />
        </linearGradient>
      </defs>
      <path
        d="M50 8 C74 24 86 44 86 60 C86 76 70 92 50 92 C30 92 14 76 14 60 C14 44 26 24 50 8 Z"
        fill="url(#leafGrad)"
      />
      <path
        d="M50 16 L50 44 L44 56 L56 64 L48 78 L50 86"
        stroke="#06281b"
        strokeWidth={4.5}
        strokeLinejoin="round"
        strokeLinecap="round"
        fill="none"
      />
    </svg>
  );
}

export function Wordmark({ size = 22 }: { size?: number }) {
  return (
    <span className="brand" style={{ fontSize: size }}>
      Green<span className="accent">Pulse</span>
    </span>
  );
}

export function PulseLine({ height = 50 }: { height?: number }) {
  const d =
    'M0 30 L58 30 L68 30 L76 12 L84 48 L92 30 L150 30 L160 30 L168 14 L176 46 L184 30 L242 30 L252 30 L260 12 L268 48 L276 30 L320 30';
  return (
    <svg className="pulse-svg" width="100%" height={height} viewBox="0 0 320 60" preserveAspectRatio="none">
      <defs>
        <linearGradient id="pulseGrad" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0" stopColor="#a3e635" stopOpacity="0" />
          <stop offset="0.5" stopColor="#a3e635" stopOpacity="1" />
          <stop offset="1" stopColor="#a3e635" stopOpacity="0" />
        </linearGradient>
      </defs>
      <path className="pulse-track" d={d} strokeWidth={2.5} fill="none" strokeLinecap="round" strokeLinejoin="round" />
      <path className="pulse-run" d={d} strokeWidth={3.2} fill="none" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export function RiskBadge({ level }: { level: RiskLevel }) {
  const { tRisk } = useT();
  const c = RISK_COLOR[level];
  return (
    <span className="risk-badge" style={{ background: withAlpha(c, 0.14), border: `1px solid ${withAlpha(c, 0.35)}`, color: c }}>
      <span className="dot" style={{ background: c, boxShadow: `0 0 8px ${c}` }} />
      {tRisk(level)}
    </span>
  );
}

const SIZE = 220;
const STROKE = 16;
const R = (SIZE - STROKE) / 2 - 8;
const CX = SIZE / 2;
const C = 2 * Math.PI * R;
const ARC = C * 0.75;

export function Gauge({
  score,
  risk,
  stressType,
  subtitle,
}: {
  score: number;
  risk: RiskLevel;
  stressType?: StressType;
  subtitle?: string;
}) {
  const { t, tStress } = useT();
  const label = subtitle ?? (stressType ? tStress(stressType) : '');
  const progress = Math.max(0, Math.min(100, score)) / 100;
  const offset = ARC * (1 - progress);
  const grad = RISK_GRADIENT[risk];
  const gid = `gauge-${risk}`;

  return (
    <div className="gauge-wrap" style={{ width: SIZE, height: SIZE }}>
      <svg width={SIZE} height={SIZE}>
        <defs>
          <linearGradient id={gid} x1="0" y1="0" x2="1" y2="1">
            <stop offset="0" stopColor={grad[0]} />
            <stop offset="1" stopColor={grad[1]} />
          </linearGradient>
        </defs>
        <g transform={`rotate(135 ${CX} ${CX})`}>
          <circle className="gauge-track" cx={CX} cy={CX} r={R} strokeWidth={STROKE} fill="none" strokeLinecap="round" strokeDasharray={`${ARC} ${C}`} />
          <circle
            className="gauge-arc-value"
            cx={CX}
            cy={CX}
            r={R}
            stroke={`url(#${gid})`}
            strokeWidth={STROKE}
            fill="none"
            strokeLinecap="round"
            strokeDasharray={`${ARC} ${C}`}
            strokeDashoffset={offset}
          />
        </g>
      </svg>
      <div className="gauge-center">
        <span className="overline">{t('gauge.score')}</span>
        <div style={{ display: 'flex', alignItems: 'flex-start' }}>
          <span className="gauge-score">{score}</span>
          <span className="num" style={{ color: 'var(--text-muted)', fontSize: 18, marginTop: 8 }}>/100</span>
        </div>
        <RiskBadge level={risk} />
        <span style={{ color: RISK_COLOR[risk], fontSize: 12.5, marginTop: 2 }}>{label}</span>
      </div>
    </div>
  );
}

export function LineChart({ data, height = 170 }: { data: number[]; height?: number }) {
  const width = 640;
  const padX = 8;
  const padY = 16;
  const w = width - padX * 2;
  const h = height - padY * 2;
  const max = 100;

  const baseY = padY + h;
  const pts = data.length
    ? data.map((v, i) => ({
        x: padX + (data.length === 1 ? w / 2 : (i / (data.length - 1)) * w),
        y: baseY - (Math.max(0, Math.min(max, v)) / max) * h,
      }))
    : [];

  // A single reading becomes a flat "current level" line so the card looks
  // intentional rather than a lone dot.
  const linePts = pts.length === 1 ? [{ x: padX, y: pts[0].y }, { x: width - padX, y: pts[0].y }] : pts;
  const dotPts = pts.length === 1 ? [{ x: width - padX, y: pts[0].y }] : pts;

  const line = smooth(linePts);
  const area = linePts.length > 1 ? `${line} L ${linePts[linePts.length - 1].x} ${baseY} L ${linePts[0].x} ${baseY} Z` : '';

  return (
    <svg width="100%" viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none" style={{ display: 'block' }}>
      <defs>
        <linearGradient id="areaGrad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#10b981" stopOpacity="0.32" />
          <stop offset="1" stopColor="#10b981" stopOpacity="0" />
        </linearGradient>
      </defs>
      {[0.25, 0.5, 0.75].map((g) => (
        <line key={g} className="chart-grid" x1={padX} y1={padY + h * g} x2={width - padX} y2={padY + h * g} strokeWidth={1} />
      ))}
      {area ? <path d={area} fill="url(#areaGrad)" /> : null}
      {linePts.length > 1 ? <path d={line} stroke="#10b981" strokeWidth={3} fill="none" strokeLinecap="round" strokeLinejoin="round" /> : null}
      {dotPts.map((p, i) => (
        <circle key={i} className={i === dotPts.length - 1 ? undefined : 'chart-dot'} cx={p.x} cy={p.y} r={i === dotPts.length - 1 ? 5 : 3.2} fill={i === dotPts.length - 1 ? '#10b981' : undefined} stroke="#10b981" strokeWidth={2} />
      ))}
    </svg>
  );
}

function smooth(pts: { x: number; y: number }[]): string {
  if (pts.length === 0) return '';
  if (pts.length === 1) return `M ${pts[0].x} ${pts[0].y}`;
  let d = `M ${pts[0].x} ${pts[0].y}`;
  for (let i = 0; i < pts.length - 1; i++) {
    const p0 = pts[i === 0 ? 0 : i - 1];
    const p1 = pts[i];
    const p2 = pts[i + 1];
    const p3 = pts[i + 2 < pts.length ? i + 2 : i + 1];
    const c1x = p1.x + (p2.x - p0.x) / 6;
    const c1y = p1.y + (p2.y - p0.y) / 6;
    const c2x = p2.x - (p3.x - p1.x) / 6;
    const c2y = p2.y - (p3.y - p1.y) / 6;
    d += ` C ${c1x} ${c1y}, ${c2x} ${c2y}, ${p2.x} ${p2.y}`;
  }
  return d;
}
