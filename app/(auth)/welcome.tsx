import { View } from 'react-native';
import { useRouter } from 'expo-router';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import Animated, { FadeIn, FadeInDown } from 'react-native-reanimated';
import { colors, spacing } from '@/theme';
import { ScreenBackground, Button, Txt, Icon, LogoMark } from '@/components/ui';
import { PulseLine } from '@/components/pulse-line';
import { withAlpha } from '@/components/ui/risk-badge';
import { useT } from '@/i18n/i18n-context';
import { useTheme } from '@/theme/theme-context';
import { ThemeToggle } from '@/components/theme-toggle';

export default function Welcome() {
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const { t } = useT();
  useTheme();

  const points = [
    { symbol: 'leaf.fill', key: 'welcome.point1' },
    { symbol: 'gauge.with.dots.needle.67percent', key: 'welcome.point2' },
    { symbol: 'bolt.fill', key: 'welcome.point3' },
  ];

  return (
    <ScreenBackground>
      <View style={{ flex: 1, paddingTop: insets.top + 24, paddingBottom: insets.bottom + 16, paddingHorizontal: spacing.xl }}>
        <View style={{ position: 'absolute', top: insets.top + 14, right: spacing.xl, zIndex: 10 }}>
          <ThemeToggle />
        </View>
        <Animated.View entering={FadeIn.duration(600)} style={{ alignItems: 'center', marginTop: spacing.xxxl }}>
          <View
            style={{
              width: 100,
              height: 100,
              borderRadius: 30,
              borderCurve: 'continuous',
              alignItems: 'center',
              justifyContent: 'center',
              backgroundColor: colors.surface,
              borderWidth: 1,
              borderColor: colors.borderStrong,
              boxShadow: `0 0 44px ${withAlpha(colors.primary, 0.35)}`,
            }}
          >
            <LogoMark size={66} />
          </View>
          <View style={{ flexDirection: 'row', marginTop: spacing.xl }}>
            <Txt variant="display" style={{ fontSize: 40 }}>
              Green
            </Txt>
            <Txt variant="display" color={colors.accentText} style={{ fontSize: 40 }}>
              Pulse
            </Txt>
          </View>
          <Txt variant="overline" style={{ marginTop: 6 }}>
            {t('welcome.tagline')}
          </Txt>
        </Animated.View>

        <Animated.View entering={FadeIn.duration(800).delay(220)} style={{ marginTop: spacing.xl }}>
          <PulseLine height={50} />
        </Animated.View>

        <View style={{ flex: 1, justifyContent: 'center', gap: spacing.lg }}>
          {points.map((h, i) => (
            <Animated.View
              key={h.key}
              entering={FadeInDown.duration(500).delay(360 + i * 110)}
              style={{ flexDirection: 'row', gap: 14, alignItems: 'center' }}
            >
              <View
                style={{
                  width: 46,
                  height: 46,
                  borderRadius: 14,
                  borderCurve: 'continuous',
                  alignItems: 'center',
                  justifyContent: 'center',
                  backgroundColor: withAlpha(colors.primary, 0.12),
                  borderWidth: 1,
                  borderColor: withAlpha(colors.primary, 0.2),
                }}
              >
                <Icon name={h.symbol} size={20} color={colors.accentText} />
              </View>
              <Txt variant="subtitle" style={{ flex: 1 }}>
                {t(h.key)}
              </Txt>
            </Animated.View>
          ))}
        </View>

        <Animated.View entering={FadeInDown.duration(500).delay(720)} style={{ gap: spacing.md }}>
          <Button label={t('welcome.create')} icon="arrow.right" onPress={() => router.push('/(auth)/sign-up')} />
          <Button label={t('welcome.have')} variant="ghost" onPress={() => router.push('/(auth)/sign-in')} />
        </Animated.View>
      </View>
    </ScreenBackground>
  );
}
