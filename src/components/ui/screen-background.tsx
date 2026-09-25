import { useState, type ReactNode } from 'react';
import { View, useWindowDimensions, type LayoutChangeEvent, type ViewStyle } from 'react-native';
import Svg, { Defs, RadialGradient, Stop, Rect, Circle } from 'react-native-svg';
import { colors } from '@/theme';
import { useTheme } from '@/theme/theme-context';

interface Props {
  children?: ReactNode;
  style?: ViewStyle;
  // Intensity of the ambient canopy glow (0..1).
  intensity?: number;
}

// Ambient "canopy aurora" backdrop: a deep field with soft radial glows
// (emerald + lime) painted with SVG so it renders crisply at any size. The
// glows are dimmed and the bottom hue lightened for the light theme.
export function ScreenBackground({ children, style, intensity = 1 }: Props) {
  const win = useWindowDimensions();
  // Painted to the view's own size, not the window's: on Android the window
  // leaves out the strip behind the navigation bar, and the glow stopped short
  // of it in a visible seam.
  const [size, setSize] = useState<{ w: number; h: number } | null>(null);
  const onLayout = (e: LayoutChangeEvent) => {
    const { width: w, height: hh } = e.nativeEvent.layout;
    setSize((s) => (s && s.w === w && s.h === hh ? s : { w, h: hh }));
  };
  const width = size?.w ?? win.width;
  const { mode } = useTheme();
  const h = Math.max(size?.h ?? win.height, 1);
  const light = mode === 'light';

  const aOp = (light ? 0.1 : 0.32) * intensity;
  const bOp = (light ? 0.06 : 0.16) * intensity;
  const cOp = (light ? 0.1 : 0.5) * intensity;
  const cColor = light ? '#34D399' : '#064E3B';

  return (
    <View onLayout={onLayout} style={[{ flex: 1, backgroundColor: colors.bg }, style]}>
      <Svg width={width} height={h} style={{ position: 'absolute', top: 0, left: 0 }} pointerEvents="none">
        <Defs>
          <RadialGradient id="glowA" cx="20%" cy="6%" r="62%">
            <Stop offset="0" stopColor="#10B981" stopOpacity={aOp} />
            <Stop offset="1" stopColor="#10B981" stopOpacity={0} />
          </RadialGradient>
          <RadialGradient id="glowB" cx="92%" cy="30%" r="55%">
            <Stop offset="0" stopColor="#A3E635" stopOpacity={bOp} />
            <Stop offset="1" stopColor="#A3E635" stopOpacity={0} />
          </RadialGradient>
          <RadialGradient id="glowC" cx="50%" cy="108%" r="70%">
            <Stop offset="0" stopColor={cColor} stopOpacity={cOp} />
            <Stop offset="1" stopColor={cColor} stopOpacity={0} />
          </RadialGradient>
        </Defs>
        <Rect x={0} y={0} width={width} height={h} fill={colors.bg} />
        <Circle cx={width * 0.2} cy={h * 0.06} r={width * 0.8} fill="url(#glowA)" />
        <Circle cx={width * 0.92} cy={h * 0.3} r={width * 0.7} fill="url(#glowB)" />
        <Rect x={0} y={0} width={width} height={h} fill="url(#glowC)" />
      </Svg>
      {children}
    </View>
  );
}
