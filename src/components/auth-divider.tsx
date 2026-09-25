import { View } from 'react-native';
import { colors } from '@/theme';
import { Txt } from './ui/text';

export function AuthDivider({ label = 'or' }: { label?: string }) {
  return (
    <View style={{ flexDirection: 'row', alignItems: 'center', gap: 12, marginVertical: 2 }}>
      <View style={{ flex: 1, height: 1, backgroundColor: colors.border }} />
      <Txt variant="caption" color={colors.textMuted}>
        {label}
      </Txt>
      <View style={{ flex: 1, height: 1, backgroundColor: colors.border }} />
    </View>
  );
}
