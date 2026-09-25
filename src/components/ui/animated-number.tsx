import { useEffect, useRef, useState } from 'react';
import { Txt, type TxtProps } from './text';

interface Props extends Omit<TxtProps, 'children'> {
  value: number;
  decimals?: number;
  duration?: number;
  suffix?: string;
  prefix?: string;
  thousands?: boolean;
}

// Eases a displayed number toward its target. JS-driven, which is plenty smooth
// for the handful of headline counters on screen and avoids extra deps.
export function AnimatedNumber({ value, decimals = 0, duration = 700, suffix = '', prefix = '', thousands = false, ...rest }: Props) {
  const [display, setDisplay] = useState(value);
  const fromRef = useRef(value);
  const startRef = useRef(0);
  const rafRef = useRef<number | null>(null);

  useEffect(() => {
    const from = fromRef.current;
    const delta = value - from;
    if (delta === 0) return;
    startRef.current = Date.now();

    const tick = () => {
      const t = Math.min(1, (Date.now() - startRef.current) / duration);
      // easeOutCubic
      const eased = 1 - Math.pow(1 - t, 3);
      const current = from + delta * eased;
      setDisplay(current);
      if (t < 1) {
        rafRef.current = requestAnimationFrame(tick);
      } else {
        fromRef.current = value;
      }
    };
    rafRef.current = requestAnimationFrame(tick);
    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
      fromRef.current = value;
    };
  }, [value, duration]);

  const num = thousands
    ? Math.round(display).toLocaleString()
    : display.toFixed(decimals);

  return (
    <Txt {...rest}>
      {prefix}
      {num}
      {suffix}
    </Txt>
  );
}
