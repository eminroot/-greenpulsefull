// Auth input validation. Functions return i18n keys (not literal text) so the
// screens can render them in the active language. Password policy: at least 8
// characters and at least one letter, matching server/app/security.py.

import { ApiError } from '@/api/client';

export function validateEmail(email: string): string | null {
  const e = email.trim();
  if (!e) return 'valid.enterEmail';
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(e)) return 'valid.invalidEmail';
  return null;
}

export function validatePassword(password: string): string | null {
  if (password.length < 8) return 'valid.minChars';
  if (!/[A-Za-z]/.test(password)) return 'valid.oneLetter';
  return null;
}

export interface PasswordStrength {
  score: 0 | 1 | 2 | 3;
  labelKey: string;
  meetsPolicy: boolean;
}

export function passwordStrength(password: string): PasswordStrength {
  const lengthOk = password.length >= 8;
  const hasLetter = /[A-Za-z]/.test(password);
  const hasNumber = /\d/.test(password);
  const hasSymbol = /[^A-Za-z0-9]/.test(password);
  const meetsPolicy = lengthOk && hasLetter;

  let points = 0;
  if (lengthOk) points++;
  if (hasLetter && hasNumber) points++;
  if (hasSymbol || password.length >= 12) points++;

  const map: Record<number, string> = {
    0: 'strength.tooShort',
    1: 'strength.fair',
    2: 'strength.good',
    3: 'strength.strong',
  };
  const score = Math.min(3, points) as PasswordStrength['score'];
  return { score, labelKey: meetsPolicy ? map[score] : 'strength.tooWeak', meetsPolicy };
}

// Maps the server's error codes to i18n keys. The server deliberately answers
// with short stable codes rather than sentences, so the wording stays here and
// works in every language the app ships.
export function friendlyAuthError(error: unknown): string {
  const code =
    error instanceof ApiError
      ? error.code
      : typeof error === 'string'
        ? error
        : undefined;

  switch (code) {
    case 'invalid_credentials':
      return 'err.wrongCredentials';
    case 'email_in_use':
      return 'err.emailInUse';
    case 'password_too_short':
      return 'valid.minChars';
    case 'password_needs_letter':
      return 'valid.oneLetter';
    case 'too_many_attempts':
      return 'err.tooManyRequests';
    case 'account_disabled':
      return 'err.userDisabled';
    case 'network':
      return 'err.network';
    case 'timeout':
      return 'err.timeout';
    case 'session_expired':
    case 'refresh_invalid':
    case 'refresh_expired':
      return 'err.sessionExpired';
    case 'google_not_configured':
      return 'err.googleNotConfigured';
    case 'google_token_invalid':
      return 'err.googleFailed';
    case 'google_email_unverified':
      return 'err.googleUnverified';
    case 'invalid_request':
      return 'err.invalidEmail';
    default:
      return 'err.generic';
  }
}
