import { ActivityIndicator, View, type ViewStyle } from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import * as Haptics from 'expo-haptics';
import { colors, gradients, radius } from '@/theme';
import { Txt } from './text';
import { Icon } from './icon';
import { PressableScale } from './pressable-scale';

type Variant = 'primary' | 'secondary' | 'ghost' | 'danger';

export interface ButtonProps {
  label: string;
  onPress?: () => void;
  variant?: Variant;
  icon?: string;
  loading?: boolean;
  disabled?: boolean;
  fullWidth?: boolean;
  style?: ViewStyle;
}

export function Button({
  label,
  onPress,
  variant = 'primary',
  icon,
  loading = false,
  disabled = false,
  fullWidth = true,
  style,
}: ButtonProps) {
  const isGradient = variant === 'primary';
  const inactive = disabled || loading;

  const inner = (
    <View
      style={{
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 10,
        paddingVertical: 16,
        paddingHorizontal: 22,
      }}
    >
      {loading ? (
        <ActivityIndicator color={variant === 'primary' ? colors.textInverse : colors.text} />
      ) : (
        <>
          {icon ? (
            <Icon
              name={icon}
              size={18}
              color={variant === 'primary' ? colors.textInverse : labelColor(variant)}
              weight="semibold"
            />
          ) : null}
          <Txt variant="label" style={{ fontSize: 15 }} color={variant === 'primary' ? colors.textInverse : labelColor(variant)}>
            {label}
          </Txt>
        </>
      )}
    </View>
  );

  const containerStyle: ViewStyle = {
    borderRadius: radius.pill,
    borderCurve: 'continuous',
    overflow: 'hidden',
    opacity: inactive ? 0.55 : 1,
    width: fullWidth ? '100%' : undefined,
    ...style,
  };

  return (
    <PressableScale
      disabled={inactive}
      haptic={Haptics.ImpactFeedbackStyle.Medium}
      onPress={onPress}
      style={containerStyle}
    >
      {isGradient ? (
        <LinearGradient
          colors={gradients.brand}
          start={{ x: 0, y: 0 }}
          end={{ x: 1, y: 1 }}
          style={{ borderRadius: radius.pill }}
        >
          {inner}
        </LinearGradient>
      ) : (
        <View
          style={{
            backgroundColor:
              variant === 'ghost' ? 'transparent' : variant === 'danger' ? 'rgba(248,113,113,0.12)' : colors.surface2,
            borderWidth: variant === 'ghost' ? 1 : 0,
            borderColor: colors.border,
            borderRadius: radius.pill,
          }}
        >
          {inner}
        </View>
      )}
    </PressableScale>
  );
}

function labelColor(variant: Variant): string {
  if (variant === 'danger') return colors.danger;
  if (variant === 'ghost') return colors.textSecondary;
  return colors.text;
}
