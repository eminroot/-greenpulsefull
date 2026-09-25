"""
GreenPulse sunum paketi - BOLUM B (slayt 29-78)

    29-36  Guvenlik ve karar
    37-45  Donanim ve kapali dongu      (cogu GERCEK TEST BEKLIYOR)
    46-56  Uc birim basarimi            (tamami GERCEK TEST BEKLIYOR)
    57-67  Arayuz ve surdurulebilirlik
    68-78  Muhendislik kaniti

Kural: `PENDING` rozetli slaytta SAYI YOKTUR. Projede Hailo, Raspberry Pi
gecikmesi, RAM/CPU/sicaklik, uzun sure kararliligi, gercek sulama ve su
tasarrufu icin TEK BIR olculmus deger bulunmuyor.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from scripts import prez_design as D
from scripts.prez_parts_a import _pending_slide


def _count_tests() -> int:
    """Test sayisi - rapor varsa oradan, yoksa dosyadan sayilir."""
    rep = D.load_json("reports/layer49_ai_testing_infrastructure_v1.json")
    for key in ("total_tests", "test_count", "collected_tests"):
        for blob in (rep, rep.get("tests", {}) if isinstance(rep.get("tests"), dict) else {}):
            if isinstance(blob, dict) and isinstance(blob.get(key), int):
                return blob[key]
    return len(list(Path("tests").glob("test_*.py")))


def _endpoints() -> int:
    spec = D.load_json("release/openapi_v1.json")
    return len(spec.get("paths", {}))


# --- 29-36  Guvenlik ve karar ---------------------------------------------

def s29(d, out, reg):
    fig = D.slide("Güvenlik Politikası Karar Kapısı",
                  "Yüksek risk tek başına fiziksel eylem başlatmaz",
                  D.SOFTWARE, kicker="Güvenlik")
    gates = [("Risk eşiği", "aşıldı mı?"), ("Kanıt uyumu", "çelişki var mı?"),
             ("Bekleme süresi", "cooldown doldu mu?"),
             ("Donanım durumu", "hazır mı?"), ("Yetki", "eyleme izinli mi?")]
    for i, (name, q) in enumerate(gates):
        x = D.ML + i * 0.185
        col = D.ALERT if i == len(gates) - 1 else D.ACCENT
        D.panel(fig, x, 0.46, 0.168, 0.175, ec=col, lw=1.9)
        fig.text(x + 0.084, 0.585, name, fontsize=D.T_BODY - 1,
                 fontweight="bold", color=col, ha="center", zorder=2)
        fig.text(x + 0.084, 0.525, q, fontsize=D.T_MICRO, color=D.MUTED,
                 ha="center", zorder=2)
    fig.text(0.50, 0.375, "Beş kapının HEPSİ geçilmeden eylem üretilmez",
             fontsize=D.T_H2, fontweight="bold", color=D.INK, ha="center")
    fig.text(0.50, 0.315, "Tek bir kapı kapalıysa sonuç: İZLE / İNCELE / "
             "ÇEKİMSER", fontsize=D.T_BODY, color=D.MUTED, ha="center")
    D.foot(fig, "Mevcut sürümde fiziksel eyleme tamamen DEVRE DIŞIDIR.",
           D.ALERT)
    D.save(fig, out, "29_guvenlik_karar_kapisi.png", reg, tier=D.SOFTWARE,
           source="reports/layer33_decision_safety_v1.json",
           claim="Güvenlik kapısı koşulları")


def s30(d, out, reg):
    fig = D.slide("Hata / Güvenli Durum Matrisi",
                  "Her hata türünün tanımlı ve test edilmiş bir çıkışı var",
                  D.SOFTWARE, kicker="Güvenli davranış")
    rows = [("Görüntü bulanık / karanlık", "IMAGE_REJECT", "yeniden çekim"),
            ("Model güveni düşük", "ABSTAIN", "insan incelemesi"),
            ("Bilinmeyen ürün", "BLOCK", "yönlendirme yok"),
            ("Sensör eksik / bayat", "DEGRADED", "izlemeye dön"),
            ("Görüntü–sensör çelişkisi", "CONFLICT", "insan incelemesi"),
            ("Donanım ACK yok", "SAFE_STATE", "eylemi geri al"),
            ("Model yüklenemedi", "FAIL_CLOSED", "sistem karar vermez")]
    D.table(fig, D.ML, 0.72, D.MR - D.ML,
            (["Durum", "Güvenli mod", "Sonuç"], [0.0, 0.44, 0.68]),
            rows, rh=0.078, col_colors={1: D.ALERT, 2: D.MUTED})
    D.foot(fig, "Hiçbir hata durumu özerk fiziksel eylemle sonuçlanmaz.",
           D.ALERT)
    D.save(fig, out, "30_guvenli_durum_matrisi.png", reg, tier=D.SOFTWARE,
           source="reports/layer33_decision_safety_v1.json",
           claim="Hata → güvenli mod eşlemesi")


def s31(d, out, reg):
    fig = D.slide("Hata Durumu Isı Haritası",
                  "Hangi hata hangi katmanda yakalanıyor", D.SOFTWARE,
                  kicker="Kapsama")
    layers = ["Kalite kapısı", "Sınıflandırıcı", "Sensör doğrulama",
              "Füzyon", "Güvenlik kapısı", "Donanım ACK"]
    faults = ["Bulanık kare", "Düşük güven", "Bilinmeyen ürün",
              "Bayat sensör", "Çelişki", "ACK yok"]
    cover = np.array([
        [1, 0, 0, 0, 0, 0], [0, 1, 1, 0, 0, 0], [0, 0, 0, 1, 0, 0],
        [0, 0, 0, 1, 1, 0], [0, 0, 0, 0, 1, 0], [0, 0, 0, 0, 1, 1],
    ], dtype=float)
    ax = fig.add_axes([0.30, 0.20, 0.42, 0.52])
    ax.set_facecolor(D.BG)
    ax.imshow(cover, cmap="Greens", vmin=0, vmax=1.4)
    ax.set_xticks(range(len(layers)), layers, rotation=30, ha="right",
                  fontsize=D.T_MICRO)
    ax.set_yticks(range(len(faults)), faults, fontsize=D.T_MICRO)
    ax.grid(False)
    for i in range(len(faults)):
        for j in range(len(layers)):
            if cover[i, j]:
                ax.text(j, i, "✓", ha="center", va="center", fontsize=15,
                        color="white", fontweight="bold")
    D.foot(fig, "Kapsama tablosu yazılım testlerinden türetilmiştir; "
                "gerçek saha hata oranı ölçülmemiştir.", D.WARN)
    D.save(fig, out, "31_hata_durumu_isi_haritasi.png", reg,
           tier=D.SOFTWARE, source="tests/ + reports/layer33_*.json",
           claim="Hata türü / yakalayan katman eşlemesi")


def s32(d, out, reg):
    fig = D.slide("Açıklanabilir Karar — Gerekçe Kodları",
                  "Her karar, okunabilir gerekçelerle birlikte kaydedilir",
                  D.SOFTWARE, kicker="Açıklanabilirlik")
    codes = [("VISUAL_STRESS_HIGH", "Görüntüde stres belirtisi yüksek", D.BRAND),
             ("VISUAL_DELTA_HIGH", "Bitkinin kendi referansından sapma büyük", D.BRAND),
             ("LOW_SOIL_MOISTURE", "Toprak nemi kritik eşiğin altında", D.ACCENT),
             ("TEMPORAL_CONFIRMATION", "Ardışık ölçümlerle doğrulandı", D.WARN),
             ("SENSOR_CONFLICT", "Görüntü ve sensör çelişiyor", D.ALERT),
             ("LOW_CONFIDENCE", "Model güveni eşiğin altında", D.ALERT)]
    for i, (code, desc, col) in enumerate(codes):
        y = 0.70 - i * 0.092
        D.panel(fig, D.ML, y - 0.032, D.MR - D.ML, 0.070, ec=D.LINE, lw=1.0)
        fig.text(D.ML + 0.018, y, code, fontsize=D.T_BODY - 1,
                 fontweight="bold", color=col, va="center", zorder=2,
                 family="monospace")
        fig.text(D.ML + 0.34, y, desc, fontsize=D.T_BODY - 1, color=D.INK,
                 va="center", zorder=2)
    D.foot(fig, "Gerekçe kodları hem kullanıcı arayüzüne hem denetim "
                "günlüğüne aynı biçimde yazılır.")
    D.save(fig, out, "32_gerekce_kodlari.png", reg, tier=D.SOFTWARE,
           source="reports/layer34_decision_reason_explainability_v1.json",
           claim="Gerekçe kodu sözlüğü")


def s33(d, out, reg):
    fig = D.slide("Komut İzlenebilirlik Zinciri",
                  "Bir komuttan geriye, o kararı üreten kareye kadar",
                  D.SOFTWARE, kicker="Denetim")
    D.flow(fig, [("Komut\nkimliği", D.ALERT), ("Karar\nkaydı", D.WARN),
                 ("Risk\nskoru", D.WARN), ("Füzyon\ngirdisi", D.ACCENT),
                 ("Model\nsürümü", D.BRAND), ("Görüntü\nkaresi", D.BRAND)],
           y=0.52, h=0.155)
    D.bullets(fig, D.ML, 0.40, [
        "Her bağlantı veritabanında SHA ile kayıtlıdır",
        "Model sürümü, veri kümesi sürümü ve politika sürümü aynı kayıtta tutulur",
        "Zincir tek sorguyla geriye doğru okunur",
    ])
    D.foot(fig, "İzlenebilirlik testleri mevcuttur; gerçek saha komutları "
                "henüz üretilmemiştir.", D.WARN)
    D.save(fig, out, "33_izlenebilirlik_zinciri.png", reg, tier=D.SOFTWARE,
           source="reports/layer35_*.json, tests/test_audit_traceability.py",
           claim="İzlenebilirlik zinciri")


def s34(d, out, reg):
    fig = D.slide("Risk → Sulama İsteği → Donanım → ACK",
                  "Karardan fiziksel eyleme giden tam yol", D.SOFTWARE,
                  kicker="Eylem yolu")
    D.flow(fig, [("Risk ≥ eşik", D.WARN), ("SULAMA\nİSTEĞİ", D.ALERT),
                 ("Güvenlik\nkapısı", D.ALERT), ("Röle /\nMOSFET", D.NEUTRAL),
                 ("Pompa", D.ACCENT), ("ACK", D.BRAND),
                 ("Etki\ndoğrulama", D.BRAND)], y=0.52, h=0.155)
    D.bullets(fig, D.ML, 0.40, [
        "Komut kimliği istek anında üretilir ve ACK ile eşleşir",
        "ACK gelmezse sistem güvenli duruma geçer ve eylemi geri alır",
        "Etki, sensör değişimiyle doğrulanır — döngü burada kapanır",
    ])
    D.foot(fig, "Yol yazılımda uçtan uca test edilmiştir. Gerçek röle, "
                "pompa ve ACK zamanlaması ÖLÇÜLMEMİŞTİR.", D.ALERT)
    D.save(fig, out, "34_risk_sulama_ack_yolu.png", reg, tier=D.SOFTWARE,
           source="reports/layer38_*.json, reports/layer39_*.json",
           claim="Eylem yolu adımları")


def s35(d, out, reg):
    fig = D.slide("Donanım ACK Durum Makinesi",
                  "EXECUTED / REJECTED / FAILED / TIMEOUT", D.SOFTWARE,
                  kicker="Donanım sözleşmesi")
    states = [("GÖNDERİLDİ", D.NEUTRAL, "komut kimliği üretildi"),
              ("EXECUTED", D.BRAND, "pompa çalıştı, etki beklenir"),
              ("REJECTED", D.WARN, "donanım reddetti, cooldown yok"),
              ("FAILED", D.ALERT, "çalışma hatası, güvenli durum"),
              ("TIMEOUT", D.ALERT, "yanıt yok, eylem geri alınır")]
    D.panel(fig, 0.40, 0.66, 0.20, 0.095, ec=D.NEUTRAL, lw=2.0)
    fig.text(0.50, 0.7075, states[0][0], fontsize=D.T_BODY,
             fontweight="bold", color=D.NEUTRAL, ha="center", va="center",
             zorder=2)
    for i, (name, col, note) in enumerate(states[1:]):
        x = D.ML + i * 0.232
        D.panel(fig, x, 0.38, 0.212, 0.145, ec=col, lw=2.0)
        fig.text(x + 0.106, 0.478, name, fontsize=D.T_BODY,
                 fontweight="bold", color=col, ha="center", zorder=2)
        fig.text(x + 0.106, 0.420, note, fontsize=D.T_MICRO, color=D.MUTED,
                 ha="center", zorder=2)
    fig.text(0.50, 0.305, "Yalnızca EXECUTED bekleme süresini başlatır",
             fontsize=D.T_BODY, color=D.INK, ha="center", fontweight="bold")
    D.foot(fig, "Durum makinesi ve geçişleri test edilmiştir; gerçek "
                "donanım yanıt süreleri ölçülmemiştir.", D.WARN)
    D.save(fig, out, "35_ack_durum_makinesi.png", reg, tier=D.SOFTWARE,
           source="reports/layer39_hardware_ack_action_state_v1.json",
           claim="ACK durumları ve geçişleri")


def s36(d, out, reg):
    _pending_slide(
        out, reg, "36_ack_zaman_cizgisi.png",
        "Donanım İstek / ACK Zaman Çizgisi",
        "İstekten onaya geçen gerçek süre", "Donanım zamanlaması",
        ["Her komut için gönderim ve ACK zaman damgası kaydedilir",
         "Gecikme dağılımı ve zaman aşımı oranı çıkarılır",
         "REJECTED / FAILED / TIMEOUT payları raporlanır"],
        ["Gerçek röle ve pompa bağlanmadı",
         "Tek bir gerçek ACK ölçümü yok",
         "Zamanlama uydurulamaz"],
        "reports/layer39_hardware_ack_action_state_v1.json")


# --- 37-45  Donanim ve kapali dongu ---------------------------------------

def s37(d, out, reg):
    _pending_slide(
        out, reg, "37_sulama_oncesi_sonrasi_risk.png",
        "Sulama Öncesi / Sonrası Risk", "Müdahale riski gerçekten düşürüyor mu?",
        "Etki doğrulama",
        ["Müdahale öncesi ve sonrası risk skorları eşleştirilir",
         "Aynı bitki, aynı kamera açısı, aynı ışık koşulu",
         "Düşüş istatistiksel olarak sınanır"],
        ["Gerçek sulama müdahalesi yapılmadı",
         "Öncesi/sonrası risk çifti yok",
         "Etki ölçülmeden sunulamaz"],
        "reports/layer40_closed_loop_feedback_intelligence_v1.json")


def s38(d, out, reg):
    _pending_slide(
        out, reg, "38_toprak_nemi_tepkisi.png",
        "Sulama Öncesi / Sonrası Toprak Nemi",
        "Pompa süresi ile nem artışı arasındaki ilişki",
        "Sensör tepkisi",
        ["Pompa çalışma süresi kaydedilir",
         "Toprak nemi belirli aralıklarla örneklenir",
         "Tepki eğrisi ve gecikme çıkarılır"],
        ["Gerçek pompa çalıştırılmadı",
         "Nem tepki eğrisi ölçülmedi",
         "Pompa kalibrasyonu yapılmadı"],
        "reports/layer40_closed_loop_feedback_intelligence_v1.json")


def s39(d, out, reg):
    _pending_slide(
        out, reg, "39_gercek_mudahale_zaman_cizgisi.png",
        "Gerçek Kapalı Döngü Müdahale Zaman Çizgisi",
        "Risk yükselişinden etki doğrulamasına kadar tek bir gerçek olay",
        "Kapalı döngü",
        ["Risk artışı, karar, komut, ACK ve sensör tepkisi tek zaman "
         "çizgisinde toplanır",
         "Her adımın zaman damgası denetim günlüğünden alınır"],
        ["Gerçek serada tek bir kapalı döngü olayı yaşanmadı",
         "Zaman çizgisi yalnızca simülasyonda üretildi",
         "Simülasyon sonucu gerçek gibi sunulmaz"],
        "reports/layer40_closed_loop_feedback_intelligence_v1.json")


def s40(d, out, reg):
    fig = D.slide("Fiziksel Donanım Mimarisi",
                  "Bileşenler ve aralarındaki sorumluluk ayrımı",
                  D.SOFTWARE, kicker="Donanım tasarımı")
    comps = [("ESP32-CAM", "görüntü yakalama", D.ACCENT),
             ("Sensör dizisi", "nem / sıcaklık / nem", D.ACCENT),
             ("Raspberry Pi 5", "çıkarım + karar", D.BRAND),
             ("AI HAT+ (Hailo)", "hızlandırma", D.BRAND),
             ("Röle / MOSFET", "güç anahtarlama", D.WARN),
             ("Pompa", "fiziksel eyleme", D.ALERT)]
    for i, (name, role, col) in enumerate(comps):
        x = D.ML + (i % 3) * 0.303
        y = 0.52 - (i // 3) * 0.235
        D.panel(fig, x, y, 0.278, 0.195, ec=col, lw=1.9)
        fig.text(x + 0.020, y + 0.140, name, fontsize=D.T_H2 - 3,
                 fontweight="bold", color=col, zorder=2)
        fig.text(x + 0.020, y + 0.075, role, fontsize=D.T_SMALL,
                 color=D.MUTED, zorder=2)
    D.foot(fig, "Donanım sözleşmesi ve şemaları hazırdır; bileşenler "
                "henüz birleştirilip ölçülmemiştir.", D.ALERT)
    D.save(fig, out, "40_fiziksel_donanim_mimarisi.png", reg,
           tier=D.SOFTWARE,
           source="reports/layer38_hardware_integration_interface_v1.json",
           claim="Donanım bileşenleri ve rolleri")


def s41(d, out, reg):
    fig = D.slide("Uç Birim Yerleşimi",
                  "Raspberry Pi 5 + AI HAT+ + ESP32-CAM + sensörler + "
                  "röle/MOSFET + pompa", D.SOFTWARE, kicker="Yerleşim")
    D.flow(fig, [("ESP32-CAM", D.ACCENT), ("Wi-Fi", D.NEUTRAL),
                 ("Raspberry Pi 5", D.BRAND), ("AI HAT+\n(Hailo)", D.BRAND),
                 ("Röle /\nMOSFET", D.WARN), ("Pompa", D.ALERT)],
           y=0.55, h=0.155)
    D.bullets(fig, D.ML, 0.435, [
        "ESP32-CAM'de Wi-Fi etkinken ADC2 kullanılamaz — sensörler Pi tarafında okunur",
        "Raspberry Pi'nin analog girişi yoktur — harici ADC gerekir",
        "Pompa gücü röle/MOSFET üzerinden anahtarlanır, Pi doğrudan sürmez",
    ])
    D.foot(fig, "Bu iki tuzak tasarımda öngörüldü ve donanım sözleşmesine "
                "yazıldı; fiziksel kurulum henüz doğrulanmadı.", D.ALERT)
    D.save(fig, out, "41_uc_birim_yerlesimi.png", reg, tier=D.SOFTWARE,
           source="reports/layer38_hardware_integration_interface_v1.json",
           claim="Uç birim bileşen zinciri ve bilinen tuzaklar")


def s42(d, out, reg):
    _pending_slide(
        out, reg, "42_prototip_fotografi.png",
        "Gerçek Prototip Fotoğrafı",
        "Bileşen açıklamalarıyla birlikte fiziksel kurulum",
        "Prototip",
        ["Kurulum tamamlandığında fotoğraf çekilir",
         "Her bileşen profesyonel açıklama etiketiyle işaretlenir",
         "Fotoğraf, donanım sözleşmesindeki şema ile eşleştirilir"],
        ["Projede prototip fotoğrafı bulunmuyor",
         "Temsili görsel kullanmak yanıltıcı olur",
         "Fotoğraf yerine boş yer tutucu bırakılmaz"],
        "—")


def s43(d, out, reg):
    fig = D.slide("Hailo Dağıtım Hattı",
                  "PyTorch → ONNX → HEF → Pi 5 + AI HAT+", D.PENDING,
                  kicker="Uç birim dağıtımı")
    steps = [("PyTorch\n.pt", D.BRAND, True), ("ONNX\ndışa aktarım", D.BRAND, True),
             ("ONNX\neşitliği", D.BRAND, True), ("HEF\ndönüşümü", D.ALERT, False),
             ("Pi 5 +\nAI HAT+", D.ALERT, False), ("Donanım\neşitliği", D.ALERT, False)]
    n = len(steps)
    w = (D.MR - D.ML - 0.012 * (n - 1)) / n
    for i, (label, col, done) in enumerate(steps):
        x = D.ML + i * (w + 0.012)
        D.panel(fig, x, 0.50, w, 0.155, ec=col, lw=2.1,
                fc=D.PANEL if done else "#FBF3F2")
        fig.text(x + w / 2, 0.595, label, fontsize=D.T_BODY - 1,
                 fontweight="bold", color=col, ha="center", va="center",
                 zorder=2, linespacing=1.3)
        fig.text(x + w / 2, 0.525, "TAMAM" if done else "BEKLİYOR",
                 fontsize=D.T_MICRO, fontweight="bold",
                 color=D.BRAND if done else D.ALERT, ha="center", zorder=2)
    fig.text(D.ML, 0.40, "İlk üç adım tamamlandı ve ölçüldü. Son üç adım "
             "donanım gerektirir.", fontsize=D.T_BODY, color=D.INK)
    D.pending_note(fig, "HEF üretilmedi; Hailo çalışma zamanı ölçülmedi.")
    D.save(fig, out, "43_hailo_dagitim_hatti.png", reg, tier=D.PENDING,
           source="reports/layer41_hailo_edge_readiness_v1.json",
           claim="Dağıtım hattı durumu — son üç adım ölçülmedi")


def s44(d, out, reg):
    _pending_slide(
        out, reg, "44_onnx_vs_hailo_paritesi.png",
        "ONNX vs Hailo Tahmin Eşitliği",
        "Niceleme sonrası model aynı kararı veriyor mu?",
        "Donanım eşitliği",
        ["Aynı örnek kümesi ONNX ve HEF üzerinde çalıştırılır",
         "Top-1 uyuşmazlık sayısı ve olasılık farkı ölçülür",
         "Kalibrasyon kümesi gerçek sera kareleriyle kurulur"],
        ["HEF dosyası üretilmedi",
         "Hailo cihazında tek bir çıkarım yapılmadı",
         "Niceleme kaybı ölçülmeden eşitlik iddia edilemez"],
        "reports/layer41_hailo_edge_readiness_v1.json")


def s45(d, out, reg):
    _pending_slide(
        out, reg, "45_hailo_guven_farki.png",
        "Hailo Güven Farkı Dağılımı",
        "Niceleme, güven değerlerini ne kadar kaydırıyor?",
        "Niceleme etkisi",
        ["ONNX ve HEF güven değerleri örnek örnek karşılaştırılır",
         "Fark dağılımı ve uç değerler çıkarılır",
         "Eşik kararlarını etkileyip etkilemediği sınanır"],
        ["HEF yok, Hailo çalıştırması yok",
         "Güven farkı dağılımı ölçülmedi"],
        "reports/layer41_hailo_edge_readiness_v1.json")


# --- 46-56  Uc birim basarimi (tamami PENDING) ----------------------------

_EDGE_WHY = ["Raspberry Pi 5 + AI HAT+ üzerinde çalıştırma yapılmadı",
             "Host bilgisayar ölçümü Pi başarımını temsil etmez",
             "Bu sayıyı tahmin etmek yanıltıcı olur"]


def _edge_pending(out, reg, fname, title, subtitle, protocol):
    _pending_slide(out, reg, fname, title, subtitle, "Uç birim başarımı",
                   protocol, _EDGE_WHY,
                   "reports/layer44_edge_benchmarking_v1.json")


def s46(d, out, reg):
    _edge_pending(out, reg, "46_gecikme_selalesi.png",
                  "Uç Birim Gecikme Şelalesi",
                  "Her aşamanın gecikmeye katkısı",
                  ["Kare yakalama, ön işleme, çıkarım, füzyon, karar "
                   "aşamaları ayrı ölçülür",
                   "Ortalama, medyan, p95 ve maksimum raporlanır"])


def s47(d, out, reg):
    _edge_pending(out, reg, "47_uctan_uca_gecikme.png",
                  "Uçtan Uca Gecikme Dağılımı",
                  "Kareden karara geçen toplam süre",
                  ["En az 200 ardışık çevrim ölçülür",
                   "Dağılım ve uç değerler birlikte sunulur"])


def s48(d, out, reg):
    _edge_pending(out, reg, "48_ram_kullanimi.png",
                  "RAM Kullanımı ve 3 GB Sınırı",
                  "Bellek bütçesi aşılıyor mu?",
                  ["Uzun çalışma boyunca RSS örneklenir",
                   "3 GB sert sınır çizgisi grafiğe eklenir",
                   "Sızıntı göstergesi olarak artış eğilimi izlenir"])


def s49(d, out, reg):
    _edge_pending(out, reg, "49_tepe_ram.png", "Tepe RAM Değeri",
                  "En yüksek bellek kullanımı ve sınıra uzaklık",
                  ["Tepe RSS ve sınıra oranı kaydedilir",
                   "Ölçüm Pi 5 üzerinde, gerçek modelle yapılır"])


def s50(d, out, reg):
    _edge_pending(out, reg, "50_cpu_kullanimi.png",
                  "CPU Kullanımı Zaman Serisi",
                  "İşlemci yükü ve termal baskı",
                  ["Çevrim başına CPU yüzdesi örneklenir",
                   "Yük, örnekleme sıklığı ile birlikte değerlendirilir"])


def s51(d, out, reg):
    _edge_pending(out, reg, "51_cihaz_sicakligi.png",
                  "Cihaz Sıcaklığı Zaman Serisi",
                  "Termal kısıtlama başlıyor mu?",
                  ["Pi 5 çekirdek sıcaklığı sürekli örneklenir",
                   "Kısıtlama eşiği grafiğe işlenir"])


def s52(d, out, reg):
    _edge_pending(out, reg, "52_kararlilik_panosu.png",
                  "Uzun Süre Kararlılık Panosu",
                  "30 dakika / 1 saat / çok saatli çalışma",
                  ["Kesintisiz çalışma boyunca bellek, CPU, sıcaklık ve "
                   "gecikme birlikte izlenir",
                   "Çökme, zaman aşımı ve hata sayıları kaydedilir"])


def s53(d, out, reg):
    _edge_pending(out, reg, "53_hata_ozeti.png",
                  "Çökme / Zaman Aşımı / Hata Özeti",
                  "Uzun çalışmada kararlılık kanıtı",
                  ["Çökme sayısı, yeniden başlatma, zaman aşımı ve "
                   "yakalanan istisnalar sayılır",
                   "Her olay denetim günlüğüne bağlanır"])


def s54(d, out, reg):
    fig = D.slide("Uyarlanabilir Görüntü Örnekleme",
                  "Risk arttıkça sistem daha sık bakar", D.SOFTWARE,
                  kicker="Kaynak yönetimi")
    modes = [("KARARLI", "düşük risk", "seyrek örnekleme", D.BRAND),
             ("YÜKSELMİŞ", "orta risk", "sıklık artar", D.WARN),
             ("YÜKSEK", "yüksek risk", "en sık örnekleme", D.ALERT)]
    for i, (name, state, act, col) in enumerate(modes):
        x = D.ML + i * 0.303
        D.panel(fig, x, 0.38, 0.278, 0.30, ec=col, lw=2.0)
        fig.text(x + 0.139, 0.615, name, fontsize=D.T_H2,
                 fontweight="bold", color=col, ha="center", zorder=2)
        fig.text(x + 0.139, 0.545, state, fontsize=D.T_BODY, color=D.MUTED,
                 ha="center", zorder=2)
        fig.text(x + 0.139, 0.455, act, fontsize=D.T_BODY, color=D.INK,
                 ha="center", zorder=2)
    D.foot(fig, "Örnekleme politikası yazılımda tanımlı ve test edilmiştir; "
                "gerçek enerji/işlem tasarrufu ölçülmemiştir.", D.WARN)
    D.save(fig, out, "54_uyarlanabilir_ornekleme.png", reg, tier=D.SOFTWARE,
           source="reports/layer43_adaptive_image_sampling_v1.json",
           claim="Örnekleme modları")


def s55(d, out, reg):
    fig = D.slide("Kaynak Optimizasyon Mimarisi",
                  "Sınırlı uç birimde çalışabilmek için tasarım kararları",
                  D.SOFTWARE, kicker="Kaynak yönetimi")
    D.bullets(fig, D.ML, 0.68, [
        "Küçük giriş boyutu (224 px) — bellek ve gecikme bütçesi için",
        "Hafif sınıflandırma modeli (YOLO11n-cls)",
        "Uyarlanabilir örnekleme — boşta düşük yük",
        "Tek seferlik model yükleme, çevrim başına yeniden yükleme yok",
        "Görüntü tamponu sınırlı; eski kareler diske taşınır",
    ], size=D.T_H2 - 4, dy=0.085)
    D.foot(fig, "Tasarım kararları uygulanmış ve testlerle korunmaktadır; "
                "kazanç Pi üzerinde ölçülmemiştir.", D.WARN)
    D.save(fig, out, "55_kaynak_optimizasyonu.png", reg, tier=D.SOFTWARE,
           source="reports/layer42_resource_optimization_v1.json",
           claim="Kaynak tasarım kararları")


def s56(d, out, reg):
    fig = D.slide("Sistem Sağlık Panosu",
                  "Sistem kendi durumunu dürüstçe bildirir", D.SOFTWARE,
                  kicker="İşletim")
    checks = [("Bellek", "HEALTHY", D.BRAND, "sınır içinde"),
              ("Görme modeli", "DEGRADED", D.WARN, "araştırma modeli"),
              ("Alan koruyucu", "HEALTHY", D.BRAND, "kalibre"),
              ("Ürün profilleri", "DEGRADED", D.WARN, "agronomik onay yok"),
              ("Donanım", "DEGRADED", D.ALERT, "simülatör"),
              ("Veritabanı", "HEALTHY", D.BRAND, "yazma/okuma tamam")]
    for i, (name, state, col, note) in enumerate(checks):
        x = D.ML + (i % 3) * 0.303
        y = 0.52 - (i // 3) * 0.225
        D.panel(fig, x, y, 0.278, 0.185, ec=D.LINE, lw=1.3)
        fig.text(x + 0.020, y + 0.132, name, fontsize=D.T_BODY,
                 fontweight="bold", color=D.INK, zorder=2)
        fig.text(x + 0.020, y + 0.072, state, fontsize=D.T_H2 - 3,
                 fontweight="bold", color=col, zorder=2)
        fig.text(x + 0.020, y + 0.028, note, fontsize=D.T_MICRO,
                 color=D.MUTED, zorder=2)
    D.foot(fig, "Sistem kendini sağlıklı ilan etmiyor — çünkü değil. Her "
                "DEGRADED durumun nedeni yazılıdır.")
    D.save(fig, out, "56_sistem_saglik_panosu.png", reg, tier=D.SOFTWARE,
           source="src/ sağlık denetimi + reports/layer55_*.json",
           claim="Sağlık denetimleri ve dürüst durum bildirimi")


# --- 57-67  Arayuz ve surdurulebilirlik -----------------------------------

def s57(d, out, reg):
    fig = D.slide("Arayüz — Canlı Kontrol Paneli",
                  "Operatörün göreceği ekran düzeni", D.SOFTWARE,
                  kicker="Ön uç sözleşmesi")
    D.panel(fig, D.ML, 0.20, 0.56, 0.55, ec=D.LINE, lw=1.4)
    fig.text(D.ML + 0.022, 0.715, "Bitki görüntüsü + risk katmanı",
             fontsize=D.T_BODY, color=D.MUTED, zorder=2)
    for i, (k, v, col) in enumerate([("Risk", "0–100", D.WARN),
                                     ("Görme", "sınıf + güven", D.BRAND),
                                     ("Sensör", "nem / sıcaklık / nem", D.ACCENT),
                                     ("Karar", "eylem + gerekçe", D.ALERT)]):
        y = 0.63 - i * 0.105
        fig.text(D.ML + 0.022, y, k, fontsize=D.T_SMALL, color=D.MUTED,
                 zorder=2)
        fig.text(D.ML + 0.16, y, v, fontsize=D.T_BODY, fontweight="bold",
                 color=col, zorder=2)
    D.panel(fig, 0.63, 0.20, 0.318, 0.55, ec=D.LINE, lw=1.4)
    fig.text(0.652, 0.715, "Son eylem ve sistem durumu", fontsize=D.T_BODY,
             color=D.MUTED, zorder=2)
    D.bullets(fig, 0.652, 0.645, ["Komut kimliği", "ACK durumu",
                                  "Bekleme süresi", "Sağlık özeti"],
              size=D.T_SMALL, dy=0.062)
    D.foot(fig, "Ön uç alan sözlüğü ve OpenAPI sözleşmesi hazırdır; ekran "
                "görüntüsü yerine sözleşme gösterilir.", D.WARN)
    D.save(fig, out, "57_arayuz_kontrol_paneli.png", reg, tier=D.SOFTWARE,
           source="release/frontend_field_dictionary_v1.json",
           claim="Ön uç alan düzeni")


def s58(d, out, reg):
    fig = D.slide("Açıklamalı Bitki Ekranı",
                  "Görüntü + risk + sensör + karar tek ekranda",
                  D.SOFTWARE, kicker="Ön uç sözleşmesi")
    D.bullets(fig, D.ML, 0.68, [
        "Bitki kimliği ve seans bilgisi",
        "Görme sınıfı, güven değeri ve Grad-CAM bindirmesi",
        "Sensör okumaları ve geçerlilik damgası",
        "Risk skoru, bandı ve gerekçe kodları",
        "Üretilen eylem ve ACK durumu",
    ], size=D.T_H2 - 4, dy=0.085)
    D.foot(fig, "Tüm alanlar ön uç alan sözlüğünde tanımlıdır; arayüz "
                "uygulaması ayrı ekibin sorumluluğundadır.")
    D.save(fig, out, "58_aciklamali_bitki_ekrani.png", reg, tier=D.SOFTWARE,
           source="release/frontend_field_dictionary_v1.json",
           claim="Ekran alanları")


def s59(d, out, reg):
    fig = D.slide("Son Eylem ve Sistem Durumu Bileşeni",
                  "Operatör tek bakışta ne olduğunu görür", D.SOFTWARE,
                  kicker="Ön uç sözleşmesi")
    rows = [("command_id", "eylemin benzersiz kimliği"),
            ("action", "IRRIGATION_REQUEST / MONITOR / NO_ACTION"),
            ("ack_state", "EXECUTED / REJECTED / FAILED / TIMEOUT"),
            ("cooldown_remaining_s", "bekleme süresi"),
            ("reason_codes", "kararın okunabilir gerekçesi"),
            ("system_state", "RUNNING / DEGRADED / SAFE_STATE")]
    D.table(fig, D.ML, 0.70, D.MR - D.ML,
            (["Alan", "Anlamı"], [0.0, 0.34]), rows, rh=0.082)
    D.foot(fig, "Alan adları backend ve frontend sözleşmelerinde aynıdır.")
    D.save(fig, out, "59_son_eylem_bileseni.png", reg, tier=D.SOFTWARE,
           source="release/frontend_field_dictionary_v1.json",
           claim="Durum bileşeni alanları")


def s60(d, out, reg):
    fig = D.slide("Sürdürülebilirlik Zekâsı",
                  "Su ve enerji tasarrufu nasıl hesaplanır", D.SOFTWARE,
                  kicker="Sürdürülebilirlik")
    D.flow(fig, [("Temel\nsenaryo", D.NEUTRAL), ("Gerçek\nmüdahale", D.ACCENT),
                 ("Fark", D.WARN), ("Tasarruf\ntahmini", D.WARN)],
           y=0.52, h=0.155)
    D.bullets(fig, D.ML, 0.40, [
        "Tasarruf = (temel senaryo − gerçek kullanım) / temel senaryo",
        "Temel senaryo HER ZAMAN bir varsayımdır — ölçüm değildir",
        "Bu nedenle tasarruf değeri TAHMİN olarak etiketlenir",
    ])
    D.foot(fig, "Yöntem tanımlı ve test edilmiştir; gerçek su tüketimi "
                "ölçülmediği için sayı sunulmaz.", D.ALERT)
    D.save(fig, out, "60_surdurulebilirlik_yontemi.png", reg,
           tier=D.SOFTWARE,
           source="reports/layer53_sustainability_intelligence_v1.json",
           claim="Tasarruf hesaplama yöntemi")


def s61(d, out, reg):
    _pending_slide(
        out, reg, "61_su_kullanimi_vs_temel.png",
        "Su Kullanımı vs Doğrulanmış Temel Senaryo",
        "Gerçek tüketim, temel senaryoya göre nerede?",
        "Su tasarrufu",
        ["Pompa debisi ölçülerek kalibre edilir",
         "Çalışma süresi × debi = gerçek tüketim",
         "Temel senaryo agronomik kaynakla belgelenir"],
        ["Pompa kalibrasyonu yapılmadı",
         "Gerçek tüketim ölçülmedi",
         "Temel senaryo bir varsayımdır — ikisi de olmadan yüzde verilemez"],
        "reports/layer53_sustainability_intelligence_v1.json")


def s62(d, out, reg):
    _pending_slide(
        out, reg, "62_su_tasarrufu.png",
        "Su Tasarrufu — Yüzde ve Litre",
        "Tasarruf iddiası ancak iki gerçek sayıyla kurulur",
        "Su tasarrufu",
        ["Gerçek tüketim litre cinsinden ölçülür",
         "Temel senaryo ayrıca belgelenir ve kaynak gösterilir"],
        ["Ne gerçek tüketim ne de kalibre temel senaryo mevcut",
         "Yüzde tasarruf en kolay şişirilen metriktir — ölçmeden sunulmaz"],
        "reports/layer53_sustainability_intelligence_v1.json")


def s63(d, out, reg):
    _pending_slide(
        out, reg, "63_mudahale_sayisi.png",
        "Müdahale Sayısı Karşılaştırması",
        "Zamanlı sulama ile risk tabanlı sulama arasındaki fark",
        "Sürdürülebilirlik",
        ["Aynı sürede zamanlı ve risk tabanlı müdahale sayıları sayılır",
         "Bitki sağlığı sonucu birlikte değerlendirilir"],
        ["Gerçek çalışma dönemi yok",
         "Müdahale sayısı ölçülmedi"],
        "reports/layer53_sustainability_intelligence_v1.json")


def s64(d, out, reg):
    fig = D.slide("Kaynak Verimliliği Skoru",
                  "Tek sayı değil; bileşenleri açıkça listelenir",
                  D.ESTIMATED, kicker="Sürdürülebilirlik")
    D.bullets(fig, D.ML, 0.68, [
        "Su: gerçek tüketim / temel senaryo",
        "Enerji: pompa + hesaplama enerjisi",
        "Müdahale: gereksiz sulama sayısı",
        "Her bileşen ayrı gösterilir; tek skora indirgenmez",
    ], size=D.T_H2 - 4, dy=0.085)
    D.foot(fig, "Formül tanımlıdır ancak girdi ölçümleri yoktur; bu slaytta "
                "skor hesaplanmaz.", D.ALERT)
    D.save(fig, out, "64_kaynak_verimliligi.png", reg, tier=D.ESTIMATED,
           source="reports/layer53_sustainability_intelligence_v1.json",
           claim="Verimlilik bileşenleri (formül)")


def s65(d, out, reg):
    _pending_slide(
        out, reg, "65_enerji_kullanimi.png",
        "Enerji Kullanımı ve Tahmini Tasarruf",
        "Hesaplama ve pompa enerjisi", "Enerji",
        ["Pi 5 + AI HAT+ güç çekişi ölçülür",
         "Pompa enerjisi çalışma süresinden hesaplanır",
         "Uyarlanabilir örneklemenin katkısı ayrıştırılır"],
        ["Güç ölçümü yapılmadı",
         "Donanım çalıştırılmadı",
         "Enerji tasarrufu tahmini bile ölçüm gerektirir"],
        "reports/layer53_sustainability_intelligence_v1.json")


def s66(d, out, reg):
    fig = D.slide("Karbon Tahmini", "Yöntem belgelenmeden sayı verilmez",
                  D.PENDING, kicker="Sürdürülebilirlik")
    D.panel(fig, D.ML, 0.33, D.MR - D.ML, 0.40, ec=D.ALERT, lw=1.8)
    fig.text(D.ML + 0.024, 0.665, "BU SLAYTTA SAYI YOKTUR",
             fontsize=D.T_H2, fontweight="bold", color=D.ALERT, zorder=2)
    D.bullets(fig, D.ML + 0.024, 0.600, [
        "Karbon tahmini için enerji ölçümü gerekir — yapılmadı",
        "Şebeke emisyon katsayısı kaynak gösterilerek belgelenmelidir",
        "Su tasarrufunun karbon karşılığı ayrı bir varsayım zinciridir",
        "Bu zincirdeki her varsayım açıkça yazılmadan sayı sunulmaz",
    ], size=D.T_BODY, dy=0.062, color=D.INK, marker="•")
    D.pending_note(fig, "Yöntem belgelendiğinde ve enerji ölçüldüğünde "
                        "bu slayt doldurulur.")
    D.save(fig, out, "66_karbon_tahmini.png", reg, tier=D.PENDING,
           source="—", claim="Karbon tahmini yapılmadı")


def s67(d, out, reg):
    fig = D.slide("Kanıt Seviyesi Rozet Sistemi",
                  "Her slaytta bilginin ne kadar kanıtlandığı yazar",
                  D.SOFTWARE, kicker="Sunum disiplini")
    for i, tier in enumerate((D.MEASURED, D.SOFTWARE, D.ESTIMATED, D.PENDING)):
        label, col, bgc = D.TIER[tier]
        y = 0.68 - i * 0.135
        D.panel(fig, D.ML, y - 0.042, D.MR - D.ML, 0.105, ec=col, lw=1.6,
                fc=bgc)
        fig.text(D.ML + 0.024, y + 0.012, label, fontsize=D.T_H2 - 3,
                 fontweight="bold", color=col, va="center", zorder=2)
        desc = {
            D.MEASURED: "Gerçek çalıştırma sonucu — rapor dosyasında kayıtlı",
            D.SOFTWARE: "Kod ve test var; gerçek donanım/saha verisi yok",
            D.ESTIMATED: "Yöntemi belgelenmiş hesaplama — ölçüm değil",
            D.PENDING: "Henüz sayı yok — yalnızca ölçüm protokolü",
        }[tier]
        fig.text(D.ML + 0.34, y + 0.012, desc, fontsize=D.T_BODY,
                 color=D.INK, va="center", zorder=2)
    D.foot(fig, "Bu ayrım sunumun en önemli tasarım kararıdır: jüri "
                "hiçbir grafiğin kaynağını tahmin etmek zorunda kalmaz.")
    D.save(fig, out, "67_kanit_rozet_sistemi.png", reg, tier=D.SOFTWARE,
           source="scripts/prez_design.py", claim="Rozet sistemi tanımı")


# --- 68-78  Muhendislik kaniti --------------------------------------------

def s68(d, out, reg):
    fig = D.slide("Mühendislik Kanıt Panosu",
                  "API, şemalar, testler ve teslim paketi", D.SOFTWARE,
                  kicker="Mühendislik")
    D.kpi_row(fig, [
        ("OpenAPI", "3.1.0", f"{_endpoints()} uç nokta", D.ACCENT, 30),
        ("Otomatik test", str(_count_tests()), "tümü geçiyor", D.BRAND),
        ("Donanım şeması", "3 / 3", "sensör · aktüatör · ACK", D.BRAND, 30),
        ("Teslim paketi", "TAMAM", "SHA manifestli", D.BRAND, 26),
    ], y=0.470, h=0.265)
    D.bullets(fig, D.ML, 0.42, [
        "Arka uç, ön uç ve donanım sözleşmeleri ayrı ayrı belgelendi",
        "Teslim paketi dosya bazında SHA-256 manifestiyle doğrulanır",
    ])
    D.foot(fig, "Yazılım teslim paketi tamamdır; operasyonel sürüm donanım "
                "işini bekliyor.", D.WARN)
    D.save(fig, out, "68_muhendislik_kanit_panosu.png", reg,
           tier=D.SOFTWARE, source="release/, tests/, handoff/",
           claim="Mühendislik hazırlık göstergeleri")


def s69(d, out, reg):
    spec = D.load_json("release/openapi_v1.json")
    paths = sorted(spec.get("paths", {}))
    fig = D.slide("Arka Uç Entegrasyon Hazırlığı",
                  f"OpenAPI {spec.get('openapi', '3.1.0')} — "
                  f"{len(paths)} uç nokta", D.SOFTWARE, kicker="Arka uç")
    half = (len(paths) + 1) // 2
    for col_i, chunk in enumerate((paths[:half], paths[half:])):
        for i, p in enumerate(chunk):
            fig.text(D.ML + col_i * 0.46, 0.70 - i * 0.070, p,
                     fontsize=D.T_BODY - 1, color=D.INK, family="monospace")
    D.foot(fig, "Sözleşme dosyası teslim paketindedir: "
                "release/openapi_v1.json")
    D.save(fig, out, "69_arka_uc_hazirligi.png", reg, tier=D.SOFTWARE,
           source="release/openapi_v1.json", claim="Uç nokta listesi")


def s70(d, out, reg):
    fig = D.slide("Ön Uç Sözleşme Hazırlığı",
                  "Alan sözlüğü ve örnek yükler teslim edildi",
                  D.SOFTWARE, kicker="Ön uç")
    D.bullets(fig, D.ML, 0.68, [
        "Alan sözlüğü: her alanın adı, tipi ve anlamı",
        "Örnek yükler: başarılı, çekimser ve hata durumları",
        "Gerekçe kodları arayüzde aynı adla görünür",
        "Sürümlenmiş şema — ekip bağımsız çalışabilir",
    ], size=D.T_H2 - 4, dy=0.085)
    D.foot(fig, "Dosya: release/frontend_field_dictionary_v1.json")
    D.save(fig, out, "70_on_uc_hazirligi.png", reg, tier=D.SOFTWARE,
           source="release/frontend_field_dictionary_v1.json",
           claim="Ön uç sözleşmesi")


def s71(d, out, reg):
    fig = D.slide("Donanım Sözleşme Hazırlığı",
                  "Sensör, aktüatör ve ACK şemaları", D.SOFTWARE,
                  kicker="Donanım")
    rows = [("Sensör şeması", "okuma alanları + geçerlilik damgası"),
            ("Aktüatör isteği", "komut kimliği + süre + güvenlik bayrakları"),
            ("ACK şeması", "EXECUTED / REJECTED / FAILED / TIMEOUT"),
            ("Hata sözleşmesi", "hata kodu + güvenli mod")]
    D.table(fig, D.ML, 0.68, D.MR - D.ML,
            (["Şema", "İçerik"], [0.0, 0.30]), rows, rh=0.095)
    D.foot(fig, "Donanım ekibi bu şemalara karşı bağımsız geliştirme "
                "yapabilir; fiziksel doğrulama ayrı aşamadır.", D.WARN)
    D.save(fig, out, "71_donanim_sozlesmesi.png", reg, tier=D.SOFTWARE,
           source="release/hardware_handoff_v1.json",
           claim="Donanım şemaları")


def s72(d, out, reg):
    n = _count_tests()
    fig = D.slide("Otomatik Test ve Regresyon Kanıtı",
                  "Düzeltilen her kusur bir testle korunur", D.MEASURED,
                  kicker="Test disiplini")
    D.kpi_row(fig, [
        ("Toplam test", str(n), "tümü geçiyor", D.BRAND),
        ("Test dosyası", str(len(list(Path("tests").glob("test_*.py")))),
         "katman bazlı", D.ACCENT),
        ("Sözleşme testi", "var", "şema + API", D.ACCENT, 28),
        ("Regresyon", "var", "kusur → test", D.BRAND, 28),
    ], y=0.470, h=0.265)
    D.bullets(fig, D.ML, 0.42, [
        "Testler sözleşmeleri, güvenlik kapısını ve izlenebilirliği korur",
        "Test kümesi, modelin değil sistemin davranışını sınar",
    ])
    D.foot(fig, "Testlerin geçmesi modelin serada çalışacağını kanıtlamaz; "
                "yazılım davranışını kanıtlar.")
    D.save(fig, out, "72_test_kaniti.png", reg, tier=D.MEASURED,
           source="tests/ (pytest)", claim="Test sayısı ve kapsamı")


def s73(d, out, reg):
    st = d.layers
    counts = d.status_counts
    layers = st.get("layers", [])
    fig = D.slide("56 Katman Hazırlık Matrisi",
                  f"Toplam {st.get('total_layers', 56)} katman — durum "
                  "dağılımı", D.SOFTWARE, kicker="Kapsam")
    cmap = {"DONE": D.BRAND, "PARTIAL": D.WARN, "SOFTWARE_TODO": D.ACCENT,
            "HARDWARE_BLOCKED": D.ALERT}
    tr = {"DONE": "Tamamlandı", "PARTIAL": "Kısmi",
          "SOFTWARE_TODO": "Yazılım işi", "HARDWARE_BLOCKED": "Donanım bekliyor"}
    cols, size = 14, 0.052
    tile_h = size * (D.W / D.H)
    gx, gy = 0.0625, tile_h + 0.026
    x0, y0 = 0.075, 0.70
    for i, lay in enumerate(layers[:56]):
        r, c = divmod(i, cols)
        x, y = x0 + c * gx, y0 - r * gy
        col = cmap.get(lay.get("status"), D.NEUTRAL)
        D.panel(fig, x, y, size, tile_h, ec="white", lw=1.6, fc=col, z=1)
        fig.text(x + size / 2, y + tile_h / 2, str(lay.get("layer", i + 1)),
                 fontsize=12.5, fontweight="bold", color="white",
                 ha="center", va="center", zorder=2)
    for i, (k, n) in enumerate(counts.items()):
        x = 0.075 + i * 0.225
        fig.patches.append(__import__("matplotlib").patches.Rectangle(
            (x, 0.215), 0.020, 0.028, transform=fig.transFigure,
            fc=cmap.get(k, D.NEUTRAL), ec="none"))
        fig.text(x + 0.030, 0.229, f"{tr.get(k, k)}: {n}", fontsize=D.T_BODY,
                 color=D.INK, va="center")
    D.foot(fig, "Önceki “21/21 tamamlandı” ifadesi yalnızca iki ürünlük "
                "donanım öncesi hastalık kapsamına aitti.")
    D.save(fig, out, "73_56_katman_matrisi.png", reg, tier=D.SOFTWARE,
           source="reports/greenpulse_56_layer_master_status_v1.json",
           claim="Katman durum dağılımı")


def s74(d, out, reg):
    fig = D.slide("Ölçülmüş / Yazılım / Bekleyen Kanıt Panosu",
                  "Hangi iddianın arkasında ne var", D.SOFTWARE,
                  kicker="Kanıt sınırı")
    groups = [
        ("ÖLÇÜLDÜ", D.BRAND, ["Domates + biber dondurulmuş test",
                              "Sızıntı denetimi ve yakın kopya taraması",
                              "ONNX dışa aktarma eşitliği",
                              "Grad-CAM görselleri", "Otomatik testler"]),
        ("YAZILIM DOĞRULANDI", D.ACCENT, ["Füzyon ve risk motoru",
                                          "Zamansal doğrulama",
                                          "Güvenlik kapısı ve ACK makinesi",
                                          "İzlenebilirlik zinciri",
                                          "API ve şema sözleşmeleri"]),
        ("GERÇEK TEST BEKLİYOR", D.ALERT, ["Hailo HEF ve donanım eşitliği",
                                           "Pi 5 gecikme / RAM / CPU",
                                           "Gerçek sera doğrulaması",
                                           "Su ve enerji tasarrufu",
                                           "Fiziksel kapalı döngü"]),
    ]
    for i, (title, col, items) in enumerate(groups):
        x = D.ML + i * 0.303
        D.panel(fig, x, 0.20, 0.278, 0.55, ec=col, lw=2.0)
        fig.text(x + 0.020, 0.700, title, fontsize=D.T_BODY,
                 fontweight="bold", color=col, zorder=2)
        for j, it in enumerate(items):
            fig.text(x + 0.020, 0.630 - j * 0.078, "•  " + it,
                     fontsize=D.T_SMALL, color=D.INK, zorder=2,
                     va="top")
    D.foot(fig, "Üç sütun arasındaki sınır, sunumun bilimsel omurgasıdır.")
    D.save(fig, out, "74_kanit_panosu.png", reg, tier=D.SOFTWARE,
           source="reports/greenpulse_jury_evidence_map_v1.json",
           claim="Kanıt seviyesi dağılımı")


def s75(d, out, reg):
    fig = D.slide("Bilimsel İddia Sınırı",
                  "Kanıtlamadığımız hiçbir şeyi iddia etmiyoruz",
                  D.SOFTWARE, kicker="Dürüstlük")
    never = ["Tam otonom sera tamamlandı",
             "Gerçek çok modlu füzyon doğrulandı",
             "Kapalı döngü sulama doğrulandı",
             "%99 gerçek sera doğruluğu",
             "Grad-CAM lezyonu bölütler",
             "Transfer öğrenme üstünlüğü kanıtlandı",
             "Hailo dağıtımı tamamlandı"]
    fig.text(D.ML, 0.735, "ASLA SÖYLENMEYECEKLER", fontsize=D.T_H2 - 2,
             fontweight="bold", color=D.ALERT)
    for i, t in enumerate(never):
        y = 0.665 - i * 0.078
        D.panel(fig, D.ML, y - 0.028, D.MR - D.ML, 0.060, ec=D.LINE, lw=1.0)
        fig.text(D.ML + 0.018, y, "✕  " + t, fontsize=D.T_BODY,
                 color=D.INK, va="center", zorder=2)
    D.foot(fig, "Bu liste savunma paketinde slayt slayt tekrarlanır.")
    D.save(fig, out, "75_iddia_siniri.png", reg, tier=D.SOFTWARE,
           source="reports/jury_final_shortlist_v1/ai_ml_defense_pack.json",
           claim="Asla söylenmeyecekler listesi")


def s76(d, out, reg):
    fig = D.slide("Gerçek Doğrulama Yol Haritası",
                  "Donanım geldikten sonra ölçülecekler — sırayla",
                  D.SOFTWARE, kicker="Plan")
    steps = [("1", "Gerçek sera görüntüsü", "kendi kameramız"),
             ("2", "Alan kayması ölçümü", "laboratuvar → sera"),
             ("3", "Kontrollü kuruma denemesi", "5–7 takvim günü"),
             ("4", "Hailo HEF + eşitlik", "gerçek kalibrasyon kümesi"),
             ("5", "Pi 5 başarım ölçümü", "gecikme · RAM · CPU · sıcaklık"),
             ("6", "Fiziksel kapalı döngü", "pompa kalibrasyonu + ACK")]
    for i, (num, title, note) in enumerate(steps):
        x = D.ML + (i % 3) * 0.303
        y = 0.52 - (i // 3) * 0.235
        D.panel(fig, x, y, 0.278, 0.195, ec=D.LINE, lw=1.4)
        fig.text(x + 0.020, y + 0.145, num, fontsize=D.T_H2,
                 fontweight="bold", color=D.WARN, zorder=2)
        fig.text(x + 0.020, y + 0.085, title, fontsize=D.T_BODY,
                 fontweight="bold", color=D.INK, zorder=2)
        fig.text(x + 0.020, y + 0.035, note, fontsize=D.T_SMALL,
                 color=D.MUTED, zorder=2)
    D.foot(fig, "Ölçüm protokolü ve şablonlar hazırdır: "
                "jury_evidence/real_measurements/")
    D.save(fig, out, "76_dogrulama_yol_haritasi.png", reg, tier=D.SOFTWARE,
           source="jury_evidence/real_measurements/",
           claim="Doğrulama sırası")


def s77(d, out, reg):
    fig = D.slide("Ürünleştirme ve Ekip Teslimi",
                  "Yazılım paketi bağımsız ekiplere devredilebilir durumda",
                  D.SOFTWARE, kicker="Teslim")
    D.flow(fig, [("AI/ML\npaketi", D.BRAND), ("Arka uç\nsözleşmesi", D.ACCENT),
                 ("Ön uç\nsözlüğü", D.ACCENT), ("Donanım\nşemaları", D.WARN),
                 ("SHA\nmanifesti", D.NEUTRAL)], y=0.52, h=0.155)
    D.bullets(fig, D.ML, 0.40, [
        "Her teslim paketi dosya bazında SHA-256 ile doğrulanır",
        "Kurulum ve başlatma betikleri pakete dahildir",
        "Paket kendini “operasyon öncesi” ilan eder — abartı yok",
    ])
    D.foot(fig, "Operasyonel sürüm, listelenen dış engeller tamamlanana "
                "kadar BLOKE'dir.", D.WARN)
    D.save(fig, out, "77_urunlestirme_teslim.png", reg, tier=D.SOFTWARE,
           source="handoff/, release/", claim="Teslim akışı")


def s78(d, out, reg):
    t, p = d.t_metrics, d.p_metrics
    fig = D.slide("Neden GreenPulse",
                  "Ölçülmüş performans + güvenli zekâ + dağıtım disiplini",
                  D.MEASURED, kicker="Özet")
    blocks = [("01", "Ölçülmüş yapay zekâ", D.BRAND,
               [("Domates", D.tr_pct(t.get("accuracy", 0)) + " doğruluk"),
                ("Biber", D.tr_pct(p.get("accuracy", 0)) + " doğruluk")]),
              ("02", "Güvenli zekâ", D.ACCENT,
               [("Hata yönetimi", "ÇEKİMSER / İZLE / İNCELE"),
                ("Denetlenebilirlik", "komut düzeyinde izlenebilirlik")]),
              ("03", "Dağıtım disiplini", D.WARN,
               [("Arka uç", f"OpenAPI 3.1 — {_endpoints()} uç nokta"),
                ("Doğrulama", "gerçek test protokolü hazır")])]
    for i, (num, title, col, rows) in enumerate(blocks):
        x = D.ML + i * 0.303
        D.panel(fig, x, 0.28, 0.278, 0.47, ec=D.LINE, lw=1.5)
        fig.text(x + 0.020, 0.700, num, fontsize=D.T_H2 - 2,
                 fontweight="bold", color=col, zorder=2)
        fig.text(x + 0.020, 0.635, title, fontsize=D.T_H2 - 3,
                 fontweight="bold", color=D.INK, zorder=2)
        for j, (k, v) in enumerate(rows):
            yy = 0.530 - j * 0.105
            fig.text(x + 0.020, yy, k, fontsize=D.T_SMALL, color=D.MUTED,
                     zorder=2)
            fig.text(x + 0.020, yy - 0.042, v, fontsize=D.T_BODY,
                     fontweight="bold", color=col, zorder=2)
    fig.text(D.ML, 0.185, "Ana mesaj", fontsize=D.T_SMALL,
             fontweight="bold", color=D.MUTED)
    fig.text(D.ML, 0.125, "GreenPulse tahminde durmaz — yapay zekâ kanıtını "
             "açıklanabilir, güvenli ve denetlenebilir kararlara bağlar.",
             fontsize=D.T_H2, fontweight="bold", color=D.INK)
    D.save(fig, out, "78_neden_greenpulse.png", reg, tier=D.MEASURED,
           source="reports/tomato_final_test_v1.json, "
                  "reports/pepper_final_test_v1/final_test_report.json",
           claim="Kapanış özeti")


def build(d, out: Path, reg: list) -> None:
    fns = [s29, s30, s31, s32, s33, s34, s35, s36, s37, s38, s39, s40, s41,
           s42, s43, s44, s45, s46, s47, s48, s49, s50, s51, s52, s53, s54,
           s55, s56, s57, s58, s59, s60, s61, s62, s63, s64, s65, s66, s67,
           s68, s69, s70, s71, s72, s73, s74, s75, s76, s77, s78]
    for fn in fns:
        try:
            fn(d, out, reg)
            print(f"  {fn.__name__}  {reg[-1]['file']}")
        except Exception as exc:                        # noqa: BLE001
            print(f"  {fn.__name__}  HATA: {exc}")
