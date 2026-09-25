import { View } from 'react-native';
import { Image } from 'expo-image';
import Animated, { FadeInDown } from 'react-native-reanimated';
import { colors, radius, riskColor, spacing } from '@/theme';
import { imageSource } from '@/api/client';
import type { Capture, SubScores } from '@/api/types';
import { METRICS } from '@/greenpulse/metrics';
import { useT } from '@/i18n/i18n-context';
import { formatDateTime } from '@/utils/format';
import { Card } from './ui/card';
import { Txt } from './ui/text';
import { Icon } from './ui/icon';
import { RiskBadge, withAlpha } from './ui/risk-badge';
import { GpssGauge } from './gpss-gauge';
import { DecisionCard } from './decision-card';
import { DiagnosisCard } from './diagnosis-card';
import { KeyValue } from './key-value';
import { STRESS_SYMBOL } from '@/greenpulse';

// Weights match server/app/engine/gpss.py. When a probe is missing the server
// renormalises over what is left, which is why an absent input is labelled here
// rather than drawn as a zero bar.
const SUB_META: {
  key: keyof SubScores;
  labelKey: string;
  weight: string;
  color: string;
}[] = [
  { key: 'damage_score', labelKey: 'result.leafDamage', weight: '40%', color: '#F87171' },
  { key: 'water_score', labelKey: 'stress.Water Stress', weight: '30%', color: '#38BDF8' },
  { key: 'thermal_score', labelKey: 'stress.Heat Stress', weight: '15%', color: '#FB923C' },
  { key: 'light_score', labelKey: 'stress.Light Stress', weight: '15%', color: '#FACC15' },
];

interface Props {
  capture: Capture;
  /** A local file uri, when the photo is still on the phone from this scan. */
  imageUri?: string;
}

export function ResultDetails({ capture, imageUri }: Props) {
  const { t, tStress, tCaptureReason } = useT();

  // A scan just taken is still on the phone; anything else is fetched from
  // the server, which needs the auth header attached.
  const photo = imageUri ? { uri: imageUri } : imageSource(capture.image_url);
  const reading = capture.reading;
  const fromPhone = capture.source === 'phone';

  const sensors: { key: keyof typeof METRICS; value: number | null }[] = [
    { key: 'soil_moisture', value: reading?.soil_moisture ?? null },
    { key: 'temperature', value: reading?.temperature ?? null },
    { key: 'humidity', value: reading?.humidity ?? null },
    { key: 'light', value: reading?.light ?? null },
  ];

  return (
    <View style={{ gap: spacing.lg }}>
      {/* summary */}
      <Animated.View entering={FadeInDown.duration(450)}>
        <Card padding={spacing.xl} radius={28}>
          {photo ? (
            <View style={{ alignItems: 'center', marginBottom: spacing.md }}>
              <Image
                source={photo}
                style={{ width: 120, height: 120, borderRadius: radius.lg }}
                contentFit="cover"
              />
            </View>
          ) : null}

          <View style={{ alignItems: 'center' }}>
            <GpssGauge
              score={capture.gpss_score}
              risk={capture.gpss_risk_level}
              stressType={capture.stress_type}
            />
          </View>

          <View
            style={{
              flexDirection: 'row',
              alignItems: 'center',
              gap: 8,
              alignSelf: 'center',
              marginTop: spacing.sm,
              paddingVertical: 7,
              paddingHorizontal: 12,
              borderRadius: radius.pill,
              backgroundColor: withAlpha(colors.mint, 0.12),
              borderWidth: 1,
              borderColor: withAlpha(colors.mint, 0.25),
            }}
          >
            <Icon
              name={fromPhone ? 'camera.fill' : 'antenna.radiowaves.left.and.right'}
              size={13}
              color={colors.mint}
            />
            <Txt variant="caption" color={colors.mint}>
              {fromPhone ? t('result.fromPhone') : t('result.fromNode')}
            </Txt>
          </View>
        </Card>
      </Animated.View>

      {/* key metrics */}
      <Animated.View entering={FadeInDown.duration(450).delay(80)}>
        <Card>
          <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
            <Icon
              name={STRESS_SYMBOL[capture.stress_type]}
              size={16}
              color={riskColor[capture.gpss_risk_level]}
            />
            <Txt variant="heading" style={{ flex: 1 }}>
              {tStress(capture.stress_type)}
            </Txt>
            <RiskBadge level={capture.gpss_risk_level} size="sm" />
          </View>
          <View style={{ flexDirection: 'row', marginTop: spacing.lg }}>
            <Metric
              label={t('result.leafRisk')}
              value={capture.risk_score != null ? `${Math.round(capture.risk_score)}` : '--'}
            />
            <Metric
              label={t('result.confidence')}
              value={
                capture.confidence != null ? `${Math.round(capture.confidence * 100)}%` : '--'
              }
            />
            <Metric label={t('result.score')} value={`${capture.gpss_score}`} />
          </View>

          {capture.label && !capture.diagnosis ? (
            <View
              style={{
                marginTop: spacing.lg,
                paddingTop: spacing.md,
                borderTopWidth: 1,
                borderTopColor: colors.border,
              }}
            >
              <Txt variant="overline">{t('result.finding')}</Txt>
              <Txt variant="bodyMedium" style={{ marginTop: 4 }}>
                {capture.label}
              </Txt>
            </View>
          ) : null}
        </Card>
      </Animated.View>

      {/* what the leaf model saw */}
      {capture.diagnosis ? (
        <Animated.View entering={FadeInDown.duration(450).delay(110)}>
          <DiagnosisCard capture={capture} />
        </Animated.View>
      ) : null}

      {/* decision */}
      <Animated.View entering={FadeInDown.duration(450).delay(140)}>
        <DecisionCard
          decision={capture.decision}
          actuator={capture.actuator}
          reason={tCaptureReason(capture)}
          notify={capture.notify_farmer}
          leafFinding={capture.diagnosis?.disease_found}
        />
      </Animated.View>

      {/* stress breakdown */}
      <Animated.View entering={FadeInDown.duration(450).delay(200)}>
        <Card>
          <Txt variant="overline">{t('result.breakdown')}</Txt>
          <View style={{ gap: spacing.md, marginTop: spacing.md }}>
            {SUB_META.map((s) => {
              const v = capture.sub_scores?.[s.key] ?? null;
              const missing = v == null;
              return (
                <View key={s.key} style={{ gap: 6, opacity: missing ? 0.5 : 1 }}>
                  <View style={{ flexDirection: 'row', justifyContent: 'space-between' }}>
                    <Txt variant="caption" color={colors.textSecondary}>
                      {t(s.labelKey)}
                      <Txt variant="caption" color={colors.textMuted}>
                        {'  '}· {t('result.weight', { w: s.weight })}
                      </Txt>
                    </Txt>
                    <Txt
                      variant="caption"
                      color={missing ? colors.textMuted : colors.text}
                      style={{ fontVariant: ['tabular-nums'] }}
                    >
                      {missing
                        ? t(s.key === 'damage_score' ? 'result.noLeafRead' : 'result.noSensor')
                        : v.toFixed(0)}
                    </Txt>
                  </View>
                  <View
                    style={{
                      height: 6,
                      borderRadius: 99,
                      backgroundColor: colors.surfaceHi,
                      overflow: 'hidden',
                    }}
                  >
                    {!missing ? (
                      <View
                        style={{
                          width: `${Math.max(2, Math.min(100, v))}%`,
                          height: '100%',
                          backgroundColor: s.color,
                        }}
                      />
                    ) : null}
                  </View>
                </View>
              );
            })}
          </View>
        </Card>
      </Animated.View>

      {/* conditions at the time of the reading */}
      <Animated.View entering={FadeInDown.duration(450).delay(260)}>
        <Card>
          <Txt variant="overline">{t('result.conditions')}</Txt>
          <View style={{ marginTop: spacing.sm }}>
            {sensors.map((s) => {
              const meta = METRICS[s.key];
              return (
                <KeyValue
                  key={s.key}
                  symbol={meta.symbol}
                  label={t(`metric.${s.key}`)}
                  value={
                    s.value != null
                      ? `${s.value.toFixed(meta.decimals)} ${meta.unit}`
                      : t('result.noSensor')
                  }
                />
              );
            })}
          </View>
        </Card>
      </Animated.View>

      {/* provenance */}
      <Animated.View entering={FadeInDown.duration(450).delay(320)}>
        <Card>
          <Txt variant="overline">{t('result.source')}</Txt>
          <View style={{ marginTop: spacing.sm }}>
            <KeyValue symbol="clock.fill" label={t('result.taken')} value={formatDateTime(capture.captured_at)} />
            {capture.inference_ms != null ? (
              <KeyValue
                symbol="bolt.fill"
                label={t('result.analysisTime')}
                value={`${Math.round(capture.inference_ms)} ms`}
              />
            ) : null}
            {capture.model_version ? (
              <KeyValue symbol="cpu" label={t('result.model')} value={capture.model_version} />
            ) : null}
          </View>
        </Card>
      </Animated.View>
    </View>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <View style={{ flex: 1, gap: 4 }}>
      <Txt variant="numeric" style={{ fontSize: 22, color: colors.text }}>
        {value}
      </Txt>
      <Txt variant="overline" style={{ fontSize: 9.5 }}>
        {label}
      </Txt>
    </View>
  );
}
