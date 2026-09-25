import { View } from 'react-native';
import { BlurView } from 'expo-blur';
import * as Haptics from 'expo-haptics';
import type { BottomTabBarProps } from '@react-navigation/bottom-tabs';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import Animated, { FadeIn, FadeOut, LinearTransition } from 'react-native-reanimated';
import { colors, radius } from '@/theme';
import { useTheme } from '@/theme/theme-context';
import { useT } from '@/i18n/i18n-context';
import { Txt } from './ui/text';
import { Icon } from './ui/icon';
import { PressableScale } from './ui/pressable-scale';
import { withAlpha } from './ui/risk-badge';

const TABS: Record<string, { labelKey: string; symbol: string }> = {
  index: { labelKey: 'tab.pulse', symbol: 'waveform.path.ecg' },
  scan: { labelKey: 'tab.scan', symbol: 'camera.viewfinder' },
  sustainability: { labelKey: 'tab.sustainability', symbol: 'leaf.fill' },
  history: { labelKey: 'tab.history', symbol: 'chart.xyaxis.line' },
  settings: { labelKey: 'tab.settings', symbol: 'gearshape.fill' },
};

export function TabBar({ state, navigation }: BottomTabBarProps) {
  const insets = useSafeAreaInsets();
  const { t } = useT();
  const { mode } = useTheme();

  return (
    <View
      style={{
        position: 'absolute',
        left: 0,
        right: 0,
        bottom: 0,
        alignItems: 'center',
        paddingBottom: insets.bottom > 0 ? insets.bottom : 14,
      }}
      pointerEvents="box-none"
    >
      <BlurView
        tint={mode === 'dark' ? 'dark' : 'light'}
        intensity={40}
        style={{
          flexDirection: 'row',
          gap: 4,
          padding: 7,
          borderRadius: radius.pill,
          borderWidth: 1,
          borderColor: colors.border,
          backgroundColor: mode === 'dark' ? 'rgba(10,20,15,0.6)' : 'rgba(255,255,255,0.72)',
          overflow: 'hidden',
          boxShadow: mode === 'dark' ? '0 14px 34px rgba(0,0,0,0.5)' : '0 14px 34px rgba(6,40,27,0.18)',
        }}
      >
        {state.routes
          .filter((r) => TABS[r.name])
          .map((route) => {
            const index = state.routes.findIndex((r) => r.key === route.key);
            const focused = state.index === index;
            const tab = TABS[route.name];

            const onPress = () => {
              if (process.env.EXPO_OS === 'ios') Haptics.selectionAsync().catch(() => {});
              const event = navigation.emit({ type: 'tabPress', target: route.key, canPreventDefault: true });
              if (!focused && !event.defaultPrevented) {
                navigation.navigate(route.name);
              }
            };

            return (
              <PressableScale key={route.key} haptic={false} onPress={onPress} scaleTo={0.9}>
                <Animated.View
                  layout={LinearTransition.springify().damping(18).stiffness(220)}
                  style={{
                    flexDirection: 'row',
                    alignItems: 'center',
                    gap: 7,
                    height: 44,
                    paddingHorizontal: focused ? 15 : 12,
                    borderRadius: radius.pill,
                    backgroundColor: focused ? withAlpha(colors.primary, 0.16) : 'transparent',
                    borderWidth: 1,
                    borderColor: focused ? withAlpha(colors.accent, 0.3) : 'transparent',
                  }}
                >
                  <Icon
                    name={tab.symbol}
                    size={20}
                    color={focused ? colors.accentText : colors.textMuted}
                    weight={focused ? 'semibold' : 'regular'}
                  />
                  {focused ? (
                    <Animated.View entering={FadeIn.duration(180)} exiting={FadeOut.duration(120)}>
                      <Txt variant="label" color={colors.text} style={{ fontSize: 13.5 }}>
                        {t(tab.labelKey)}
                      </Txt>
                    </Animated.View>
                  ) : null}
                </Animated.View>
              </PressableScale>
            );
          })}
      </BlurView>
    </View>
  );
}
