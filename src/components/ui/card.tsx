import { type ReactNode } from 'react';
import { View, type ViewStyle } from 'react-native';
import { BlurView } from 'expo-blur';
import { LinearGradient } from 'expo-linear-gradient';
import { colors, radius, spacing } from '@/theme';

export interface CardProps {
  children: ReactNode;
  style?: ViewStyle | ViewStyle[];
  padding?: number;
  radius?: number;
  glass?: boolean;
  glow?: string | false;
  borderColor?: string;
  // A faint diagonal sheen across the surface, on by default for depth.
  sheen?: boolean;
}

export function Card({
  children,
  style,
  padding = spacing.lg,
  radius: r = radius.lg,
  glass = false,
  glow = false,
  borderColor = colors.border,
  sheen = true,
}: CardProps) {
  const base: ViewStyle = {
    borderRadius: r,
    borderCurve: 'continuous',
    borderWidth: 1,
    borderColor,
    overflow: 'hidden',
    ...(glow ? { boxShadow: `0 0 30px ${glow}` } : null),
  };

  const content = (
    <>
      {sheen ? (
        <LinearGradient
          colors={['rgba(255,255,255,0.06)', 'rgba(255,255,255,0)']}
          start={{ x: 0, y: 0 }}
          end={{ x: 0.9, y: 1 }}
          style={{ position: 'absolute', inset: 0 }}
          pointerEvents="none"
        />
      ) : null}
      <View style={{ padding }}>{children}</View>
    </>
  );

  if (glass) {
    return (
      <BlurView tint="dark" intensity={36} style={[base, { backgroundColor: colors.glassTint }, style]}>
        {content}
      </BlurView>
    );
  }

  return <View style={[base, { backgroundColor: colors.surface }, style]}>{content}</View>;
}
