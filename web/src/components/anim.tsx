import { useEffect, useRef, useState } from 'react';

// Eases a displayed number toward its target with an easeOutCubic ramp. Used by
// the sustainability metrics so they count up as values change.
export function AnimatedNumber({
  value,
  duration = 800,
  decimals = 0,
  format,
}: {
  value: number;
  duration?: number;
  decimals?: number;
  format?: (n: number) => string;
}) {
  const [display, setDisplay] = useState(value);
  const from = useRef(value);
  const raf = useRef<number | undefined>(undefined);
  const start = useRef(0);

  useEffect(() => {
    const f = from.current;
    const delta = value - f;
    if (delta === 0) return;
    start.current = performance.now();
    const tick = (now: number) => {
      const t = Math.min(1, (now - start.current) / duration);
      const eased = 1 - Math.pow(1 - t, 3);
      setDisplay(f + delta * eased);
      if (t < 1) raf.current = requestAnimationFrame(tick);
      else from.current = value;
    };
    raf.current = requestAnimationFrame(tick);
    return () => {
      if (raf.current) cancelAnimationFrame(raf.current);
      from.current = value;
    };
  }, [value, duration]);

  return <>{format ? format(display) : display.toFixed(decimals)}</>;
}
