import { SymbolView, type SymbolViewProps, type SFSymbol } from 'expo-symbols';
import { View } from 'react-native';
import { colors } from '@/theme';

export interface IconProps {
  name: SFSymbol | string;
  size?: number;
  color?: string;
  weight?: SymbolViewProps['weight'];
  animationSpec?: SymbolViewProps['animationSpec'];
  style?: SymbolViewProps['style'];
}

// Thin wrapper over SF Symbols. iOS-first (the GreenPulse target). On platforms
// without SF Symbols it renders a neutral spacer so layouts never collapse.
export function Icon({
  name,
  size = 20,
  color = colors.text,
  weight = 'medium',
  animationSpec,
  style,
}: IconProps) {
  if (process.env.EXPO_OS !== 'ios') {
    return <View style={[{ width: size, height: size }, style]} />;
  }
  return (
    <SymbolView
      name={name as SFSymbol}
      tintColor={color}
      size={size}
      weight={weight}
      resizeMode="scaleAspectFit"
      animationSpec={animationSpec}
      style={style}
    />
  );
}
