"""
GreenPulse - Juri belgelerindeki karakter bozulmasini onarir.

SORUN
-----
Belgeler cp1252/ASCII bir akisa yazildigi icin ozel karakterler `?`
haline gelmisti. Iki farkli bozulma tipi vardi:

  TIP A - uzun tire (em dash):  "Slayt 1 ? Problem"
          Kayip TEK karakterdir, baglamdan kesin bilinir -> otomatik onarilir.

  TIP B - Azerice harfler:      "hiss?sini t?k ... qurmu?uq"
          Her `?` yedi ayri harften biri olabilir; kayip GERI GETIRILEMEZ.
          Bu yuzden tahmin edilmedi, TEKNOFEST sunum dili olan TURKCE ile
          yeniden yazildi.

Bu betik TIP A'yi tum belgelerde onarir ve `greenpulse_jury_evidence_map_v1`
icindeki 12 konusmaci cumlesini (TIP B) Turkce metinle degistirir.
Savunma paketi ayri betikte: `scripts/rebuild_jury_defense_pack_tr.py`.

Calistirma:
    python -m scripts.repair_jury_text_encoding
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

#: TIP A - yalnizca ayirici konumundaki `?` uzun tireye donusur.
#: Kelime ICINDEKI `?` (TIP B) bu kaliba UYMAZ; yanlislikla degistirilmez.
EM_DASH = re.compile(r"(?<=[\w\)\]%])\s\?\s(?=[\w\(\[])")

#: Konusmaci cumleleri - Azericeden TURKCE'ye yeniden yazildi.
SPEAKER_TR: dict[int, str] = {
    1: "GreenPulse'u yalnızca bir YOLO modeli olarak kurmadık. Görüntü "
       "çıkarımından model kayıt defterine, güvenlik kapısına, insan "
       "incelemeli aktif öğrenmeye, denetime ve donanım sözleşmesine kadar "
       "modüler bir yapay zekâ mimarisi kurduk.",
    2: "En önemli metodolojik kararımız budur: nihai test, model seçimine "
       "katılmadı. Kontrol noktası önce donduruldu, test yalnızca bir kez "
       "açıldı ve sonraki analizler model çıkarımıyla değil, kaydedilmiş "
       "tahminler üzerinden yapıldı.",
    3: "Domates modelini önceki domates kontrol noktasından başlatmadık. "
       "Genel ön eğitimli bir temelden temiz bir deney kurduk ve model "
       "seçimini doğrulama sonuçlarına dayandırdık.",
    4: "Yalnızca %99 doğruluk demiyoruz. Karışıklık matrisi ve hata çifti "
       "analiziyle modelin tam olarak nerede yanıldığını da gösteriyoruz. "
       "2.737 dondurulmuş test örneğinde 23 hata var.",
    5: "Model kararını yalnızca sınıf etiketi olarak saklamıyoruz. "
       "Doğrulama örneklerinde Grad-CAM ile ağın dikkat ettiği bölgeleri "
       "görsel olarak denetleyebiliyoruz.",
    6: "Burada sonucu şişirmedik. Domatesten başlayan transfer modeli ile "
       "genel temel model doğrulamada aynı sonucu verdi. Bu nedenle "
       "transfer üstünlüğünü kanıtlanmış gibi sunmuyoruz.",
    7: "İkinci ürünü yalnızca doğrulama sonucuyla kapatmadık. 371 örneklik "
       "ayrı bir dondurulmuş testte doğruluk %98,11 ve Makro F1 0,9802 "
       "oldu.",
    8: "Uç birim dağıtımı için yalnızca ONNX dışa aktarımı yapmadık. "
       "PyTorch ve ONNX çıktılarını örnek örnek karşılaştırarak tahmin "
       "eşitliğini ayrıca doğruladık.",
    9: "Sistem bilinmeyen bir ürün gördüğünde en yakın modele zorunlu "
       "yönlendirme yapmaz. Kayıt defterinde bulunmayan ürün için politika "
       "ABSTAIN/BLOCK'tur.",
    10: "Aktif öğrenmeyi özerk yeniden eğitim olarak kurmadık. Riskli ve "
        "belirsiz örnekler insan inceleme kuyruğuna düşer; otomatik "
        "etiketleme ve otomatik yeniden eğitim yasaktır.",
    11: "Bugün kapatılmış kapsam iki üründür: domates ve dolmalık biber. "
        "Her ikisi için dondurulmuş test, açıklanabilirlik, ONNX eşitliği "
        "ve kayıt defteri kanıtı mevcuttur. Mevcut dağıtım durumumuz "
        "yalnızca araştırmadır; operasyonel sürüm onaylanmamıştır ve "
        "fiziksel eyleme devre dışıdır.",
    12: "Projenin gücü yalnızca yüksek metriklerde değil, kanıtlamadığımız "
        "şeyi iddia etmememizdedir. Bu sütunda yazılım tarafında "
        "kapattığımız bölümleri, diğer sütunda ise gerçek donanım "
        "geldikten sonra ölçülecek bölümleri ayırdık.",
}

LANGUAGE_NOTE = (
    "Konuşmacı cümleleri Türkçedir. Önceki sürümde metin Azerice idi ve "
    "dosya cp1252/ASCII bir akışa yazıldığı için özel harfler '?' "
    "karakterine dönüşmüştü. Kayıplı bozulma geri getirilemediği için metin "
    "tahmin edilerek onarılmadı; TEKNOFEST sunum dili olan Türkçe ile "
    "yeniden yazıldı."
)


def fix_em_dash(path: Path) -> int:
    """TIP A: ayirici konumundaki `?` -> `—`. Degisen sayisini dondurur."""
    txt = path.read_text(encoding="utf-8")
    new, n = EM_DASH.subn(" — ", txt)
    if n:
        path.write_text(new, encoding="utf-8")
    return n


def fix_evidence_map(json_path: Path) -> int:
    """TIP B: 12 konusmaci cumlesini Turkce metinle degistirir."""
    if not json_path.exists():
        return 0
    d = json.loads(json_path.read_text(encoding="utf-8"))
    n = 0
    for stage in d.get("storyline", []):
        tr = SPEAKER_TR.get(stage.get("order"))
        if tr:
            stage["speaker_line"] = tr
            n += 1
    if n:
        d["presentation_language"] = "tr"
        d["language_note"] = LANGUAGE_NOTE
        d["regenerated_at_utc"] = datetime.now(timezone.utc).isoformat()
        json_path.write_text(json.dumps(d, indent=2, ensure_ascii=False),
                             encoding="utf-8")
        md = json_path.with_suffix(".md")
        if md.exists():
            md.write_text(render_evidence_map(d), encoding="utf-8")
    return n


def render_evidence_map(d: dict) -> str:
    """`.md` dosyasini JSON'dan URETIR - ikisi artik ayri dusemez."""
    out: list[str] = []
    add = out.append
    add("# GreenPulse — Jüri Kanıt Haritası")
    add("")
    add(f"**Amaç:** {d.get('purpose', '-')}")
    add("")
    add(f"**Doğrulanmış görsel sayısı:** {d.get('verified_visual_count', '-')}")
    add("")
    add("> **Sunum dili: Türkçe.** " + d.get("language_note", ""))
    add("")
    for s in d.get("storyline", []):
        add(f"## {s.get('order')}. {s.get('title', '')}")
        add("")
        add(f"**Bölüm:** {s.get('section', '-')}")
        add("")
        add(f"**Ana görsel:** `{s.get('primary_visual', '-')}`")
        sup = s.get("supporting_visuals") or []
        if sup:
            add("")
            add("**Destekleyici görseller:** " +
                ", ".join(f"`{x}`" for x in sup))
        add("")
        add(f"**Jüri sorusu:** {s.get('jury_question', '')}")
        add("")
        add(f"**Kanıt:** {s.get('proof', '')}")
        add("")
        add(f"**Konuşmacı cümlesi:** {s.get('speaker_line', '')}")
        dnc = s.get("do_not_claim") or []
        if dnc:
            add("")
            add("**İddia etme:** " + "; ".join(dnc))
        add("")
    if d.get("rapid_fire"):
        add("## Hızlı soru-cevap")
        add("")
        for i, r in enumerate(d["rapid_fire"], 1):
            add(f"**{i}. {r.get('question', '')}**")
            add("")
            add(r.get("answer", ""))
            add("")
    sb = d.get("scientific_boundary") or {}
    if sb:
        add("## Bilimsel sınır")
        add("")
        add("| Madde | Durum |")
        add("|---|---|")
        for k, v in sb.items():
            val = v if isinstance(v, str) else ("EVET" if v else "HAYIR")
            add(f"| `{k}` | {val} |")
        add("")
    return "\n".join(out) + "\n"


def main() -> int:
    root = Path(".")
    print("=" * 66)
    print("JURI BELGELERI - KARAKTER ONARIMI")
    print("=" * 66)

    n_map = 0
    for jp in sorted(root.rglob("greenpulse_jury_evidence_map_v1.json")):
        if ".venv" in str(jp):
            continue
        k = fix_evidence_map(jp)
        n_map += k
        if k:
            print(f"  TIP B  {k:>3} konuşmacı cümlesi  {jp.as_posix()}")

    total = 0
    for md in sorted(root.rglob("*.md")):
        if ".venv" in str(md):
            continue
        n = fix_em_dash(md)
        if n:
            total += n
            print(f"  TIP A  {n:>3} uzun tire          {md.as_posix()}")

    print("-" * 66)
    print(f"  Uzun tire onarildi       : {total}")
    print(f"  Turkce cumle yazildi     : {n_map}")
    print("=" * 66)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
