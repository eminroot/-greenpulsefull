import { View } from 'react-native';
import { radius } from '@/theme';
import { riskColor } from '@/theme';
import type { RiskLevel } from '@/api/types';
import { useT } from '@/i18n/i18n-context';
import { Txt } from './text';

const withAlpha = (hex: string, a: number) => {
  const n = parseInt(hex.slice(1), 16);
  const r = (n >> 16) & 255;
  const g = (n >> 8) & 255;
  const b = n & 255;
  return `rgba(${r}, ${g}, ${b}, ${a})`;
};

export function RiskBadge({ level, size = 'md' }: { level: RiskLevel; size?: 'sm' | 'md' }) {
  const { tRisk } = useT();
  const c = riskColor[level];
  const sm = size === 'sm';
  return (
    <View
      style={{
        flexDirection: 'row',
        alignItems: 'center',
        gap: 6,
        paddingVertical: sm ? 4 : 6,
        paddingHorizontal: sm ? 9 : 12,
        borderRadius: radius.pill,
        backgroundColor: withAlpha(c, 0.14),
        borderWidth: 1,
        borderColor: withAlpha(c, 0.35),
      }}
    >
      <View style={{ width: sm ? 6 : 7, height: sm ? 6 : 7, borderRadius: 99, backgroundColor: c, boxShadow: `0 0 8px ${c}` }} />
      <Txt variant="label" color={c} style={{ fontSize: sm ? 11.5 : 13 }}>
        {tRisk(level)}
      </Txt>
    </View>
  );
}

export { withAlpha };
