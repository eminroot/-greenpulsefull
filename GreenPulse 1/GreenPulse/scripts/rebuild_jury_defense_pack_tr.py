"""
GreenPulse - Juri savunma paketini TURKCE yeniden uretir.

NEDEN BU BETIK VAR
------------------
`ai_ml_defense_pack.json` / `.md` icindeki sunum metinleri Azerice yazilmis,
ancak dosyalar cp1252/ASCII bir akisa yazildigi icin TUM ozel harfler
tek tek `?` karakterine donusmustu:

    "GreenPulse-un AI hiss?sini t?k model kimi deyil..."

Toplam 1.384 karakter bozulmustu; bunlarin 130'u tam olarak jurinin onunde
okunacak savunma metnindeydi. `?` kayipli bir degisim oldugu icin orijinal
metin dosyadan geri getirilemez.

TEKNOFEST sunumu TURKCE yapilacagi icin metin tahmin edilerek onarilmadi;
dogrudan TURKCE yeniden yazildi. Boylece hem bozulma ortadan kalkti hem de
sunum dili ile belge dili ayni oldu.

  `_az` alanlari `_tr` olarak yeniden adlandirildi: icerigi degistirip
  anahtar adini korumak yaniltici olurdu.

`.md` dosyasi artik JSON'dan URETILIR. Onceden ikisi ayri tutuluyordu;
bu yuzden biri guncellenip digeri eskiyebiliyordu.

Calistirma:
    python -m scripts.rebuild_jury_defense_pack_tr
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = Path("reports/jury_final_shortlist_v1")
JSON_PATH = BASE / "ai_ml_defense_pack.json"
MD_PATH = BASE / "ai_ml_defense_pack.md"

#: slayt -> (açılış, teknik cümle, cevap)
SLIDES: dict[int, tuple[str, str, str]] = {
    1: (
        "GreenPulse'un yapay zekâ tarafını tek bir model olarak değil, "
        "modüler bir karar sistemi olarak kurduk.",
        "Görüntü çıkarımı, sensör doğrulama, zaman senkronizasyonu, model "
        "kayıt defteri, güvenlik kapısı, aktif öğrenme kuyruğu ve denetim "
        "katmanları birbirinden ayrılmıştır.",
        "Şu anda hastalık sınıflandırma dalı gerçek kanıta bağlanmıştır. "
        "Füzyon için yazılım sözleşmesi mevcuttur; ancak gerçek senkronize "
        "sensör-kamera veri kümesi olmadığı için kalibre edilmiş çok modlu "
        "füzyon iddiasında bulunmuyoruz. Bu bölümü operasyonel değil, "
        "arayüze hazır durumda tutuyoruz.",
    ),
    2: (
        "En güçlü metodolojik yanımız, nihai testin model seçiminden "
        "tamamen ayrılmış olmasıdır.",
        "Aday model, kontrol noktası doğrulama sonuçlarına göre seçildi; "
        "test açılmadan önce SHA ile donduruldu, dondurulmuş test bir kez "
        "çalıştırıldı ve ardından CONSUMED durumuna geçirildi.",
        "Hayır. Testten sonraki hata analizi yalnızca önceden kaydedilmiş "
        "tahmin CSV dosyaları üzerinden yapıldı. Test görüntüleri üzerinde "
        "ikinci bir çıkarım, yeniden eğitim, yeniden model seçimi veya eşik "
        "ayarı yapmadık.",
    ),
    3: (
        "Ana domates modelimizi 2.737 görüntüden oluşan dondurulmuş nihai "
        "testte değerlendirdik.",
        "Nihai doğruluk %99,1597 ve Makro F1 0,989933'tür. Toplam 23 hata "
        "vardır; bu nedenle yalnızca doğruluğu değil, sınıf düzeyindeki "
        "karışıklık yapısını da gösteriyoruz.",
        "Bu sonucu gerçek sera doğruluğu olarak sunmuyoruz. Bu, sızıntı "
        "denetiminden geçirilmiş, ayrılmış bir veri kümesi ölçütüdür. Alan "
        "kayması ve gerçek sera doğrulaması ayrı bir bekleyen aşama olarak "
        "kayıt altına alınmıştır.",
    ),
    4: (
        "Tahminin yanı sıra modelin hangi bölgelere dikkat ettiğini "
        "Grad-CAM ile görsel olarak denetliyoruz.",
        "Grad-CAM ön işleme adımı, standart Ultralytics sınıflandırma "
        "çıkarımı ile eşitlik testinden geçirilmiştir.",
        "Hayır. Grad-CAM yalnızca niteliksel bir dikkat tanılamasıdır. "
        "Piksel düzeyinde lezyon bölütleme, konumlandırma doğruluğu veya "
        "nedensel açıklama iddiasında bulunmuyoruz.",
    ),
    5: (
        "Transfer öğrenmeyi üstün varsayarak kabul etmedik; genel bir temel "
        "modelle karşılaştırdık.",
        "Aynı hedef veri kümesi üzerinde domatesle başlatılan ve genel ön "
        "eğitimli adaylar, doğrulamada aynı nihai doğruluğa ulaştı.",
        "Doğrulama kanıtı transferin üstünlüğünü göstermedi. Bu nedenle "
        "transfer avantajı iddiasında bulunmuyoruz. Transfer deneyi uyarlama "
        "yapılabilirliğini gösterir, üstünlüğü değil.",
    ),
    6: (
        "Uç birim dağıtımı için modelin yalnızca ONNX dosyasını üretmekle "
        "yetinmedik.",
        "PyTorch ve ONNX çıktıları doğrulama örnekleri üzerinde örnek örnek "
        "karşılaştırıldı; her iki üründe de Top-1 tahmin eşitliği elde "
        "ettik.",
        "Hayır. ONNX eşitliği yalnızca dışa aktarma düzeyindeki tutarlılığı "
        "kanıtlar. HEF dönüşümü, Raspberry Pi 5 + Hailo çıkarım gecikmesi, "
        "RAM kullanımı ve gerçek donanım çalışma zamanı ayrıca beklemededir.",
    ),
    7: (
        "Sonuç olarak mevcut bilgisayar tarafı kapsamını iki ürün için "
        "kapattık.",
        "Domates nihai test doğruluğu %99,16, biber ise %98,11'dir. Her iki "
        "model için dondurulmuş değerlendirme, ONNX eşitliği, "
        "açıklanabilirlik ve kayıt defteri kanıtı mevcuttur.",
        "Gerçek sera doğrulaması, kalibre edilmiş su stresi modeli, gerçek "
        "çok modlu füzyon, Pi/Hailo donanım doğrulaması, pompa kalibrasyonu "
        "ve fiziksel kapalı döngü, operasyonel sürümden önce "
        "tamamlanmalıdır.",
    ),
}

#: hızlı soru -> TÜRKÇE cevap
RAPID: dict[str, str] = {
    "Why YOLO11n instead of a standard CNN?":
        "YOLO11n sınıflandırma, Ultralytics ekosisteminde hafif bir dağıtım "
        "yolu sunduğu için seçildi. Burada nesne tespiti değil, "
        "sınıflandırma görevi kullanıyoruz. Seçimin temel pratik nedeni, "
        "ileride yapılacak uç birim dışa aktarımıyla uyumluluktur.",
    "Is crop recognition automatic?":
        "Mevcut sistemde ürün kimliği bağımsız olarak doğrulanmıyor; "
        "dışarıdan gelen bir bildirim olarak kabul ediliyor. Bu nedenle "
        "yanlış ürün yönlendirme riskini gizlemiyoruz ve bilinmeyen ürün "
        "politikasını ABSTAIN olarak bırakıyoruz.",
    "What protects you from duplicate leakage?":
        "Tam SHA çakışması kontrol edildi, eşlenmiş domates alt kümesinde "
        "yaprak grubu ayrık bölme kuruldu ve ek olarak dHash/pHash yakın "
        "kopya taraması yapıldı. Ancak eşlenmemiş bölüm için fiziksel "
        "yaprak kimliğini kanıtlanmış saymıyoruz.",
    "Why is Macro F1 important if accuracy is already high?":
        "Doğruluk, baskın sınıfların etkisini gizleyebilir. Makro F1 her "
        "sınıfa eşit ağırlık verir ve 10 sınıflı domates modelinde daha "
        "dengeli bir genelleme göstergesidir.",
    "Do you automatically retrain on difficult samples?":
        "Hayır. Düşük güvenli, dağılım dışı ve çelişen durumlar yalnızca "
        "insan inceleme kuyruğuna gider. Otomatik etiketleme ve otomatik "
        "yeniden eğitim mevcut politikada açıkça devre dışıdır.",
    "Can disease confidence directly trigger irrigation?":
        "Hayır. Hastalık sınıflandırması su stresi kanıtı değildir. Mevcut "
        "güvenlik kapısı özerk fiziksel eyleme izin vermez.",
    "Why no cucumber?":
        "Mevcut doğrulanmış kapsamı iki üründe bilimsel olarak tam "
        "kapatmayı, üçüncü ürünü yarım eklemeye tercih ettik. Salatalık "
        "kayıt defterinde yoktur ve ABSTAIN/BLOCK uygulanır.",
    "What is your strongest technical contribution?":
        "Tek başına yüksek doğruluk değil; sızıntıya duyarlı değerlendirme, "
        "dondurulmuş test disiplini, model izlenebilirliği, ONNX eşitliği, "
        "açıklanabilirlik ve güvenlik yönetimli yönlendirmeyi aynı yapay "
        "zekâ hattında birleştirmemizdir.",
}

LANGUAGE_NOTE = (
    "Sunum metinleri Türkçedir. Önceki sürümde metin Azerice idi ve dosya "
    "cp1252/ASCII bir akışa yazıldığı için tüm özel harfler '?' karakterine "
    "dönüşmüştü (1.384 karakter). Kayıplı bozulma geri getirilemediği için "
    "metin tahmin edilerek onarılmadı; TEKNOFEST sunum dili olan Türkçe ile "
    "yeniden yazıldı."
)


def to_turkish(data: dict) -> tuple[dict, int]:
    """`*_az` alanlarını Türkçe `*_tr` alanlarıyla değiştirir."""
    replaced = 0
    for slide in data.get("defense", []):
        tr = SLIDES.get(slide.get("slide"))
        if not tr:
            continue
        for old, new, value in (
            ("opening_line_az", "opening_line_tr", tr[0]),
            ("technical_line_az", "technical_line_tr", tr[1]),
            ("answer_az", "answer_tr", tr[2]),
        ):
            slide.pop(old, None)
            slide[new] = value
            replaced += 1

    for item in data.get("rapid_fire", []):
        answer = RAPID.get(item.get("question"))
        if answer:
            item.pop("answer_az", None)
            item["answer_tr"] = answer
            replaced += 1

    data["presentation_language"] = "tr"
    data["language_note"] = LANGUAGE_NOTE
    data["regenerated_at_utc"] = datetime.now(timezone.utc).isoformat()
    return data, replaced


def render_markdown(d: dict) -> str:
    """`.md` dosyasını JSON'dan ÜRETİR - ikisi artık ayrı düşemez."""
    out: list[str] = []
    add = out.append
    add("# GreenPulse — AI/ML Mimari Savunma Paketi")
    add("")
    add(f"**Hedef kitle:** {d.get('audience', '-')}")
    add("")
    add("**Doğrulanmış mevcut kapsam:** Domates + Biber, bilgisayar tarafı "
        "hastalık sınıflandırması")
    add("")
    add("**Dağıtım:** RESEARCH_ONLY")
    add("")
    add("**Fiziksel eyleme:** DEVRE DIŞI")
    add("")
    add("> **Sunum dili: Türkçe.** " + d.get("language_note", ""))
    add("")

    for s in d.get("defense", []):
        add(f"## Slayt {s['slide']} — {s.get('purpose', '')}")
        add("")
        add(f"**Görsel:** `{s.get('visual', '-')}`")
        add("")
        add(f"**Açılış:** {s.get('opening_line_tr', '')}")
        add("")
        add("**Neyi göster:** " + ", ".join(s.get("point_at", [])))
        add("")
        add(f"**Teknik cümle:** {s.get('technical_line_tr', '')}")
        add("")
        add(f"**Olası itiraz:** {s.get('architect_attack_question', '')}")
        add("")
        add(f"**Cevap:** {s.get('answer_tr', '')}")
        add("")
        add(f"**Yedek görsel:** `{s.get('backup_visual', '-')}`")
        add("")
        add("**Asla söyleme:** " + "; ".join(s.get("never_say", [])))
        add("")

    if d.get("rapid_fire"):
        add("## Hızlı soru-cevap")
        add("")
        for i, r in enumerate(d["rapid_fire"], 1):
            add(f"**{i}. {r.get('question', '')}**")
            add("")
            add(r.get("answer_tr", ""))
            add("")

    term = d.get("terminology") or {}
    if term:
        add("## Terminoloji")
        add("")
        add("| Anahtar | Şöyle söyle |")
        add("|---|---|")
        for k, v in term.items():
            add(f"| `{k}` | {v} |")
        add("")

    ex = d.get("execution") or {}
    if ex:
        add("## Bu paket üretilirken yapılmayanlar")
        add("")
        add("| İşlem | Yapıldı mı |")
        add("|---|---|")
        for k, v in ex.items():
            add(f"| `{k}` | {'EVET' if v else 'HAYIR'} |")
        add("")

    return "\n".join(out) + "\n"


def main() -> int:
    if not JSON_PATH.exists():
        print(f"  {JSON_PATH} bulunamadı")
        return 1

    data = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    data, n = to_turkish(data)

    JSON_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False),
                         encoding="utf-8")
    MD_PATH.write_text(render_markdown(data), encoding="utf-8")

    print(f"  Türkçeye çevrilen alan : {n}")
    print(f"  JSON                   : {JSON_PATH}")
    print(f"  Markdown (JSON'dan)    : {MD_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
