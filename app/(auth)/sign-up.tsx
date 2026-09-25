import { useMemo, useState } from 'react';
import { KeyboardAvoidingView, Platform, ScrollView, View } from 'react-native';
import { useRouter } from 'expo-router';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import Animated, { FadeIn, FadeInDown } from 'react-native-reanimated';
import { colors, spacing } from '@/theme';
import { ScreenBackground, Button, Txt, Icon, PressableScale } from '@/components/ui';
import { Input } from '@/components/ui/input';
import { GoogleSection } from '@/components/google-section';
import { useAuth } from '@/auth/auth-context';
import { useT } from '@/i18n/i18n-context';
import { useTheme } from '@/theme/theme-context';
import {
  friendlyAuthError,
  passwordStrength,
  validateEmail,
  validatePassword,
} from '@/auth/validation';

export default function SignUp() {
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const { signUp } = useAuth();
  const { t } = useT();
  useTheme();

  // Read at render so the colors follow the active theme.
  const STRENGTH_COLORS = [colors.danger, colors.warning, colors.mint, colors.primary];

  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const strength = useMemo(() => passwordStrength(password), [password]);

  const submit = async () => {
    const emailErr = validateEmail(email);
    if (emailErr) return setError(t(emailErr));
    const passErr = validatePassword(password);
    if (passErr) return setError(t(passErr));

    setError(null);
    setLoading(true);
    try {
      await signUp(email, password, name);
    } catch (e) {
      setError(t(friendlyAuthError(e)));
    } finally {
      setLoading(false);
    }
  };

  return (
    <ScreenBackground>
      <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : undefined} style={{ flex: 1 }}>
        <ScrollView
          contentContainerStyle={{
            paddingTop: insets.top + 8,
            paddingBottom: insets.bottom + 24,
            paddingHorizontal: spacing.xl,
            flexGrow: 1,
          }}
          keyboardShouldPersistTaps="handled"
          showsVerticalScrollIndicator={false}
        >
          <PressableScale
            haptic={false}
            onPress={() => router.back()}
            style={{ width: 42, height: 42, alignItems: 'center', justifyContent: 'center', marginLeft: -8 }}
          >
            <Icon name="chevron.left" size={22} color={colors.textSecondary} />
          </PressableScale>

          <Animated.View entering={FadeInDown.duration(500)} style={{ marginTop: spacing.lg }}>
            <Txt variant="display" style={{ fontSize: 32 }}>
              {t('auth.createTitle')}
            </Txt>
            <Txt variant="body" style={{ marginTop: 8, fontSize: 15.5 }}>
              {t('auth.createSubtitle')}
            </Txt>
          </Animated.View>

          <Animated.View entering={FadeInDown.duration(500).delay(120)} style={{ marginTop: spacing.xl, gap: spacing.lg }}>
            <Input
              label={t('auth.name')}
              icon="person.fill"
              placeholder={t('auth.namePlaceholder')}
              autoCapitalize="words"
              textContentType="name"
              value={name}
              onChangeText={setName}
            />
            <Input
              label={t('auth.email')}
              icon="envelope.fill"
              placeholder={t('auth.emailPlaceholder')}
              keyboardType="email-address"
              autoCapitalize="none"
              autoComplete="email"
              textContentType="emailAddress"
              value={email}
              onChangeText={(t) => {
                setEmail(t);
                if (error) setError(null);
              }}
            />
            <View>
              <Input
                label={t('auth.password')}
                icon="lock.fill"
                placeholder={t('auth.passwordCreatePlaceholder')}
                secure
                autoCapitalize="none"
                textContentType="newPassword"
                value={password}
                onChangeText={(t) => {
                  setPassword(t);
                  if (error) setError(null);
                }}
              />
              {password.length > 0 ? (
                <Animated.View entering={FadeIn.duration(200)} style={{ marginTop: 12, gap: 8 }}>
                  <View style={{ flexDirection: 'row', gap: 6 }}>
                    {[0, 1, 2].map((i) => (
                      <View
                        key={i}
                        style={{
                          flex: 1,
                          height: 4,
                          borderRadius: 99,
                          backgroundColor:
                            i <= strength.score - 1 ? STRENGTH_COLORS[strength.score] : colors.surfaceHi,
                        }}
                      />
                    ))}
                  </View>
                  <Txt variant="caption" color={strength.meetsPolicy ? colors.mint : colors.textMuted}>
                    {strength.meetsPolicy ? t('auth.strength', { label: t(strength.labelKey) }) : t('auth.policy')}
                  </Txt>
                </Animated.View>
              ) : null}
            </View>

            {error ? (
              <Animated.View entering={FadeIn.duration(200)}>
                <View
                  style={{
                    flexDirection: 'row',
                    alignItems: 'center',
                    gap: 8,
                    padding: spacing.md,
                    borderRadius: 14,
                    borderCurve: 'continuous',
                    backgroundColor: 'rgba(248,113,113,0.1)',
                    borderWidth: 1,
                    borderColor: 'rgba(248,113,113,0.25)',
                  }}
                >
                  <Icon name="exclamationmark.triangle.fill" size={15} color={colors.danger} />
                  <Txt variant="caption" color={colors.danger} style={{ flex: 1 }}>
                    {error}
                  </Txt>
                </View>
              </Animated.View>
            ) : null}

            <Button label={t('auth.create')} loading={loading} onPress={submit} style={{ marginTop: 4 }} />

            <GoogleSection onError={setError} />
          </Animated.View>

          <View style={{ flex: 1 }} />
          <Animated.View
            entering={FadeIn.duration(400).delay(300)}
            style={{ flexDirection: 'row', justifyContent: 'center', gap: 6, marginTop: spacing.xl }}
          >
            <Txt variant="body">{t('auth.haveQ')}</Txt>
            <PressableScale haptic={false} onPress={() => router.replace('/(auth)/sign-in')}>
              <Txt variant="bodyMedium" color={colors.accentText}>
                {t('auth.signInLink')}
              </Txt>
            </PressableScale>
          </Animated.View>
        </ScrollView>
      </KeyboardAvoidingView>
    </ScreenBackground>
  );
}
