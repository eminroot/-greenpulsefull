import { useEffect, useState } from 'react';
import * as Google from 'expo-auth-session/providers/google';
import * as WebBrowser from 'expo-web-browser';
import { useAuth } from '@/auth/auth-context';
import { friendlyAuthError } from '@/auth/validation';
import { googleClientId } from '@/config/env';

// Required so the auth popup can settle when the app regains focus.
WebBrowser.maybeCompleteAuthSession();

export interface GoogleAuthState {
  promptAsync: () => void;
  ready: boolean;
  enabled: boolean;
  inProgress: boolean;
  error: string | null;
}

// "Continue with Google". Google returns an id_token, which we hand to our own
// server; the server verifies it against Google's signing keys and answers with
// a GreenPulse session. The app never holds a Google credential of its own.
export function useGoogleAuth(): GoogleAuthState {
  const { signInWithGoogle } = useAuth();
  const [inProgress, setInProgress] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const enabled = !!googleClientId;

  const [request, response, promptAsync] = Google.useIdTokenAuthRequest({
    clientId: googleClientId,
    iosClientId: googleClientId,
    webClientId: googleClientId,
  });

  useEffect(() => {
    if (!response) return;

    if (response.type === 'success') {
      const idToken = response.params?.id_token;
      if (!idToken) {
        setInProgress(false);
        setError('err.googleNoToken');
        return;
      }
      signInWithGoogle(idToken)
        .catch((err) => setError(friendlyAuthError(err)))
        .finally(() => setInProgress(false));
    } else if (response.type === 'error') {
      setInProgress(false);
      setError('err.googleCancelled');
    } else if (response.type === 'dismiss' || response.type === 'cancel') {
      setInProgress(false);
    }
  }, [response, signInWithGoogle]);

  return {
    ready: !!request,
    enabled,
    inProgress,
    error,
    promptAsync: () => {
      setError(null);
      setInProgress(true);
      promptAsync().catch(() => setInProgress(false));
    },
  };
}
