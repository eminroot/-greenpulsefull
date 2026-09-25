import { SlidersHorizontal, RotateCcw, AlertTriangle } from 'lucide-react';
import { Gauge } from '../components/visuals';
import { SliderControl, ActuatorMatrix } from '../components/twin';
import { IDEAL } from '../constants';
import { useT } from '../i18n';
import { useGreenhouse } from '../greenhouse';
import { useTwin } from '../twinState';

/**
 * A what-if on top of the greenhouse's real current state.
 *
 * The scoring is not done in the browser. Every change is sent to the server
 * and scored by the same engine that scores real readings, so what this shows
 * is what the greenhouse would actually do.
 */
export function Twin() {
  const { t, tStress } = useT();
  const { live } = useGreenhouse();
  const twin = useTwin(live);
  const preview = twin.preview;

  return (
    <>
      <div className="page-head">
        <div>
          <span className="overline">{t('twin.simulator')}</span>
          <h1 className="page-title">{t('twin.title')}</h1>
        </div>
        <span className="chip" style={{ borderColor: 'var(--border-strong)', color: 'var(--accent)' }}>
          <SlidersHorizontal size={13} /> {t('twin.projection')}
        </span>
      </div>

      <p className="t2" style={{ fontSize: 13.5, marginTop: -14, marginBottom: 4 }}>
        {twin.seeded ? t('twin.seeded') : t('twin.noReading')}
      </p>

      {twin.error ? (
        <div className="error-banner" style={{ marginBottom: 14 }}>
          <AlertTriangle size={15} />
          {t(twin.error)}
        </div>
      ) : null}

      <div className="col">
        <div className="row">
          <div
            className="card glow"
            style={{ display: 'grid', placeItems: 'center', minWidth: 300, opacity: twin.pending ? 0.75 : 1, transition: 'opacity 140ms' }}
          >
            {preview ? (
              <Gauge
                score={preview.gpss_score}
                risk={preview.risk_level}
                subtitle={tStress(preview.stress_type)}
              />
            ) : (
              <span className="spinner" style={{ borderTopColor: 'var(--accent)' }} />
            )}
          </div>

          <div className="col" style={{ flex: 1 }}>
            <div className="card">
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <span className="overline">{t('twin.sensorControls')}</span>
                {!twin.atCurrent && twin.seeded ? (
                  <button className="auto-reset" onClick={twin.resetToCurrent}>
                    <RotateCcw size={11} /> {t('twin.backToCurrent')}
                  </button>
                ) : null}
              </div>

              <div className="col" style={{ gap: 18, marginTop: 16 }}>
                <SliderControl
                  label={t('twin.leafDamage')}
                  value={twin.leaf_damage}
                  unit=""
                  min={0}
                  max={100}
                  step={1}
                  ideal={[0, 15]}
                  tint="#f87171"
                  onChange={(v) => twin.set('leaf_damage', v)}
                />
                {twin.wired.soil_moisture ? (
                  <SliderControl
                    label={t('twin.soil')}
                    value={twin.soil_moisture}
                    unit="%"
                    min={0}
                    max={100}
                    step={1}
                    ideal={IDEAL.soil_moisture}
                    tint="#38bdf8"
                    onChange={(v) => twin.set('soil_moisture', v)}
                  />
                ) : (
                  <NotWired label={t('twin.soil')} />
                )}
                {twin.wired.temperature ? (
                  <SliderControl
                    label={t('twin.temp')}
                    value={twin.temperature}
                    unit="°C"
                    min={0}
                    max={45}
                    step={1}
                    ideal={IDEAL.temperature}
                    tint="#fb923c"
                    onChange={(v) => twin.set('temperature', v)}
                  />
                ) : (
                  <NotWired label={t('twin.temp')} />
                )}
                {twin.wired.light ? (
                  <SliderControl
                    label={t('twin.light')}
                    value={twin.light}
                    unit="lux"
                    min={0}
                    max={1500}
                    step={10}
                    ideal={IDEAL.light}
                    tint="#facc15"
                    onChange={(v) => twin.set('light', v)}
                  />
                ) : (
                  <NotWired label={t('twin.light')} />
                )}
                {twin.wired.humidity ? (
                  <SliderControl
                    label={t('twin.humidity')}
                    value={twin.humidity}
                    unit="%"
                    min={10}
                    max={100}
                    step={1}
                    ideal={IDEAL.humidity}
                    tint="#34d399"
                    onChange={(v) => twin.set('humidity', v)}
                  />
                ) : (
                  <NotWired label={t('twin.humidity')} />
                )}
              </div>

              {/* Humidity is recorded on every reading but carries no weight in
                  the score. Saying so beats letting the operator wonder why the
                  slider does nothing. */}
              {twin.wired.humidity ? (
                <p className="muted" style={{ fontSize: 12, marginTop: 14, lineHeight: 1.5 }}>
                  {t('twin.humidityNote')}
                </p>
              ) : null}
            </div>

            {preview ? <Verdict preview={preview} /> : null}
          </div>
        </div>

        {preview ? (
          <ActuatorMatrix
            irrigation={preview.actuator === 'WATER_PUMP'}
            ventilation={preview.actuator === 'FAN'}
            light={preview.actuator === 'GROW_LIGHT'}
          />
        ) : null}
      </div>
    </>
  );
}

// A probe this greenhouse does not have. It is left out of the projection
// entirely, the same way the server leaves it out of a real reading.
function NotWired({ label }: { label: string }) {
  const { t } = useT();
  return (
    <div style={{ opacity: 0.5 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13 }}>
        <span className="t2">{label}</span>
        <span className="muted">{t('twin.notWired')}</span>
      </div>
      <div className="bar" style={{ marginTop: 8 }} />
    </div>
  );
}

function Verdict({ preview }: { preview: NonNullable<ReturnType<typeof useTwin>['preview']> }) {
  const { t, tDecision, tReason } = useT();
  const acting = preview.actuator !== 'NONE' || preview.decision === 'ALERT_AGRONOMIST';

  return (
    <div className="card">
      <span className="overline">{t('twin.wouldDo')}</span>
      <div style={{ fontWeight: 600, fontSize: 18, marginTop: 10 }}>
        {tDecision(preview.decision)}
      </div>
      <p className="t2" style={{ marginTop: 8, fontSize: 14, lineHeight: 1.5 }}>
        {tReason(preview.decision, preview.gpss_score)}
      </p>
      {preview.notify_farmer ? (
        <p className="muted" style={{ fontSize: 12.5, marginTop: 8 }}>{t('twin.wouldNotify')}</p>
      ) : null}
      {!acting ? (
        <p className="muted" style={{ fontSize: 12.5, marginTop: 8 }}>{t('twin.wouldWatch')}</p>
      ) : null}
    </div>
  );
}
