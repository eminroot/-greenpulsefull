import { useState } from 'react';
import { View, type LayoutChangeEvent } from 'react-native';
import Svg, { Defs, LinearGradient, Stop, Path, Circle, Line } from 'react-native-svg';
import { colors } from '@/theme';

interface Props {
  data: number[]; // GPSS values, oldest → newest
  height?: number;
  color?: string;
  domainMax?: number;
}

// Smooth area chart for the GPSS trend. Catmull-Rom → bezier for soft curves.
export function LineChart({ data, height = 160, color = colors.primary, domainMax = 100 }: Props) {
  const [width, setWidth] = useState(0);
  const onLayout = (e: LayoutChangeEvent) => setWidth(e.nativeEvent.layout.width);

  const padX = 6;
  const padY = 14;
  const w = Math.max(0, width - padX * 2);
  const h = height - padY * 2;

  const baseY = padY + h;

  const pts = data.length
    ? data.map((v, i) => {
        const x = padX + (data.length === 1 ? w / 2 : (i / (data.length - 1)) * w);
        const y = baseY - (Math.max(0, Math.min(domainMax, v)) / domainMax) * h;
        return { x, y };
      })
    : [];

  // With a single reading, draw a flat "current level" line across the width so
  // the card reads as a deliberate sparkline instead of a lonely dot.
  const linePts =
    pts.length === 1 ? [{ x: padX, y: pts[0].y }, { x: width - padX, y: pts[0].y }] : pts;
  const dotPts = pts.length === 1 ? [{ x: width - padX, y: pts[0].y }] : pts;

  const linePath = smoothPath(linePts);
  const areaPath =
    linePts.length > 1
      ? `${linePath} L ${linePts[linePts.length - 1].x} ${baseY} L ${linePts[0].x} ${baseY} Z`
      : '';

  return (
    <View onLayout={onLayout} style={{ width: '100%', height }}>
      {width > 0 && pts.length > 0 ? (
        <Svg width={width} height={height}>
          <Defs>
            <LinearGradient id="area" x1="0" y1="0" x2="0" y2="1">
              <Stop offset="0" stopColor={color} stopOpacity={0.32} />
              <Stop offset="1" stopColor={color} stopOpacity={0} />
            </LinearGradient>
          </Defs>

          {[0.25, 0.5, 0.75].map((g) => (
            <Line key={g} x1={padX} y1={padY + h * g} x2={width - padX} y2={padY + h * g} stroke={colors.hairline} strokeWidth={1} />
          ))}

          {areaPath ? <Path d={areaPath} fill="url(#area)" /> : null}
          {linePts.length > 1 ? (
            <Path d={linePath} stroke={color} strokeWidth={3} fill="none" strokeLinecap="round" strokeLinejoin="round" />
          ) : null}

          {dotPts.map((p, i) => (
            <Circle
              key={i}
              cx={p.x}
              cy={p.y}
              r={i === dotPts.length - 1 ? 5 : 3}
              fill={i === dotPts.length - 1 ? color : colors.bg}
              stroke={color}
              strokeWidth={2}
            />
          ))}
        </Svg>
      ) : null}
    </View>
  );
}

function smoothPath(pts: { x: number; y: number }[]): string {
  if (pts.length === 0) return '';
  if (pts.length === 1) return `M ${pts[0].x} ${pts[0].y}`;
  let d = `M ${pts[0].x} ${pts[0].y}`;
  for (let i = 0; i < pts.length - 1; i++) {
    const p0 = pts[i === 0 ? 0 : i - 1];
    const p1 = pts[i];
    const p2 = pts[i + 1];
    const p3 = pts[i + 2 < pts.length ? i + 2 : i + 1];
    const c1x = p1.x + (p2.x - p0.x) / 6;
    const c1y = p1.y + (p2.y - p0.y) / 6;
    const c2x = p2.x - (p3.x - p1.x) / 6;
    const c2y = p2.y - (p3.y - p1.y) / 6;
    d += ` C ${c1x} ${c1y}, ${c2x} ${c2y}, ${p2.x} ${p2.y}`;
  }
  return d;
}
