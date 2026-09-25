import { type ReactNode } from 'react';
import { Pressable, type PressableProps, type ViewStyle } from 'react-native';
import * as Haptics from 'expo-haptics';
import Animated, {
  useAnimatedStyle,
  useSharedValue,
  withSpring,
} from 'react-native-reanimated';

const AnimatedPressable = Animated.createAnimatedComponent(Pressable);

export interface PressableScaleProps extends PressableProps {
  children: ReactNode;
  scaleTo?: number;
  haptic?: Haptics.ImpactFeedbackStyle | false;
  style?: ViewStyle | ViewStyle[];
}

export function PressableScale({
  children,
  scaleTo = 0.96,
  haptic = Haptics.ImpactFeedbackStyle.Light,
  onPressIn,
  onPress,
  style,
  ...rest
}: PressableScaleProps) {
  const scale = useSharedValue(1);
  const animatedStyle = useAnimatedStyle(() => ({ transform: [{ scale: scale.value }] }));

  return (
    <AnimatedPressable
      {...rest}
      onPressIn={(e) => {
        scale.value = withSpring(scaleTo, { damping: 18, stiffness: 320 });
        if (haptic !== false && process.env.EXPO_OS === 'ios') {
          Haptics.impactAsync(haptic).catch(() => {});
        }
        onPressIn?.(e);
      }}
      onPressOut={() => {
        scale.value = withSpring(1, { damping: 14, stiffness: 260 });
      }}
      onPress={onPress}
      style={[animatedStyle, style as ViewStyle]}
    >
      {children}
    </AnimatedPressable>
  );
}
