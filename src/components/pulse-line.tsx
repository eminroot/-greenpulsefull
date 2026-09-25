import { useEffect } from 'react';
import { View, type ViewStyle } from 'react-native';
import Svg, { Defs, LinearGradient, Stop, Path } from 'react-native-svg';
import Animated, {
  useAnimatedProps,
  useSharedValue,
  withRepeat,
  withTiming,
  Easing,
} from 'react-native-reanimated';
import { colors } from '@/theme';

const AnimatedPath = Animated.createAnimatedComponent(Path);

// A periodic ECG-style waveform; a bright dash travels along it on a loop to
// signal the system is "listening" to the plant.
const D =
  'M0 30 L58 30 L68 30 L76 12 L84 48 L92 30 L150 30 L160 30 L168 14 L176 46 L184 30 L242 30 L252 30 L260 12 L268 48 L276 30 L320 30';

const PATTERN = 400;

interface Props {
  height?: number;
  color?: string;
  trackColor?: string;
  duration?: number;
  style?: ViewStyle;
}

export function PulseLine({
  height = 56,
  color = colors.accent,
  trackColor = 'rgba(163,230,53,0.16)',
  duration = 2400,
  style,
}: Props) {
  const offset = useSharedValue(0);

  useEffect(() => {
    offset.value = withRepeat(
      withTiming(-PATTERN, { duration, easing: Easing.linear }),
      -1,
      false
    );
  }, [offset, duration]);

  const animatedProps = useAnimatedProps(() => ({ strokeDashoffset: offset.value }));

  return (
    <View style={[{ height, width: '100%' }, style]}>
      <Svg width="100%" height={height} viewBox="0 0 320 60" preserveAspectRatio="none">
        <Defs>
          <LinearGradient id="pulseGrad" x1="0" y1="0" x2="1" y2="0">
            <Stop offset="0" stopColor={color} stopOpacity={0} />
            <Stop offset="0.5" stopColor={color} stopOpacity={1} />
            <Stop offset="1" stopColor={color} stopOpacity={0} />
          </LinearGradient>
        </Defs>
        <Path d={D} stroke={trackColor} strokeWidth={2.5} fill="none" strokeLinejoin="round" strokeLinecap="round" />
        <AnimatedPath
          d={D}
          stroke="url(#pulseGrad)"
          strokeWidth={3.2}
          fill="none"
          strokeLinejoin="round"
          strokeLinecap="round"
          strokeDasharray={`56 ${PATTERN - 56}`}
          animatedProps={animatedProps}
        />
      </Svg>
    </View>
  );
}
