import { View } from 'react-native';
import { colors, radius, spacing } from '@/theme';
import { METRICS, inIdealRange, type MetricKey } from '@/greenpulse/metrics';
import { useT } from '@/i18n/i18n-context';
import { Card } from './ui/card';
import { Txt } from './ui/text';
import { Icon } from './ui/icon';
import { AnimatedNumber } from './ui/animated-number';
import { withAlpha } from './ui/risk-badge';

interface Props {
  metricKey: MetricKey;
  /** null when this probe is not wired on the greenhouse node. */
  value: number | null;
}

// A live sensor tile: value + unit, plus a range track that shows the ideal
// band and where the current reading sits inside the full sensor span.
//
// A probe that is not wired reads null, and the tile says so. It never shows a
// number the greenhouse did not measure.
export function SensorCard({ metricKey, value }: Props) {
  const { t, tMetric } = useT();
  const m = METRICS[metricKey];

  if (value == null) {
    return (
      <Card padding={spacing.lg} radius={radius.lg} style={{ flex: 1, opacity: 0.55 }}>
        <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
          <View
            style={{
              width: 30,
              height: 30,
              borderRadius: 10,
              borderCurve: 'continuous',
              alignItems: 'center',
              justifyContent: 'center',
              backgroundColor: withAlpha(colors.textMuted, 0.12),
            }}
          >
            <Icon name={m.symbol} size={16} color={colors.textMuted} />
          </View>
          <Txt variant="caption" color={colors.textSecondary} style={{ flex: 1 }}>
            {tMetric(metricKey)}
          </Txt>
        </View>

        <View style={{ marginTop: 14 }}>
          <Txt variant="numeric" style={{ fontSize: 28, color: colors.textMuted }}>
            --
          </Txt>
        </View>
        <Txt variant="caption" color={colors.textMuted} style={{ marginTop: 10, fontSize: 11.5 }}>
          {t('sensor.notWired')}
        </Txt>
      </Card>
    );
  }

  const ok = inIdealRange(metricKey, value);
  const span = m.max - m.min;
  const pos = Math.max(0, Math.min(1, (value - m.min) / span));
  const idealStart = Math.max(0, Math.min(1, (m.ideal[0] - m.min) / span));
  const idealWidth = Math.max(0, Math.min(1, (m.ideal[1] - m.min) / span)) - idealStart;
  const marker = ok ? colors.mint : colors.warning;

  return (
    <Card padding={spacing.lg} radius={radius.lg} style={{ flex: 1 }}>
      <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
        <View
          style={{
            width: 30,
            height: 30,
            borderRadius: 10,
            borderCurve: 'continuous',
            alignItems: 'center',
            justifyContent: 'center',
            backgroundColor: withAlpha(m.tint, 0.16),
          }}
        >
          <Icon name={m.symbol} size={16} color={m.tint} />
        </View>
        <Txt variant="caption" color={colors.textSecondary} style={{ flex: 1 }}>
          {tMetric(metricKey)}
        </Txt>
      </View>

      <View style={{ flexDirection: 'row', alignItems: 'baseline', gap: 3, marginTop: 14 }}>
        <AnimatedNumber
          value={value}
          decimals={m.decimals}
          variant="numeric"
          style={{ fontSize: 28, color: colors.text }}
        />
        <Txt variant="caption" color={colors.textMuted}>
          {m.unit}
        </Txt>
      </View>

      {/* range track */}
      <View
        style={{
          height: 6,
          borderRadius: 99,
          backgroundColor: colors.surfaceHi,
          marginTop: 14,
          overflow: 'hidden',
        }}
      >
        <View
          style={{
            position: 'absolute',
            left: `${idealStart * 100}%`,
            width: `${idealWidth * 100}%`,
            top: 0,
            bottom: 0,
            backgroundColor: withAlpha(colors.mint, 0.35),
          }}
        />
      </View>
      <View
        style={{
          position: 'absolute',
          left: spacing.lg,
          right: spacing.lg,
          bottom: spacing.lg + 1,
        }}
        pointerEvents="none"
      >
        <View
          style={{
            position: 'absolute',
            left: `${pos * 100}%`,
            width: 4,
            height: 14,
            marginLeft: -2,
            marginTop: -4,
            borderRadius: 2,
            backgroundColor: marker,
            boxShadow: `0 0 8px ${marker}`,
          }}
        />
      </View>
    </Card>
  );
}
