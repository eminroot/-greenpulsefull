import { View } from 'react-native';
import Svg, { Defs, LinearGradient, Stop, Path, Line } from 'react-native-svg';
import { colors, font } from '@/theme';
import { Txt } from './text';

// The GreenPulse mark: a vesica-piscis leaf with a midrib that breaks into an
// ECG-style pulse, tying "leaf" and "pulse" into one glyph.
export function LogoMark({ size = 40 }: { size?: number }) {
  return (
    <Svg width={size} height={size} viewBox="0 0 100 100">
      <Defs>
        <LinearGradient id="leaf" x1="0" y1="0" x2="1" y2="1">
          <Stop offset="0" stopColor="#A3E635" />
          <Stop offset="1" stopColor="#10B981" />
        </LinearGradient>
        <LinearGradient id="pulse" x1="0" y1="0" x2="1" y2="0">
          <Stop offset="0" stopColor="#06281B" />
          <Stop offset="1" stopColor="#0B3D2E" />
        </LinearGradient>
      </Defs>
      {/* Leaf body (intersection of two arcs) */}
      <Path
        d="M50 8 C74 24 86 44 86 60 C86 76 70 92 50 92 C30 92 14 76 14 60 C14 44 26 24 50 8 Z"
        fill="url(#leaf)"
      />
      {/* Midrib turning into a pulse */}
      <Path
        d="M50 16 L50 44 L44 56 L56 64 L48 78 L50 86"
        stroke="url(#pulse)"
        strokeWidth={4.5}
        strokeLinejoin="round"
        strokeLinecap="round"
        fill="none"
      />
    </Svg>
  );
}

export function Wordmark({ size = 22, markSize, tagline }: { size?: number; markSize?: number; tagline?: string }) {
  return (
    <View style={{ flexDirection: 'row', alignItems: 'center', gap: 10 }}>
      <LogoMark size={markSize ?? size * 1.55} />
      <View>
        <View style={{ flexDirection: 'row' }}>
          <Txt style={{ fontFamily: font.display, fontSize: size, color: colors.text, letterSpacing: -0.3 }}>
            Green
          </Txt>
          <Txt style={{ fontFamily: font.display, fontSize: size, color: colors.accent, letterSpacing: -0.3 }}>
            Pulse
          </Txt>
        </View>
        {tagline ? (
          <Txt variant="overline" style={{ marginTop: 2 }}>
            {tagline}
          </Txt>
        ) : null}
      </View>
    </View>
  );
}
