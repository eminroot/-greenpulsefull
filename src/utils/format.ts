// The server sends ISO timestamps; older local data used epoch milliseconds.
// Both are accepted so a timestamp never renders as "Invalid Date".
type Timestamp = string | number | null | undefined;

function toMillis(ts: Timestamp): number | null {
  if (ts == null) return null;
  if (typeof ts === 'number') return Number.isFinite(ts) ? ts : null;
  const parsed = Date.parse(ts);
  return Number.isNaN(parsed) ? null : parsed;
}

export function timeAgo(ts: Timestamp): string {
  const ms = toMillis(ts);
  if (ms == null) return '--';

  const sec = Math.floor((Date.now() - ms) / 1000);
  if (sec < 0) return 'just now'; // clock skew between phone and server
  if (sec < 45) return 'just now';
  const min = Math.floor(sec / 60);
  if (min < 60) return `${min}m ago`;
  const hr = Math.floor(min / 60);
  if (hr < 24) return `${hr}h ago`;
  const day = Math.floor(hr / 24);
  if (day < 7) return `${day}d ago`;
  return new Date(ms).toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}

export function formatDateTime(ts: Timestamp): string {
  const ms = toMillis(ts);
  if (ms == null) return '--';
  return new Date(ms).toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}
