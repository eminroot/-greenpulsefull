import { googleClientId } from '@/config/env';
import { AuthDivider } from './auth-divider';
import { GoogleButton } from './google-button';

// The divider only makes sense when there is a second way to sign in, so the
// whole block disappears together when Google is not configured.
export function GoogleSection({ onError }: { onError?: (msg: string) => void }) {
  if (!googleClientId) return null;

  return (
    <>
      <AuthDivider />
      <GoogleButton onError={onError} />
    </>
  );
}
