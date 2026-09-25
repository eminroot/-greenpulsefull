import { Text as RNText, type TextProps, type TextStyle } from 'react-native';
import { colors, font } from '@/theme';

type Variant =
  | 'display'
  | 'title'
  | 'heading'
  | 'subtitle'
  | 'body'
  | 'bodyMedium'
  | 'label'
  | 'caption'
  | 'overline'
  | 'numeric';

type ColorKey = 'text' | 'textSecondary' | 'textMuted';

// Static (non-color) styling per variant. Color is resolved at render time so it
// follows the active theme (the `colors` proxy must not be read at module load).
const VARIANTS: Record<Variant, TextStyle> = {
  display: { fontFamily: font.display, fontSize: 34, lineHeight: 38 },
  title: { fontFamily: font.displayMedium, fontSize: 26, lineHeight: 30 },
  heading: { fontFamily: font.bodySemibold, fontSize: 18, lineHeight: 24 },
  subtitle: { fontFamily: font.bodyMedium, fontSize: 16, lineHeight: 22 },
  body: { fontFamily: font.body, fontSize: 15, lineHeight: 22 },
  bodyMedium: { fontFamily: font.bodyMedium, fontSize: 15, lineHeight: 21 },
  label: { fontFamily: font.bodySemibold, fontSize: 13, lineHeight: 17 },
  caption: { fontFamily: font.body, fontSize: 12.5, lineHeight: 17 },
  overline: { fontFamily: font.bodySemibold, fontSize: 11, lineHeight: 14, letterSpacing: 1.4, textTransform: 'uppercase' },
  numeric: { fontFamily: font.numeric, fontSize: 24, fontVariant: ['tabular-nums'] },
};

const VARIANT_COLOR: Record<Variant, ColorKey> = {
  display: 'text',
  title: 'text',
  heading: 'text',
  subtitle: 'text',
  body: 'textSecondary',
  bodyMedium: 'text',
  label: 'text',
  caption: 'textMuted',
  overline: 'textMuted',
  numeric: 'text',
};

export interface TxtProps extends TextProps {
  variant?: Variant;
  color?: string;
  center?: boolean;
}

export function Txt({ variant = 'body', color, center, style, ...rest }: TxtProps) {
  return (
    <RNText
      {...rest}
      style={[
        VARIANTS[variant],
        { color: color ?? colors[VARIANT_COLOR[variant]] },
        center ? { textAlign: 'center' } : null,
        style,
      ]}
    />
  );
}
