import { RefreshControl, View } from 'react-native';
import { useRouter } from 'expo-router';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import Animated, { FadeIn, FadeInDown } from 'react-native-reanimated';
import { colors, spacing } from '@/theme';
import { ScreenBackground, Txt, Card, Icon, PressableScale } from '@/components/ui';
import { GpssGauge } from '@/components/gpss-gauge';
import { SensorCard } from '@/components/sensor-card';
import { DecisionCard } from '@/components/decision-card';
import { DiagnosisCard } from '@/components/diagnosis-card';
import { CameraShotCard } from '@/components/camera-shot-card';
import { LinkPill } from '@/components/link-pill';
import { ThemeToggle } from '@/components/theme-toggle';
import { LiveDot } from '@/components/live-dot';
import { LogoMark } from '@/components/ui/logo';
import { withAlpha } from '@/components/ui/risk-badge';
import { useAuth } from '@/auth/auth-context';
import { useGreenhouse } from '@/store/greenhouse-context';
import { useT } from '@/i18n/i18n-context';
import { useTheme } from '@/theme/theme-context';
import { timeAgo } from '@/utils/format';

export default function Dashboard() {
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const { user } = useAuth();
  const { live, loading, error, link, refresh } = useGreenhouse();
  const { t, tCaptureReason } = useT();
  useTheme(); // re-render this screen's tree when the theme flips

  const firstName = user?.display_name?.split(' ')[0] || t('dash.grower');
  const capture = live?.capture ?? null;
  const reading = live?.reading ?? null;

  return (
    <ScreenBackground>
      <Animated.ScrollView
        showsVerticalScrollIndicator={false}
        refreshControl={
          <RefreshControl
            refreshing={loading}
            onRefresh={refresh}
            tintColor={colors.textMuted}
          />
        }
        contentContainerStyle={{
          paddingTop: insets.top + 12,
          paddingBottom: insets.bottom + 96,
          paddingHorizontal: spacing.xl,
          gap: spacing.xl,
        }}
      >
        {/* header */}
        <Animated.View
          entering={FadeIn.duration(500)}
          style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }}
        >
          <View>
            <Txt variant="overline">{t('dash.live')}</Txt>
            <Txt variant="title" style={{ marginTop: 4 }}>
              {t('dash.hello', { name: firstName })}
            </Txt>
          </View>
          <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
            <ThemeToggle />
            <LinkPill />
          </View>
        </Animated.View>

        {error ? (
          <Animated.View entering={FadeIn.duration(300)}>
            <Card padding={spacing.md} borderColor={withAlpha(colors.danger, 0.25)}>
              <View style={{ flexDirection: 'row', gap: 8, alignItems: 'center' }}>
                <Icon name="exclamationmark.triangle.fill" size={15} color={colors.danger} />
                <Txt variant="caption" color={colors.danger} style={{ flex: 1 }}>
                  {t(error)}
                </Txt>
              </View>
            </Card>
          </Animated.View>
        ) : null}

        {capture ? (
          <>
            {/* hero gauge */}
            <Animated.View entering={FadeInDown.duration(600).delay(80)}>
              <Card padding={spacing.xl} radius={28} glow={withAlpha(colors.primary, 0.18)}>
                <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8, alignSelf: 'center' }}>
                  {link === 'live' && !live?.stale ? <LiveDot /> : null}
                  <Txt variant="caption" color={colors.textSecondary}>
                    {live?.stale
                      ? t('dash.lastReport', { when: timeAgo(capture.captured_at) })
                      : t('dash.streamingFrom', { name: live?.site.name ?? '' })}
                  </Txt>
                </View>

                <View style={{ alignItems: 'center', marginTop: spacing.sm }}>
                  <GpssGauge
                    score={capture.gpss_score}
                    risk={capture.gpss_risk_level}
                    stressType={capture.stress_type}
                  />
                </View>

                <View style={{ flexDirection: 'row', justifyContent: 'space-around', marginTop: spacing.sm }}>
                  <MiniStat
                    symbol="leaf.fill"
                    label={t('dash.stat.leaf')}
                    value={capture.risk_score != null ? `${Math.round(capture.risk_score)}` : '--'}
                  />
                  <MiniStat
                    symbol="checkmark.seal.fill"
                    label={t('dash.stat.confidence')}
                    value={
                      capture.confidence != null
                        ? `${Math.round(capture.confidence * 100)}%`
                        : '--'
                    }
                  />
                  <MiniStat
                    symbol="clock.fill"
                    label={t('dash.stat.updated')}
                    value={timeAgo(capture.captured_at)}
                  />
                </View>
              </Card>
            </Animated.View>

            {/* what the leaf model saw */}
            {capture.diagnosis ? (
              <Animated.View entering={FadeInDown.duration(600).delay(120)}>
                <DiagnosisCard capture={capture} lastLeaf={live?.last_leaf_capture} />
              </Animated.View>
            ) : null}

            {/* sensors */}
            <Animated.View entering={FadeInDown.duration(600).delay(160)} style={{ gap: spacing.md }}>
              <Txt variant="overline">{t('dash.sensors')}</Txt>
              <View style={{ flexDirection: 'row', gap: spacing.md }}>
                <SensorCard metricKey="soil_moisture" value={reading?.soil_moisture ?? null} />
                <SensorCard metricKey="temperature" value={reading?.temperature ?? null} />
              </View>
              <View style={{ flexDirection: 'row', gap: spacing.md }}>
                <SensorCard metricKey="humidity" value={reading?.humidity ?? null} />
                <SensorCard metricKey="light" value={reading?.light ?? null} />
              </View>
            </Animated.View>

            {/* decision */}
            <Animated.View entering={FadeInDown.duration(600).delay(240)}>
              <DecisionCard
                decision={capture.decision}
                actuator={capture.actuator}
                reason={tCaptureReason(capture)}
                notify={capture.notify_farmer}
                leafFinding={capture.diagnosis?.disease_found}
              />
            </Animated.View>
          </>
        ) : (
          <WaitingForNode hasNode={!!live?.devices.length} />
        )}

        {/* the greenhouse camera, on request */}
        {live?.devices.length ? (
          <Animated.View entering={FadeInDown.duration(600).delay(280)}>
            <CameraShotCard />
          </Animated.View>
        ) : null}

        {/* scan CTA */}
        <Animated.View entering={FadeInDown.duration(600).delay(320)}>
          <PressableScale onPress={() => router.navigate('/(tabs)/scan')}>
            <Card padding={spacing.lg} borderColor={withAlpha(colors.accent, 0.25)}>
              <View style={{ flexDirection: 'row', alignItems: 'center', gap: 14 }}>
                <View
                  style={{
                    width: 46,
                    height: 46,
                    borderRadius: 14,
                    borderCurve: 'continuous',
                    alignItems: 'center',
                    justifyContent: 'center',
                    backgroundColor: withAlpha(colors.accent, 0.14),
                  }}
                >
                  <Icon name="camera.viewfinder" size={22} color={colors.accentText} />
                </View>
                <View style={{ flex: 1 }}>
                  <Txt variant="bodyMedium">{t('dash.scanLeaf')}</Txt>
                  <Txt variant="caption" style={{ marginTop: 2 }}>
                    {t('dash.scanLeafSub')}
                  </Txt>
                </View>
                <Icon name="chevron.right" size={16} color={colors.textMuted} />
              </View>
            </Card>
          </PressableScale>
        </Animated.View>
      </Animated.ScrollView>
    </ScreenBackground>
  );
}

// Shown until the greenhouse has actually reported something. The app would
// rather say nothing than show a number no sensor produced.
function WaitingForNode({ hasNode }: { hasNode: boolean }) {
  const router = useRouter();
  const { t } = useT();

  return (
    <Animated.View entering={FadeInDown.duration(600).delay(80)}>
      <Card padding={spacing.xl} radius={28}>
        <View style={{ alignItems: 'center', gap: spacing.md }}>
          <View style={{ opacity: 0.45 }}>
            <LogoMark size={56} />
          </View>
          <Txt variant="heading" center>
            {hasNode ? t('dash.waitingTitle') : t('dash.noNodeTitle')}
          </Txt>
          <Txt variant="body" center style={{ maxWidth: 280, lineHeight: 21 }}>
            {hasNode ? t('dash.waitingSub') : t('dash.noNodeSub')}
          </Txt>

          {!hasNode ? (
            <PressableScale
              onPress={() => router.navigate('/(tabs)/settings')}
              style={{ marginTop: 4 }}
            >
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
                <Icon name="antenna.radiowaves.left.and.right" size={16} color={colors.accentText} />
                <Txt variant="label" color={colors.accentText}>
                  {t('dash.pairNode')}
                </Txt>
              </View>
            </PressableScale>
          ) : null}
        </View>
      </Card>
    </Animated.View>
  );
}

function MiniStat({ symbol, label, value }: { symbol: string; label: string; value: string }) {
  return (
    <View style={{ alignItems: 'center', gap: 5 }}>
      <Icon name={symbol} size={15} color={colors.textMuted} />
      <Txt variant="numeric" style={{ fontSize: 15, color: colors.text }}>
        {value}
      </Txt>
      <Txt variant="overline" style={{ fontSize: 9.5 }}>
        {label}
      </Txt>
    </View>
  );
}
