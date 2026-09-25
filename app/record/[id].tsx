import { useEffect, useState } from 'react';
import { ActivityIndicator, Alert, View } from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import Animated from 'react-native-reanimated';
import { colors, spacing } from '@/theme';
import { ScreenBackground, Txt, Icon, PressableScale } from '@/components/ui';
import { ResultDetails } from '@/components/result-details';
import { api } from '@/api/client';
import type { Capture } from '@/api/types';
import { useHistory } from '@/store/history-context';
import { useT } from '@/i18n/i18n-context';
import { useTheme } from '@/theme/theme-context';
import { formatDateTime } from '@/utils/format';

export default function RecordDetail() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const { records, remove } = useHistory();
  const { t } = useT();
  useTheme();

  const cached = records.find((r) => r.id === id) ?? null;
  const [record, setRecord] = useState<Capture | null>(cached);
  const [loading, setLoading] = useState(!cached);

  // Opened from a notification or a deep link, the reading may not be in the
  // loaded page of history yet. Fetch it rather than showing "unavailable".
  useEffect(() => {
    if (cached || !id) return;
    let cancelled = false;
    setLoading(true);
    api
      .get<Capture>(`/api/v1/captures/${id}`)
      .then((c) => {
        if (!cancelled) setRecord(c);
      })
      .catch(() => {})
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [id, cached]);

  const onDelete = () => {
    if (!record) return;
    Alert.alert(t('history.deleteTitle'), t('history.deleteMsg'), [
      { text: t('common.cancel'), style: 'cancel' },
      {
        text: t('history.deleteConfirm'),
        style: 'destructive',
        onPress: () => {
          remove(record.id)
            .then(() => router.back())
            .catch(() => Alert.alert(t('history.report'), t('err.deleteFailed')));
        },
      },
    ]);
  };

  return (
    <ScreenBackground>
      <View
        style={{
          flexDirection: 'row',
          alignItems: 'center',
          justifyContent: 'space-between',
          paddingTop: insets.top + 8,
          paddingHorizontal: spacing.lg,
          paddingBottom: spacing.sm,
        }}
      >
        <PressableScale
          haptic={false}
          onPress={() => router.back()}
          style={{ width: 42, height: 42, alignItems: 'center', justifyContent: 'center' }}
        >
          <Icon name="chevron.left" size={22} color={colors.text} />
        </PressableScale>
        <Txt variant="heading">{t('history.report')}</Txt>
        <PressableScale
          haptic={false}
          onPress={onDelete}
          style={{ width: 42, height: 42, alignItems: 'center', justifyContent: 'center' }}
        >
          <Icon name="trash" size={18} color={colors.textMuted} />
        </PressableScale>
      </View>

      {record ? (
        <Animated.ScrollView
          showsVerticalScrollIndicator={false}
          contentContainerStyle={{
            paddingHorizontal: spacing.xl,
            paddingBottom: insets.bottom + 32,
            gap: spacing.lg,
          }}
        >
          <Txt variant="caption" center color={colors.textMuted}>
            {formatDateTime(record.captured_at)}
          </Txt>
          <ResultDetails capture={record} />
        </Animated.ScrollView>
      ) : loading ? (
        <View style={{ flex: 1, alignItems: 'center', justifyContent: 'center' }}>
          <ActivityIndicator color={colors.accentText} />
        </View>
      ) : (
        <View
          style={{
            flex: 1,
            alignItems: 'center',
            justifyContent: 'center',
            gap: spacing.md,
            padding: spacing.xl,
          }}
        >
          <Icon name="doc.questionmark" size={36} color={colors.textMuted} />
          <Txt variant="bodyMedium" center>
            {t('history.unavailable')}
          </Txt>
        </View>
      )}
    </ScreenBackground>
  );
}
