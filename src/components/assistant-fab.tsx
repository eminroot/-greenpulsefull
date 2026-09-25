import { View } from 'react-native';
import { useRouter, usePathname } from 'expo-router';
import { LinearGradient } from 'expo-linear-gradient';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import * as Haptics from 'expo-haptics';
import { colors, gradients } from '@/theme';
import { Icon } from './ui/icon';
import { PressableScale } from './ui/pressable-scale';
import { withAlpha } from './ui/risk-badge';

// Global "Ask GreenPulse" action. Floats above the tab bar on the right so it
// never overlaps the centered glass tab bar, and opens the assistant modal.
export function AssistantFab() {
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const pathname = usePathname();

  // The Scan tab has its own bottom capture controls; keep that area clear.
  if (pathname === '/scan') return null;

  return (
    <View
      pointerEvents="box-none"
      style={{
        position: 'absolute',
        right: 20,
        bottom: (insets.bottom > 0 ? insets.bottom : 14) + 78,
      }}
    >
      <PressableScale
        haptic={Haptics.ImpactFeedbackStyle.Medium}
        onPress={() => router.push('/assistant')}
        scaleTo={0.92}
        style={{ borderRadius: 99 }}
      >
        <LinearGradient
          colors={gradients.brand}
          start={{ x: 0, y: 0 }}
          end={{ x: 1, y: 1 }}
          style={{
            width: 58,
            height: 58,
            borderRadius: 99,
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: `0 8px 26px ${withAlpha(colors.primary, 0.5)}`,
          }}
        >
          <Icon name="sparkles" size={24} color={colors.textInverse} weight="semibold" />
        </LinearGradient>
      </PressableScale>
    </View>
  );
}
