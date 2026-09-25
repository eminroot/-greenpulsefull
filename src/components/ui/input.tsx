import { useState } from 'react';
import {
  TextInput,
  View,
  type TextInputProps,
  type ViewStyle,
} from 'react-native';
import Animated, {
  useAnimatedStyle,
  useSharedValue,
  withTiming,
} from 'react-native-reanimated';
import { colors, font, radius } from '@/theme';
import { Txt } from './text';
import { Icon } from './icon';
import { PressableScale } from './pressable-scale';

export interface InputProps extends Omit<TextInputProps, 'style'> {
  label?: string;
  icon?: string;
  error?: string | null;
  secure?: boolean;
  containerStyle?: ViewStyle;
}

export function Input({
  label,
  icon,
  error,
  secure = false,
  containerStyle,
  ...rest
}: InputProps) {
  const [focused, setFocused] = useState(false);
  const [hidden, setHidden] = useState(secure);
  const focus = useSharedValue(0);

  const borderStyle = useAnimatedStyle(() => ({
    borderColor: error
      ? colors.danger
      : interpolateColor(focus.value),
  }));

  return (
    <View style={containerStyle}>
      {label ? (
        <Txt variant="overline" style={{ marginBottom: 8, marginLeft: 4 }}>
          {label}
        </Txt>
      ) : null}
      <Animated.View
        style={[
          {
            flexDirection: 'row',
            alignItems: 'center',
            gap: 10,
            paddingHorizontal: 16,
            height: 54,
            borderRadius: radius.md,
            borderCurve: 'continuous',
            borderWidth: 1.5,
            backgroundColor: colors.surface,
          },
          borderStyle,
        ]}
      >
        {icon ? <Icon name={icon} size={18} color={focused ? colors.primary : colors.textMuted} /> : null}
        <TextInput
          {...rest}
          secureTextEntry={hidden}
          onFocus={(e) => {
            setFocused(true);
            focus.value = withTiming(1, { duration: 160 });
            rest.onFocus?.(e);
          }}
          onBlur={(e) => {
            setFocused(false);
            focus.value = withTiming(0, { duration: 160 });
            rest.onBlur?.(e);
          }}
          placeholderTextColor={colors.textMuted}
          style={{
            flex: 1,
            color: colors.text,
            fontFamily: font.bodyMedium,
            fontSize: 16,
            paddingVertical: 0,
          }}
        />
        {secure ? (
          <PressableScale haptic={false} onPress={() => setHidden((h) => !h)} style={{ padding: 4 }}>
            <Icon name={hidden ? 'eye.slash.fill' : 'eye.fill'} size={17} color={colors.textMuted} />
          </PressableScale>
        ) : null}
      </Animated.View>
      {error ? (
        <View style={{ flexDirection: 'row', alignItems: 'center', gap: 5, marginTop: 7, marginLeft: 4 }}>
          <Icon name="exclamationmark.circle.fill" size={12} color={colors.danger} />
          <Txt variant="caption" color={colors.danger}>
            {error}
          </Txt>
        </View>
      ) : null}
    </View>
  );
}

// Lightweight 2-stop color lerp between the resting border and the focused
// emerald, kept on the JS side since the input count is tiny.
function interpolateColor(t: number): string {
  'worklet';
  const from = [42, 58, 49]; // ~ colors.border on surface
  const to = [16, 185, 129]; // primary
  const r = Math.round(from[0] + (to[0] - from[0]) * t);
  const g = Math.round(from[1] + (to[1] - from[1]) * t);
  const b = Math.round(from[2] + (to[2] - from[2]) * t);
  return `rgb(${r}, ${g}, ${b})`;
}
