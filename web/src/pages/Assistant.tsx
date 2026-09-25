import { useRef, useState } from 'react';
import { Sparkles, ArrowUp } from 'lucide-react';
import { useT } from '../i18n';
import { useGreenhouse } from '../greenhouse';
import { sendChat, assistantErrorKey, type ChatTurn } from '../chat';
import { LogoMark } from '../components/visuals';

interface Msg {
  id: number;
  role: 'user' | 'model';
  text: string;
  error?: boolean;
}

const SUGGESTIONS = ['asst.s1', 'asst.s2', 'asst.s3', 'asst.s4'];

export function Assistant() {
  const { t, lang } = useT();
  const { live, site } = useGreenhouse();
  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const idRef = useRef(0);
  const scrollRef = useRef<HTMLDivElement>(null);

  const scrollDown = () => requestAnimationFrame(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  });

  const send = async (raw: string) => {
    const text = raw.trim();
    if (!text || sending) return;
    const userMsg: Msg = { id: idRef.current++, role: 'user', text };
    const next = [...messages, userMsg];
    setMessages(next);
    setInput('');
    setSending(true);
    scrollDown();
    try {
      const turns: ChatTurn[] = next.filter((m) => !m.error).map((m) => ({ role: m.role, text: m.text }));
      // The server reads the greenhouse state itself, so nothing about the
      // readings is sent from here.
      const reply = await sendChat(turns, { lang, siteId: site?.id ?? null });
      setMessages((m) => [...m, { id: idRef.current++, role: 'model', text: reply }]);
    } catch (e) {
      const msg = t(assistantErrorKey(e));
      setMessages((m) => [...m, { id: idRef.current++, role: 'model', text: msg, error: true }]);
    } finally {
      setSending(false);
      scrollDown();
    }
  };

  const empty = messages.length === 0;

  return (
    <>
      <div className="page-head">
        <div>
          <span className="overline">{t('asst.menu')}</span>
          <h1 className="page-title">{t('asst.title')}</h1>
        </div>
        <span className="chip" style={{ borderColor: 'var(--border-strong)', color: 'var(--accent)' }}>
          <Sparkles size={13} /> {t(live?.capture ? 'asst.aware' : 'asst.awareEmpty')}
        </span>
      </div>

      <div className="chat-shell card">
        <div className="chat-messages" ref={scrollRef}>
          {empty ? (
            <div className="chat-empty">
              <LogoMark size={52} />
              <h2 style={{ fontFamily: 'var(--font-display)', fontWeight: 600, fontSize: 20 }}>{t('asst.askTitle')}</h2>
              <p className="t2" style={{ maxWidth: 360, textAlign: 'center', fontSize: 14 }}>{t('asst.askSub')}</p>
            </div>
          ) : (
            messages.map((m) =>
              m.role === 'user' ? (
                <div key={m.id} className="bubble-row user">
                  <div className="bubble user">{m.text}</div>
                </div>
              ) : (
                <div key={m.id} className="bubble-row bot">
                  <span className="bot-avatar"><LogoMark size={18} /></span>
                  <div className={`bubble bot${m.error ? ' error' : ''}`}>{m.text}</div>
                </div>
              )
            )
          )}
          {sending ? (
            <div className="bubble-row bot">
              <span className="bot-avatar"><LogoMark size={18} /></span>
              <div className="bubble bot">
                <span className="typing"><i /><i /><i /></span>
              </div>
            </div>
          ) : null}
        </div>

        {empty ? (
          <div className="chat-suggestions">
            {SUGGESTIONS.map((k) => (
              <button key={k} className="suggestion" onClick={() => send(t(k))}>
                {t(k)}
              </button>
            ))}
          </div>
        ) : null}

        <div className="chat-input-bar">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                send(input);
              }
            }}
            placeholder={t('asst.placeholder')}
          />
          <button className="chat-send" disabled={!input.trim() || sending} onClick={() => send(input)}>
            <ArrowUp size={19} />
          </button>
        </div>
      </div>
    </>
  );
}
