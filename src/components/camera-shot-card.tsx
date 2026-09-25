import { useCallback, useEffect, useRef, useState } from 'react';
import { ActivityIndicator, View } from 'react-native';
import { useRouter } from 'expo-router';
import * as Haptics from 'expo-haptics';
import { colors, spacing } from '@/theme';
import { Card, Txt, Icon, PressableScale } from '@/components/ui';
import { withAlpha } from '@/components/ui/risk-badge';
import { ApiError, api } from '@/api/client';
import type { Capture, ScanStatus, ScanSubmitted } from '@/api/types';
import { useGreenhouse } from '@/store/greenhouse-context';
import { useT } from '@/i18n/i18n-context';

type Phase = 'idle' | 'asking' | 'waiting' | 'done' | 'failed';

const POLL_MS = 2000;
// The server gives the node three minutes before it calls the request expired.
// This only covers a server the app has stopped hearing from.
const GIVE_UP_MS = 200000;

const UNREADABLE = ['too_dark', 'overexposed', 'no_leaf', 'too_small'];
const CAMERA_ERRORS = ['camera_unreachable', 'camera_refused', 'camera_failed'];

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
 * and follows the request until the reading lands.
 *
 * The photo, its score and the sensors come back like any scheduled reading,
 * so the dashboard above updates on its own. This card only says how the
 * request went, and opens the new reading when it is in.
 */
export function CameraShotCard() {
  const router = useRouter();
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
      Haptics.notificationAsync(Haptics.NotificationFeedbackType.Warning).catch(() => {});
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
        Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success).catch(() => {});
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
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium).catch(() => {});

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
  const tint = phase === 'failed' ? colors.warning : phase === 'done' ? colors.mint : colors.accent;

  let title = t('shot.title');
  let sub = t('shot.sub');
  if (phase === 'asking') {
    title = t('shot.asking');
  } else if (phase === 'waiting') {
    title = t('shot.waiting');
    sub = nodeQuiet ? t('shot.waitingQuiet') : t('shot.waitingSub');
  } else if (phase === 'done' && result) {
    title = t('shot.done');
    sub = t('shot.doneSub');
  } else if (phase === 'failed') {
    title = t('shot.failed');
    sub = t(problem ?? 'shot.err.camera_failed');
  }

  return (
    <Card padding={spacing.lg} borderColor={withAlpha(tint, 0.25)}>
      <View style={{ flexDirection: 'row', alignItems: 'center', gap: 14 }}>
        <View
          style={{
            width: 46,
            height: 46,
            borderRadius: 14,
            borderCurve: 'continuous',
            alignItems: 'center',
            justifyContent: 'center',
            backgroundColor: withAlpha(tint, 0.14),
          }}
        >
          {busy ? (
            <ActivityIndicator color={colors.accentText} />
          ) : (
            <Icon
              name={
                phase === 'done'
                  ? 'checkmark.circle.fill'
                  : phase === 'failed'
                    ? 'exclamationmark.triangle.fill'
                    : 'camera.aperture'
              }
              size={22}
              color={phase === 'idle' ? colors.accentText : tint}
            />
          )}
        </View>
        <View style={{ flex: 1 }}>
          <Txt variant="bodyMedium">{title}</Txt>
          <Txt variant="caption" style={{ marginTop: 2 }}>
            {sub}
          </Txt>
        </View>
      </View>

      {!busy ? (
        <View style={{ flexDirection: 'row', gap: spacing.sm, marginTop: spacing.md }}>
          {phase === 'done' && result ? (
            <ShotButton
              label={t('shot.open')}
              onPress={() => router.push(`/record/${result.id}`)}
              filled
            />
          ) : null}
          <ShotButton
            label={phase === 'idle' ? t('shot.take') : t('shot.again')}
            onPress={takePhoto}
            filled={phase !== 'done'}
          />
        </View>
      ) : null}
    </Card>
  );
}

function ShotButton({
  label,
  onPress,
  filled,
}: {
  label: string;
  onPress: () => void;
  filled: boolean;
}) {
  return (
    <PressableScale onPress={onPress} style={{ flex: 1 }}>
      <View
        style={{
          alignItems: 'center',
          paddingVertical: 11,
          borderRadius: 99,
          backgroundColor: filled ? withAlpha(colors.accent, 0.16) : 'transparent',
          borderWidth: 1,
          borderColor: withAlpha(colors.accent, filled ? 0.35 : 0.2),
        }}
      >
        <Txt variant="label" color={colors.accentText}>
          {label}
        </Txt>
      </View>
    </PressableScale>
  );
}
