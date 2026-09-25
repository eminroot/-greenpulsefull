import { View } from 'react-native';
import { Tabs } from 'expo-router';
import { colors } from '@/theme';
import { useTheme } from '@/theme/theme-context';
import { TabBar } from '@/components/tab-bar';
import { AssistantFab } from '@/components/assistant-fab';

export default function TabsLayout() {
  useTheme(); // re-render the tab group (background) on theme change
  return (
    <View style={{ flex: 1, backgroundColor: colors.bg }}>
      <Tabs
        tabBar={(props) => <TabBar {...props} />}
        screenOptions={{
          headerShown: false,
          sceneStyle: { backgroundColor: colors.bg },
        }}
      >
        <Tabs.Screen name="index" options={{ title: 'Pulse' }} />
        <Tabs.Screen name="scan" options={{ title: 'Scan' }} />
        <Tabs.Screen name="sustainability" options={{ title: 'Sustainability' }} />
        <Tabs.Screen name="history" options={{ title: 'History' }} />
        <Tabs.Screen name="settings" options={{ title: 'Settings' }} />
      </Tabs>
      <AssistantFab />
    </View>
  );
}
