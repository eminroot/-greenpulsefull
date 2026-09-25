import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { ApiError, api } from './api/client';
import type { Capture, Live, ScorePreview } from './api/types';

// Long enough that dragging a slider does not fire a request per pixel, short
// enough that the numbers feel attached to the handle.
const DEBOUNCE_MS = 140;

export interface TwinInputs {
  leaf_damage: number;
  soil_moisture: number;
  temperature: number;
  humidity: number;
  light: number;
}

/** Which probes this greenhouse actually has. */
export type Wired = Record<'soil_moisture' | 'temperature' | 'humidity' | 'light', boolean>;

export interface TwinController extends TwinInputs {
  set: (key: keyof TwinInputs, value: number) => void;
  /** The server's verdict for these inputs. Null until the first answer. */
  preview: ScorePreview | null;
  pending: boolean;
  error: string | null;
  /** True when the sliders still match the greenhouse's real current reading. */
  atCurrent: boolean;
  /** Snap every slider back to what the greenhouse is actually reporting. */
  resetToCurrent: () => void;
  /** Whether a real reading was available to seed from. */
  seeded: boolean;
  /**
   * Probes this greenhouse has wired. A probe it does not have is left out of
   * the projection entirely, exactly as the server leaves it out of a real
   * reading, so the twin cannot predict a greenhouse that does not exist.
   */
  wired: Wired;
}

const FALLBACK: TwinInputs = {
  leaf_damage: 0,
  soil_moisture: 58,
  temperature: 23,
  humidity: 62,
  light: 600,
};

const ALL_WIRED: Wired = {
  soil_moisture: true,
  temperature: true,
  humidity: true,
  light: true,
};

function fromLive(live: Live | null): { inputs: TwinInputs; seeded: boolean; wired: Wired } {
  const capture: Capture | null = live?.capture ?? null;
  const reading = live?.reading ?? null;
  // A dark frame has no leaf score; start from the last leaf that had one.
  const leafScore = capture?.risk_score ?? live?.last_leaf_capture?.risk_score ?? null;

  // With no reading at all there is nothing to learn about the hardware, so
  // every control is offered and the operator explores freely.
  if (!capture && !reading) {
    return { inputs: FALLBACK, seeded: false, wired: ALL_WIRED };
  }

  return {
    inputs: {
      leaf_damage: leafScore != null ? Math.round(leafScore) : FALLBACK.leaf_damage,
      soil_moisture: reading?.soil_moisture ?? FALLBACK.soil_moisture,
      temperature: reading?.temperature ?? FALLBACK.temperature,
      humidity: reading?.humidity ?? FALLBACK.humidity,
      light: reading?.light ?? FALLBACK.light,
    },
    seeded: true,
    wired: {
      soil_moisture: reading?.soil_moisture != null,
      temperature: reading?.temperature != null,
      humidity: reading?.humidity != null,
      light: reading?.light != null,
    },
  };
}

function same(a: TwinInputs, b: TwinInputs): boolean {
  return (
    a.leaf_damage === b.leaf_damage &&
    a.soil_moisture === b.soil_moisture &&
    a.temperature === b.temperature &&
    a.humidity === b.humidity &&
    a.light === b.light
  );
}

/**
 * The digital twin: a what-if on top of the greenhouse's real current state.
 *
 * The scoring is not done here. Every change is sent to the server and scored
 * by the same engine that scores real readings, so what this shows is what the
 * greenhouse would actually do, not an approximation that can drift from it.
 */
export function useTwin(live: Live | null): TwinController {
  const seed = useMemo(() => fromLive(live), [live]);
  const wired = seed.wired;

  const [inputs, setInputs] = useState<TwinInputs>(seed.inputs);
  const [preview, setPreview] = useState<ScorePreview | null>(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Re-seed while the operator has not touched anything, so an open panel keeps
  // tracking the greenhouse. Once they move a slider, their values stand.
  const touchedRef = useRef(false);
  useEffect(() => {
    if (!touchedRef.current) setInputs(seed.inputs);
  }, [seed.inputs]);

  const set = useCallback((key: keyof TwinInputs, value: number) => {
    touchedRef.current = true;
    setInputs((current) => ({ ...current, [key]: value }));
  }, []);

  const resetToCurrent = useCallback(() => {
    touchedRef.current = false;
    setInputs(seed.inputs);
  }, [seed.inputs]);

  // Ask the server what it would do. The previous answer stays on screen while
  // a new one is in flight, so the gauge does not blink on every keystroke.
  useEffect(() => {
    const controller = new AbortController();
    const timer = setTimeout(async () => {
      setPending(true);
      try {
        // A probe the greenhouse does not have is sent as null, so the server
        // renormalises the weights exactly as it does for a real reading.
        const result = await api.post<ScorePreview>(
          '/api/v1/score/preview',
          {
            damage_percentage: inputs.leaf_damage,
            soil_moisture: wired.soil_moisture ? inputs.soil_moisture : null,
            temperature: wired.temperature ? inputs.temperature : null,
            humidity: wired.humidity ? inputs.humidity : null,
            light: wired.light ? inputs.light : null,
          },
          { signal: controller.signal }
        );
        setPreview(result);
        setError(null);
      } catch (err) {
        // A superseded request is not a failure.
        if (err instanceof ApiError && err.code === 'aborted') return;
        setError(err instanceof ApiError && err.code === 'network' ? 'err.serverUnreachable' : 'err.generic');
      } finally {
        setPending(false);
      }
    }, DEBOUNCE_MS);

    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [inputs, wired]);

  return {
    ...inputs,
    set,
    preview,
    pending,
    error,
    atCurrent: same(inputs, seed.inputs),
    resetToCurrent,
    seeded: seed.seeded,
    wired,
  };
}
