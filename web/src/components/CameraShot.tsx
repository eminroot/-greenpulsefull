import { useCallback, useEffect, useRef, useState } from 'react';
import { Aperture, AlertTriangle, CheckCircle2 } from 'lucide-react';
import { ApiError, api } from '../api/client';
import { useGreenhouse } from '../greenhouse';
import { useT } from '../i18n';
import type { Capture, ScanStatus, ScanSubmitted } from '../types';

type Phase = 'idle' | 'asking' | 'waiting' | 'done' | 'failed';

const POLL_MS = 2000;
// The server gives the node three minutes before it calls the request expired.
// This only covers a server the panel has stopped hearing from.
const GIVE_UP_MS = 200000;

const UNREADABLE = ['too_dark', 'overexposed', 'no_leaf', 'too_small'];
const CAMERA_ERRORS = ['camera_unreachable', 'camera_refused', 'camera_outdated', 'camera_failed'];

// The node reports why a photo was not taken as a code. Each gets its own text.
function failureKey(status: ScanStatus['status'] | 'gave_up', error: string | null): string {
  if (status === 'expired' || status === 'gave_up') return 'shot.err.noAnswer';
  if (error?.startsWith('unreadable:')) {
    const reason = error.slice('unreadable:'.length);
    if (UNREADABLE.includes(reason)) return `shot.unreadable.${reason}`;
  }
  if (error && CAMERA_ERRORS.includes(error)) return `shot.err.${error}`;
  return 'shot.err.camera_failed';
}

function requestErrorKey(err: unknown): string {
  if (err instanceof ApiError) {
    if (err.code === 'network' || err.code === 'timeout') return 'err.serverUnreachable';
    if (err.status === 429) return 'shot.err.tooMany';
  }
  return 'shot.err.request';
}

/**
 * "Take a photo now". Asks the greenhouse camera for a photo off its schedule
 * and follows the request until the reading lands. The photo, its score and
 * the sensors arrive like any scheduled reading, so the page updates on its
 * own; this only says how the request went and opens the new reading.
 */
export function CameraShot({ onOpen }: { onOpen: (capture: Capture) => void }) {
  const { site, subscribe, refresh } = useGreenhouse();
  const { t } = useT();

  const [phase, setPhase] = useState<Phase>('idle');
  const [problem, setProblem] = useState<string | null>(null);
  const [result, setResult] = useState<Capture | null>(null);
  const [nodeQuiet, setNodeQuiet] = useState(false);

  const jobRef = useRef<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const stopWatching = useCallback(() => {
    if (pollRef.current) clearInterval(pollRef.current);
    if (timeoutRef.current) clearTimeout(timeoutRef.current);
    pollRef.current = null;
    timeoutRef.current = null;
    jobRef.current = null;
  }, []);

  useEffect(() => stopWatching, [stopWatching]);

  // Another greenhouse means another camera. Drop whatever was in flight.
  const siteId = site?.id ?? null;
  useEffect(() => {
    stopWatching();
    setPhase('idle');
    setProblem(null);
    setResult(null);
  }, [siteId, stopWatching]);

  const fail = useCallback(
    (key: string) => {
      stopWatching();
      setProblem(key);
      setPhase('failed');
    },
    [stopWatching]
  );

  const check = useCallback(async () => {
    const id = jobRef.current;
    if (!id) return;
    try {
      const status = await api.get<ScanStatus>(`/api/v1/scans/${id}`);
      if (jobRef.current !== id) return;
      if (status.status === 'done' && status.capture) {
        stopWatching();
        setResult(status.capture);
        setPhase('done');
        refresh();
      } else if (status.status === 'failed' || status.status === 'expired') {
        fail(failureKey(status.status, status.error));
      }
    } catch {
      // a dropped poll is not a failed photo; the next one will tell
    }
  }, [stopWatching, refresh, fail]);

  // The new reading usually lands on the live connection before the next poll
  // would, so any push is a cue to look right away.
  useEffect(
    () =>
      subscribe(() => {
        if (jobRef.current) check();
      }),
    [subscribe, check]
  );

  const takePhoto = async () => {
    if (!site || phase === 'asking' || phase === 'waiting') return;
    setPhase('asking');
    setProblem(null);
    setResult(null);
    try {
      const submitted = await api.post<ScanSubmitted>(`/api/v1/sites/${site.id}/camera/capture`);
      stopWatching();
      jobRef.current = submitted.job_id;
      setNodeQuiet(!submitted.node_online);
      setPhase('waiting');
      pollRef.current = setInterval(check, POLL_MS);
      timeoutRef.current = setTimeout(() => fail(failureKey('gave_up', null)), GIVE_UP_MS);
    } catch (err) {
      fail(requestErrorKey(err));
    }
  };

  const busy = phase === 'asking' || phase === 'waiting';

  let note: string | null = null;
  if (phase === 'waiting') note = nodeQuiet ? t('shot.waitingQuiet') : t('shot.waitingSub');
  else if (phase === 'done') note = t('shot.doneSub');
  else if (phase === 'failed') note = t(problem ?? 'shot.err.camera_failed');

  return (
    <div className="shot">
      <div className="shot-actions">
        {phase === 'done' && result ? (
          <button className="btn btn-secondary btn-sm shot-btn" onClick={() => onOpen(result)}>
            <CheckCircle2 size={15} color="var(--mint)" />
            {t('shot.open')}
          </button>
        ) : null}
        <button
          className="btn btn-primary btn-sm shot-btn"
          onClick={takePhoto}
          disabled={busy || !site}
          title={t('shot.sub')}
        >
          {busy ? (
            <span className="spinner" style={{ width: 14, height: 14 }} />
          ) : (
            <Aperture size={15} />
          )}
          {phase === 'asking'
            ? t('shot.asking')
            : phase === 'waiting'
              ? t('shot.waiting')
              : phase === 'idle'
                ? t('shot.take')
                : t('shot.again')}
        </button>
      </div>
      {note ? (
        <p className={`shot-note${phase === 'failed' ? ' is-failed' : ''}`} role="status">
          {phase === 'failed' ? <AlertTriangle size={13} /> : null}
          {phase === 'done' ? <strong>{t('shot.done')}. </strong> : null}
          {note}
        </p>
      ) : null}
    </div>
  );
}
