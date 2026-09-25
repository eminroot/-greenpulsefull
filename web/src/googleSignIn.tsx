import { useEffect, useRef, useState } from 'react';

// Set VITE_GOOGLE_CLIENT_ID to the same OAuth client id the server holds in
// GP_GOOGLE_CLIENT_ID. Without it the button is not shown at all, rather than
// shown and broken.
export const googleClientId = (import.meta.env.VITE_GOOGLE_CLIENT_ID as string | undefined) ?? '';

const GSI_SRC = 'https://accounts.google.com/gsi/client';

interface GsiCredentialResponse {
  credential?: string;
}

interface GsiIdApi {
  initialize: (config: {
    client_id: string;
    callback: (response: GsiCredentialResponse) => void;
  }) => void;
  renderButton: (parent: HTMLElement, options: Record<string, unknown>) => void;
}

declare global {
  interface Window {
    google?: { accounts?: { id?: GsiIdApi } };
  }
}

let scriptPromise: Promise<void> | null = null;

function loadGsi(): Promise<void> {
  if (scriptPromise) return scriptPromise;

  scriptPromise = new Promise((resolve, reject) => {
    if (window.google?.accounts?.id) {
      resolve();
      return;
    }
    const script = document.createElement('script');
    script.src = GSI_SRC;
    script.async = true;
    script.defer = true;
    script.onload = () => resolve();
    script.onerror = () => reject(new Error('Could not load Google sign-in'));
    document.head.appendChild(script);
  });

  return scriptPromise;
}

/**
 * Renders Google's own sign-in button.
 *
 * Google hands back an id_token, which goes straight to our server; the server
 * verifies it against Google's signing keys and answers with a GreenPulse
 * session. The panel never holds a Google credential of its own.
 */
export function GoogleSignIn({
  onToken,
  onError,
}: {
  onToken: (idToken: string) => void;
  onError: (message: string) => void;
}) {
  const holder = useRef<HTMLDivElement>(null);
  const [ready, setReady] = useState(false);

  // Keep the latest callbacks without re-initialising the widget.
  const onTokenRef = useRef(onToken);
  onTokenRef.current = onToken;
  const onErrorRef = useRef(onError);
  onErrorRef.current = onError;

  useEffect(() => {
    if (!googleClientId) return;
    let cancelled = false;

    loadGsi()
      .then(() => {
        if (cancelled || !holder.current) return;
        const id = window.google?.accounts?.id;
        if (!id) {
          onErrorRef.current('err.googleFailed');
          return;
        }

        id.initialize({
          client_id: googleClientId,
          callback: (response) => {
            if (response.credential) onTokenRef.current(response.credential);
            else onErrorRef.current('err.googleFailed');
          },
        });
        id.renderButton(holder.current, {
          type: 'standard',
          theme: 'outline',
          size: 'large',
          width: 320,
          text: 'continue_with',
        });
        setReady(true);
      })
      .catch(() => {
        if (!cancelled) onErrorRef.current('err.googleFailed');
      });

    return () => {
      cancelled = true;
    };
  }, []);

  if (!googleClientId) return null;

  return (
    <div
      ref={holder}
      style={{ display: 'flex', justifyContent: 'center', minHeight: ready ? undefined : 44 }}
    />
  );
}
