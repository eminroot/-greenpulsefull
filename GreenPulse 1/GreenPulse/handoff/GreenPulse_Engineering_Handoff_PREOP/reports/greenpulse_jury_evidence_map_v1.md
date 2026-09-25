# GreenPulse — Jüri Kanıt Haritası

**Amaç:** AI_ML_ARCHITECT_JURY_EVIDENCE_MAP

**Doğrulanmış görsel sayısı:** 16

> **Sunum dili: Türkçe.** Konuşmacı cümleleri Türkçedir. Önceki sürümde metin Azerice idi ve dosya cp1252/ASCII bir akışa yazıldığı için özel harfler '?' karakterine dönüşmüştü. Kayıplı bozulma geri getirilemediği için metin tahmin edilerek onarılmadı; TEKNOFEST sunum dili olan Türkçe ile yeniden yazıldı.

## 1. What exactly did we build?

**Bölüm:** SYSTEM OVERVIEW

**Ana görsel:** `11_end_to_end_ai_architecture.png`

**Jüri sorusu:** Is this merely a classifier demo, or is there an actual system architecture?

**Kanıt:** GreenPulse contains separate vision, sensor-contract, time-sync, registry, safety-gate, active-learning, audit and hardware-contract layers.

**Konuşmacı cümlesi:** GreenPulse'u yalnızca bir YOLO modeli olarak kurmadık. Görüntü çıkarımından model kayıt defterine, güvenlik kapısına, insan incelemeli aktif öğrenmeye, denetime ve donanım sözleşmesine kadar modüler bir yapay zekâ mimarisi kurduk.

**İddia etme:** D; o;  ; n; o; t;  ; s; a; y;  ; r; e; a; l;  ; g; r; e; e; n; h; o; u; s; e;  ; c; l; o; s; e; d; -; l; o; o; p;  ; o; p; e; r; a; t; i; o; n;  ; i; s;  ; a; l; r; e; a; d; y;  ; v; a; l; i; d; a; t; e; d; .

## 2. How did we prevent test leakage?

**Bölüm:** SCIENTIFIC VALIDATION

**Ana görsel:** `12_frozen_test_protocol_timeline.png`

**Destekleyici görseller:** `16_model_lifecycle_traceability.png`

**Jüri sorusu:** How do we know your final accuracy was not optimized against the test set?

**Kanıt:** Model selection ended on validation. The final checkpoint was frozen before final-test exposure. Tomato final test was consumed once, and post-test analysis used saved predictions only.

**Konuşmacı cümlesi:** En önemli metodolojik kararımız budur: nihai test, model seçimine katılmadı. Kontrol noktası önce donduruldu, test yalnızca bir kez açıldı ve sonraki analizler model çıkarımıyla değil, kaydedilmiş tahminler üzerinden yapıldı.

**İddia etme:** D; o;  ; n; o; t;  ; c; a; l; l;  ; t; h; e;  ; f; u; l; l;  ; t; o; m; a; t; o;  ; d; a; t; a; s; e; t;  ; p; h; y; s; i; c; a; l; l; y;  ; l; e; a; f; -; i; n; d; e; p; e; n; d; e; n; t; ;;  ; u; n; m; a; p; p; e; d;  ; p; h; y; s; i; c; a; l;  ; i; d; e; n; t; i; t; y;  ; r; e; m; a; i; n; s;  ; u; n; k; n; o; w; n; .

## 3. Did the model actually converge?

**Bölüm:** TOMATO TRAINING

**Ana görsel:** `01_tomato_training_evidence.png`

**Jüri sorusu:** What happened during training, and was the reported model simply an old checkpoint?

**Kanıt:** A new tomato clean experiment used a generic pretrained base only; the historical tomato checkpoint was not used.

**Konuşmacı cümlesi:** Domates modelini önceki domates kontrol noktasından başlatmadık. Genel ön eğitimli bir temelden temiz bir deney kurduk ve model seçimini doğrulama sonuçlarına dayandırdık.

**İddia etme:** D; o;  ; n; o; t;  ; p; r; e; s; e; n; t;  ; t; r; a; i; n; i; n; g;  ; a; c; c; u; r; a; c; y;  ; a; l; o; n; e;  ; a; s;  ; g; e; n; e; r; a; l; i; z; a; t; i; o; n; .

## 4. What does the frozen test actually show?

**Bölüm:** TOMATO FINAL PERFORMANCE

**Ana görsel:** `03_tomato_final_confusion_matrix.png`

**Destekleyici görseller:** `05_tomato_error_pairs.png`, `06_tomato_confidence_profile.png`

**Jüri sorusu:** Where does the 10-class tomato model fail?

**Kanıt:** Frozen final-test accuracy = 0.991597, Macro F1 = 0.989933, with 23 errors across 2,737 images.

**Konuşmacı cümlesi:** Yalnızca %99 doğruluk demiyoruz. Karışıklık matrisi ve hata çifti analiziyle modelin tam olarak nerede yanıldığını da gösteriyoruz. 2.737 dondurulmuş test örneğinde 23 hata var.

**İddia etme:** D; o;  ; n; o; t;  ; d; e; s; c; r; i; b; e;  ; 9; 9; .; 1; 6; %;  ; a; s;  ; r; e; a; l; -; g; r; e; e; n; h; o; u; s; e;  ; a; c; c; u; r; a; c; y; .

## 5. Can we inspect what the network attends to?

**Bölüm:** EXPLAINABILITY

**Ana görsel:** `07_tomato_gradcam_evidence.png`

**Destekleyici görseller:** `08_pepper_gradcam_evidence.png`

**Jüri sorusu:** Is the network relying on plausible image regions?

**Kanıt:** Grad-CAM evidence is generated on validation samples with preprocessing parity to standard YOLO inference.

**Konuşmacı cümlesi:** Model kararını yalnızca sınıf etiketi olarak saklamıyoruz. Doğrulama örneklerinde Grad-CAM ile ağın dikkat ettiği bölgeleri görsel olarak denetleyebiliyoruz.

**İddia etme:** G; r; a; d; -; C; A; M;  ; i; s;  ; q; u; a; l; i; t; a; t; i; v; e;  ; e; x; p; l; a; i; n; a; b; i; l; i; t; y; ,;  ; n; o; t;  ; l; e; s; i; o; n;  ; s; e; g; m; e; n; t; a; t; i; o; n; ,;  ; p; i; x; e; l; -; l; e; v; e; l;  ; l; o; c; a; l; i; z; a; t; i; o; n;  ; o; r;  ; c; a; u; s; a; l;  ; p; r; o; o; f; .

## 6. Did transfer learning really improve pepper?

**Bölüm:** TRANSFER LEARNING

**Ana görsel:** `02_pepper_transfer_vs_generic.png`

**Jüri sorusu:** Did tomato-to-pepper transfer outperform a generic baseline?

**Kanıt:** Both transfer and generic baseline reached identical validation accuracy; therefore transfer advantage was not claimed.

**Konuşmacı cümlesi:** Burada sonucu şişirmedik. Domatesten başlayan transfer modeli ile genel temel model doğrulamada aynı sonucu verdi. Bu nedenle transfer üstünlüğünü kanıtlanmış gibi sunmuyoruz.

**İddia etme:** D; o;  ; n; o; t;  ; c; l; a; i; m;  ; t; r; a; n; s; f; e; r;  ; l; e; a; r; n; i; n; g;  ; d; e; m; o; n; s; t; r; a; t; e; d;  ; s; u; p; e; r; i; o; r; i; t; y; .

## 7. How well did the second crop generalize?

**Bölüm:** PEPPER FINAL PERFORMANCE

**Ana görsel:** `04_pepper_final_confusion_matrix.png`

**Jüri sorusu:** Was the second crop independently evaluated?

**Kanıt:** Pepper frozen final-test accuracy = 0.981132, Macro F1 = 0.980212 on 371 images.

**Konuşmacı cümlesi:** İkinci ürünü yalnızca doğrulama sonucuyla kapatmadık. 371 örneklik ayrı bir dondurulmuş testte doğruluk %98,11 ve Makro F1 0,9802 oldu.

**İddia etme:** D; o;  ; n; o; t;  ; c; l; a; i; m;  ; t; h; e;  ; p; e; p; p; e; r;  ; r; e; s; u; l; t;  ; p; r; o; v; e; s;  ; p; e; r; f; o; r; m; a; n; c; e;  ; u; n; d; e; r;  ; g; r; e; e; n; h; o; u; s; e;  ; d; o; m; a; i; n;  ; s; h; i; f; t; .

## 8. Will the exported model behave like the PyTorch model?

**Bölüm:** EDGE READINESS

**Ana görsel:** `09_onnx_parity_evidence.png`

**Jüri sorusu:** How do you know ONNX export did not alter predictions?

**Kanıt:** Tomato and pepper ONNX validation showed matching Top-1 predictions with extremely small probability differences.

**Konuşmacı cümlesi:** Uç birim dağıtımı için yalnızca ONNX dışa aktarımı yapmadık. PyTorch ve ONNX çıktılarını örnek örnek karşılaştırarak tahmin eşitliğini ayrıca doğruladık.

**İddia etme:** O; N; N; X;  ; p; a; r; i; t; y;  ; i; s;  ; n; o; t;  ; R; a; s; p; b; e; r; r; y;  ; P; i;  ; o; r;  ; H; a; i; l; o;  ; d; e; p; l; o; y; m; e; n; t;  ; v; a; l; i; d; a; t; i; o; n; .

## 9. What happens when the crop is unsupported?

**Bölüm:** MODEL GOVERNANCE

**Ana görsel:** `14_registry_routing_safety_gate.png`

**Jüri sorusu:** Will the model blindly make a prediction for any crop?

**Kanıt:** Registry contains tomato and bell pepper only. Unsupported crops, including cucumber in current scope, are blocked under ABSTAIN policy.

**Konuşmacı cümlesi:** Sistem bilinmeyen bir ürün gördüğünde en yakın modele zorunlu yönlendirme yapmaz. Kayıt defterinde bulunmayan ürün için politika ABSTAIN/BLOCK'tur.

**İddia etme:** C; r; o; p;  ; i; d; e; n; t; i; t; y;  ; i; t; s; e; l; f;  ; i; s;  ; c; u; r; r; e; n; t; l; y;  ; a; n;  ; u; n; v; e; r; i; f; i; e; d;  ; e; x; t; e; r; n; a; l;  ; c; l; a; i; m; .

## 10. How does GreenPulse handle uncertainty?

**Bölüm:** ACTIVE LEARNING

**Ana görsel:** `13_active_learning_safety_flow.png`

**Jüri sorusu:** Does the system automatically learn from uncertain samples?

**Kanıt:** Low-confidence, OOD, conflict and image-quality cases can enter a human review queue; automatic labeling and retraining remain disabled.

**Konuşmacı cümlesi:** Aktif öğrenmeyi özerk yeniden eğitim olarak kurmadık. Riskli ve belirsiz örnekler insan inceleme kuyruğuna düşer; otomatik etiketleme ve otomatik yeniden eğitim yasaktır.

**İddia etme:** D; o;  ; n; o; t;  ; i; m; p; l; y;  ; t; h; e;  ; s; y; s; t; e; m;  ; s; e; l; f; -; u; p; d; a; t; e; s;  ; i; n;  ; p; r; o; d; u; c; t; i; o; n; .

## 11. What is complete today?

**Bölüm:** FINAL SCORECARD

**Ana görsel:** `10_two_crop_final_scorecard.png`

**Jüri sorusu:** What are the final verified AI/ML results?

**Kanıt:** Computer-side disease classification is closed for tomato and bell pepper, with model, test, explainability, ONNX and governance evidence. Current deployment mode is RESEARCH-ONLY; operational release is not approved and physical actuation remains disabled.

**Konuşmacı cümlesi:** Bugün kapatılmış kapsam iki üründür: domates ve dolmalık biber. Her ikisi için dondurulmuş test, açıklanabilirlik, ONNX eşitliği ve kayıt defteri kanıtı mevcuttur. Mevcut dağıtım durumumuz yalnızca araştırmadır; operasyonel sürüm onaylanmamıştır ve fiziksel eyleme devre dışıdır.

**İddia etme:** D; o;  ; n; o; t;  ; s; a; y;  ; t; h; e;  ; c; o; m; p; l; e; t; e;  ; g; r; e; e; n; h; o; u; s; e;  ; p; r; o; d; u; c; t;  ; i; s;  ; f; i; n; i; s; h; e; d; .

## 12. What is intentionally not claimed yet?

**Bölüm:** SCIENTIFIC BOUNDARY

**Ana görsel:** `15_verified_vs_pending_matrix.png`

**Jüri sorusu:** Which parts still require hardware and greenhouse validation?

**Kanıt:** Real greenhouse, calibrated water stress, Hailo runtime, physical closed loop and measured savings remain pending.

**Konuşmacı cümlesi:** Projenin gücü yalnızca yüksek metriklerde değil, kanıtlamadığımız şeyi iddia etmememizdedir. Bu sütunda yazılım tarafında kapattığımız bölümleri, diğer sütunda ise gerçek donanım geldikten sonra ölçülecek bölümleri ayırdık.

**İddia etme:** D; o;  ; n; o; t;  ; c; l; a; i; m;  ; 4; 5; %;  ; w; a; t; e; r;  ; s; a; v; i; n; g; ,;  ; 3; 0; %;  ; e; n; e; r; g; y;  ; s; a; v; i; n; g; ,;  ; e; a; r; l; y;  ; s; t; r; e; s; s;  ; d; e; t; e; c; t; i; o; n;  ; h; o; u; r; s; ,;  ; H; a; i; l; o;  ; l; a; t; e; n; c; y;  ; o; r;  ; <; 3;  ; G; B;  ; R; A; M;  ; u; n; t; i; l;  ; p; h; y; s; i; c; a; l; l; y;  ; m; e; a; s; u; r; e; d; .

## Hızlı soru-cevap

**1. Why YOLO11n?**

We selected a lightweight Ultralytics classification architecture suitable for later edge deployment. Current ONNX parity is verified; Hailo runtime is not yet validated.

**2. Why not use test data during model selection?**

Because that would bias the reported final estimate. Model selection was validation-only, followed by checkpoint freeze and one-time held-out evaluation.

**3. Is Grad-CAM proof of disease localization?**

No. It is a qualitative attention diagnostic only. We do not claim pixel-level lesion segmentation.

**4. Did transfer learning beat the baseline?**

No demonstrated advantage was observed on validation; both candidates reached identical validation accuracy.

**5. Can the current system irrigate autonomously?**

No. Physical actuation is explicitly disabled in the current research-only software state.

**6. What happens for cucumber?**

Cucumber is outside the current two-crop scope and has no registered model, so routing is blocked under the abstention policy.

**7. Does ONNX parity mean Hailo deployment is complete?**

No. It proves export-level consistency only. HEF conversion, Pi/Hailo latency and memory remain hardware-stage tasks.

## Bilimsel sınır

| Madde | Durum |
|---|---|
| `verified_scope` | Tomato + Bell Pepper computer-side disease classification |
| `operational_release` | HAYIR |
| `real_greenhouse_validated` | HAYIR |
| `water_stress_validated` | HAYIR |
| `hailo_runtime_validated` | HAYIR |
| `physical_closed_loop_validated` | HAYIR |

