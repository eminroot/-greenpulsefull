import { useCallback, useEffect, useRef, useState } from 'react';
import { ActivityIndicator, View } from 'react-native';
import { Image } from 'expo-image';
import { CameraView, useCameraPermissions } from 'expo-camera';
import * as ImagePicker from 'expo-image-picker';
import * as Haptics from 'expo-haptics';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import Animated, { FadeIn, FadeInDown } from 'react-native-reanimated';
import { colors, radius, spacing } from '@/theme';
import { ScreenBackground, Txt, Card, Button, Icon, PressableScale } from '@/components/ui';
import { ResultDetails } from '@/components/result-details';
import { PulseLine } from '@/components/pulse-line';
import { withAlpha } from '@/components/ui/risk-badge';
import { ApiError, api } from '@/api/client';
import type { Capture, ScanStatus, ScanSubmitted } from '@/api/types';
import { useGreenhouse } from '@/store/greenhouse-context';
import { useT } from '@/i18n/i18n-context';
import { useTheme } from '@/theme/theme-context';
import { compressLeafImage } from '@/greenpulse/image';

type Mode = 'capture' | 'preview' | 'sending' | 'waiting' | 'result' | 'failed';

const POLL_MS = 2000;
// The node long polls for work, so a result normally lands in a few seconds.
// This is the point at which we stop waiting and say so.
const GIVE_UP_MS = 180000;

// The node reports a photo its model could not read as "unreadable:<reason>".
// Those get a specific retake instruction; anything else the generic failure.
const UNREADABLE = ['too_dark', 'overexposed', 'no_leaf', 'too_small'];

function failureKey(error: string | null): string {
  const reason = error?.startsWith('unreadable:') ? error.slice('unreadable:'.length) : '';
  return UNREADABLE.includes(reason) ? `scan.unreadable.${reason}` : 'scan.nodeFailed';
}

export default function Scan() {
  const insets = useSafeAreaInsets();
  const { site, live, subscribe, refresh } = useGreenhouse();
  const { t } = useT();
  useTheme();

  const [permission, requestPermission] = useCameraPermissions();
  const cameraRef = useRef<CameraView>(null);

  const [mode, setMode] = useState<Mode>('capture');
  const [facing, setFacing] = useState<'back' | 'front'>('back');
  const [imageUri, setImageUri] = useState<string | null>(null);
  const [jobId, setJobId] = useState<string | null>(null);
  const [capture, setCapture] = useState<Capture | null>(null);
  const [problem, setProblem] = useState<string | null>(null);

  const nodeOnline = !!live?.online;
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const stopWaiting = useCallback(() => {
    if (pollRef.current) clearInterval(pollRef.current);
    if (timeoutRef.current) clearTimeout(timeoutRef.current);
    pollRef.current = null;
    timeoutRef.current = null;
  }, []);

  useEffect(() => stopWaiting, [stopWaiting]);

  const finish = useCallback(
    (result: Capture) => {
      stopWaiting();
      setCapture(result);
      setMode('result');
      refresh();
      Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success).catch(() => {});
    },
    [stopWaiting, refresh]
  );

  // The node's answer usually arrives on the live connection before the poll
  // fires, so take whichever gets here first.
  useEffect(
    () =>
      subscribe((pushed) => {
        if (mode === 'waiting' && pushed.source === 'phone') finish(pushed);
      }),
    [subscribe, mode, finish]
  );

  const capturePhoto = async () => {
    const photo = await cameraRef.current?.takePictureAsync({ quality: 0.7 });
    if (photo?.uri) {
      setImageUri(photo.uri);
      setMode('preview');
    }
  };

  const pickFromLibrary = async () => {
    const res = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ['images'],
      quality: 0.8,
    });
    if (!res.canceled && res.assets[0]?.uri) {
      setImageUri(res.assets[0].uri);
      setMode('preview');
    }
  };

  const send = async () => {
    if (!imageUri || !site) return;

    setMode('sending');
    setProblem(null);
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium).catch(() => {});

    try {
      const compressed = await compressLeafImage(imageUri);
      setImageUri(compressed.uri);

      const form = new FormData();
      form.append('image', {
        uri: compressed.uri,
        name: 'leaf.jpg',
        type: 'image/jpeg',
      } as unknown as Blob);

      const submitted = await api.postForm<ScanSubmitted>(
        `/api/v1/sites/${site.id}/scans`,
        form
      );
      setJobId(submitted.job_id);
      setMode('waiting');
      startPolling(submitted.job_id);
    } catch (err) {
      setProblem(
        err instanceof ApiError && err.code === 'network'
          ? 'err.serverUnreachable'
          : 'scan.uploadFailed'
      );
      setMode('failed');
    }
  };

  const startPolling = (id: string) => {
    stopWaiting();

    pollRef.current = setInterval(async () => {
      try {
        const status = await api.get<ScanStatus>(`/api/v1/scans/${id}`);
        if (status.status === 'done' && status.capture) {
          finish(status.capture);
        } else if (status.status === 'failed' || status.status === 'expired') {
          stopWaiting();
          setProblem(status.status === 'expired' ? 'scan.noNodeAnswered' : failureKey(status.error));
          setMode('failed');
        }
      } catch {
        // keep polling; a dropped request is not a failed scan
      }
    }, POLL_MS);

    timeoutRef.current = setTimeout(() => {
      stopWaiting();
      setProblem('scan.noNodeAnswered');
      setMode('failed');
    }, GIVE_UP_MS);
  };

  const reset = () => {
    stopWaiting();
    setImageUri(null);
    setJobId(null);
    setCapture(null);
    setProblem(null);
    setMode('capture');
  };

  // ---------- result ----------
  if (mode === 'result' && capture) {
    return (
      <ScreenBackground>
        <Animated.ScrollView
          showsVerticalScrollIndicator={false}
          contentContainerStyle={{
            paddingTop: insets.top + 12,
            paddingBottom: insets.bottom + 110,
            paddingHorizontal: spacing.xl,
            gap: spacing.lg,
          }}
        >
          <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }}>
            <Txt variant="title">{t('scan.report')}</Txt>
            <PressableScale haptic={false} onPress={reset} style={{ padding: 6 }}>
              <Icon name="xmark.circle.fill" size={26} color={colors.textMuted} />
            </PressableScale>
          </View>

          <Card padding={spacing.md} borderColor={withAlpha(colors.mint, 0.25)}>
            <View style={{ flexDirection: 'row', gap: 8, alignItems: 'center' }}>
              <Icon name="checkmark.seal.fill" size={15} color={colors.mint} />
              <Txt variant="caption" color={colors.mint} style={{ flex: 1 }}>
                {t('scan.savedToGreenhouse')}
              </Txt>
            </View>
          </Card>

          <ResultDetails capture={capture} imageUri={imageUri ?? undefined} />

          <Button label={t('scan.scanAnother')} variant="secondary" icon="camera.viewfinder" onPress={reset} />
        </Animated.ScrollView>
      </ScreenBackground>
    );
  }

  // ---------- sending / waiting ----------
  if (mode === 'sending' || mode === 'waiting') {
    return (
      <ScreenBackground>
        <View style={{ flex: 1, alignItems: 'center', justifyContent: 'center', padding: spacing.xl, gap: spacing.lg }}>
          {imageUri ? (
            <Image
              source={{ uri: imageUri }}
              style={{ width: 140, height: 140, borderRadius: radius.xl }}
              contentFit="cover"
            />
          ) : null}
          <PulseLine />
          <Txt variant="heading" center>
            {mode === 'sending' ? t('scan.sending') : t('scan.scoring')}
          </Txt>
          <Txt variant="body" center style={{ maxWidth: 280, lineHeight: 21 }}>
            {mode === 'sending' ? t('scan.sendingSub') : t('scan.scoringSub')}
          </Txt>
          <ActivityIndicator color={colors.accentText} />
          <PressableScale haptic={false} onPress={reset} style={{ marginTop: spacing.sm }}>
            <Txt variant="label" color={colors.textMuted}>
              {t('common.cancel')}
            </Txt>
          </PressableScale>
        </View>
      </ScreenBackground>
    );
  }

  // ---------- failed ----------
  if (mode === 'failed') {
    return (
      <ScreenBackground>
        <View style={{ flex: 1, alignItems: 'center', justifyContent: 'center', padding: spacing.xl, gap: spacing.lg }}>
          <Icon name="exclamationmark.triangle.fill" size={40} color={colors.warning} />
          <Txt variant="heading" center>
            {t('scan.notScored')}
          </Txt>
          <Txt variant="body" center style={{ maxWidth: 300, lineHeight: 21 }}>
            {problem ? t(problem) : t('err.generic')}
          </Txt>
          <View style={{ width: '100%', gap: spacing.md, marginTop: spacing.sm }}>
            <Button label={t('scan.tryAgain')} onPress={reset} />
          </View>
        </View>
      </ScreenBackground>
    );
  }

  // ---------- preview ----------
  if (mode === 'preview' && imageUri) {
    return (
      <ScreenBackground>
        <Animated.ScrollView
          showsVerticalScrollIndicator={false}
          contentContainerStyle={{
            paddingTop: insets.top + 12,
            paddingBottom: insets.bottom + 110,
            paddingHorizontal: spacing.xl,
            gap: spacing.lg,
          }}
        >
          <Txt variant="title">{t('scan.preview')}</Txt>
          <Image
            source={{ uri: imageUri }}
            style={{ width: '100%', aspectRatio: 1, borderRadius: radius.xl }}
            contentFit="cover"
          />

          {!nodeOnline ? (
            <Card padding={spacing.md} borderColor={withAlpha(colors.warning, 0.25)}>
              <View style={{ flexDirection: 'row', gap: 8, alignItems: 'center' }}>
                <Icon name="antenna.radiowaves.left.and.right.slash" size={15} color={colors.warning} />
                <Txt variant="caption" color={colors.warning} style={{ flex: 1 }}>
                  {t('scan.nodeOffline')}
                </Txt>
              </View>
            </Card>
          ) : null}

          <View style={{ gap: spacing.md }}>
            <Button
              label={t('scan.analyze')}
              icon="sparkles"
              onPress={send}
              disabled={!site}
            />
            <Button label={t('scan.retake')} variant="ghost" onPress={reset} />
          </View>
        </Animated.ScrollView>
      </ScreenBackground>
    );
  }

  // ---------- capture ----------
  if (!permission) {
    return (
      <ScreenBackground>
        <View style={{ flex: 1, alignItems: 'center', justifyContent: 'center' }}>
          <ActivityIndicator color={colors.accentText} />
        </View>
      </ScreenBackground>
    );
  }

  if (!permission.granted) {
    return (
      <ScreenBackground>
        <View style={{ flex: 1, alignItems: 'center', justifyContent: 'center', padding: spacing.xl, gap: spacing.lg }}>
          <Icon name="camera.fill" size={40} color={colors.textMuted} />
          <Txt variant="heading" center>
            {t('scan.cameraTitle')}
          </Txt>
          <Txt variant="body" center style={{ maxWidth: 280, lineHeight: 21 }}>
            {t('scan.cameraSub')}
          </Txt>
          <View style={{ width: '100%', gap: spacing.md }}>
            <Button label={t('scan.allowCamera')} onPress={requestPermission} />
            <Button label={t('scan.chooseFromLibrary')} variant="secondary" onPress={pickFromLibrary} />
          </View>
        </View>
      </ScreenBackground>
    );
  }

  return (
    <ScreenBackground>
      <View style={{ flex: 1, paddingTop: insets.top + 12, paddingHorizontal: spacing.xl, gap: spacing.lg }}>
        <View>
          <Txt variant="overline">{t('scan.overline')}</Txt>
          <Txt variant="title" style={{ marginTop: 4 }}>
            {t('scan.title')}
          </Txt>
        </View>

        <Animated.View entering={FadeIn.duration(400)} style={{ flex: 1, borderRadius: radius.xl, overflow: 'hidden' }}>
          <CameraView ref={cameraRef} style={{ flex: 1 }} facing={facing} />
        </Animated.View>

        <Animated.View
          entering={FadeInDown.duration(400)}
          style={{
            flexDirection: 'row',
            alignItems: 'center',
            justifyContent: 'space-between',
            paddingBottom: insets.bottom + 96,
          }}
        >
          <PressableScale onPress={pickFromLibrary} style={{ padding: 12 }}>
            <Icon name="photo.on.rectangle" size={24} color={colors.textSecondary} />
          </PressableScale>

          <PressableScale onPress={capturePhoto}>
            <View
              style={{
                width: 72,
                height: 72,
                borderRadius: 99,
                alignItems: 'center',
                justifyContent: 'center',
                backgroundColor: withAlpha(colors.accent, 0.18),
                borderWidth: 2,
                borderColor: colors.accent,
              }}
            >
              <View style={{ width: 54, height: 54, borderRadius: 99, backgroundColor: colors.accent }} />
            </View>
          </PressableScale>

          <PressableScale
            onPress={() => setFacing((f) => (f === 'back' ? 'front' : 'back'))}
            style={{ padding: 12 }}
          >
            <Icon name="arrow.triangle.2.circlepath.camera" size={24} color={colors.textSecondary} />
          </PressableScale>
        </Animated.View>
      </View>
    </ScreenBackground>
  );
}
