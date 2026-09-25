import { useCallback, useEffect, useState } from 'react';
import { View } from 'react-native';
import { Stack, useRouter, useSegments } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import * as SplashScreen from 'expo-splash-screen';
import { GestureHandlerRootView } from 'react-native-gesture-handler';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { useFonts } from 'expo-font';
import { fontMap } from '@/theme/fonts';
import { colors } from '@/theme';
import { loadStoredBaseUrl } from '@/api/client';
import { ThemeProvider, useTheme } from '@/theme/theme-context';
import { AuthProvider, useAuth } from '@/auth/auth-context';
import { SettingsProvider } from '@/store/settings-context';
import { GreenhouseProvider } from '@/store/greenhouse-context';
import { HistoryProvider } from '@/store/history-context';
import { I18nProvider } from '@/i18n/i18n-context';

SplashScreen.preventAutoHideAsync().catch(() => {});

function RootNavigator({ fontsLoaded }: { fontsLoaded: boolean }) {
  const { user, initializing } = useAuth();
  const { mode } = useTheme();
  const segments = useSegments();
  const router = useRouter();

  const ready = fontsLoaded && !initializing;

  const onLayout = useCallback(() => {
    if (ready) SplashScreen.hideAsync().catch(() => {});
  }, [ready]);

  useEffect(() => {
    if (!ready) return;
    const inAuthGroup = segments[0] === '(auth)';
    if (!user && !inAuthGroup) {
      router.replace('/(auth)/welcome');
    } else if (user && inAuthGroup) {
      router.replace('/(tabs)');
    }
  }, [user, ready, segments, router]);

  if (!ready) return <View style={{ flex: 1, backgroundColor: colors.bg }} />;

  return (
    <View style={{ flex: 1, backgroundColor: colors.bg }} onLayout={onLayout}>
      <StatusBar style={mode === 'dark' ? 'light' : 'dark'} />
      <Stack
        screenOptions={{
          headerShown: false,
          contentStyle: { backgroundColor: colors.bg },
          animation: 'fade',
        }}
      >
        <Stack.Screen name="(auth)" />
        <Stack.Screen name="(tabs)" />
        <Stack.Screen
          name="record/[id]"
          options={{ presentation: 'card', animation: 'slide_from_right' }}
        />
        <Stack.Screen
          name="assistant"
          options={{ presentation: 'modal', animation: 'slide_from_bottom' }}
        />
      </Stack>
    </View>
  );
}

export default function RootLayout() {
  const [fontsLoaded] = useFonts(fontMap);
  const [apiReady, setApiReady] = useState(false);

  // The saved server address has to be in place before anything can call the
  // API, including the session restore that AuthProvider runs on mount.
  useEffect(() => {
    loadStoredBaseUrl().finally(() => setApiReady(true));
  }, []);

  if (!apiReady) {
    return <View style={{ flex: 1, backgroundColor: colors.bg }} />;
  }

  return (
    <GestureHandlerRootView style={{ flex: 1, backgroundColor: colors.bg }}>
      <SafeAreaProvider>
        <ThemeProvider>
          <I18nProvider>
            <AuthProvider>
              <SettingsProvider>
                <GreenhouseProvider>
                  <HistoryProvider>
                    <RootNavigator fontsLoaded={fontsLoaded} />
                  </HistoryProvider>
                </GreenhouseProvider>
              </SettingsProvider>
            </AuthProvider>
          </I18nProvider>
        </ThemeProvider>
      </SafeAreaProvider>
    </GestureHandlerRootView>
  );
}
