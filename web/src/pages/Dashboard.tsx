import { useMemo, useState } from 'react';
import {
  LayoutGrid,
  SlidersHorizontal,
  BarChart3,
  MessageSquare,
  Images,
  LogOut,
  Camera,
  AlertTriangle,
  RadioTower,
} from 'lucide-react';
import { useAuth } from '../auth';
import { useGreenhouse } from '../greenhouse';
import { useT, LangToggle } from '../i18n';
import { ThemeToggle } from '../theme';
import type { Capture } from '../types';
import { LogoMark, Wordmark, Gauge, LineChart } from '../components/visuals';
import { SensorCard, DecisionCard, PhotoCard } from '../components/cards';
import { DetailModal } from '../components/DetailModal';
import { DiagnosisCard } from '../components/DiagnosisCard';
import { CameraShot } from '../components/CameraShot';
import { Twin } from './Twin';
import { Sustainability } from './Sustainability';
import { Assistant } from './Assistant';
import { timeAgo } from '../format';

type View = 'overview' | 'twin' | 'sustainability' | 'assistant' | 'gallery';

export function Dashboard() {
  const { user, signOut } = useAuth();
  const { captures, loading, error, site, sites, selectSite, removeCapture } =
    useGreenhouse();
  const { t } = useT();
  const [view, setView] = useState<View>('overview');
  const [selected, setSelected] = useState<Capture | null>(null);

  const trend = useMemo(
    () => captures.slice(0, 20).reverse().map((c) => c.gpss_score),
    [captures]
  );
  const withPhotos = useMemo(() => captures.filter((c) => c.image_url), [captures]);

  const initials = (user?.display_name || user?.email || 'G').slice(0, 2).toUpperCase();

  const onDelete = async (record: Capture) => {
    setSelected(null);
    await removeCapture(record.id).catch(() => {});
  };

  return (
    <div className="shell">
      <div className="lang-fixed">
        <ThemeToggle />
        <LangToggle />
      </div>
      <aside className="sidebar">
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '4px 8px 18px' }}>
          <LogoMark size={34} />
          <Wordmark size={20} />
        </div>

        {sites.length > 1 ? (
          <select
            className="site-select"
            value={site?.id ?? ''}
            onChange={(e) => selectSite(e.target.value)}
          >
            {sites.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </select>
        ) : null}

        <NavItem icon={<LayoutGrid size={19} />} label={t('nav.overview')} active={view === 'overview'} onClick={() => setView('overview')} />
        <NavItem icon={<SlidersHorizontal size={19} />} label={t('nav.twin')} active={view === 'twin'} onClick={() => setView('twin')} />
        <NavItem icon={<BarChart3 size={19} />} label={t('nav.sustainability')} active={view === 'sustainability'} onClick={() => setView('sustainability')} />
        <NavItem icon={<MessageSquare size={19} />} label={t('nav.assistant')} active={view === 'assistant'} onClick={() => setView('assistant')} />
        <NavItem icon={<Images size={19} />} label={t('nav.gallery')} active={view === 'gallery'} onClick={() => setView('gallery')} />

        <div className="sidebar-bottom">
          <div className="sidebar-user">
            <div className="avatar">{initials}</div>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontSize: 13.5, fontWeight: 500, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                {user?.display_name || t('common.grower')}
              </div>
              <div className="muted" style={{ fontSize: 11.5, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                {user?.email}
              </div>
            </div>
            <button onClick={signOut} title={t('common.signOut')} style={{ color: 'var(--text-muted)', padding: 6 }}>
              <LogOut size={17} />
            </button>
          </div>
        </div>
      </aside>

      <main className="main">
        {error ? (
          <div className="error-banner" style={{ marginBottom: 16 }}>
            <AlertTriangle size={15} />
            {t(error)}
          </div>
        ) : null}

        {view === 'overview' ? (
          <Overview
            loading={loading}
            trend={trend}
            recent={withPhotos.slice(0, 8)}
            onOpen={setSelected}
          />
        ) : view === 'twin' ? (
          <Twin />
        ) : view === 'sustainability' ? (
          <Sustainability />
        ) : view === 'assistant' ? (
          <Assistant />
        ) : (
          <Gallery records={captures} onOpen={setSelected} />
        )}
      </main>

      {selected ? (
        <DetailModal record={selected} onClose={() => setSelected(null)} onDelete={onDelete} />
      ) : null}

    </div>
  );
}

function NavItem({ icon, label, active, onClick }: { icon: React.ReactNode; label: string; active: boolean; onClick: () => void }) {
  return (
    <button className={`nav-item${active ? ' active' : ''}`} onClick={onClick}>
      {icon}
      {label}
    </button>
  );
}

/**
 * Says where the numbers come from, honestly:
 *   Live      connected and the greenhouse is reporting
 *   Quiet     connected, but the node has gone silent
 *   No node   connected, but no hardware has ever reported here
 *   Offline   the panel cannot reach the server
 */
export function LinkChip() {
  const { link, live } = useGreenhouse();
  const { t } = useT();

  const { color, label } = (() => {
    if (link === 'offline') return { color: '#dc2626', label: t('link.offline') };
    if (link === 'connecting') return { color: '#d97706', label: t('link.connecting') };
    if (!live?.devices.length) return { color: '#6c8579', label: t('link.noNode') };
    if (!live.online || live.stale) return { color: '#d97706', label: t('link.quiet') };
    return { color: '#34d399', label: t('link.live') };
  })();

  return (
    <span className="chip">
      <span style={{ width: 7, height: 7, borderRadius: 99, background: color, boxShadow: `0 0 8px ${color}` }} />
      {label}
    </span>
  );
}

function Overview({
  loading,
  trend,
  recent,
  onOpen,
}: {
  loading: boolean;
  trend: number[];
  recent: Capture[];
  onOpen: (r: Capture) => void;
}) {
  const { live } = useGreenhouse();
  const { t, tCaptureReason } = useT();
  const latest = live?.capture ?? null;
  const reading = live?.reading ?? null;

  return (
    <>
      <div className="page-head">
        <div>
          <span className="overline">{t('ov.greenhouse')}</span>
          <h1 className="page-title">{live?.site.name ?? t('ov.title')}</h1>
        </div>
        <div className="head-right">
          {live?.devices.length ? <CameraShot onOpen={onOpen} /> : null}
          <LinkChip />
        </div>
      </div>

      {loading && !latest ? (
        <div className="empty-state">
          <span className="spinner" style={{ borderTopColor: 'var(--accent)' }} />
        </div>
      ) : !latest ? (
        <WaitingState hasNode={!!live?.devices.length} />
      ) : (
        <div className="col">
          {live?.stale ? (
            <div className="error-banner" style={{ background: 'rgba(217,119,6,0.12)', borderColor: 'rgba(217,119,6,0.3)', color: '#d97706' }}>
              <AlertTriangle size={15} />
              {t('ov.stale', { when: timeAgo(latest.captured_at) })}
            </div>
          ) : null}

          <div className="row">
            <div className="card glow" style={{ display: 'grid', placeItems: 'center', minWidth: 300 }}>
              <Gauge
                score={latest.gpss_score}
                risk={latest.gpss_risk_level}
                stressType={latest.stress_type}
              />
            </div>
            <div className="col" style={{ flex: 1 }}>
              <DecisionCard
                decision={latest.decision}
                actuator={latest.actuator}
                reason={tCaptureReason(latest)}
                notify={latest.notify_farmer}
                leafFinding={latest.diagnosis?.disease_found}
              />
              <DiagnosisCard capture={latest} lastLeaf={live?.last_leaf_capture} />
            </div>
          </div>

          <div className="grid grid-4">
            <SensorCard metricKey="soil_moisture" value={reading?.soil_moisture ?? null} />
            <SensorCard metricKey="temperature" value={reading?.temperature ?? null} />
            <SensorCard metricKey="humidity" value={reading?.humidity ?? null} />
            <SensorCard metricKey="light" value={reading?.light ?? null} />
          </div>

          <div className="card">
            <span className="overline">{t('ov.stressTrend')}</span>
            <div style={{ marginTop: 14 }}>
              <LineChart data={trend} />
            </div>
          </div>

          {recent.length ? (
            <div className="card">
              <span className="overline">{t('ov.recent')}</span>
              <div className="gallery" style={{ marginTop: 14 }}>
                {recent.map((r) => (
                  <PhotoCard key={r.id} record={r} onClick={() => onOpen(r)} />
                ))}
              </div>
            </div>
          ) : null}
        </div>
      )}
    </>
  );
}

function Gallery({ records, onOpen }: { records: Capture[]; onOpen: (r: Capture) => void }) {
  const { live } = useGreenhouse();
  const { t } = useT();
  return (
    <>
      <div className="page-head">
        <div>
          <span className="overline">{t('gal.records', { n: records.length })}</span>
          <h1 className="page-title">{t('gal.title')}</h1>
        </div>
        <div className="head-right">
          {live?.devices.length ? <CameraShot onOpen={onOpen} /> : null}
          <LinkChip />
        </div>
      </div>
      {records.length === 0 ? (
        <WaitingState hasNode={!!live?.devices.length} />
      ) : (
        <div className="gallery">
          {records.map((r) => (
            <PhotoCard key={r.id} record={r} onClick={() => onOpen(r)} />
          ))}
        </div>
      )}
    </>
  );
}

// Shown until the greenhouse has actually reported. The panel would rather say
// nothing than show a number no sensor produced.
function WaitingState({ hasNode }: { hasNode: boolean }) {
  const { t } = useT();
  return (
    <div className="empty-state">
      <div style={{ opacity: 0.6 }}>
        <LogoMark size={60} />
      </div>
      <h2 style={{ fontFamily: 'var(--font-display)', fontWeight: 600 }}>
        {hasNode ? t('ov.waiting') : t('ov.noNode')}
      </h2>
      <p className="t2" style={{ maxWidth: 340 }}>
        {hasNode ? t('ov.waitingSub') : t('ov.noNodeSub')}
      </p>
      <span className="chip">
        {hasNode ? <Camera size={14} /> : <RadioTower size={14} />}{' '}
        {hasNode ? t('ov.scanHint') : t('ov.pairHint')}
      </span>
    </div>
  );
}
