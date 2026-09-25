import { useState } from 'react';
import { Mail, Lock, ArrowRight, AlertTriangle } from 'lucide-react';
import { useAuth, friendlyAuthError } from '../auth';
import { GoogleSignIn, googleClientId } from '../googleSignIn';
import { useT, LangToggle } from '../i18n';
import { ThemeToggle } from '../theme';
import { LogoMark, PulseLine } from '../components/visuals';

export function Login() {
  const { signIn, signInWithGoogle } = useAuth();
  const { t } = useT();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim() || !password) {
      setError(t('login.enterBoth'));
      return;
    }
    setError(null);
    setLoading(true);
    try {
      await signIn(email, password);
    } catch (err) {
      setError(t(friendlyAuthError(err)));
    } finally {
      setLoading(false);
    }
  };

  const onGoogleToken = async (idToken: string) => {
    setError(null);
    setLoading(true);
    try {
      await signInWithGoogle(idToken);
    } catch (err) {
      setError(t(friendlyAuthError(err)));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-wrap">
      <div style={{ position: 'absolute', top: 20, right: 20, display: 'flex', gap: 10, alignItems: 'center' }}>
        <ThemeToggle />
        <LangToggle />
      </div>
      <div className="login-card fade-up">
        <div className="login-logo">
          <div className="logo-badge"><LogoMark size={58} /></div>
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4 }}>
            <span className="brand">Green<span className="accent">Pulse</span></span>
            <span className="overline">{t('login.subtitle')}</span>
          </div>
        </div>

        <PulseLine height={44} />

        <form className="col" onSubmit={submit} style={{ gap: 14 }}>
          <div className="field">
            <label className="overline">{t('login.email')}</label>
            <div className="input-wrap">
              <Mail size={18} />
              <input type="email" placeholder={t('login.emailPh')} value={email} onChange={(e) => { setEmail(e.target.value); setError(null); }} autoComplete="email" />
            </div>
          </div>
          <div className="field">
            <label className="overline">{t('login.password')}</label>
            <div className="input-wrap">
              <Lock size={18} />
              <input type="password" placeholder={t('login.passwordPh')} value={password} onChange={(e) => { setPassword(e.target.value); setError(null); }} autoComplete="current-password" />
            </div>
          </div>

          {error ? (
            <div className="error-banner">
              <AlertTriangle size={15} />
              {error}
            </div>
          ) : null}

          <button className="btn btn-primary" type="submit" disabled={loading}>
            {loading ? <span className="spinner" /> : <>{t('login.signin')} <ArrowRight size={17} /></>}
          </button>
        </form>

        {googleClientId ? (
          <>
            <div className="divider-or">{t('common.or')}</div>
            <GoogleSignIn onToken={onGoogleToken} onError={(key) => setError(t(key))} />
          </>
        ) : null}

        <p className="muted" style={{ textAlign: 'center', fontSize: 12.5, marginTop: 4 }}>
          {t('login.hint')}
        </p>
      </div>
    </div>
  );
}
