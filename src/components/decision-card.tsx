import { View } from 'react-native';
import Animated, { FadeIn } from 'react-native-reanimated';
import { colors, radius, spacing } from '@/theme';
import type { Actuator, DecisionCode } from '@/api/types';
import { useT } from '@/i18n/i18n-context';
import { Card } from './ui/card';
import { Txt } from './ui/text';
import { Icon } from './ui/icon';
import { withAlpha } from './ui/risk-badge';

const DECISION_SYMBOL: Record<DecisionCode, string> = {
  MONITORING: 'eye.fill',
  IRRIGATION_ON: 'drop.fill',
  VENTILATION_ON: 'wind',
  SUPPLEMENTAL_LIGHT_ON: 'lightbulb.fill',
  ALERT_AGRONOMIST: 'exclamationmark.triangle.fill',
};

interface Props {
  decision: DecisionCode;
  actuator: Actuator;
  reason: string;
  notify: boolean;
  /** The leaf model found a disease: the farmer was told about the leaf, not a critical score. */
  leafFinding?: boolean;
}

export function DecisionCard({ decision, actuator, reason, notify, leafFinding }: Props) {
  const { t, tDecision, tActuator } = useT();
  const active = actuator !== 'NONE';
  const alert = decision === 'ALERT_AGRONOMIST';
  const accent = alert ? colors.warning : active ? colors.primary : colors.textMuted;

  return (
    <Animated.View entering={FadeIn.duration(400)}>
      <Card glow={active ? withAlpha(accent, 0.45) : false} borderColor={active ? withAlpha(accent, 0.3) : colors.border}>
        <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
          <Icon name="cpu" size={15} color={colors.textMuted} />
          <Txt variant="overline">{t('decision.title')}</Txt>
        </View>

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
            <Icon name={DECISION_SYMBOL[decision]} size={24} color={accent} />
          </View>
          <View style={{ flex: 1 }}>
            <Txt variant="heading">{tDecision(decision)}</Txt>
            <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8, marginTop: 4 }}>
              <View
                style={{
                  width: 7,
                  height: 7,
                  borderRadius: 99,
                  backgroundColor: active ? colors.mint : colors.textMuted,
                  boxShadow: active ? `0 0 8px ${colors.mint}` : undefined,
                }}
              />
              <Txt variant="caption" color={active ? colors.mint : colors.textMuted}>
                {active ? t('decision.on', { actuator: tActuator(actuator) }) : t('decision.none')}
              </Txt>
            </View>
          </View>
        </View>

        <Txt variant="body" style={{ marginTop: 14, lineHeight: 21 }}>
          {reason}
        </Txt>

        {notify ? (
          <View
            style={{
              flexDirection: 'row',
              alignItems: 'center',
              gap: 8,
              marginTop: 14,
              padding: spacing.md,
              borderRadius: radius.md,
              borderCurve: 'continuous',
              backgroundColor: withAlpha(colors.warning, 0.1),
              borderWidth: 1,
              borderColor: withAlpha(colors.warning, 0.25),
            }}
          >
            <Icon name="bell.badge.fill" size={15} color={colors.warning} />
            <Txt variant="caption" color={colors.warning} style={{ flex: 1 }}>
              {t(leafFinding ? 'decision.notifiedLeaf' : 'decision.notified')}
            </Txt>
          </View>
        ) : null}
      </Card>
    </Animated.View>
  );
}
