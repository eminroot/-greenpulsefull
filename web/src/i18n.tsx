import { createContext, useContext, useMemo, useState, type ReactNode } from 'react';
import type {
  Actuator,
  Capture,
  DecisionCode,
  RiskLevel,
  StressType,
} from './types';
import { diagnosisStrings } from './diagnosisStrings';

export type Lang = 'en' | 'tr';

type Vars = Record<string, string | number>;
type Dict = Record<string, string>;

const en: Dict = {
  'nav.overview': 'Overview',
  'nav.twin': 'Digital twin',
  'nav.sustainability': 'Sustainability',
  'nav.assistant': 'Assistant',
  'nav.gallery': 'Leaf gallery',

  'common.signOut': 'Sign out',
  'common.grower': 'Grower',
  'common.live': 'Live',
  'common.or': 'or',

  'login.subtitle': 'Greenhouse control panel',
  'login.email': 'Email',
  'login.password': 'Password',
  'login.emailPh': 'you@greenhouse.com',
  'login.passwordPh': 'Your password',
  'login.signin': 'Sign in',
  'login.google': 'Continue with Google',
  'login.hint': 'Sign in with the same account you use in the GreenPulse app.',
  'login.enterBoth': 'Enter your email and password.',

  'err.invalidEmail': 'That email address is not valid.',
  'err.wrongCred': 'Email or password is incorrect.',
  'err.tooMany': 'Too many attempts. Wait a moment and try again.',
  'err.network': 'Network problem. Check your connection.',
  'err.generic': 'Could not sign in. Try again.',

  'ov.greenhouse': 'Greenhouse',
  'ov.title': 'Overview',
  'ov.stressTrend': 'Stress trend',
  'ov.recent': 'Recent captures',

  'gal.records': '{n} records',
  'gal.title': 'Leaf gallery',

  'twin.simulator': 'What if',
  'twin.title': 'Digital twin',
  'twin.sensorControls': 'Sensor controls',
  'twin.soil': 'Soil moisture',
  'twin.temp': 'Air temperature',
  'twin.humidity': 'Relative humidity',
  'twin.ideal': 'Ideal {lo}–{hi}{unit}',
  'twin.actuatorMatrix': 'Projected actuator states',
  'twin.irrigationValve': 'Irrigation valve',
  'twin.irrigationHint': 'Drip line · zone A',
  'twin.ventilationFan': 'Ventilation fan',
  'twin.ventilationHint': 'Roof exhaust',
  'twin.on': 'ON',
  'twin.off': 'OFF',


  'sus.title': 'Sustainability & ROI',
  'sus.vsTraditional': 'vs traditional farming',
  'sus.compare': 'GreenPulse vs traditional',
  'sus.waterSaved': 'Water saved',
  'sus.energySaved': 'Energy saved',
  'sus.traditional': 'Traditional',
  'sus.greenpulse': 'GreenPulse',
  'sus.irrigationEvents': 'Irrigation events',
  'sus.autonomousActions': 'Autonomous actions',
  'sus.costReduction': 'Cost reduction / mo',
  'sus.co2': 'CO₂ saved / mo',
  'sus.waterLiters': 'Water saved / mo',
  'sus.yield': 'Yield protected',
  'sus.disease': 'Disease risk ↓',
  'sus.manualChecks': 'Manual checks avoided',
  'sus.labor': 'Labor saved / mo',
  'sus.fertilizer': 'Fertilizer saved',
  'sus.tradLabel': 'Traditional system',
  'sus.tradDesc': 'Scheduled irrigation, no savings',
  'sus.gpLabel': 'GreenPulse',
  'sus.gpDesc': 'Autonomous, demand-based control',

  'gauge.score': 'Score',

  'risk.Low': 'Low',
  'risk.Medium': 'Medium',
  'risk.High': 'High',
  'risk.Critical': 'Critical',

  'stress.Healthy': 'Healthy',
  'stress.Water Stress': 'Water stress',
  'stress.Heat Stress': 'Heat stress',
  'stress.Light Stress': 'Light stress',
  'stress.Tissue Damage': 'Tissue damage',


  'dec.MONITORING': 'Monitoring',
  'dec.IRRIGATION_ON': 'Irrigation on',
  'dec.VENTILATION_ON': 'Ventilation on',
  'dec.SUPPLEMENTAL_LIGHT_ON': 'Grow light on',
  'dec.ALERT_AGRONOMIST': 'Alert agronomist',

  'act.NONE': 'None',
  'act.WATER_PUMP': 'Water pump',
  'act.FAN': 'Ventilation fan',
  'act.GROW_LIGHT': 'Grow light',


  'metric.soil_moisture': 'Soil moisture',
  'metric.temperature': 'Temperature',
  'metric.humidity': 'Humidity',
  'metric.light': 'Light',

  'reason.MONITORING': 'Stress score {score} is within a healthy range.',
  'reason.IRRIGATION_ON': 'Soil moisture deficit detected (score {score}).',
  'reason.VENTILATION_ON': 'Thermal stress detected (score {score}).',
  'reason.SUPPLEMENTAL_LIGHT_ON': 'Light shortfall detected (score {score}).',
  'reason.ALERT_AGRONOMIST': 'Visible tissue damage detected (score {score}). Human inspection needed.',

  'decision.title': 'Autonomous decision',
  'decision.on': '{actuator} · ON',
  'decision.none': 'No actuator action',
  'decision.notified': 'Farmer notified, critical stress level reached.',

  'detail.stressBreakdown': 'Stress breakdown',
  'detail.weight': 'weight {w}',
  'detail.analysisTime': 'Analysis time',
  'detail.leafDamage': 'Leaf damage',

  'asst.menu': 'Assistant',
  'asst.title': 'GreenPulse Assistant',
  'asst.aware': 'Reading your live greenhouse',
  'asst.askTitle': 'Ask about your greenhouse',
  'asst.askSub': 'I can read your latest readings, explain the score and decisions, and suggest ways to cut water and energy.',
  'asst.placeholder': 'Ask GreenPulse',
  'asst.s1': 'Explain my score',
  'asst.s2': 'Why this decision?',
  'asst.s3': 'How can I save more water?',
  'asst.s4': 'What should I check today?',

  // --- server backed data flow ---
  'link.live': 'Live',
  'link.quiet': 'Quiet',
  'link.noNode': 'No node',
  'link.connecting': 'Connecting',
  'link.offline': 'Offline',
  'src.node': 'Greenhouse node',
  'src.phone': 'Photographed in the app',
  'sensor.notWired': 'No sensor wired',
  'ov.waiting': 'Waiting for the first reading',
  'ov.waitingSub': 'The greenhouse node is paired. Readings appear here the moment it sends one.',
  'ov.noNode': 'No greenhouse node yet',
  'ov.noNodeSub': 'Pair the node in your greenhouse from the phone app, and its readings will appear here on their own.',
  'ov.scanHint': 'Readings arrive automatically',

  // take a photo now, with the greenhouse camera
  'shot.title': 'Photograph the leaf now',
  'shot.sub': 'The greenhouse camera takes a photo right away instead of waiting for its schedule.',
  'shot.take': 'Take photo',
  'shot.asking': 'Asking the camera',
  'shot.waiting': 'Taking the photo',
  'shot.waitingSub': 'The camera is photographing the leaf. This takes a few seconds.',
  'shot.waitingQuiet': 'Your node has been quiet lately, so this may take a while or not arrive.',
  'shot.done': 'New photo is in',
  'shot.doneSub': 'The dashboard shows it now, with its score.',
  'shot.open': 'Open it',
  'shot.again': 'Take another',
  'shot.failed': 'No photo this time',
  'shot.err.noAnswer': 'Your greenhouse did not answer. Check that the Pi is on and online.',
  'shot.err.camera_unreachable': 'The camera did not answer. Check that it has power and Wi-Fi.',
  'shot.err.camera_refused': 'The camera and the Pi do not recognise each other. Check the camera\'s setup.',
  'shot.err.camera_outdated': 'The camera is on but still runs old firmware, so it only sends its regular photos. Flash the new firmware to use this button.',
  'shot.err.camera_failed': 'The camera could not take a photo. Try again in a moment.',
  'shot.err.request': 'The request did not go through. Try again.',
  'shot.err.tooMany': 'That is a lot of photos in a short time. Wait a few minutes.',
  'shot.unreadable.too_dark': 'The photo came out too dark to read the leaf. Turn on a light near the camera.',
  'shot.unreadable.overexposed': 'The photo came out too bright. Shade the camera from direct sun.',
  'shot.unreadable.no_leaf': 'The camera does not see a leaf. Point it at one leaf, close up.',
  'shot.unreadable.too_small': 'The photo was too small to read. Check the camera settings.',
  'ov.pairHint': 'Pair a node in the app',
  'ov.stale': 'The node has gone quiet. This reading is from {when}.',
  'detail.model': 'What the node saw',
  'detail.leafRisk': 'Leaf risk',
  'detail.confidence': 'Confidence',
  'detail.finding': 'Finding',
  'detail.noSensor': 'No sensor',
  'detail.renormalised': 'A probe for this greenhouse is not wired, so its share of the score was spread across the readings that are available.',
  'detail.source': 'Where this came from',
  'detail.taken': 'Taken',
  'detail.modelVersion': 'Model',
  'detail.delete': 'Delete this reading',
  'twin.projection': 'Projection',
  'twin.seeded': 'Starts from what your greenhouse is reporting right now. Move a slider to ask what would happen instead.',
  'twin.noReading': 'No reading has arrived yet, so this starts from typical values. Move a slider to explore.',
  'twin.leafDamage': 'Leaf damage',
  'twin.light': 'Light',
  'twin.backToCurrent': 'Back to current',
  'twin.humidityNote': 'Humidity is recorded with every reading but does not affect the score, so this slider moves the record, not the result.',
  'twin.wouldDo': 'What the system would do',
  'twin.wouldNotify': 'At this score the farmer is notified as well.',
  'twin.wouldWatch': 'Below the action threshold, so it would keep watching rather than act.',
  'twin.actuatorProjected': 'What these would be doing at the values above. This is a projection, not a switch: the panel does not drive your hardware.',
  'twin.growLight': 'Grow light',
  'twin.growLightHint': 'Supplemental lighting',
  'sus.measured': 'Measured',
  'sus.subtitle': 'Counted from what this greenhouse actually did, not from an assumed baseline.',
  'sus.noneYet': 'Nothing to count yet',
  'sus.noneYetSub': 'The system has not needed to act on any of the {n} readings so far. Savings appear here once it irrigates or ventilates on its own.',
  'sus.basis': 'Based on {n} autonomous actions.',
  'sus.since': 'First action {when}.',
  'asst.awareEmpty': 'Waiting for the first reading',
  'err.timeout': 'That took too long. Check your connection and try again.',
  'err.sessionExpired': 'Your session ended. Sign in again.',
  'err.serverUnreachable': 'Cannot reach the server.',
  'err.disabled': 'This account has been disabled.',
  'err.googleNotConfigured': 'Google sign-in is not set up on this server.',
  'err.googleFailed': 'Could not complete Google sign-in.',
  'err.googleUnverified': 'That Google account has no verified email address.',
  'twin.notWired': 'No probe wired, left out of the projection',

  'asst.err.notConfigured': 'The assistant is not set up on this server yet.',
  'asst.err.busy': 'You have asked a lot of questions just now. Give it a minute.',
  'asst.err.rateLimited': 'The assistant is busy right now. Try again shortly.',
  'asst.err.blocked': 'That question could not be answered.',
  'asst.err.generic': 'The assistant could not reply. Try again.',
};

const tr: Dict = {
  'nav.overview': 'Genel bakış',
  'nav.twin': 'Dijital ikiz',
  'nav.sustainability': 'Sürdürülebilirlik',
  'nav.assistant': 'Asistan',
  'nav.gallery': 'Yaprak galerisi',

  'common.signOut': 'Çıkış yap',
  'common.grower': 'Üretici',
  'common.live': 'Canlı',
  'common.or': 'veya',

  'login.subtitle': 'Sera kontrol paneli',
  'login.email': 'E-posta',
  'login.password': 'Şifre',
  'login.emailPh': 'sen@sera.com',
  'login.passwordPh': 'Şifren',
  'login.signin': 'Giriş yap',
  'login.google': 'Google ile devam et',
  'login.hint': 'GreenPulse uygulamasında kullandığın hesapla giriş yap.',
  'login.enterBoth': 'E-posta ve şifreni gir.',

  'err.invalidEmail': 'Bu e-posta adresi geçerli değil.',
  'err.wrongCred': 'E-posta veya şifre yanlış.',
  'err.tooMany': 'Çok fazla deneme. Biraz bekleyip tekrar dene.',
  'err.network': 'Ağ sorunu. Bağlantını kontrol et.',
  'err.generic': 'Giriş yapılamadı. Tekrar dene.',

  'ov.greenhouse': 'Sera',
  'ov.title': 'Genel bakış',
  'ov.stressTrend': 'Stres eğilimi',
  'ov.recent': 'Son kayıtlar',

  'gal.records': '{n} kayıt',
  'gal.title': 'Yaprak galerisi',

  'twin.simulator': 'Ya olsaydı',
  'twin.title': 'Dijital ikiz',
  'twin.sensorControls': 'Sensör kontrolleri',
  'twin.soil': 'Toprak nemi',
  'twin.temp': 'Hava sıcaklığı',
  'twin.humidity': 'Bağıl nem',
  'twin.ideal': 'İdeal {lo}–{hi}{unit}',
  'twin.actuatorMatrix': 'Öngörülen aktüatör durumu',
  'twin.irrigationValve': 'Sulama vanası',
  'twin.irrigationHint': 'Damla hattı · bölge A',
  'twin.ventilationFan': 'Havalandırma fanı',
  'twin.ventilationHint': 'Çatı egzozu',
  'twin.on': 'AÇIK',
  'twin.off': 'KAPALI',


  'sus.title': 'Sürdürülebilirlik & ROI',
  'sus.vsTraditional': 'geleneksele kıyasla',
  'sus.compare': 'GreenPulse ile geleneksel',
  'sus.waterSaved': 'Su tasarrufu',
  'sus.energySaved': 'Enerji tasarrufu',
  'sus.traditional': 'Geleneksel',
  'sus.greenpulse': 'GreenPulse',
  'sus.irrigationEvents': 'Sulama olayları',
  'sus.autonomousActions': 'Otonom işlemler',
  'sus.costReduction': 'Maliyet azalması / ay',
  'sus.co2': 'CO₂ tasarrufu / ay',
  'sus.waterLiters': 'Su tasarrufu / ay',
  'sus.yield': 'Korunan verim',
  'sus.disease': 'Hastalık riski ↓',
  'sus.manualChecks': 'Önlenen manuel kontrol',
  'sus.labor': 'İş gücü tasarrufu / ay',
  'sus.fertilizer': 'Gübre tasarrufu',
  'sus.tradLabel': 'Geleneksel sistem',
  'sus.tradDesc': 'Programlı sulama, tasarruf yok',
  'sus.gpLabel': 'GreenPulse',
  'sus.gpDesc': 'Otonom, talebe dayalı kontrol',

  'gauge.score': 'Skor',

  'risk.Low': 'Düşük',
  'risk.Medium': 'Orta',
  'risk.High': 'Yüksek',
  'risk.Critical': 'Kritik',

  'stress.Healthy': 'Sağlıklı',
  'stress.Water Stress': 'Su stresi',
  'stress.Heat Stress': 'Sıcaklık stresi',
  'stress.Light Stress': 'Işık stresi',
  'stress.Tissue Damage': 'Doku hasarı',


  'dec.MONITORING': 'İzleme',
  'dec.IRRIGATION_ON': 'Sulama açık',
  'dec.VENTILATION_ON': 'Havalandırma açık',
  'dec.SUPPLEMENTAL_LIGHT_ON': 'Bitki ışığı açık',
  'dec.ALERT_AGRONOMIST': 'Ziraat mühendisini uyar',

  'act.NONE': 'Yok',
  'act.WATER_PUMP': 'Su pompası',
  'act.FAN': 'Havalandırma fanı',
  'act.GROW_LIGHT': 'Bitki ışığı',


  'metric.soil_moisture': 'Toprak nemi',
  'metric.temperature': 'Sıcaklık',
  'metric.humidity': 'Nem',
  'metric.light': 'Işık',

  'reason.MONITORING': 'Stres skoru {score} sağlıklı aralıkta.',
  'reason.IRRIGATION_ON': 'Toprak nemi açığı tespit edildi (skor {score}).',
  'reason.VENTILATION_ON': 'Isı stresi tespit edildi (skor {score}).',
  'reason.SUPPLEMENTAL_LIGHT_ON': 'Işık eksikliği tespit edildi (skor {score}).',
  'reason.ALERT_AGRONOMIST': 'Görünür doku hasarı tespit edildi (skor {score}). İnceleme gerekli.',

  'decision.title': 'Otonom karar',
  'decision.on': '{actuator} · AÇIK',
  'decision.none': 'İşlem gerekmiyor',
  'decision.notified': 'Üretici bilgilendirildi, kritik stres seviyesine ulaşıldı.',

  'detail.stressBreakdown': 'Stres dağılımı',
  'detail.weight': 'ağırlık {w}',
  'detail.analysisTime': 'Analiz süresi',
  'detail.leafDamage': 'Yaprak hasarı',

  'asst.menu': 'Asistan',
  'asst.title': 'GreenPulse Asistanı',
  'asst.aware': 'Seranın canlı verisini okuyor',
  'asst.askTitle': 'Seranız hakkında soru sorun',
  'asst.askSub': 'Son okumalarınızı okuyabilir, skoru ve kararları açıklayabilir, su ve enerji tasarrufu için öneriler verebilirim.',
  'asst.placeholder': 'GreenPulse’a sor',
  'asst.s1': 'Skorumu açıkla',
  'asst.s2': 'Neden bu karar?',
  'asst.s3': 'Nasıl daha çok su tasarrufu yaparım?',
  'asst.s4': 'Bugün neyi kontrol etmeliyim?',

  // --- server backed data flow ---
  'link.live': 'Canlı',
  'link.quiet': 'Sessiz',
  'link.noNode': 'Cihaz yok',
  'link.connecting': 'Bağlanıyor',
  'link.offline': 'Çevrimdışı',
  'src.node': 'Sera cihazı',
  'src.phone': 'Uygulamada çekildi',
  'sensor.notWired': 'Sensör bağlı değil',
  'ov.waiting': 'İlk ölçüm bekleniyor',
  'ov.waitingSub': 'Sera cihazı eşleşti. Ölçüm gönderir göndermez burada görünecek.',
  'ov.noNode': 'Henüz sera cihazı yok',
  'ov.noNodeSub': 'Seradaki cihazı telefon uygulamasından eşleştir, ölçümleri buraya kendiliğinden gelsin.',
  'ov.scanHint': 'Ölçümler kendiliğinden gelir',

  // take a photo now, with the greenhouse camera
  'shot.title': 'Yaprağı şimdi çek',
  'shot.sub': 'Sera kamerası sırasını beklemeden hemen bir fotoğraf çeker.',
  'shot.take': 'Fotoğraf çek',
  'shot.asking': 'Kameraya soruluyor',
  'shot.waiting': 'Fotoğraf çekiliyor',
  'shot.waitingSub': 'Kamera yaprağı çekiyor. Birkaç saniye sürer.',
  'shot.waitingQuiet': 'Cihazından bir süredir ses yok, bu yüzden gecikebilir ya da hiç gelmeyebilir.',
  'shot.done': 'Yeni fotoğraf geldi',
  'shot.doneSub': 'Pano artık onu puanıyla birlikte gösteriyor.',
  'shot.open': 'Aç',
  'shot.again': 'Bir tane daha',
  'shot.failed': 'Bu sefer fotoğraf yok',
  'shot.err.noAnswer': 'Seran yanıt vermedi. Pi açık ve bağlı mı, kontrol et.',
  'shot.err.camera_unreachable': 'Kamera yanıt vermedi. Elektriği ve Wi-Fi bağlantısı var mı, kontrol et.',
  'shot.err.camera_refused': 'Kamera ile Pi birbirini tanımıyor. Kameranın kurulumunu kontrol et.',
  'shot.err.camera_outdated': 'Kamera açık ama eski yazılımla çalışıyor, bu yüzden yalnızca düzenli fotoğraflarını gönderiyor. Bu düğme için yeni yazılımı yükle.',
  'shot.err.camera_failed': 'Kamera fotoğraf çekemedi. Birazdan tekrar dene.',
  'shot.err.request': 'İstek gönderilemedi. Tekrar dene.',
  'shot.err.tooMany': 'Kısa sürede çok fazla fotoğraf istendi. Birkaç dakika bekle.',
  'shot.unreadable.too_dark': 'Fotoğraf yaprağı okumak için çok karanlık çıktı. Kameranın yakınında bir ışık aç.',
  'shot.unreadable.overexposed': 'Fotoğraf çok parlak çıktı. Kamerayı doğrudan güneşten koru.',
  'shot.unreadable.no_leaf': 'Kamera yaprak görmüyor. Onu tek bir yaprağa, yakından çevir.',
  'shot.unreadable.too_small': 'Fotoğraf okunamayacak kadar küçük. Kamera ayarlarını kontrol et.',
  'ov.pairHint': 'Uygulamadan cihaz eşleştir',
  'ov.stale': 'Cihaz sessizleşti. Bu ölçüm {when} alınmış.',
  'detail.model': 'Cihazın gördüğü',
  'detail.leafRisk': 'Yaprak riski',
  'detail.confidence': 'Güven',
  'detail.finding': 'Bulgu',
  'detail.noSensor': 'Sensör yok',
  'detail.renormalised': 'Bu serada bir prob bağlı değil, bu yüzden onun puandaki payı mevcut ölçümlere dağıtıldı.',
  'detail.source': 'Bu veri nereden geldi',
  'detail.taken': 'Alındı',
  'detail.modelVersion': 'Model',
  'detail.delete': 'Bu ölçümü sil',
  'twin.projection': 'Öngörü',
  'twin.seeded': 'Seranın şu anki değerlerinden başlar. Farklı bir durumu denemek için kaydırıcıyı oynat.',
  'twin.noReading': 'Henüz ölçüm gelmedi, bu yüzden tipik değerlerden başlıyor. Denemek için kaydırıcıyı oynat.',
  'twin.leafDamage': 'Yaprak hasarı',
  'twin.light': 'Işık',
  'twin.backToCurrent': 'Şu ana dön',
  'twin.humidityNote': 'Nem her ölçümde kaydedilir ama puana girmez; bu kaydırıcı kaydı değiştirir, sonucu değil.',
  'twin.wouldDo': 'Sistem ne yapardı',
  'twin.wouldNotify': 'Bu puanda çiftçiye de bildirim gider.',
  'twin.wouldWatch': 'Hareket eşiğinin altında, yani harekete geçmek yerine izlemeye devam ederdi.',
  'twin.actuatorProjected': 'Yukarıdaki değerlerde bunlar ne yapıyor olurdu. Bu bir öngörü, anahtar değil: panel donanımı sürmez.',
  'twin.growLight': 'Bitki lambası',
  'twin.growLightHint': 'Ek aydınlatma',
  'sus.measured': 'Ölçülen',
  'sus.subtitle': 'Varsayılan bir temelden değil, bu seranın gerçekte yaptıklarından sayıldı.',
  'sus.noneYet': 'Henüz sayılacak bir şey yok',
  'sus.noneYetSub': 'Şimdiye kadarki {n} ölçümün hiçbirinde sistemin harekete geçmesi gerekmedi. Kendi kendine sulama ya da havalandırma yaptığında tasarruflar burada görünecek.',
  'sus.basis': '{n} otonom hareket üzerinden.',
  'sus.since': 'İlk hareket {when}.',
  'asst.awareEmpty': 'İlk ölçüm bekleniyor',
  'err.timeout': 'Bu çok uzun sürdü. Bağlantını kontrol edip tekrar dene.',
  'err.sessionExpired': 'Oturumun sona erdi. Tekrar giriş yap.',
  'err.serverUnreachable': 'Sunucuya ulaşılamıyor.',
  'err.disabled': 'Bu hesap devre dışı bırakılmış.',
  'err.googleNotConfigured': 'Bu sunucuda Google ile giriş kurulu değil.',
  'err.googleFailed': 'Google ile giriş tamamlanamadı.',
  'err.googleUnverified': 'Bu Google hesabının doğrulanmış e-posta adresi yok.',
  'twin.notWired': 'Prob bağlı değil, öngörüye dahil edilmedi',

  'asst.err.notConfigured': 'Bu sunucuda asistan henüz kurulu değil.',
  'asst.err.busy': 'Kısa sürede çok soru sordun. Bir dakika bekle.',
  'asst.err.rateLimited': 'Asistan şu an yoğun. Birazdan tekrar dene.',
  'asst.err.blocked': 'Bu soru yanıtlanamadı.',
  'asst.err.generic': 'Asistan yanıt veremedi. Tekrar dene.',
};

const TABLES: Record<Lang, Dict> = {
  en: { ...en, ...diagnosisStrings.en },
  tr: { ...tr, ...diagnosisStrings.tr },
};

function interpolate(s: string, vars?: Vars) {
  if (!vars) return s;
  return s.replace(/\{(\w+)\}/g, (_, k) => (vars[k] != null ? String(vars[k]) : `{${k}}`));
}

interface I18nValue {
  lang: Lang;
  setLang: (l: Lang) => void;
  t: (key: string, vars?: Vars) => string;
  tRisk: (r: RiskLevel) => string;
  tStress: (s: StressType) => string;
  tDecision: (d: DecisionCode) => string;
  tActuator: (a: Actuator) => string;
  tMetric: (k: 'soil_moisture' | 'temperature' | 'humidity' | 'light') => string;
  tReason: (d: DecisionCode, score: number) => string;
  /** A disease code from the leaf model, as a name. Unknown codes are spelled out. */
  tDisease: (code: string | null | undefined) => string;
  /** The decision's reason, naming the disease when the leaf model found one. */
  tCaptureReason: (c: Pick<Capture, 'decision' | 'gpss_score' | 'diagnosis'>) => string;
}

const Ctx = createContext<I18nValue | null>(null);
const KEY = 'gp.lang';

export function I18nProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<Lang>(() => {
    const v = typeof localStorage !== 'undefined' ? localStorage.getItem(KEY) : null;
    return v === 'tr' ? 'tr' : 'en';
  });

  const value = useMemo<I18nValue>(() => {
    const t = (key: string, vars?: Vars) =>
      interpolate(TABLES[lang][key] ?? TABLES.en[key] ?? key, vars);
    const tDisease = (code: string | null | undefined) => {
      if (!code) return '--';
      const key = `disease.${code}`;
      const name = t(key);
      // A model the ML team ships later may know a disease this build does not.
      return name === key ? code.replace(/_/g, ' ').replace(/^./, (c) => c.toUpperCase()) : name;
    };
    return {
      lang,
      setLang: (l) => {
        setLangState(l);
        try {
          localStorage.setItem(KEY, l);
        } catch {
          // ignore
        }
      },
      t,
      tRisk: (r) => t(`risk.${r}`),
      tStress: (s) => t(`stress.${s}`),
      tDecision: (d) => t(`dec.${d}`),
      tActuator: (a) => t(`act.${a}`),
      tMetric: (k) => t(`metric.${k}`),
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
  }, [lang]);

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useT(): I18nValue {
  const v = useContext(Ctx);
  if (!v) throw new Error('useT outside provider');
  return v;
}

export function LangToggle() {
  const { lang, setLang } = useT();
  return (
    <div className="lang-toggle">
      {(['en', 'tr'] as Lang[]).map((l) => (
        <button key={l} className={`lang-opt${lang === l ? ' active' : ''}`} onClick={() => setLang(l)}>
          {l.toUpperCase()}
        </button>
      ))}
    </div>
  );
}
