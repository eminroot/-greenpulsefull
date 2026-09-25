// Runtime configuration.
//
// Accounts and greenhouse data live on our own server now, so there are no
// third party project keys here. The only thing the app needs to know is where
// that server is.

// Where the GreenPulse server runs. Set EXPO_PUBLIC_GREENPULSE_API in .env (or
// in the EAS build profile) to point a build at production. The value can also
// be changed in Settings, which is how you test against a laptop on the same
// wifi without rebuilding.
export const DEFAULT_API_URL =
  process.env.EXPO_PUBLIC_GREENPULSE_API ?? 'http://192.168.1.67:8000';

// OAuth client id for "Continue with Google". The server verifies the token it
// issues, so this id must match GP_GOOGLE_CLIENT_ID on the server. Empty hides
// the Google button.
export const googleClientId = process.env.EXPO_PUBLIC_GOOGLE_CLIENT_ID ?? '';

// The assistant runs through our own server (/api/v1/assistant/chat), so the
// model key lives in the server's environment and is never shipped in this
// bundle. Anything compiled in here is readable by anyone holding the app.

// How long the dashboard waits before it calls a greenhouse quiet. The server
// decides this too; this is only used for the wording on screen.
export const STALE_AFTER_SECONDS = 15 * 60;
