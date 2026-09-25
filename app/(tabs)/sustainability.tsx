import { useCallback, useEffect, useRef, useState } from 'react';
import { RefreshControl, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import Animated, {
  FadeIn,
  FadeInDown,
  Easing,
  useAnimatedStyle,
  useSharedValue,
  withSequence,
  withTiming,
} from 'react-native-reanimated';
import { colors, radius, spacing } from '@/theme';
import { ScreenBackground, Txt, Card, Icon } from '@/components/ui';
import { withAlpha } from '@/components/ui/risk-badge';
import { AnimatedNumber } from '@/components/ui/animated-number';
import { SavingsRing } from '@/components/savings-ring';
import { api } from '@/api/client';
import type { Sustainability } from '@/api/types';
import { useGreenhouse } from '@/store/greenhouse-context';
import { useT } from '@/i18n/i18n-context';
import { useTheme } from '@/theme/theme-context';

export default function SustainabilityScreen() {
  const insets = useSafeAreaInsets();
  const { site, subscribe } = useGreenhouse();
  const { t } = useT();
  useTheme();

  // Counted on the server from the actions this greenhouse actually took.
  // Before it has taken any, every figure is zero, which is the truth.
  const [sus, setSus] = useState<Sustainability | null>(null);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    if (!site) return;
    setLoading(true);
    try {
      setSus(await api.get<Sustainability>(`/api/v1/sites/${site.id}/sustainability`));
    } catch {
      // keep whatever is on screen; the pull to refresh can try again
    } finally {
      setLoading(false);
    }
  }, [site?.id]);

  useEffect(() => {
    load();
  }, [load]);

  // A new reading may have triggered an actuator, which moves these numbers.
  useEffect(() => subscribe(() => load()), [subscribe, load]);

  const metrics = [
    { icon: 'drop.fill', label: t('sus.waterSaved'), value: sus?.water_saved_pct ?? 0, color: '#0EA5E9', suffix: '%' },
    { icon: 'bolt.fill', label: t('sus.energySaved'), value: sus?.energy_saved_pct ?? 0, color: '#65A30D', suffix: '%' },
    { icon: 'drop.circle.fill', label: t('sus.irrigationEvents'), value: sus?.irrigation_events ?? 0, color: '#10B981' },
    { icon: 'sparkles', label: t('sus.autonomousActions'), value: sus?.autonomous_actions ?? 0, color: '#D97706' },
    { icon: 'creditcard.fill', label: t('sus.costReduction'), value: sus?.cost_reduction ?? 0, color: '#EA580C', prefix: '₺', thousands: true },
    { icon: 'cloud.fill', label: t('sus.co2'), value: sus?.co2_kg ?? 0, color: '#10B981', suffix: ' kg' },
    { icon: 'drop.fill', label: t('sus.waterLiters'), value: sus?.water_liters ?? 0, color: '#0EA5E9', suffix: ' L', thousands: true },
    { icon: 'leaf.fill', label: t('sus.yield'), value: sus?.yield_protected_pct ?? 0, color: '#16A34A', suffix: '%' },
    { icon: 'cross.case.fill', label: t('sus.disease'), value: sus?.disease_risk_pct ?? 0, color: '#14B8A6', suffix: '%' },
    { icon: 'checkmark.circle.fill', label: t('sus.manualChecks'), value: sus?.manual_checks ?? 0, color: '#8B5CF6' },
    { icon: 'clock.fill', label: t('sus.labor'), value: sus?.labor_hours ?? 0, color: '#D97706', suffix: ' h' },
    { icon: 'leaf.circle.fill', label: t('sus.fertilizer'), value: sus?.fertilizer_saved_pct ?? 0, color: '#65A30D', suffix: '%' },
  ];

  return (
    <ScreenBackground>
      <Animated.ScrollView
        showsVerticalScrollIndicator={false}
        refreshControl={
          <RefreshControl refreshing={loading} onRefresh={load} tintColor={colors.textMuted} />
        }
        contentContainerStyle={{
          paddingTop: insets.top + 12,
          paddingBottom: insets.bottom + 96,
          paddingHorizontal: spacing.xl,
          gap: spacing.lg,
        }}
      >
        <Animated.View entering={FadeIn.duration(500)} style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }}>
          <View>
            <Txt variant="overline">{t('sus.simulator')}</Txt>
            <Txt variant="title" style={{ marginTop: 4 }}>
              {t('sus.title')}
            </Txt>
          </View>
          <View
            style={{
              flexDirection: 'row',
              alignItems: 'center',
              gap: 6,
              paddingVertical: 7,
              paddingHorizontal: 12,
              borderRadius: radius.pill,
              backgroundColor: colors.surface,
              borderWidth: 1,
              borderColor: colors.borderStrong,
            }}
          >
            <Icon name="leaf.fill" size={13} color={colors.accentText} />
            <Txt variant="caption" color={colors.accentText}>
              {t('sus.vsTraditional')}
            </Txt>
          </View>
        </Animated.View>

        {/* hero rings */}
        <Animated.View entering={FadeInDown.duration(600).delay(80)}>
          <Card padding={spacing.xl} radius={28} glow={withAlpha(colors.primary, 0.16)}>
            <Txt variant="caption" center color={colors.textSecondary}>
              {t('sus.subtitle')}
            </Txt>
            <View style={{ flexDirection: 'row', justifyContent: 'space-around', marginTop: spacing.lg }}>
              <SavingsRing value={sus?.water_saved_pct ?? 0} color="#38BDF8" label={t('sus.waterSaved')} />
              <SavingsRing value={sus?.energy_saved_pct ?? 0} color="#84CC16" label={t('sus.energySaved')} />
            </View>
          </Card>
        </Animated.View>

        {/* comparison */}
        <Animated.View entering={FadeInDown.duration(600).delay(160)}>
          <Card>
            <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }}>
              <Txt variant="overline">{t('sus.gpLabel')}</Txt>
              <Txt variant="caption" color={colors.textMuted}>
                {t('sus.tradLabel')} · {t('sus.tradDesc')}
              </Txt>
            </View>
            <View style={{ gap: spacing.lg, marginTop: spacing.lg }}>
              <SaveBar label={t('sus.waterSaved')} value={sus?.water_saved_pct ?? 0} color="#38BDF8" />
              <SaveBar label={t('sus.energySaved')} value={sus?.energy_saved_pct ?? 0} color="#84CC16" />
            </View>
          </Card>
        </Animated.View>

        {/* metric grid */}
        <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: spacing.md }}>
          {metrics.map((m, i) => (
            <MetricTile key={m.label + i} index={i} {...m} />
          ))}
        </View>
      </Animated.ScrollView>
    </ScreenBackground>
  );
}

function SaveBar({ label, value, color }: { label: string; value: number; color: string }) {
  const { t } = useT();
  const w = useSharedValue(0);
  useEffect(() => {
    w.value = withTiming(value, { duration: 950, easing: Easing.out(Easing.cubic) });
  }, [value, w]);
  const fill = useAnimatedStyle(() => ({ width: `${w.value}%` }));

  return (
    <View style={{ gap: 8 }}>
      <View style={{ flexDirection: 'row', justifyContent: 'space-between' }}>
        <Txt variant="caption" color={colors.textSecondary}>
          {label}
        </Txt>
        <AnimatedNumber value={value} suffix="%" variant="caption" color={color} />
      </View>
      <View style={{ height: 8, borderRadius: 99, backgroundColor: colors.surfaceHi, overflow: 'hidden' }}>
        <Animated.View style={[{ height: '100%', borderRadius: 99, backgroundColor: color }, fill]} />
      </View>
      <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6 }}>
        <View style={{ width: 6, height: 6, borderRadius: 99, backgroundColor: colors.textMuted }} />
        <Txt variant="caption" color={colors.textMuted} style={{ fontSize: 11 }}>
          {t('sus.traditional')} 0%
        </Txt>
      </View>
    </View>
  );
}

function MetricTile({
  icon,
  label,
  value,
  color,
  suffix,
  prefix,
  thousands,
  index,
}: {
  icon: string;
  label: string;
  value: number;
  color: string;
  suffix?: string;
  prefix?: string;
  thousands?: boolean;
  index: number;
}) {
  const prev = useRef(value);
  const scale = useSharedValue(1);
  useEffect(() => {
    if (value > prev.current) {
      scale.value = withSequence(withTiming(1.06, { duration: 160 }), withTiming(1, { duration: 280 }));
    }
    prev.current = value;
  }, [value, scale]);
  const style = useAnimatedStyle(() => ({ transform: [{ scale: scale.value }] }));

  return (
    <Animated.View entering={FadeInDown.duration(420).delay(index * 45)} style={[{ flexBasis: '46%', flexGrow: 1 }, style]}>
      <Card padding={spacing.lg}>
        <View
          style={{
            width: 32,
            height: 32,
            borderRadius: 10,
            borderCurve: 'continuous',
            alignItems: 'center',
            justifyContent: 'center',
            backgroundColor: withAlpha(color, 0.16),
          }}
        >
          <Icon name={icon} size={16} color={color} />
        </View>
        <AnimatedNumber
          value={value}
          variant="numeric"
          style={{ fontSize: 22, color: colors.text, marginTop: 12 }}
          suffix={suffix}
          prefix={prefix}
          thousands={thousands}
        />
        <Txt variant="overline" style={{ fontSize: 9.5, marginTop: 4 }}>
          {label}
        </Txt>
      </Card>
    </Animated.View>
  );
}
