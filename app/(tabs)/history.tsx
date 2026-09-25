import { useMemo } from 'react';
import { Alert, RefreshControl, View } from 'react-native';
import { Image } from 'expo-image';
import { useRouter } from 'expo-router';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import Animated, { FadeIn, FadeInDown } from 'react-native-reanimated';
import { colors, riskColor, spacing } from '@/theme';
import { ScreenBackground, Txt, Card, Icon, PressableScale } from '@/components/ui';
import { RiskBadge, withAlpha } from '@/components/ui/risk-badge';
import { LineChart } from '@/components/line-chart';
import { LogoMark } from '@/components/ui/logo';
import { imageSource } from '@/api/client';
import { useHistory } from '@/store/history-context';
import { STRESS_SYMBOL } from '@/greenpulse';
import { useT } from '@/i18n/i18n-context';
import { useTheme } from '@/theme/theme-context';
import { timeAgo } from '@/utils/format';

export default function History() {
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const { records, loading, refresh, clearAll } = useHistory();
  const { t, tStress, tDisease } = useT();
  useTheme();

  const chartData = useMemo(
    () => records.slice(0, 20).reverse().map((r) => r.gpss_score),
    [records]
  );
  const avg = useMemo(
    () => (records.length ? Math.round(records.reduce((s, r) => s + r.gpss_score, 0) / records.length) : 0),
    [records]
  );
  const criticals = useMemo(
    () => records.filter((r) => r.gpss_risk_level === 'Critical' || r.gpss_risk_level === 'High').length,
    [records]
  );

  const confirmClear = () => {
    Alert.alert(t('history.clearTitle'), t('history.clearMsg'), [
      { text: t('common.cancel'), style: 'cancel' },
      {
        text: t('history.clearConfirm'),
        style: 'destructive',
        onPress: () => {
          clearAll().catch(() => Alert.alert(t('history.title'), t('err.deleteFailed')));
        },
      },
    ]);
  };

  return (
    <ScreenBackground>
      <Animated.ScrollView
        showsVerticalScrollIndicator={false}
        refreshControl={
          <RefreshControl refreshing={loading} onRefresh={refresh} tintColor={colors.textMuted} />
        }
        contentContainerStyle={{
          paddingTop: insets.top + 12,
          paddingBottom: insets.bottom + 96,
          paddingHorizontal: spacing.xl,
          gap: spacing.lg,
        }}
      >
        <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }}>
          <View>
            <Txt variant="overline">{t('history.records')}</Txt>
            <Txt variant="title" style={{ marginTop: 4 }}>
              {t('history.title')}
            </Txt>
          </View>
          {records.length > 0 ? (
            <PressableScale haptic={false} onPress={confirmClear} style={{ padding: 8 }}>
              <Icon name="trash" size={18} color={colors.textMuted} />
            </PressableScale>
          ) : null}
        </View>

        {records.length === 0 ? (
          <Animated.View entering={FadeIn.duration(400)} style={{ alignItems: 'center', gap: spacing.md, paddingTop: spacing.xxxl }}>
            <View style={{ opacity: 0.5 }}>
              <LogoMark size={64} />
            </View>
            <Txt variant="heading">{t('history.empty')}</Txt>
            <Txt variant="body" center style={{ maxWidth: 260 }}>
              {t('history.emptySub')}
            </Txt>
            <PressableScale onPress={() => router.navigate('/(tabs)/scan')} style={{ marginTop: 6 }}>
              <View
                style={{
                  flexDirection: 'row',
                  alignItems: 'center',
                  gap: 8,
                  paddingVertical: 12,
                  paddingHorizontal: 20,
                  borderRadius: 99,
                  backgroundColor: withAlpha(colors.accent, 0.14),
                  borderWidth: 1,
                  borderColor: withAlpha(colors.accent, 0.3),
                }}
              >
                <Icon name="camera.viewfinder" size={16} color={colors.accentText} />
                <Txt variant="label" color={colors.accentText}>
                  {t('history.scan')}
                </Txt>
              </View>
            </PressableScale>
          </Animated.View>
        ) : (
          <>
            <Animated.View entering={FadeInDown.duration(500)}>
              <Card>
                <View style={{ flexDirection: 'row', justifyContent: 'space-between', marginBottom: spacing.md }}>
                  <Txt variant="overline">{t('history.trend')}</Txt>
                  <View style={{ flexDirection: 'row', gap: spacing.lg }}>
                    <Summary label={t('history.average')} value={`${avg}`} />
                    <Summary label={t('history.elevated')} value={`${criticals}`} color={criticals ? colors.riskHigh : colors.mint} />
                    <Summary label={t('history.total')} value={`${records.length}`} />
                  </View>
                </View>
                <LineChart data={chartData} color={colors.primary} />
              </Card>
            </Animated.View>

            <View style={{ gap: spacing.md }}>
              {records.map((r, i) => (
                <Animated.View key={r.id} entering={FadeInDown.duration(400).delay(Math.min(i, 8) * 50)}>
                  <PressableScale onPress={() => router.push(`/record/${r.id}`)}>
                    <Card padding={spacing.lg}>
                      <View style={{ flexDirection: 'row', alignItems: 'center', gap: 14 }}>
                        {r.image_url ? (
                          <Image
                            source={imageSource(r.image_url)}
                            style={{ width: 46, height: 46, borderRadius: 14 }}
                            contentFit="cover"
                          />
                        ) : (
                          <View
                            style={{
                              width: 46,
                              height: 46,
                              borderRadius: 14,
                              borderCurve: 'continuous',
                              alignItems: 'center',
                              justifyContent: 'center',
                              backgroundColor: withAlpha(riskColor[r.gpss_risk_level], 0.14),
                              borderWidth: 1,
                              borderColor: withAlpha(riskColor[r.gpss_risk_level], 0.28),
                            }}
                          >
                            <Icon name={STRESS_SYMBOL[r.stress_type]} size={20} color={riskColor[r.gpss_risk_level]} />
                          </View>
                        )}
                        <View style={{ flex: 1, gap: 4 }}>
                          <Txt variant="bodyMedium">
                            {r.diagnosis?.disease_found ? tDisease(r.diagnosis.code) : tStress(r.stress_type)}
                          </Txt>
                          <Txt variant="caption">
                            {t(r.source === 'phone' ? 'history.fromPhone' : 'history.fromNode')} · {timeAgo(r.captured_at)}
                          </Txt>
                        </View>
                        <View style={{ alignItems: 'flex-end', gap: 6 }}>
                          <Txt variant="numeric" style={{ fontSize: 22, color: colors.text }}>
                            {r.gpss_score}
                          </Txt>
                          <RiskBadge level={r.gpss_risk_level} size="sm" />
                        </View>
                      </View>
                    </Card>
                  </PressableScale>
                </Animated.View>
              ))}
            </View>
          </>
        )}
      </Animated.ScrollView>
    </ScreenBackground>
  );
}

function Summary({ label, value, color = colors.text }: { label: string; value: string; color?: string }) {
  return (
    <View style={{ alignItems: 'flex-end' }}>
      <Txt variant="numeric" style={{ fontSize: 16, color }}>
        {value}
      </Txt>
      <Txt variant="overline" style={{ fontSize: 9 }}>
        {label}
      </Txt>
    </View>
  );
}
