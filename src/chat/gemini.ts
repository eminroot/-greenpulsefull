// The in-app assistant.
//
// This used to call Google's API directly with the model key compiled into the
// bundle. It now goes through our own server, which holds the key and builds
// the greenhouse snapshot from the database. Two things follow: the key is not
// shippable to anyone holding the app, and the assistant can only talk about
// readings the greenhouse actually produced, because the phone no longer
// supplies them.

import { ApiError, api } from '@/api/client';
import type { Lang } from '@/i18n/translations';

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

export interface SendChatOptions {
  lang?: Lang;
  siteId?: string | null;
}

/** Error codes the server can return, mapped to i18n keys by the caller. */
export function assistantErrorKey(error: unknown): string {
  const code = error instanceof ApiError ? error.code : undefined;
  switch (code) {
    case 'assistant_not_configured':
      return 'assistant.err.notConfigured';
    case 'assistant_busy':
      return 'assistant.err.busy';
    case 'assistant_rate_limited':
      return 'assistant.err.rateLimited';
    case 'assistant_blocked':
      return 'assistant.err.blocked';
    case 'network':
      return 'err.serverUnreachable';
    case 'timeout':
      return 'err.timeout';
    default:
      return 'assistant.err.generic';
  }
}

export async function sendChat(
  history: ChatTurn[],
  opts: SendChatOptions = {}
): Promise<string> {
  const messages = history
    .slice(-MAX_TURNS)
    .map((turn) => ({ role: turn.role, text: turn.text.slice(0, MAX_CHARS) }))
    .filter((turn) => turn.text.length > 0);

  const { reply } = await api.post<ChatResponse>(
    '/api/v1/assistant/chat',
    { messages, lang: opts.lang ?? 'en', site_id: opts.siteId ?? null },
    // The model can take a while; the default request timeout is too short.
    { timeoutMs: 60000 }
  );
  return reply;
}
