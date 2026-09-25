import { useEffect } from 'react';
import { View } from 'react-native';
import Svg, { Defs, LinearGradient, Stop, Circle, G } from 'react-native-svg';
import Animated, {
  useAnimatedProps,
  useSharedValue,
  withTiming,
  Easing,
} from 'react-native-reanimated';
import { colors, riskColor, riskGradient } from '@/theme';
import type { RiskLevel, StressType } from '@/api/types';
import { useT } from '@/i18n/i18n-context';
import { Txt } from './ui/text';
import { AnimatedNumber } from './ui/animated-number';
import { RiskBadge } from './ui/risk-badge';

const AnimatedCircle = Animated.createAnimatedComponent(Circle);

const SIZE = 230;
const STROKE = 16;
const R = (SIZE - STROKE) / 2 - 8;
const CX = SIZE / 2;
const CY = SIZE / 2;
const C = 2 * Math.PI * R;
const SWEEP = 0.75; // 270° gauge
const ARC = C * SWEEP;

interface Props {
  score: number; // 0..100
  risk: RiskLevel;
  stressType: StressType;
  subtitle?: string;
}

export function GpssGauge({ score, risk, stressType, subtitle }: Props) {
  const { t, tStress } = useT();
  const progress = useSharedValue(0);

  useEffect(() => {
    progress.value = withTiming(Math.max(0, Math.min(100, score)) / 100, {
      duration: 900,
      easing: Easing.out(Easing.cubic),
    });
  }, [score, progress]);

  const animatedProps = useAnimatedProps(() => ({
    strokeDashoffset: ARC * (1 - progress.value),
  }));

  const grad = riskGradient[risk];

  return (
    <View style={{ width: SIZE, height: SIZE, alignItems: 'center', justifyContent: 'center' }}>
      <Svg width={SIZE} height={SIZE}>
        <Defs>
          <LinearGradient id="gauge" x1="0" y1="0" x2="1" y2="1">
            <Stop offset="0" stopColor={grad[0]} />
            <Stop offset="1" stopColor={grad[1]} />
          </LinearGradient>
        </Defs>
        {/* rotate so the 90° gap sits centered at the bottom */}
        <G rotation={135} originX={CX} originY={CY}>
          {/* track */}
          <Circle
            cx={CX}
            cy={CY}
            r={R}
            stroke={colors.surfaceHi}
            strokeWidth={STROKE}
            strokeDasharray={`${ARC} ${C}`}
            strokeLinecap="round"
            fill="none"
          />
          {/* value */}
          <AnimatedCircle
            cx={CX}
            cy={CY}
            r={R}
            stroke="url(#gauge)"
            strokeWidth={STROKE}
            strokeDasharray={`${ARC} ${C}`}
            strokeLinecap="round"
            fill="none"
            animatedProps={animatedProps}
          />
        </G>
      </Svg>

      <View style={{ position: 'absolute', alignItems: 'center', gap: 6 }}>
        <Txt variant="overline">{t('result.score')}</Txt>
        <View style={{ flexDirection: 'row', alignItems: 'flex-start' }}>
          <AnimatedNumber
            value={score}
            style={{ fontSize: 64, lineHeight: 64, color: colors.text }}
            variant="numeric"
          />
          <Txt variant="numeric" color={colors.textMuted} style={{ fontSize: 20, marginTop: 8, marginLeft: 2 }}>
            /100
          </Txt>
        </View>
        <RiskBadge level={risk} />
        <Txt variant="caption" color={riskColor[risk]} center style={{ marginTop: 2 }}>
          {subtitle ?? tStress(stressType)}
        </Txt>
      </View>
    </View>
  );
}
