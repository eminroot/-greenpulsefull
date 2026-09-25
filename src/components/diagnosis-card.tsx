import { View } from 'react-native';
import Animated, { FadeIn } from 'react-native-reanimated';
import { colors, radius } from '@/theme';
import type { Capture, Diagnosis } from '@/api/types';
import { useT } from '@/i18n/i18n-context';
import { timeAgo } from '@/utils/format';
import { Card } from './ui/card';
import { Txt } from './ui/text';
import { Icon } from './ui/icon';
import { withAlpha } from './ui/risk-badge';

// A runner-up below this is noise, not something to mention.
const SHOW_ALTERNATIVE_FROM = 0.05;

const UNREADABLE_SYMBOL: Record<string, string> = {
  too_dark: 'moon.fill',
  overexposed: 'sun.max.fill',
  no_leaf: 'eye.slash.fill',
  too_small: 'arrow.up.left.and.arrow.down.right',
};

interface Props {
  capture: Capture;
  /** On the dashboard at night: the last capture whose leaf could be read. */
  lastLeaf?: Capture | null;
}

/**
 * What the leaf model saw: the disease, how sure it is and what to do today.
 * Renders nothing for records without a diagnosis (older nodes, the
 * placeholder model), so callers can fall back to the raw label.
 */
export function DiagnosisCard({ capture, lastLeaf }: Props) {
  const { t } = useT();
  const latest = capture.diagnosis;
  if (!latest) return null;

  // The newest photo was unreadable but an earlier one was not: lead with the
  // finding that still stands, and say the newest frame could not be read.
  const shown = latest.status === 'unreadable' && lastLeaf?.diagnosis ? lastLeaf : capture;
  const diagnosis = shown.diagnosis as Diagnosis;
  const stale = shown !== capture;

  return (
    <Animated.View entering={FadeIn.duration(400)}>
      <Card borderColor={withAlpha(accentFor(diagnosis), 0.28)}>
        <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
          <Icon name="leaf.fill" size={15} color={colors.textMuted} />
          <Txt variant="overline" style={{ flex: 1 }}>
            {t('diag.overline')}
            {diagnosis.crop ? `  ·  ${t(`crop.${diagnosis.crop}`)}` : ''}
          </Txt>
        </View>

        {stale ? (
          <Txt variant="caption" color={colors.textMuted} style={{ marginTop: 8 }}>
            {t('diag.lastRead', { when: timeAgo(shown.captured_at) })}
          </Txt>
        ) : null}

        <Verdict diagnosis={diagnosis} fromNode={shown.source === 'node'} />

        {stale && latest.reason ? (
          <Txt variant="caption" color={colors.textMuted} style={{ marginTop: 12 }}>
            {t('diag.latestUnreadable', { reason: t(`unreadable.${latest.reason}`).toLowerCase() })}
          </Txt>
        ) : null}
      </Card>
    </Animated.View>
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
          symbol={UNREADABLE_SYMBOL[reason] ?? 'questionmark.circle.fill'}
          accent={accent}
          title={t(`unreadable.${reason}`)}
          sub={t(`unreadableHint.${reason}`)}
        />
        {fromNode ? (
          <Txt variant="body" style={{ marginTop: 14, lineHeight: 21 }}>
            {t('diag.sensorsOnly')}
          </Txt>
        ) : null}
      </>
    );
  }

  if (diagnosis.uncertain) {
    return (
      <>
        <Head symbol="questionmark.circle.fill" accent={accent} title={t('diag.uncertainTitle')} />
        <Txt variant="body" style={{ marginTop: 14, lineHeight: 21 }}>
          {t('diag.uncertainBody', {
            disease: tDisease(diagnosis.code),
            pct: pct(diagnosis.confidence),
          })}
        </Txt>
      </>
    );
  }

  const runnerUp = diagnosis.alternatives.find((a) => a.p >= SHOW_ALTERNATIVE_FROM);
  const adviceKey = `advice.${diagnosis.code}`;
  const advice = t(adviceKey);
  return (
    <>
      <Head
        symbol={diagnosis.healthy ? 'leaf.fill' : 'exclamationmark.triangle.fill'}
        accent={accent}
        title={tDisease(diagnosis.code)}
        sub={t('diag.sure', { pct: pct(diagnosis.confidence) })}
      />
      {advice !== adviceKey ? (
        <Txt variant="body" style={{ marginTop: 14, lineHeight: 21 }}>
          {advice}
        </Txt>
      ) : null}
      {runnerUp ? (
        <Txt variant="caption" color={colors.textSecondary} style={{ marginTop: 10 }}>
          {t('diag.alsoPossible', { disease: tDisease(runnerUp.code), pct: pct(runnerUp.p) })}
        </Txt>
      ) : null}
      {!diagnosis.healthy ? (
        <Txt variant="caption" color={colors.textMuted} style={{ marginTop: 10 }}>
          {t('diag.caveat')}
        </Txt>
      ) : null}
    </>
  );
}

function Head({ symbol, accent, title, sub }: { symbol: string; accent: string; title: string; sub?: string }) {
  return (
    <View style={{ flexDirection: 'row', alignItems: 'center', gap: 14, marginTop: 14 }}>
      <View
        style={{
          width: 52,
          height: 52,
          borderRadius: radius.md,
          borderCurve: 'continuous',
          alignItems: 'center',
          justifyContent: 'center',
          backgroundColor: withAlpha(accent, 0.16),
          borderWidth: 1,
          borderColor: withAlpha(accent, 0.3),
        }}
      >
        <Icon name={symbol} size={24} color={accent} />
      </View>
      <View style={{ flex: 1, gap: 3 }}>
        <Txt variant="heading">{title}</Txt>
        {sub ? (
          <Txt variant="caption" color={accent}>
            {sub}
          </Txt>
        ) : null}
      </View>
    </View>
  );
}

function accentFor(d: Diagnosis): string {
  if (d.status === 'unreadable' || d.uncertain) return colors.warning;
  return d.healthy ? colors.mint : colors.danger;
}
