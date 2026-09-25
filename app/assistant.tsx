import { useRef, useState } from 'react';
import {
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  TextInput,
  View,
} from 'react-native';
import { useRouter } from 'expo-router';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import Animated, { FadeIn } from 'react-native-reanimated';
import { colors, font, radius, spacing } from '@/theme';
import { ScreenBackground, Txt, Icon, PressableScale } from '@/components/ui';
import { withAlpha } from '@/components/ui/risk-badge';
import { LogoMark } from '@/components/ui/logo';
import { MessageBubble, type ChatMessage } from '@/components/chat/message-bubble';
import { TypingDots } from '@/components/chat/typing-dots';
import { useGreenhouse } from '@/store/greenhouse-context';
import { useT } from '@/i18n/i18n-context';
import { useTheme } from '@/theme/theme-context';
import { sendChat, assistantErrorKey, type ChatTurn } from '@/chat/gemini';

const SUGGESTIONS = ['assistant.s1', 'assistant.s2', 'assistant.s3', 'assistant.s4'];

export default function Assistant() {
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const { live, site } = useGreenhouse();
  const { t, lang } = useT();
  useTheme();

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const scrollRef = useRef<ScrollView>(null);
  const idRef = useRef(0);
  const nextId = () => `m${idRef.current++}`;

  const send = async (raw: string) => {
    const text = raw.trim();
    if (!text || sending) return;

    const userMsg: ChatMessage = { id: nextId(), role: 'user', text };
    const next = [...messages, userMsg];
    setMessages(next);
    setInput('');
    setSending(true);

    try {
      const turns: ChatTurn[] = next
        .filter((m) => !m.error)
        .map((m) => ({ role: m.role, text: m.text }));
      // The server reads the greenhouse state itself, so nothing about the
      // readings is sent from here.
      const reply = await sendChat(turns, { lang, siteId: site?.id ?? null });
      setMessages((m) => [...m, { id: nextId(), role: 'model', text: reply }]);
    } catch (e) {
      const msg = t(assistantErrorKey(e));
      setMessages((m) => [...m, { id: nextId(), role: 'model', text: msg, error: true }]);
    } finally {
      setSending(false);
    }
  };

  const empty = messages.length === 0;

  return (
    <ScreenBackground>
      {/* header */}
      <View style={{ paddingTop: insets.top + 6, paddingHorizontal: spacing.lg, paddingBottom: spacing.sm }}>
        <View style={{ alignSelf: 'center', width: 38, height: 5, borderRadius: 99, backgroundColor: colors.surfaceHi, marginBottom: spacing.md }} />
        <View style={{ flexDirection: 'row', alignItems: 'center', gap: 12 }}>
          <View
            style={{
              width: 40,
              height: 40,
              borderRadius: 13,
              borderCurve: 'continuous',
              alignItems: 'center',
              justifyContent: 'center',
              backgroundColor: colors.surface,
              borderWidth: 1,
              borderColor: colors.borderStrong,
            }}
          >
            <LogoMark size={24} />
          </View>
          <View style={{ flex: 1 }}>
            <Txt variant="heading">{t('assistant.title')}</Txt>
            <Txt variant="caption" style={{ marginTop: 1 }}>
              {t(live?.capture ? 'assistant.aware' : 'assistant.awareEmpty', { name: live?.site.name ?? '' })}
            </Txt>
          </View>
          <PressableScale haptic={false} onPress={() => router.back()} style={{ padding: 6 }}>
            <Icon name="xmark.circle.fill" size={26} color={colors.textMuted} />
          </PressableScale>
        </View>
      </View>

      <KeyboardAvoidingView
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
        keyboardVerticalOffset={0}
        style={{ flex: 1 }}
      >
        <ScrollView
          ref={scrollRef}
          contentContainerStyle={{
            padding: spacing.lg,
            gap: spacing.md,
            paddingBottom: spacing.lg,
            flexGrow: 1,
          }}
          keyboardShouldPersistTaps="handled"
          showsVerticalScrollIndicator={false}
          onContentSizeChange={() => scrollRef.current?.scrollToEnd({ animated: true })}
        >
          {empty ? (
            <Animated.View entering={FadeIn.duration(400)} style={{ flex: 1, justifyContent: 'center', alignItems: 'center', gap: spacing.md, paddingHorizontal: spacing.md }}>
              <View style={{ opacity: 0.9 }}>
                <LogoMark size={52} />
              </View>
              <Txt variant="heading" center>
                {t('assistant.askTitle')}
              </Txt>
              <Txt variant="body" center style={{ maxWidth: 280 }}>
                {t('assistant.askSub')}
              </Txt>
            </Animated.View>
          ) : (
            messages.map((m) => <MessageBubble key={m.id} message={m} />)
          )}

          {sending ? (
            <View style={{ flexDirection: 'row', gap: 10, alignSelf: 'flex-start', alignItems: 'center', paddingLeft: 4 }}>
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
                }}
              >
                <LogoMark size={18} />
              </View>
              <View style={{ paddingVertical: 12, paddingHorizontal: 16, borderRadius: radius.lg, backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border }}>
                <TypingDots />
              </View>
            </View>
          ) : null}
        </ScrollView>

        {/* suggestions */}
        {empty ? (
          <ScrollView
            horizontal
            showsHorizontalScrollIndicator={false}
            contentContainerStyle={{ gap: 8, paddingHorizontal: spacing.lg, paddingBottom: spacing.sm }}
          >
            {SUGGESTIONS.map((key) => {
              const label = t(key);
              return (
                <PressableScale key={key} onPress={() => send(label)} style={{ borderRadius: radius.pill }}>
                  <View
                    style={{
                      paddingVertical: 9,
                      paddingHorizontal: 14,
                      borderRadius: radius.pill,
                      backgroundColor: colors.surface,
                      borderWidth: 1,
                      borderColor: withAlpha(colors.accent, 0.28),
                    }}
                  >
                    <Txt variant="caption" color={colors.text}>
                      {label}
                    </Txt>
                  </View>
                </PressableScale>
              );
            })}
          </ScrollView>
        ) : null}

        {/* input bar */}
        <View
          style={{
            flexDirection: 'row',
            alignItems: 'flex-end',
            gap: 10,
            paddingHorizontal: spacing.lg,
            paddingTop: spacing.sm,
            paddingBottom: insets.bottom > 0 ? insets.bottom : spacing.md,
          }}
        >
          <View
            style={{
              flex: 1,
              minHeight: 48,
              maxHeight: 120,
              justifyContent: 'center',
              paddingHorizontal: 16,
              borderRadius: radius.xl,
              borderCurve: 'continuous',
              backgroundColor: colors.surface,
              borderWidth: 1,
              borderColor: colors.border,
            }}
          >
            <TextInput
              value={input}
              onChangeText={setInput}
              placeholder={t('assistant.placeholder')}
              placeholderTextColor={colors.textMuted}
              multiline
              style={{
                color: colors.text,
                fontFamily: font.bodyMedium,
                fontSize: 15.5,
                paddingVertical: 12,
                maxHeight: 96,
              }}
            />
          </View>
          <PressableScale
            onPress={() => send(input)}
            disabled={!input.trim() || sending}
            style={{
              width: 48,
              height: 48,
              borderRadius: 99,
              alignItems: 'center',
              justifyContent: 'center',
              backgroundColor: input.trim() && !sending ? colors.accent : colors.surfaceHi,
            }}
          >
            <Icon name="arrow.up" size={20} color={input.trim() && !sending ? colors.textInverse : colors.textMuted} weight="bold" />
          </PressableScale>
        </View>
      </KeyboardAvoidingView>
    </ScreenBackground>
  );
}
