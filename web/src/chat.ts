// The panel's assistant.
//
// This used to call Google's API straight from the browser with the model key
// in the bundle, which meant anyone who opened the panel could read it out of
// devtools and spend it. It now goes through our own server, which holds the
// key and reads the greenhouse snapshot from the database, so the key is not
// shipped to a browser and the assistant can only discuss readings the
// greenhouse actually produced.

import { ApiError, api } from './api/client';
import type { Lang } from './i18n';

export interface ChatTurn {
  role: 'user' | 'model';
  text: string;
}

interface ChatResponse {
  reply: string;
}

// Matches the server's limits, so an over-long conversation is trimmed here
// rather than rejected after a round trip.
const MAX_TURNS = 24;
const MAX_CHARS = 4000;

/** Error codes the server can return, mapped to i18n keys for the caller. */
export function assistantErrorKey(error: unknown): string {
  const code = error instanceof ApiError ? error.code : undefined;
  switch (code) {
    case 'assistant_not_configured':
      return 'asst.err.notConfigured';
    case 'assistant_busy':
      return 'asst.err.busy';
    case 'assistant_rate_limited':
      return 'asst.err.rateLimited';
    case 'assistant_blocked':
      return 'asst.err.blocked';
    case 'network':
      return 'err.serverUnreachable';
    case 'timeout':
      return 'err.timeout';
    default:
      return 'asst.err.generic';
  }
}

export async function sendChat(
  history: ChatTurn[],
  opts: { lang: Lang; siteId?: string | null }
): Promise<string> {
  const messages = history
    .slice(-MAX_TURNS)
    .map((turn) => ({ role: turn.role, text: turn.text.slice(0, MAX_CHARS) }))
    .filter((turn) => turn.text.length > 0);

  const { reply } = await api.post<ChatResponse>(
    '/api/v1/assistant/chat',
    { messages, lang: opts.lang, site_id: opts.siteId ?? null },
    // The model can take a while; the default request timeout is too short.
    { timeoutMs: 60000 }
  );
  return reply;
}
