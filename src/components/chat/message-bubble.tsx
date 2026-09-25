import { View } from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import Animated, { FadeInDown } from 'react-native-reanimated';
import { colors, gradients, radius, spacing } from '@/theme';
import { Txt } from '@/components/ui/text';
import { LogoMark } from '@/components/ui/logo';

export interface ChatMessage {
  id: string;
  role: 'user' | 'model';
  text: string;
  error?: boolean;
}

export function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === 'user';

  if (isUser) {
    return (
      <Animated.View entering={FadeInDown.duration(260)} style={{ alignSelf: 'flex-end', maxWidth: '86%' }}>
        <LinearGradient
          colors={gradients.brand}
          start={{ x: 0, y: 0 }}
          end={{ x: 1, y: 1 }}
          style={{
            paddingVertical: 11,
            paddingHorizontal: 15,
            borderRadius: radius.lg,
            borderBottomRightRadius: 6,
            borderCurve: 'continuous',
          }}
        >
          <Txt variant="bodyMedium" color={colors.textInverse} selectable style={{ lineHeight: 21 }}>
            {message.text}
          </Txt>
        </LinearGradient>
      </Animated.View>
    );
  }

  return (
    <Animated.View
      entering={FadeInDown.duration(260)}
      style={{ flexDirection: 'row', gap: 10, alignSelf: 'flex-start', maxWidth: '90%' }}
    >
      <View
        style={{
          width: 30,
          height: 30,
          borderRadius: 10,
          borderCurve: 'continuous',
          alignItems: 'center',
          justifyContent: 'center',
          backgroundColor: colors.surface,
          borderWidth: 1,
          borderColor: colors.borderStrong,
          marginTop: 2,
        }}
      >
        <LogoMark size={18} />
      </View>
      <View
        style={{
          flex: 1,
          paddingVertical: 11,
          paddingHorizontal: 15,
          borderRadius: radius.lg,
          borderBottomLeftRadius: 6,
          borderCurve: 'continuous',
          backgroundColor: colors.surface,
          borderWidth: 1,
          borderColor: message.error ? 'rgba(248,113,113,0.3)' : colors.border,
        }}
      >
        <Txt
          variant="bodyMedium"
          color={message.error ? colors.danger : colors.text}
          selectable
          style={{ lineHeight: 21 }}
        >
          {message.text}
        </Txt>
      </View>
    </Animated.View>
  );
}
