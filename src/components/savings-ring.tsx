import { useEffect } from 'react';
import { View } from 'react-native';
import Svg, { Circle } from 'react-native-svg';
import Animated, {
  useAnimatedProps,
  useSharedValue,
  withTiming,
  Easing,
} from 'react-native-reanimated';
import { colors } from '@/theme';
import { Txt } from './ui/text';
import { AnimatedNumber } from './ui/animated-number';

const AnimatedCircle = Animated.createAnimatedComponent(Circle);

// Circular progress ring with an animated arc draw and a count-up center value.
export function SavingsRing({
  value,
  color,
  label,
  size = 116,
  stroke = 12,
}: {
  value: number;
  color: string;
  label: string;
  size?: number;
  stroke?: number;
}) {
  const r = (size - stroke) / 2 - 1;
  const c = 2 * Math.PI * r;
  const progress = useSharedValue(0);

  useEffect(() => {
    progress.value = withTiming(Math.max(0, Math.min(100, value)) / 100, {
      duration: 1100,
      easing: Easing.out(Easing.cubic),
    });
  }, [value, progress]);

  const animatedProps = useAnimatedProps(() => ({ strokeDashoffset: c * (1 - progress.value) }));

  return (
    <View style={{ width: size, height: size, alignItems: 'center', justifyContent: 'center' }}>
      <Svg width={size} height={size}>
        <Circle cx={size / 2} cy={size / 2} r={r} stroke={colors.surfaceHi} strokeWidth={stroke} fill="none" />
        <AnimatedCircle
          cx={size / 2}
          cy={size / 2}
          r={r}
          stroke={color}
          strokeWidth={stroke}
          fill="none"
          strokeLinecap="round"
          strokeDasharray={c}
          animatedProps={animatedProps}
          transform={`rotate(-90 ${size / 2} ${size / 2})`}
        />
      </Svg>
      <View style={{ position: 'absolute', alignItems: 'center' }}>
        <AnimatedNumber value={value} suffix="%" variant="numeric" style={{ fontSize: 26, color: colors.text }} />
        <Txt variant="overline" style={{ fontSize: 9, marginTop: 1 }}>
          {label}
        </Txt>
      </View>
    </View>
  );
}
