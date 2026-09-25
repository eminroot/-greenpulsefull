import { SymbolView, type SymbolViewProps, type SFSymbol } from 'expo-symbols';
import MaterialCommunityIcons from '@expo/vector-icons/MaterialCommunityIcons';
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

type MaterialName = keyof typeof MaterialCommunityIcons.glyphMap;

// SF Symbols exist only on Apple platforms. Everywhere else each symbol the app
// uses is drawn with its nearest Material Community icon, so an Android phone
// shows the same icons instead of blank gaps. Add a line here whenever a new
// symbol appears in the app.
const MATERIAL: Record<string, MaterialName> = {
  'antenna.radiowaves.left.and.right': 'access-point',
  'antenna.radiowaves.left.and.right.slash': 'access-point-off',
  'arrow.right': 'arrow-right',
  'arrow.triangle.2.circlepath.camera': 'camera-flip-outline',
  'arrow.up': 'arrow-up',
  'arrow.up.left.and.arrow.down.right': 'arrow-expand',
  'bell.badge.fill': 'bell-badge',
  'bolt.badge.automatic.fill': 'flash-auto',
  'bolt.fill': 'flash',
  'camera.aperture': 'camera-iris',
  'camera.fill': 'camera',
  'camera.viewfinder': 'camera-outline',
  'chart.xyaxis.line': 'chart-line',
  'checkmark.circle.fill': 'check-circle',
  'checkmark.seal.fill': 'check-decagram',
  'chevron.left': 'chevron-left',
  'chevron.right': 'chevron-right',
  'clock.fill': 'clock',
  'cloud.fill': 'cloud',
  cpu: 'chip',
  'creditcard.fill': 'credit-card',
  'cross.case.fill': 'medical-bag',
  'doc.on.doc': 'content-copy',
  'doc.questionmark': 'file-question',
  'drop.circle.fill': 'water-circle',
  'drop.fill': 'water',
  'envelope.fill': 'email',
  'exclamationmark.circle.fill': 'alert-circle',
  'exclamationmark.triangle.fill': 'alert',
  'eye.fill': 'eye',
  'eye.slash.fill': 'eye-off',
  'gauge.with.dots.needle.67percent': 'gauge',
  'gearshape.fill': 'cog',
  'humidity.fill': 'water-percent',
  'key.fill': 'key',
  'leaf.circle.fill': 'leaf-circle',
  'leaf.fill': 'leaf',
  'lightbulb.fill': 'lightbulb',
  link: 'link-variant',
  'lock.fill': 'lock',
  'moon.fill': 'weather-night',
  number: 'pound',
  'person.fill': 'account',
  'photo.on.rectangle': 'image-multiple',
  'questionmark.circle.fill': 'help-circle',
  'rectangle.portrait.and.arrow.right': 'logout',
  sparkles: 'creation',
  'sun.max.fill': 'white-balance-sunny',
  'thermometer.medium': 'thermometer',
  'thermometer.sun.fill': 'thermometer-high',
  trash: 'trash-can-outline',
  'waveform.path.ecg': 'pulse',
  wind: 'weather-windy',
  'xmark.circle.fill': 'close-circle',
};

// Thin wrapper over SF Symbols on iOS, Material Community icons elsewhere.
export function Icon({
  name,
  size = 20,
  color = colors.text,
  weight = 'medium',
  animationSpec,
  style,
}: IconProps) {
  if (process.env.EXPO_OS !== 'ios') {
    const material = MATERIAL[name];
    if (!material) {
      if (__DEV__) console.warn(`Icon: no Android icon for "${name}"; add it to MATERIAL in icon.tsx`);
      // Keeps the layout, as before, rather than drawing a wrong symbol.
      return <View style={[{ width: size, height: size }, style]} />;
    }
    return (
      <View style={[{ width: size, height: size, alignItems: 'center', justifyContent: 'center' }, style]}>
        <MaterialCommunityIcons name={material} size={size} color={color} />
      </View>
    );
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
