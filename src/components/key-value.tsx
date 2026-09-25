import { View } from 'react-native';
import { colors } from '@/theme';
import { Txt } from './ui/text';
import { Icon } from './ui/icon';

export function KeyValue({
  label,
  value,
  symbol,
  valueColor,
}: {
  label: string;
  value: string;
  symbol?: string;
  valueColor?: string;
}) {
  return (
    <View style={{ flexDirection: 'row', alignItems: 'center', paddingVertical: 9, gap: 10 }}>
      {symbol ? <Icon name={symbol} size={15} color={colors.textMuted} /> : null}
      <Txt variant="body" style={{ flex: 1 }}>
        {label}
      </Txt>
      <Txt variant="bodyMedium" color={valueColor ?? colors.text} selectable style={{ fontVariant: ['tabular-nums'] }}>
        {value}
      </Txt>
    </View>
  );
}
