import {
  createContext,
  use,
  useCallback,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { translations, type Lang } from './translations';
import type {
  Actuator,
  Capture,
  DecisionCode,
  RiskLevel,
  StressType,
} from '@/api/types';
import type { MetricKey } from '@/greenpulse/metrics';

const KEY = 'greenpulse.lang';

type Vars = Record<string, string | number>;

interface I18nValue {
  lang: Lang;
  setLang: (l: Lang) => void;
  t: (key: string, vars?: Vars) => string;
  tMetric: (k: MetricKey) => string;
  tRisk: (r: RiskLevel) => string;
  tStress: (s: StressType) => string;
  tDecision: (d: DecisionCode) => string;
  tActuator: (a: Actuator) => string;
  tReason: (d: DecisionCode, score: number) => string;
  /** A disease code from the leaf model, as a name. Unknown codes are spelled out. */
  tDisease: (code: string | null | undefined) => string;
  /** The decision's reason, naming the disease when the leaf model found one. */
  tCaptureReason: (c: Pick<Capture, 'decision' | 'gpss_score' | 'diagnosis'>) => string;
}

const I18nContext = createContext<I18nValue | null>(null);

function interpolate(template: string, vars?: Vars): string {
  if (!vars) return template;
  return template.replace(/\{(\w+)\}/g, (_, k) => (vars[k] != null ? String(vars[k]) : `{${k}}`));
}

export function I18nProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<Lang>('en');

  useEffect(() => {
    AsyncStorage.getItem(KEY)
      .then((v) => {
        if (v === 'en' || v === 'tr' || v === 'ru') setLangState(v);
      })
      .catch(() => {});
  }, []);

  const setLang = useCallback((l: Lang) => {
    setLangState(l);
    AsyncStorage.setItem(KEY, l).catch(() => {});
  }, []);

  const t = useCallback(
    (key: string, vars?: Vars) => {
      const table = translations[lang];
      const raw = table[key] ?? translations.en[key] ?? key;
      return interpolate(raw, vars);
    },
    [lang]
  );

  const value = useMemo<I18nValue>(() => {
    const tDisease = (code: string | null | undefined) => {
      if (!code) return '--';
      const key = `disease.${code}`;
      const name = t(key);
      // A model the ML team ships later may know a disease this build does not.
      return name === key ? code.replace(/_/g, ' ').replace(/^./, (c) => c.toUpperCase()) : name;
    };
    return {
      lang,
      setLang,
      t,
      tMetric: (k) => t(`metric.${k}`),
      tRisk: (r) => t(`risk.${r}`),
      tStress: (s) => t(`stress.${s}`),
      tDecision: (d) => t(`dec.${d}`),
      tActuator: (a) => t(`act.${a}`),
      tReason: (d, score) => t(`reason.${d}`, { score }),
      tDisease,
      tCaptureReason: ({ decision, gpss_score, diagnosis }) => {
        const base = t(`reason.${decision}`, { score: gpss_score });
        if (!diagnosis?.disease_found) return base;
        const disease = tDisease(diagnosis.code);
        return decision === 'ALERT_AGRONOMIST'
          ? t('reason.disease', { disease })
          : `${base} ${t('reason.alsoDisease', { disease })}`;
      },
    };
  }, [lang, setLang, t]);

  return <I18nContext value={value}>{children}</I18nContext>;
}

export function useT(): I18nValue {
  const ctx = use(I18nContext);
  if (!ctx) throw new Error('useT must be used within I18nProvider');
  return ctx;
}
