# GreenPulse — AI/ML Mimari Savunma Paketi

**Hedef kitle:** AI_ML_ARCHITECT_JURY

**Doğrulanmış mevcut kapsam:** Domates + Biber, bilgisayar tarafı hastalık sınıflandırması

**Dağıtım:** RESEARCH_ONLY

**Fiziksel eyleme:** DEVRE DIŞI

> **Sunum dili: Türkçe.** Sunum metinleri Türkçedir. Önceki sürümde metin Azerice idi ve dosya cp1252/ASCII bir akışa yazıldığı için tüm özel harfler '?' karakterine dönüşmüştü (1.384 karakter). Kayıplı bozulma geri getirilemediği için metin tahmin edilerek onarılmadı; TEKNOFEST sunum dili olan Türkçe ile yeniden yazıldı.

## Slayt 1 — Prove this is an AI system architecture, not a model demo.

**Görsel:** `S01_end_to_end_ai_architecture.png`

**Açılış:** GreenPulse'un yapay zekâ tarafını tek bir model olarak değil, modüler bir karar sistemi olarak kurduk.

**Neyi göster:** Vision Pipeline, Disease Classifier, Safety Gate, Human Review, Hardware BLOCKED

**Teknik cümle:** Görüntü çıkarımı, sensör doğrulama, zaman senkronizasyonu, model kayıt defteri, güvenlik kapısı, aktif öğrenme kuyruğu ve denetim katmanları birbirinden ayrılmıştır.

**Olası itiraz:** Is your fusion actually trained/calibrated, or is this architecture mostly conceptual?

**Cevap:** Şu anda hastalık sınıflandırma dalı gerçek kanıta bağlanmıştır. Füzyon için yazılım sözleşmesi mevcuttur; ancak gerçek senkronize sensör-kamera veri kümesi olmadığı için kalibre edilmiş çok modlu füzyon iddiasında bulunmuyoruz. Bu bölümü operasyonel değil, arayüze hazır durumda tutuyoruz.

**Yedek görsel:** `15_verified_vs_pending_matrix.png`

**Asla söyleme:** Fully autonomous greenhouse is complete; Real multimodal fusion is validated; Closed-loop irrigation is already validated

## Slayt 2 — Defend final metrics against leakage / test overfitting criticism.

**Görsel:** `S02_frozen_test_protocol.png`

**Açılış:** En güçlü metodolojik yanımız, nihai testin model seçiminden tamamen ayrılmış olmasıdır.

**Neyi göster:** Validate, Freeze, Final Test, Consume, Saved predictions only

**Teknik cümle:** Aday model, kontrol noktası doğrulama sonuçlarına göre seçildi; test açılmadan önce SHA ile donduruldu, dondurulmuş test bir kez çalıştırıldı ve ardından CONSUMED durumuna geçirildi.

**Olası itiraz:** Did you inspect the test errors and then retrain or tune thresholds?

**Cevap:** Hayır. Testten sonraki hata analizi yalnızca önceden kaydedilmiş tahmin CSV dosyaları üzerinden yapıldı. Test görüntüleri üzerinde ikinci bir çıkarım, yeniden eğitim, yeniden model seçimi veya eşik ayarı yapmadık.

**Yedek görsel:** `16_model_lifecycle_traceability.png`

**Asla söyleme:** The test set was used for optimization; We improved the model after seeing final-test errors

## Slayt 3 — Show primary 10-class model performance and failure structure.

**Görsel:** `S03_tomato_final_confusion_matrix.png`

**Açılış:** Ana domates modelimizi 2.737 görüntüden oluşan dondurulmuş nihai testte değerlendirdik.

**Neyi göster:** 99.1597% accuracy, Macro F1 = 0.989933, diagonal cells, off-diagonal error cells

**Teknik cümle:** Nihai doğruluk %99,1597 ve Makro F1 0,989933'tür. Toplam 23 hata vardır; bu nedenle yalnızca doğruluğu değil, sınıf düzeyindeki karışıklık yapısını da gösteriyoruz.

**Olası itiraz:** Why should I trust 99% accuracy on PlantVillage-style data?

**Cevap:** Bu sonucu gerçek sera doğruluğu olarak sunmuyoruz. Bu, sızıntı denetiminden geçirilmiş, ayrılmış bir veri kümesi ölçütüdür. Alan kayması ve gerçek sera doğrulaması ayrı bir bekleyen aşama olarak kayıt altına alınmıştır.

**Yedek görsel:** `05_tomato_error_pairs.png`

**Asla söyleme:** 99.16% real greenhouse accuracy; The model generalizes to every greenhouse

## Slayt 4 — Show qualitative explainability without overstating localization.

**Görsel:** `S04_tomato_gradcam.png`

**Açılış:** Tahminin yanı sıra modelin hangi bölgelere dikkat ettiğini Grad-CAM ile görsel olarak denetliyoruz.

**Neyi göster:** Original image, Grad-CAM heatmap, Overlay, Predicted class

**Teknik cümle:** Grad-CAM ön işleme adımı, standart Ultralytics sınıflandırma çıkarımı ile eşitlik testinden geçirilmiştir.

**Olası itiraz:** Are you claiming the red regions are segmented disease lesions?

**Cevap:** Hayır. Grad-CAM yalnızca niteliksel bir dikkat tanılamasıdır. Piksel düzeyinde lezyon bölütleme, konumlandırma doğruluğu veya nedensel açıklama iddiasında bulunmuyoruz.

**Yedek görsel:** `08_pepper_gradcam_evidence.png`

**Asla söyleme:** Grad-CAM segments the lesion; Heatmap proves causality

## Slayt 5 — Demonstrate scientifically controlled transfer-learning comparison.

**Görsel:** `S05_pepper_transfer_vs_generic.png`

**Açılış:** Transfer öğrenmeyi üstün varsayarak kabul etmedik; genel bir temel modelle karşılaştırdık.

**Neyi göster:** Tomato-initialized curve, Generic pretrained curve, identical final validation accuracy

**Teknik cümle:** Aynı hedef veri kümesi üzerinde domatesle başlatılan ve genel ön eğitimli adaylar, doğrulamada aynı nihai doğruluğa ulaştı.

**Olası itiraz:** So did transfer learning actually help?

**Cevap:** Doğrulama kanıtı transferin üstünlüğünü göstermedi. Bu nedenle transfer avantajı iddiasında bulunmuyoruz. Transfer deneyi uyarlama yapılabilirliğini gösterir, üstünlüğü değil.

**Yedek görsel:** `04_pepper_final_confusion_matrix.png`

**Asla söyleme:** Transfer learning significantly outperformed the baseline; Backbone freezing proved the advantage

## Slayt 6 — Prove export consistency before future edge deployment.

**Görsel:** `S06_onnx_parity.png`

**Açılış:** Uç birim dağıtımı için modelin yalnızca ONNX dosyasını üretmekle yetinmedik.

**Neyi göster:** Tomato Top-1 agreement, Pepper Top-1 agreement, maximum probability difference

**Teknik cümle:** PyTorch ve ONNX çıktıları doğrulama örnekleri üzerinde örnek örnek karşılaştırıldı; her iki üründe de Top-1 tahmin eşitliği elde ettik.

**Olası itiraz:** Does this mean your Hailo deployment is already complete?

**Cevap:** Hayır. ONNX eşitliği yalnızca dışa aktarma düzeyindeki tutarlılığı kanıtlar. HEF dönüşümü, Raspberry Pi 5 + Hailo çıkarım gecikmesi, RAM kullanımı ve gerçek donanım çalışma zamanı ayrıca beklemededir.

**Yedek görsel:** `15_verified_vs_pending_matrix.png`

**Asla söyleme:** ONNX parity proves Hailo deployment; Pi latency is validated

## Slayt 7 — Close with exact verified scope and numbers.

**Görsel:** `S07_final_two_crop_scorecard.png`

**Açılış:** Sonuç olarak mevcut bilgisayar tarafı kapsamını iki ürün için kapattık.

**Neyi göster:** Tomato 99.16%, Tomato Macro F1 0.9899, Pepper 98.11%, Pepper Macro F1 0.9802, RESEARCH_ONLY, Physical actuation DISABLED

**Teknik cümle:** Domates nihai test doğruluğu %99,16, biber ise %98,11'dir. Her iki model için dondurulmuş değerlendirme, ONNX eşitliği, açıklanabilirlik ve kayıt defteri kanıtı mevcuttur.

**Olası itiraz:** What exactly remains unfinished?

**Cevap:** Gerçek sera doğrulaması, kalibre edilmiş su stresi modeli, gerçek çok modlu füzyon, Pi/Hailo donanım doğrulaması, pompa kalibrasyonu ve fiziksel kapalı döngü, operasyonel sürümden önce tamamlanmalıdır.

**Yedek görsel:** `15_verified_vs_pending_matrix.png`

**Asla söyleme:** GreenPulse is fully finished; Operational release is approved; Autonomous irrigation is enabled

## Hızlı soru-cevap

**1. Why YOLO11n instead of a standard CNN?**

YOLO11n sınıflandırma, Ultralytics ekosisteminde hafif bir dağıtım yolu sunduğu için seçildi. Burada nesne tespiti değil, sınıflandırma görevi kullanıyoruz. Seçimin temel pratik nedeni, ileride yapılacak uç birim dışa aktarımıyla uyumluluktur.

**2. Is crop recognition automatic?**

Mevcut sistemde ürün kimliği bağımsız olarak doğrulanmıyor; dışarıdan gelen bir bildirim olarak kabul ediliyor. Bu nedenle yanlış ürün yönlendirme riskini gizlemiyoruz ve bilinmeyen ürün politikasını ABSTAIN olarak bırakıyoruz.

**3. What protects you from duplicate leakage?**

Tam SHA çakışması kontrol edildi, eşlenmiş domates alt kümesinde yaprak grubu ayrık bölme kuruldu ve ek olarak dHash/pHash yakın kopya taraması yapıldı. Ancak eşlenmemiş bölüm için fiziksel yaprak kimliğini kanıtlanmış saymıyoruz.

**4. Why is Macro F1 important if accuracy is already high?**

Doğruluk, baskın sınıfların etkisini gizleyebilir. Makro F1 her sınıfa eşit ağırlık verir ve 10 sınıflı domates modelinde daha dengeli bir genelleme göstergesidir.

**5. Do you automatically retrain on difficult samples?**

Hayır. Düşük güvenli, dağılım dışı ve çelişen durumlar yalnızca insan inceleme kuyruğuna gider. Otomatik etiketleme ve otomatik yeniden eğitim mevcut politikada açıkça devre dışıdır.

**6. Can disease confidence directly trigger irrigation?**

Hayır. Hastalık sınıflandırması su stresi kanıtı değildir. Mevcut güvenlik kapısı özerk fiziksel eyleme izin vermez.

**7. Why no cucumber?**

Mevcut doğrulanmış kapsamı iki üründe bilimsel olarak tam kapatmayı, üçüncü ürünü yarım eklemeye tercih ettik. Salatalık kayıt defterinde yoktur ve ABSTAIN/BLOCK uygulanır.

**8. What is your strongest technical contribution?**

Tek başına yüksek doğruluk değil; sızıntıya duyarlı değerlendirme, dondurulmuş test disiplini, model izlenebilirliği, ONNX eşitliği, açıklanabilirlik ve güvenlik yönetimli yönlendirmeyi aynı yapay zekâ hattında birleştirmemizdir.

## Terminoloji

| Anahtar | Şöyle söyle |
|---|---|
| `say` | YOLO11n classification |
| `do_not_say` | YOLO object detection |
| `gradcam` | qualitative attention diagnostic |
| `onnx` | export parity evidence |
| `deployment` | RESEARCH_ONLY |
| `physical_actuation` | DISABLED |
| `complete_scope` | computer-side disease classification for tomato + bell pepper |

## Bu paket üretilirken yapılmayanlar

| İşlem | Yapıldı mı |
|---|---|
| `model_loaded` | HAYIR |
| `inference_executed` | HAYIR |
| `training_executed` | HAYIR |
| `frozen_test_images_accessed` | HAYIR |
| `model_artifacts_modified` | HAYIR |

