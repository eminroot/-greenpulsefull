# GreenPulse — Optimizə Edilmiş ML Pipeline (Semifinal Versiyası)

Bu layihə, **"GreenPulse: ML Arxitektura Analizi və Optimizasiya Hesabatı"**ndə
təklif olunan 7-qatlı arxitekturanın tam işlək kod implementasiyasıdır.
Hesabatda qeyd olunan 3 əsas boşluq (HAL eksikliyi, LoRaWAN simulyasiyasının
olmaması, Edge AI resurs/gecikmə monitorinqinin yoxluğu) və 3 artıqlıq
(Layer 2/4 təkrarı, çoxlu-yarpaq seçimi, SQLite) burada həll olunub.

## 1. Qat → Fayl Xəritəsi

| Hesabatdakı Qat | Fayl | Funksiya |
|---|---|---|
| Layer 1: Unified Ingestion & HAL | `hal.py` | Simulyasiya / manual / ESP32 sensor mənbələri üçün ümumi interfeys |
| Layer 2: Leaf Vision AI Engine | `vision_engine.py` | YOLOv11n-Seg ilə yarpaq + zədə maskası çıxarılması |
| Layer 3: Biomorphic Feature Extraction | `biomorphic.py` | HSV rəng analizi (saralma/qəhvəyiləşmə faizi) |
| Layer 4: Digital Twin Sensor Fusion | `digital_twin.py` | Sensor + LoRaWAN paket strukturu/gecikmə simulyasiyası |
| Layer 5: GPSS Engine | `gpss_engine.py` | 0-100 ümumi stress skoru (riyazi düstur) |
| Layer 6: Autonomous Decision Engine | `decision_engine.py` | Skora görə aktuator qərarı (Suvarma ON və s.) |
| Layer 7: Streamlit Demo Dashboard | `app.py` | Münsiflər üçün canlı UI |
| — (utility) | `edge_monitor.py` | CPU/RAM/gecikmə ölçmələri (Layer 7-də göstərilir) |
| — (orchestrator) | `pipeline.py` | Layer 1-6-nı tək `run()` çağırışında birləşdirir |

```
greenpulse/
├── hal.py                       # Layer 1
├── vision_engine.py              # Layer 2
├── biomorphic.py                 # Layer 3
├── digital_twin.py               # Layer 4
├── gpss_engine.py                 # Layer 5
├── decision_engine.py            # Layer 6
├── edge_monitor.py               # Edge resurs monitoru
├── pipeline.py                   # Layer 1-6 orchestrator
├── app.py                        # Layer 7 (Streamlit)
├── run_cli_demo.py               # Streamlit-siz sürətli CLI test
├── scripts/
│   └── generate_test_image.py    # Real şəkil yoxdursa sintetik test şəkli
├── models/
│   └── yolo11n-seg.pt            # ←← BURAYA öz çəki faylınızı qoyun
└── requirements.txt
```

## 2. Quraşdırma

```bash
# 1) Virtual environment (tövsiyə olunur)
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

# 2) Asılılıqlar
pip install -r requirements.txt
```

> **Vacib:** `models/yolo11n-seg.pt` faylını öz repo-nuzdakı (screenshot-da
> görünən) `yolo11n-seg.pt` ilə əvəz edin. Path-ı `models/yolo11n-seg.pt`
> saxlamaq istəmirsinizsə, Streamlit sidebar-dakı "YOLOv11n-Seg çəki faylı
> yolu" sahəsindən və ya `run_cli_demo.py --weights` parametrindən fərqli
> path göstərə bilərsiniz.

## 3. İşə Salmaq

### A) Tam Streamlit Dashboard (münsif demosu üçün)
```bash
streamlit run app.py
```
Brauzerdə açılan səhifədə:
1. Sol paneldə (sidebar) sensor rejimini seçin — **Manual sliderlər** (münsif
   özü dəyişsin) və ya **Simulyasiya ssenarisi** (`drought`, `heat`,
   `low_light`, `normal`).
2. Yarpaq şəklini yükləyin və ya kameradan çəkin.
3. **"GreenPulse Pipeline-ı İşə Sal"** düyməsini basın.
4. Sağ paneldə GPSS skoru, risk səviyyəsi, qərar, inference vaxtı, CPU/RAM
   istifadəsi və LoRaWAN diaqnostikası canlı görünür.
5. Aşağıda, hər run sessiya tarixçəsinə əlavə olunur və qrafikdə göstərilir
   (`st.session_state` — SQLite yoxdur, demo riski azalır).

### B) Streamlit olmadan sürətli test (CLI)
Modelinizin və pipeline-ın düzgün işlədiyini yoxlamaq üçün, UI açmadan:
```bash
# Real yarpaq şəkliniz yoxdursa, əvvəlcə sintetik test şəkli yaradın:
python scripts/generate_test_image.py --out test_leaf.jpg --damage 25

# Pipeline-ı işə salın:
python run_cli_demo.py test_leaf.jpg --weights models/yolo11n-seg.pt --scenario drought
```
Çıxış, hesabatdakı "Demo JSON Çıxış Nümunəsi" formatında JSON-dur.

## 4. Demo JSON Sxemi (hesabatla 1:1 uyğun)

```json
{
  "stress_type": "Water Stress",
  "confidence": 0.87,
  "damage_percentage": 18.7,
  "soil_moisture": 24,
  "temperature": 34.5,
  "humidity": 78,
  "light": 620,
  "gpss_score": 82,
  "risk_level": "Critical",
  "decision": "IRRIGATION_ON",
  "inference_latency_ms": 42.5,
  "edge_cpu_usage_pct": 34.1
}
```
`pipeline.py` bu sxemi dəyişmədən qaytarır, üstəlik `_meta` altında əlavə
diaqnostik sahələr (LoRaWAN paketi, RAM istifadəsi, decision səbəbi və s.)
təqdim edir — dashboard bunlardan istifadə edir, başqa istehlakçılar
sadəcə əsas sahələri oxuya bilər.

## 5. Vacib Konfiqurasiya Nöqtələri (Münsiflərdən Əvvəl Mütləq Yoxlayın)

1. **YOLO class ID-ləri** (`vision_engine.py`, `LEAF_CLASS_ID` /
   `DAMAGE_CLASS_ID`) — öz `data.yaml`-ınızdakı class sırası ilə uyğun
   olmalıdır. Modeliniz yalnız "leaf" class-ı ilə train olunubsa (zədə
   class-ı yoxdursa), heç nə dəyişməyin — sistem avtomatik olaraq zədəni
   Layer 3-də HSV rəngindən hesablayacaq.
2. **HSV rəng həddləri** (`biomorphic.py`, `YELLOW_HSV_*` / `BROWN_HSV_*`)
   — real yarpaq şəkillərinizlə test edib lazım gələrsə tənzimləyin
   (işıqlandırma şəraitinə görə dəyişə bilər).
3. **GPSS çəkiləri və ideal diapazonlar** (`gpss_engine.py`, `WEIGHT_*` və
   `IDEAL_*`) — hazırkı dəyərlər mühəndis mülahizəsi əsasında seçilib;
   real sera datası toplandıqca kalibrasiya edin.
4. **Qərar həddləri** (`decision_engine.py`, `ACTION_THRESHOLD` =50,
   `ALERT_THRESHOLD` =76) — demo ssenarilərinizə uyğun tənzimləyin ki,
   nümayiş zamanı "Critical" vəziyyət real görünsün.

## 6. Komanda Bölgüsü ilə Uyğunluq (Hesabatın 4-cü bölməsi)

| Rol | Bu repo-da məsul olduğu fayllar |
|---|---|
| **AI/ML Lead** | `vision_engine.py`, `biomorphic.py`, `gpss_engine.py`, `decision_engine.py` — model inteqrasiyası, HSV skriptləri, GPSS düsturu, edge gecikmə ölçümü |
| **Backend Lead** | `hal.py`, `digital_twin.py`, `pipeline.py` — HAL strukturu, fake sensor/LoRaWAN generatoru, Streamlit-AI bağlantısı, `st.session_state` idarəsi |
| **Frontend Lead** | `app.py` — Dashboard dizaynı, sliderlər, status kartları, CPU/RAM/Latency monitor paneli, risk tarixçəsi qrafiki |

## 7. Dataset Lazımdırmı? (Mütləq Oxuyun)

**Bəli, çox güman ki lazımdır.** Ultralytics-in default `yolo11n-seg.pt`
faylı **COCO** dataseti üzərində train olunub (person, car, dog və s. —
80 ümumi class). Bu fayl ÖZÜ-ÖZÜNDƏN "leaf" və ya "damage" tanımır.

### Addım 1 — Əvvəlcə yoxlayın
Mövcud `yolo11n-seg.pt`-nin artıq sizin komanda tərəfindən fine-tune
olunub-olunmadığını yoxlayın:
```bash
python check_weights.py models/yolo11n-seg.pt
```
Əgər çıxışda `person`, `car`, `dog` kimi adlar görsəniz — bu, default COCO
modelidir, fine-tune lazımdır. Əgər `leaf`, `damage` (və ya oxşar) class
adları görsənirsə — komandanız artıq train edib, heç nə etməyə ehtiyac yoxdur.

### Addım 2 — Dataset tapın (lazımdırsa)
Semifinala qalan vaxta görə iki yol var:

**A) Sürətli yol (tövsiyə olunur, 3-5 günlük hazırlıq üçün):**
Yalnız **tək-class "leaf" seqmentasiya** dataseti tapın/yükləyin, zədəni isə
`biomorphic.py` (Layer 3) artıq HSV rəngindən avtomatik hesablayır —
ayrıca "damage" annotasiyası lazım deyil. Roboflow Universe-də hazır
nümunələr:
- `leaf-diseases-2` (Teresa Yong) — 588 şəkil, tək class, instance segmentation
- `Leaf Disease Segmentation` (xfhor) — instance segmentation

**B) Tam yol (vaxtınız varsa, daha dəqiq):**
Leaf + Damage iki ayrı class olan dataset:
- `plant diseases` (Roboflow, 9 class: bacterial_spot, black_rot, early_blight, esca, late_blight, leaf scorch, mold, rust, scab) — instance segmentation
- `tea leaf disease detection` (Roboflow, 7 xəstəlik class-ı) — instance segmentation

> PlantVillage/PlantDoc kimi məşhur dataset-lər əsasən **classification**
> üçündür (seqmentasiya maskası yoxdur) — YOLOv11n-Seg üçün birbaşa
> uyğun deyil, ya konvertasiya, ya da yuxarıdakı hazır seg dataset-lərdən
> istifadə edin.

Roboflow-dan endirəndə **"YOLOv11 Instance Segmentation"** export formatını
seçin — bu, birbaşa `train.py`-ın gözlədiyi `data.yaml` + `train/valid/test`
strukturunu verir.

### Addım 3 — Fine-tune edin
```bash
python train.py --data dataset/data.yaml --epochs 80 --device cpu
# GPU varsa: --device 0   (xeyli sürətli olur)
cp runs/segment/train/weights/best.pt models/yolo11n-seg.pt
```
Sonra yenidən yoxlayın: `python check_weights.py models/yolo11n-seg.pt`

## 8. Real Hardware-ə Keçid (Demo Sonrası)

`hal.py`-dakı `ESP32SensorSource` sinfi artıq stub olaraq hazırdır. Real
ESP32 + DHT22 qoşulanda:
1. `pip install pyserial`
2. `get_sensor_source(mode="esp32", connection="/dev/ttyUSB0")` çağırın.
3. ESP32 firmware-i `"<soil_moisture>,<temperature>,<humidity>,<light>\n"`
   formatında seriya port üzərindən CSV sətri göndərməlidir.
4. **Pipeline-ın, GPSS Engine-in, Decision Engine-in və Dashboard-ın heç
   biri dəyişmir** — bu, HAL-ın bütün məqsədidir.
