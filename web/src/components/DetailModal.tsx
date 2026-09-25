import { X, Trash2, Camera, RadioTower } from 'lucide-react';
import type { Capture } from '../types';
import { SUB_META } from '../constants';
import { formatDateTime } from '../format';
import { useT } from '../i18n';
import { Gauge } from './visuals';
import { SensorCard, DecisionCard } from './cards';
import { DiagnosisCard } from './DiagnosisCard';
import { AuthImage } from './AuthImage';

const SUB_LABEL_KEY: Record<string, string> = {
  damage_score: 'detail.leafDamage',
  water_score: 'stress.Water Stress',
  thermal_score: 'stress.Heat Stress',
  light_score: 'stress.Light Stress',
};

export function DetailModal({
  record,
  onClose,
  onDelete,
}: {
  record: Capture;
  onClose: () => void;
  onDelete?: (record: Capture) => void;
}) {
  const { t, tCaptureReason } = useT();
  const reading = record.reading;
  const fromPhone = record.source === 'phone';

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()} style={{ position: 'relative' }}>
        <button className="modal-close" onClick={onClose} aria-label="Close">
          <X size={18} />
        </button>

        <div className="row" style={{ alignItems: 'stretch' }}>
          {record.image_url ? (
            <AuthImage
              path={record.image_url}
              alt="Leaf scan"
              style={{
                width: 240,
                height: 240,
                borderRadius: 'var(--radius-lg)',
                objectFit: 'cover',
                flexShrink: 0,
              }}
              fallbackIcon={44}
            />
          ) : null}
          <div className="col" style={{ flex: 1, justifyContent: 'center', alignItems: 'center' }}>
            <Gauge
              score={record.gpss_score}
              risk={record.gpss_risk_level}
              stressType={record.stress_type}
            />
            <span className="chip">
              {fromPhone ? <Camera size={13} /> : <RadioTower size={13} />}
              {t(fromPhone ? 'src.phone' : 'src.node')} · {formatDateTime(record.captured_at)}
            </span>
          </div>
        </div>

        {/* what the model on the node saw */}
        <div className="card" style={{ marginTop: 18 }}>
          <span className="overline">{t('detail.model')}</span>
          <div className="row" style={{ marginTop: 12, gap: 28, flexWrap: 'wrap' }}>
            <Stat
              label={t('detail.leafRisk')}
              value={record.risk_score != null ? `${Math.round(record.risk_score)}` : '--'}
            />
            <Stat
              label={t('detail.confidence')}
              value={record.confidence != null ? `${Math.round(record.confidence * 100)}%` : '--'}
            />
            {record.label && !record.diagnosis ? (
              <Stat label={t('detail.finding')} value={record.label} />
            ) : null}
          </div>
        </div>

        {record.diagnosis ? (
          <div style={{ marginTop: 18 }}>
            <DiagnosisCard capture={record} />
          </div>
        ) : null}

        <div className="grid grid-4" style={{ marginTop: 18 }}>
          <SensorCard metricKey="soil_moisture" value={reading?.soil_moisture ?? null} />
          <SensorCard metricKey="temperature" value={reading?.temperature ?? null} />
          <SensorCard metricKey="humidity" value={reading?.humidity ?? null} />
          <SensorCard metricKey="light" value={reading?.light ?? null} />
        </div>

        <div style={{ marginTop: 18 }}>
          <DecisionCard
            decision={record.decision}
            actuator={record.actuator}
            reason={tCaptureReason(record)}
            notify={record.notify_farmer}
            leafFinding={record.diagnosis?.disease_found}
          />
        </div>

        <div className="card" style={{ marginTop: 18 }}>
          <span className="overline">{t('detail.stressBreakdown')}</span>
          <div className="col" style={{ gap: 12, marginTop: 12 }}>
            {SUB_META.map((s) => {
              const v = record.sub_scores?.[s.key] ?? null;
              const missing = v == null;
              return (
                <div
                  key={s.key}
                  style={{ display: 'flex', flexDirection: 'column', gap: 6, opacity: missing ? 0.5 : 1 }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12.5 }}>
                    <span className="t2">
                      {t(SUB_LABEL_KEY[s.key])}{' '}
                      <span className="muted">· {t('detail.weight', { w: s.weight })}</span>
                    </span>
                    <span style={{ fontVariant: 'tabular-nums' }}>
                      {missing
                        ? t(s.key === 'damage_score' ? 'result.noLeafRead' : 'detail.noSensor')
                        : v.toFixed(0)}
                    </span>
                  </div>
                  <div className="bar">
                    {!missing ? (
                      <span style={{ width: `${Math.max(2, Math.min(100, v))}%`, background: s.color }} />
                    ) : null}
                  </div>
                </div>
              );
            })}
          </div>
          {record.signals && !record.signals.light ? (
            <p className="muted" style={{ fontSize: 12, marginTop: 12, lineHeight: 1.5 }}>
              {t('detail.renormalised')}
            </p>
          ) : null}
        </div>

        <div className="card" style={{ marginTop: 18 }}>
          <span className="overline">{t('detail.source')}</span>
          <div style={{ marginTop: 8 }}>
            <KV k={t('detail.taken')} v={formatDateTime(record.captured_at)} />
            {record.inference_ms != null ? (
              <KV k={t('detail.analysisTime')} v={`${Math.round(record.inference_ms)} ms`} />
            ) : null}
            {record.model_version ? <KV k={t('detail.modelVersion')} v={record.model_version} /> : null}
          </div>
        </div>

        {onDelete ? (
          <button
            className="btn btn-secondary"
            style={{ marginTop: 18, color: '#dc2626' }}
            onClick={() => onDelete(record)}
          >
            <Trash2 size={16} /> {t('detail.delete')}
          </button>
        ) : null}
      </div>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="num" style={{ fontSize: 26 }}>{value}</div>
      <div className="overline" style={{ fontSize: 9.5 }}>{label}</div>
    </div>
  );
}

function KV({ k, v }: { k: string; v: string }) {
  return (
    <div className="kv">
      <span className="k">{k}</span>
      <span className="v">{v}</span>
    </div>
  );
}
