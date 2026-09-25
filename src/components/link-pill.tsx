import { View } from 'react-native';
import { useRouter } from 'expo-router';
import { colors, radius } from '@/theme';
import { useGreenhouse } from '@/store/greenhouse-context';
import { useT } from '@/i18n/i18n-context';
import { Txt } from './ui/text';
import { PressableScale } from './ui/pressable-scale';
import { withAlpha } from './ui/risk-badge';

// Says, honestly, where the numbers on screen are coming from:
//
//   Live      the phone holds an open connection and the greenhouse is reporting
//   Quiet     connected, but the node has not reported in a while
//   No node   connected, but no hardware has ever reported here
//   Offline   the phone cannot reach the server
//
// Tapping it opens Settings, which is where a node gets paired.
export function LinkPill() {
  const router = useRouter();
  const { link, live } = useGreenhouse();
  const { t } = useT();

  const config = (() => {
    if (link === 'offline') {
      return { color: colors.danger, label: t('link.offline') };
    }
    if (link === 'connecting') {
      return { color: colors.warning, label: t('link.connecting') };
    }
    if (!live?.devices.length) {
      return { color: colors.textMuted, label: t('link.noNode') };
    }
    if (!live.online || live.stale) {
      return { color: colors.warning, label: t('link.quiet') };
    }
    return { color: colors.mint, label: t('link.live') };
  })();

  return (
    <PressableScale haptic={false} onPress={() => router.navigate('/(tabs)/settings')}>
      <View
        style={{
          flexDirection: 'row',
          alignItems: 'center',
          gap: 7,
          paddingVertical: 7,
          paddingHorizontal: 12,
          borderRadius: radius.pill,
          backgroundColor: colors.surface,
          borderWidth: 1,
          borderColor: withAlpha(config.color, 0.3),
        }}
      >
        <View
          style={{
            width: 7,
            height: 7,
            borderRadius: 99,
            backgroundColor: config.color,
            boxShadow: `0 0 8px ${config.color}`,
          }}
        />
        <Txt variant="label" color={colors.textSecondary} style={{ fontSize: 12.5 }}>
          {config.label}
        </Txt>
      </View>
    </PressableScale>
  );
}
