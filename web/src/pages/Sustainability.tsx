import { useCallback, useEffect, useState } from 'react';
import { Leaf, AlertTriangle } from 'lucide-react';
import { SustainabilityPanel } from '../components/twin';
import { useT } from '../i18n';
import { api } from '../api/client';
import type { Sustainability as Sus } from '../types';
import { useGreenhouse } from '../greenhouse';
import { formatDateTime } from '../format';

/**
 * Savings counted from what this greenhouse actually did.
 *
 * Every counter is a row the server wrote when the system made a decision on a
 * real reading. Before it has acted, the figures are zero, which is the truth.
 */
export function Sustainability() {
  const { t } = useT();
  const { site, subscribe } = useGreenhouse();
  const [sus, setSus] = useState<Sus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!site) return;
    try {
      setSus(await api.get<Sus>(`/api/v1/sites/${site.id}/sustainability`));
      setError(null);
    } catch {
      setError('err.generic');
    } finally {
      setLoading(false);
    }
  }, [site?.id]);

  useEffect(() => {
    load();
  }, [load]);

  // A new reading may have triggered an actuator, which moves these numbers.
  useEffect(() => subscribe(() => load()), [subscribe, load]);

  return (
    <>
      <div className="page-head">
        <div>
          <span className="overline">{t('sus.measured')}</span>
          <h1 className="page-title">{t('sus.title')}</h1>
        </div>
        <span className="chip" style={{ borderColor: 'var(--border-strong)', color: 'var(--accent)' }}>
          <Leaf size={13} /> {t('sus.vsTraditional')}
        </span>
      </div>

      <p className="t2" style={{ fontSize: 13.5, marginTop: -14, marginBottom: 4 }}>
        {t('sus.subtitle')}
      </p>

      {error ? (
        <div className="error-banner" style={{ marginBottom: 14 }}>
          <AlertTriangle size={15} />
          {t(error)}
        </div>
      ) : null}

      {loading && !sus ? (
        <div className="empty-state">
          <span className="spinner" style={{ borderTopColor: 'var(--accent)' }} />
        </div>
      ) : !sus ? null : sus.autonomous_actions === 0 ? (
        <div className="empty-state">
          <div style={{ opacity: 0.6 }}>
            <Leaf size={56} />
          </div>
          <h2 style={{ fontFamily: 'var(--font-display)', fontWeight: 600 }}>{t('sus.noneYet')}</h2>
          <p className="t2" style={{ maxWidth: 360 }}>
            {t('sus.noneYetSub', { n: sus.captures })}
          </p>
        </div>
      ) : (
        <>
          <SustainabilityPanel sus={sus} />
          <p className="muted" style={{ fontSize: 12, marginTop: 16, lineHeight: 1.55 }}>
            {t('sus.basis', { n: sus.autonomous_actions })}
            {sus.since ? ` ${t('sus.since', { when: formatDateTime(sus.since) })}` : ''}
          </p>
        </>
      )}
    </>
  );
}
