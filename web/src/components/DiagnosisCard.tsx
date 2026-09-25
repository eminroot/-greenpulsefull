import {
  AlertTriangle,
  EyeOff,
  HelpCircle,
  Leaf,
  Maximize2,
  Moon,
  Sun,
  type LucideIcon,
} from 'lucide-react';
import type { Capture, Diagnosis } from '../types';
import { useT } from '../i18n';
import { timeAgo } from '../format';
import { withAlpha } from './visuals';

// A runner-up below this is noise, not something to mention.
const SHOW_ALTERNATIVE_FROM = 0.05;

const UNREADABLE_ICON: Record<string, LucideIcon> = {
  too_dark: Moon,
  overexposed: Sun,
  no_leaf: EyeOff,
  too_small: Maximize2,
};

const DANGER = '#dc2626';
const WARNING = '#d97706';
const HEALTHY = '#10b981';

/**
 * What the leaf model saw: the disease, how sure it is and what to do today.
 * Renders nothing for records without a diagnosis (older nodes, the
 * placeholder model).
 */
export function DiagnosisCard({ capture, lastLeaf }: { capture: Capture; lastLeaf?: Capture | null }) {
  const { t } = useT();
  const latest = capture.diagnosis;
  if (!latest) return null;

  // The newest photo was unreadable but an earlier one was not: lead with the
  // finding that still stands, and say the newest frame could not be read.
  const shown = latest.status === 'unreadable' && lastLeaf?.diagnosis ? lastLeaf : capture;
  const diagnosis = shown.diagnosis as Diagnosis;
  const stale = shown !== capture;
  const accent = accentFor(diagnosis);

  return (
    <div className="card" style={{ borderColor: withAlpha(accent, 0.3) }}>
      <span className="overline">
        {t('diag.overline')}
        {diagnosis.crop ? `  ·  ${t(`crop.${diagnosis.crop}`)}` : ''}
      </span>
      {stale ? (
        <div className="muted" style={{ fontSize: 12.5, marginTop: 8 }}>
          {t('diag.lastRead', { when: timeAgo(shown.captured_at) })}
        </div>
      ) : null}

      <Verdict diagnosis={diagnosis} fromNode={shown.source === 'node'} />

      {stale && latest.reason ? (
        <div className="muted" style={{ fontSize: 12.5, marginTop: 12 }}>
          {t('diag.latestUnreadable', { reason: t(`unreadable.${latest.reason}`).toLowerCase() })}
        </div>
      ) : null}
    </div>
  );
}

function Verdict({ diagnosis, fromNode }: { diagnosis: Diagnosis; fromNode: boolean }) {
  const { t, tDisease } = useT();
  const accent = accentFor(diagnosis);
  const pct = (p: number | null) => Math.round((p ?? 0) * 100);

  if (diagnosis.status === 'unreadable') {
    const reason = diagnosis.reason ?? 'unknown';
    return (
      <>
        <Head
          icon={UNREADABLE_ICON[reason] ?? HelpCircle}
          accent={accent}
          title={t(`unreadable.${reason}`)}
          sub={t(`unreadableHint.${reason}`)}
        />
        {fromNode ? (
          <p className="t2" style={{ marginTop: 14, fontSize: 14.5, lineHeight: 1.5 }}>
            {t('diag.sensorsOnly')}
          </p>
        ) : null}
      </>
    );
  }

  if (diagnosis.uncertain) {
    return (
      <>
        <Head icon={HelpCircle} accent={accent} title={t('diag.uncertainTitle')} />
        <p className="t2" style={{ marginTop: 14, fontSize: 14.5, lineHeight: 1.5 }}>
          {t('diag.uncertainBody', { disease: tDisease(diagnosis.code), pct: pct(diagnosis.confidence) })}
        </p>
      </>
    );
  }

  const runnerUp = diagnosis.alternatives.find((a) => a.p >= SHOW_ALTERNATIVE_FROM);
  const adviceKey = `advice.${diagnosis.code}`;
  const advice = t(adviceKey);
  return (
    <>
      <Head
        icon={diagnosis.healthy ? Leaf : AlertTriangle}
        accent={accent}
        title={tDisease(diagnosis.code)}
        sub={t('diag.sure', { pct: pct(diagnosis.confidence) })}
      />
      {advice !== adviceKey ? (
        <p className="t2" style={{ marginTop: 14, fontSize: 14.5, lineHeight: 1.5 }}>
          {advice}
        </p>
      ) : null}
      {runnerUp ? (
        <div className="t2" style={{ fontSize: 12.5, marginTop: 10 }}>
          {t('diag.alsoPossible', { disease: tDisease(runnerUp.code), pct: pct(runnerUp.p) })}
        </div>
      ) : null}
      {!diagnosis.healthy ? (
        <div className="muted" style={{ fontSize: 12.5, marginTop: 8 }}>
          {t('diag.caveat')}
        </div>
      ) : null}
    </>
  );
}

function Head({ icon: Icon, accent, title, sub }: { icon: LucideIcon; accent: string; title: string; sub?: string }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 14, marginTop: 14 }}>
      <span
        className="dec-icon"
        style={{ background: withAlpha(accent, 0.16), borderColor: withAlpha(accent, 0.3), color: accent }}
      >
        <Icon size={24} />
      </span>
      <div style={{ flex: 1 }}>
        <div style={{ fontWeight: 600, fontSize: 18 }}>{title}</div>
        {sub ? <div style={{ fontSize: 12.5, color: accent, marginTop: 4 }}>{sub}</div> : null}
      </div>
    </div>
  );
}

function accentFor(d: Diagnosis): string {
  if (d.status === 'unreadable' || d.uncertain) return WARNING;
  return d.healthy ? HEALTHY : DANGER;
}
