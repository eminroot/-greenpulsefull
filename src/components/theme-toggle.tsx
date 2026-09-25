import { View } from 'react-native';
import { colors, radius } from '@/theme';
import { useTheme } from '@/theme/theme-context';
import { Icon } from './ui/icon';
import { PressableScale } from './ui/pressable-scale';

// Compact sun/moon button that flips the app between dark and light.
export function ThemeToggle({ size = 38 }: { size?: number }) {
  const { mode, toggle } = useTheme();
  return (
    <PressableScale haptic={false} onPress={toggle} style={{ borderRadius: radius.pill }}>
      <View
        style={{
          width: size,
          height: size,
          borderRadius: radius.pill,
          alignItems: 'center',
          justifyContent: 'center',
          backgroundColor: colors.surface,
          borderWidth: 1,
          borderColor: colors.border,
        }}
      >
        <Icon name={mode === 'dark' ? 'sun.max.fill' : 'moon.fill'} size={17} color={colors.textSecondary} />
      </View>
    </PressableScale>
  );
}
