import { useCallback, useEffect, useState } from 'react';
import { Alert, Switch, View } from 'react-native';
import * as Clipboard from 'expo-clipboard';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import Animated, { FadeIn, FadeInDown } from 'react-native-reanimated';
import { colors, radius, spacing } from '@/theme';
import { ScreenBackground, Txt, Card, Button, Icon, PressableScale } from '@/components/ui';
import { Input } from '@/components/ui/input';
import { withAlpha } from '@/components/ui/risk-badge';
import { ApiError, api, getBaseUrl } from '@/api/client';
import type { Device, PairedDevice } from '@/api/types';
import { useAuth } from '@/auth/auth-context';
import { useSettings } from '@/store/settings-context';
import { useGreenhouse } from '@/store/greenhouse-context';
import { useT } from '@/i18n/i18n-context';
import { useTheme } from '@/theme/theme-context';
import { LANGS, LANG_LABEL, LANG_NAME } from '@/i18n/translations';
import { timeAgo } from '@/utils/format';

const THEMES = [
  { mode: 'dark' as const, key: 'settings.themeDark', symbol: 'moon.fill' },
  { mode: 'light' as const, key: 'settings.themeLight', symbol: 'sun.max.fill' },
];

export default function Settings() {
  const insets = useSafeAreaInsets();
  const { user, signOut, deleteAccount } = useAuth();
  const { serverUrl, serverStatus, setServerUrl, checkServer, autopilot, setAutopilot } =
    useSettings();
  const { site, reloadSites } = useGreenhouse();
  const { t, lang, setLang } = useT();
  const { mode, setMode } = useTheme();

  const [draftUrl, setDraftUrl] = useState(serverUrl);
  const [testing, setTesting] = useState(false);

  const [devices, setDevices] = useState<Device[]>([]);
  const [pairing, setPairing] = useState(false);
  const [newToken, setNewToken] = useState<PairedDevice | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => setDraftUrl(serverUrl), [serverUrl]);

  const initials =
    (user?.display_name || user?.email || 'G')
      .split(' ')
      .map((p) => p[0])
      .slice(0, 2)
      .join('')
      .toUpperCase();

  const statusMeta: Record<string, { color: string; key: string }> = {
    unknown: { color: colors.textMuted, key: 'settings.server.unknown' },
    checking: { color: colors.warning, key: 'settings.server.checking' },
    online: { color: colors.mint, key: 'settings.server.online' },
    offline: { color: colors.danger, key: 'settings.server.offline' },
  };
  const status = statusMeta[serverStatus];

  const loadDevices = useCallback(async () => {
    if (!site) return;
    try {
      setDevices(await api.get<Device[]>(`/api/v1/sites/${site.id}/devices`));
    } catch {
      // the greenhouse card simply shows nothing paired
    }
  }, [site?.id]);

  useEffect(() => {
    loadDevices();
  }, [loadDevices]);

  const testConnection = async () => {
    setTesting(true);
    await setServerUrl(draftUrl);
    setTesting(false);
  };

  const pairDevice = async () => {
    if (!site) return;
    setPairing(true);
    setCopied(false);
    try {
      const created = await api.post<PairedDevice>(`/api/v1/sites/${site.id}/devices`, {
        name: t('settings.nodeDefaultName'),
        kind: 'pi',
      });
      setNewToken(created);
      await loadDevices();
      await reloadSites();
    } catch (err) {
      Alert.alert(
        t('settings.greenhouse'),
        t(err instanceof ApiError && err.code === 'network' ? 'err.serverUnreachable' : 'err.generic')
      );
    } finally {
      setPairing(false);
    }
  };

  const copyToken = async () => {
    if (!newToken) return;
    await Clipboard.setStringAsync(newToken.token);
    setCopied(true);
  };

  const revokeDevice = (device: Device) => {
    Alert.alert(t('settings.removeNodeTitle'), t('settings.removeNodeMsg', { name: device.name }), [
      { text: t('common.cancel'), style: 'cancel' },
      {
        text: t('settings.removeNodeConfirm'),
        style: 'destructive',
        onPress: async () => {
          try {
            await api.delete(`/api/v1/devices/${device.id}`);
            await loadDevices();
          } catch {
            Alert.alert(t('settings.greenhouse'), t('err.generic'));
          }
        },
      },
    ]);
  };

  const confirmDelete = () => {
    Alert.alert(t('settings.deleteTitle'), t('settings.deleteMsg'), [
      { text: t('common.cancel'), style: 'cancel' },
      { text: t('settings.deleteConfirm'), style: 'destructive', onPress: runDelete },
    ]);
  };

  const runDelete = async () => {
    try {
      await deleteAccount();
    } catch {
      Alert.alert(t('settings.deleteAccount'), t('settings.deleteFailed'));
    }
  };

  return (
    <ScreenBackground>
      <Animated.ScrollView
        showsVerticalScrollIndicator={false}
        contentContainerStyle={{
          paddingTop: insets.top + 12,
          paddingBottom: insets.bottom + 96,
          paddingHorizontal: spacing.xl,
          gap: spacing.lg,
        }}
      >
        <Txt variant="title">{t('settings.title')}</Txt>

        {/* account */}
        <Animated.View entering={FadeInDown.duration(450)}>
          <Card>
            <View style={{ flexDirection: 'row', alignItems: 'center', gap: 14 }}>
              <View
                style={{
                  width: 56,
                  height: 56,
                  borderRadius: 18,
                  borderCurve: 'continuous',
                  alignItems: 'center',
                  justifyContent: 'center',
                  backgroundColor: withAlpha(colors.primary, 0.16),
                  borderWidth: 1,
                  borderColor: colors.borderStrong,
                }}
              >
                <Txt variant="numeric" style={{ fontSize: 20, color: colors.accentText }}>
                  {initials}
                </Txt>
              </View>
              <View style={{ flex: 1 }}>
                <Txt variant="heading">{user?.display_name || t('settings.grower')}</Txt>
                <Txt variant="caption" selectable style={{ marginTop: 2 }}>
                  {user?.email}
                </Txt>
              </View>
            </View>
          </Card>
        </Animated.View>

        {/* greenhouse + nodes */}
        <Animated.View entering={FadeInDown.duration(450).delay(60)}>
          <Card>
            <Txt variant="overline">{t('settings.greenhouse')}</Txt>
            <Txt variant="heading" style={{ marginTop: 6 }}>
              {site?.name ?? t('settings.noGreenhouse')}
            </Txt>
            <Txt variant="body" style={{ marginTop: 8, lineHeight: 20 }}>
              {t('settings.greenhouseDesc')}
            </Txt>

            {devices.length ? (
              <View style={{ marginTop: spacing.lg, gap: spacing.sm }}>
                {devices.map((d) => (
                  <View
                    key={d.id}
                    style={{
                      flexDirection: 'row',
                      alignItems: 'center',
                      gap: 10,
                      paddingVertical: 10,
                      paddingHorizontal: 12,
                      borderRadius: radius.md,
                      borderCurve: 'continuous',
                      backgroundColor: colors.surface2,
                      borderWidth: 1,
                      borderColor: colors.border,
                    }}
                  >
                    <View
                      style={{
                        width: 8,
                        height: 8,
                        borderRadius: 99,
                        backgroundColor: d.online ? colors.mint : colors.textMuted,
                      }}
                    />
                    <View style={{ flex: 1 }}>
                      <Txt variant="bodyMedium">{d.name}</Txt>
                      <Txt variant="caption" style={{ marginTop: 1 }}>
                        {d.online
                          ? t('settings.nodeOnline')
                          : d.last_seen_at
                            ? t('settings.nodeLastSeen', { when: timeAgo(d.last_seen_at) })
                            : t('settings.nodeNeverSeen')}
                      </Txt>
                    </View>
                    <PressableScale haptic={false} onPress={() => revokeDevice(d)} style={{ padding: 6 }}>
                      <Icon name="trash" size={15} color={colors.textMuted} />
                    </PressableScale>
                  </View>
                ))}
              </View>
            ) : null}

            <View style={{ marginTop: spacing.lg }}>
              <Button
                label={t('settings.pairNode')}
                variant="secondary"
                icon="antenna.radiowaves.left.and.right"
                loading={pairing}
                disabled={!site}
                onPress={pairDevice}
              />
            </View>

            {/* Shown once. The server keeps only a hash, so it cannot be shown again. */}
            {newToken ? (
              <Animated.View entering={FadeIn.duration(300)} style={{ marginTop: spacing.lg }}>
                <View
                  style={{
                    padding: spacing.md,
                    borderRadius: radius.md,
                    borderCurve: 'continuous',
                    backgroundColor: withAlpha(colors.accent, 0.1),
                    borderWidth: 1,
                    borderColor: withAlpha(colors.accent, 0.3),
                    gap: 10,
                  }}
                >
                  <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
                    <Icon name="key.fill" size={14} color={colors.accentText} />
                    <Txt variant="label" color={colors.accentText} style={{ flex: 1 }}>
                      {t('settings.tokenTitle')}
                    </Txt>
                  </View>
                  <Txt variant="caption" style={{ lineHeight: 18 }}>
                    {t('settings.tokenOnce')}
                  </Txt>
                  <Txt
                    variant="caption"
                    selectable
                    style={{ fontVariant: ['tabular-nums'], color: colors.text }}
                  >
                    {newToken.token}
                  </Txt>
                  <View style={{ flexDirection: 'row', gap: spacing.sm }}>
                    <Button
                      label={copied ? t('settings.copied') : t('settings.copyToken')}
                      variant="secondary"
                      icon={copied ? 'checkmark' : 'doc.on.doc'}
                      onPress={copyToken}
                    />
                    <Button
                      label={t('common.done')}
                      variant="ghost"
                      fullWidth={false}
                      onPress={() => setNewToken(null)}
                    />
                  </View>
                </View>
              </Animated.View>
            ) : null}
          </Card>
        </Animated.View>

        {/* server */}
        <Animated.View entering={FadeInDown.duration(450).delay(120)}>
          <Card>
            <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }}>
              <Txt variant="overline">{t('settings.server')}</Txt>
              <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6 }}>
                <View
                  style={{
                    width: 7,
                    height: 7,
                    borderRadius: 99,
                    backgroundColor: status.color,
                    boxShadow: `0 0 8px ${status.color}`,
                  }}
                />
                <Txt variant="caption" color={status.color}>
                  {t(status.key)}
                </Txt>
              </View>
            </View>

            <Txt variant="body" style={{ marginTop: 10, lineHeight: 20 }}>
              {t('settings.serverDesc')}
            </Txt>

            <View style={{ marginTop: spacing.lg, gap: spacing.md }}>
              <Input
                icon="link"
                placeholder={getBaseUrl()}
                autoCapitalize="none"
                keyboardType="url"
                value={draftUrl}
                onChangeText={setDraftUrl}
              />
              <Button
                label={t('settings.test')}
                variant="secondary"
                icon="antenna.radiowaves.left.and.right"
                loading={testing}
                onPress={testConnection}
              />
            </View>
          </Card>
        </Animated.View>

        {/* language */}
        <Animated.View entering={FadeInDown.duration(450).delay(160)}>
          <Card>
            <Txt variant="overline">{t('settings.language')}</Txt>
            <View style={{ flexDirection: 'row', gap: spacing.sm, marginTop: spacing.md }}>
              {LANGS.map((l) => {
                const active = l === lang;
                return (
                  <PressableScale key={l} onPress={() => setLang(l)} style={{ flex: 1, borderRadius: radius.md }}>
                    <View
                      style={{
                        paddingVertical: 12,
                        borderRadius: radius.md,
                        borderCurve: 'continuous',
                        alignItems: 'center',
                        gap: 2,
                        backgroundColor: active ? withAlpha(colors.primary, 0.16) : colors.surface2,
                        borderWidth: 1,
                        borderColor: active ? withAlpha(colors.accent, 0.4) : colors.border,
                      }}
                    >
                      <Txt variant="label" color={active ? colors.accentText : colors.text}>
                        {LANG_LABEL[l]}
                      </Txt>
                      <Txt variant="caption" color={colors.textMuted} style={{ fontSize: 11 }}>
                        {LANG_NAME[l]}
                      </Txt>
                    </View>
                  </PressableScale>
                );
              })}
            </View>
          </Card>
        </Animated.View>

        {/* appearance */}
        <Animated.View entering={FadeInDown.duration(450).delay(200)}>
          <Card>
            <Txt variant="overline">{t('settings.appearance')}</Txt>
            <View style={{ flexDirection: 'row', gap: spacing.sm, marginTop: spacing.md }}>
              {THEMES.map((th) => {
                const active = th.mode === mode;
                return (
                  <PressableScale key={th.mode} onPress={() => setMode(th.mode)} style={{ flex: 1, borderRadius: radius.md }}>
                    <View
                      style={{
                        flexDirection: 'row',
                        justifyContent: 'center',
                        alignItems: 'center',
                        gap: 8,
                        paddingVertical: 13,
                        borderRadius: radius.md,
                        borderCurve: 'continuous',
                        backgroundColor: active ? withAlpha(colors.primary, 0.16) : colors.surface2,
                        borderWidth: 1,
                        borderColor: active ? withAlpha(colors.accent, 0.4) : colors.border,
                      }}
                    >
                      <Icon name={th.symbol} size={16} color={active ? colors.accentText : colors.textMuted} />
                      <Txt variant="label" color={active ? colors.accentText : colors.text}>
                        {t(th.key)}
                      </Txt>
                    </View>
                  </PressableScale>
                );
              })}
            </View>
          </Card>
        </Animated.View>

        {/* autopilot */}
        <Animated.View entering={FadeInDown.duration(450).delay(240)}>
          <Card>
            <View style={{ flexDirection: 'row', alignItems: 'center', gap: 14 }}>
              <View
                style={{
                  width: 44,
                  height: 44,
                  borderRadius: 14,
                  borderCurve: 'continuous',
                  alignItems: 'center',
                  justifyContent: 'center',
                  backgroundColor: withAlpha(colors.accent, 0.14),
                }}
              >
                <Icon name="bolt.badge.automatic.fill" size={20} color={colors.accentText} />
              </View>
              <View style={{ flex: 1 }}>
                <Txt variant="bodyMedium">{t('settings.autonomous')}</Txt>
                <Txt variant="caption" style={{ marginTop: 2 }}>
                  {t('settings.autonomousDesc')}
                </Txt>
              </View>
              <Switch
                value={autopilot}
                onValueChange={setAutopilot}
                trackColor={{ false: colors.surfaceHi, true: colors.primary }}
                thumbColor={colors.white}
                ios_backgroundColor={colors.surfaceHi}
              />
            </View>
          </Card>
        </Animated.View>

        {/* about */}
        <Animated.View entering={FadeInDown.duration(450).delay(280)}>
          <Card>
            <Txt variant="overline">{t('settings.about')}</Txt>
            <Txt variant="body" style={{ marginTop: 10, lineHeight: 21 }}>
              {t('settings.aboutDesc')}
            </Txt>
            <View style={{ height: 1, backgroundColor: colors.border, marginVertical: spacing.md }} />
            <AboutRow symbol="drop.fill" label={t('settings.water')} value={t('settings.waterValue')} />
            <AboutRow symbol="bolt.fill" label={t('settings.energy')} value={t('settings.energyValue')} />
            <AboutRow symbol="number" label={t('settings.version')} value="2.0.0" />
          </Card>
        </Animated.View>

        <Animated.View entering={FadeInDown.duration(450).delay(320)} style={{ marginTop: spacing.sm, gap: spacing.md }}>
          <Button
            label={t('settings.signOut')}
            variant="secondary"
            icon="rectangle.portrait.and.arrow.right"
            onPress={signOut}
          />
          <Button label={t('settings.deleteAccount')} variant="danger" icon="trash" onPress={confirmDelete} />
        </Animated.View>
      </Animated.ScrollView>
    </ScreenBackground>
  );
}

function AboutRow({ symbol, label, value }: { symbol: string; label: string; value: string }) {
  return (
    <View style={{ flexDirection: 'row', alignItems: 'center', gap: 10, paddingVertical: 7 }}>
      <Icon name={symbol} size={15} color={colors.textMuted} />
      <Txt variant="body" style={{ flex: 1 }}>
        {label}
      </Txt>
      <Txt variant="bodyMedium">{value}</Txt>
    </View>
  );
}
