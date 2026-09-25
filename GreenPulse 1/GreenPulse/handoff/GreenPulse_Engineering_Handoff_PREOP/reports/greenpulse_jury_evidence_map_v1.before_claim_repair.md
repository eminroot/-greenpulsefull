# GreenPulse — AI/ML Jury Evidence Map

**Verified scope:** Tomato + Bell Pepper computer-side disease classification
**Operational release:** NO
**Physical actuation:** DISABLED

## 1. What exactly did we build?

**Section:** SYSTEM OVERVIEW
**Primary visual:** `11_end_to_end_ai_architecture.png`

**Likely jury question:** Is this merely a classifier demo, or is there an actual system architecture?

**What it proves:** GreenPulse contains separate vision, sensor-contract, time-sync, registry, safety-gate, active-learning, audit and hardware-contract layers.

**Speaker line:** GreenPulse-u yaln?z bir YOLO modeli kimi qurmad?q. Vision inference-dan model registry, safety gate, human-review active learning, audit v? hardware contract-a q?d?r modulyar AI/ML arxitektura qurmu?uq.

**Do not claim:** Do not say real greenhouse closed-loop operation is already validated.

## 2. How did we prevent test leakage?

**Section:** SCIENTIFIC VALIDATION
**Primary visual:** `12_frozen_test_protocol_timeline.png`
**Supporting visuals:** `16_model_lifecycle_traceability.png`

**Likely jury question:** How do we know your final accuracy was not optimized against the test set?

**What it proves:** Model selection ended on validation. The final checkpoint was frozen before final-test exposure. Tomato final test was consumed once, and post-test analysis used saved predictions only.

**Speaker line:** ?n vacib metodoloji q?rar?m?z budur: final test model se?imind? i?tirak etm?yib. Checkpoint ?vv?lc? freeze olunub, test yaln?z bir d?f? a??l?b v? bundan sonrak? analizl?r model inference il? deyil, saxlan?lm?? prediction-lar ?z?rind?n apar?l?b.

**Do not claim:** Do not call the full tomato dataset physically leaf-independent; unmapped physical identity remains unknown.

## 3. Did the model actually converge?

**Section:** TOMATO TRAINING
**Primary visual:** `01_tomato_training_evidence.png`

**Likely jury question:** What happened during training, and was the reported model simply an old checkpoint?

**What it proves:** A new tomato clean experiment used a generic pretrained base only; the historical tomato checkpoint was not used.

**Speaker line:** Tomato modelini ?vv?lki tomato checkpoint-d?n ba?lamad?q. Generic pretrained base-d?n clean experiment qurduq v? model se?imini validation n?tic?l?rin? ?sas?n etdik.

**Do not claim:** Do not present training accuracy alone as generalization.

## 4. What does the frozen test actually show?

**Section:** TOMATO FINAL PERFORMANCE
**Primary visual:** `03_tomato_final_confusion_matrix.png`
**Supporting visuals:** `05_tomato_error_pairs.png`, `06_tomato_confidence_profile.png`

**Likely jury question:** Where does the 10-class tomato model fail?

**What it proves:** Frozen final-test accuracy = 0.991597, Macro F1 = 0.989933, with 23 errors across 2,737 images.

**Speaker line:** Sad?c? 99 faiz accuracy demirik. Confusion matrix v? error-pair analizi il? modelin konkret harada s?hv etdiyini d? g?st?ririk. 2,737 frozen test n?mun?sind? 23 s?hv var.

**Do not claim:** Do not describe 99.16% as real-greenhouse accuracy.

## 5. Can we inspect what the network attends to?

**Section:** EXPLAINABILITY
**Primary visual:** `07_tomato_gradcam_evidence.png`
**Supporting visuals:** `08_pepper_gradcam_evidence.png`

**Likely jury question:** Is the network relying on plausible image regions?

**What it proves:** Grad-CAM evidence is generated on validation samples with preprocessing parity to standard YOLO inference.

**Speaker line:** Model q?rar?n? yaln?z class label kimi saxlam?r?q. Validation n?mun?l?rind? Grad-CAM il? ??b?k?nin diqq?t verdiyi regionlar? vizual audit ed? bilirik.

**Do not claim:** Grad-CAM is qualitative explainability, not lesion segmentation, pixel-level localization or causal proof.

## 6. Did transfer learning really improve pepper?

**Section:** TRANSFER LEARNING
**Primary visual:** `02_pepper_transfer_vs_generic.png`

**Likely jury question:** Did tomato-to-pepper transfer outperform a generic baseline?

**What it proves:** Both transfer and generic baseline reached identical validation accuracy; therefore transfer advantage was not claimed.

**Speaker line:** Burada n?tic?ni ?i?irtm?dik. Tomato-dan ba?layan transfer model v? generic baseline validation-da eyni n?tic?ni verdi. Ona g?r? transfer ?st?nl?y?n? s?but olunmu? kimi t?qdim etmirik.

**Do not claim:** Do not claim transfer learning demonstrated superiority.

## 7. How well did the second crop generalize?

**Section:** PEPPER FINAL PERFORMANCE
**Primary visual:** `04_pepper_final_confusion_matrix.png`

**Likely jury question:** Was the second crop independently evaluated?

**What it proves:** Pepper frozen final-test accuracy = 0.981132, Macro F1 = 0.980212 on 371 images.

**Speaker line:** ?kinci crop-u yaln?z validation n?tic?si il? ba?lamad?q. 371 n?mun?lik ayr?ca frozen testd? accuracy 98.11%, Macro F1 is? 0.9802 oldu.

**Do not claim:** Do not claim the pepper result proves performance under greenhouse domain shift.

## 8. Will the exported model behave like the PyTorch model?

**Section:** EDGE READINESS
**Primary visual:** `09_onnx_parity_evidence.png`

**Likely jury question:** How do you know ONNX export did not alter predictions?

**What it proves:** Tomato and pepper ONNX validation showed matching Top-1 predictions with extremely small probability differences.

**Speaker line:** Edge deployment ???n sad?c? ONNX export etm?mi?ik. PyTorch v? ONNX output-lar?n? n?mun?-n?mun? m?qayis? edib prediction parity-ni ayr?ca yoxlam???q.

**Do not claim:** ONNX parity is not Raspberry Pi or Hailo deployment validation.

## 9. What happens when the crop is unsupported?

**Section:** MODEL GOVERNANCE
**Primary visual:** `14_registry_routing_safety_gate.png`

**Likely jury question:** Will the model blindly make a prediction for any crop?

**What it proves:** Registry contains tomato and bell pepper only. Unsupported crops, including cucumber in current scope, are blocked under ABSTAIN policy.

**Speaker line:** Sistem unknown crop g?r?nd? ?n yax?n model? m?cburi routing etmir. Registry-d? olmayan crop ???n siyas?t ABSTAIN/BLOCK-dur.

**Do not claim:** Crop identity itself is currently an unverified external claim.

## 10. How does GreenPulse handle uncertainty?

**Section:** ACTIVE LEARNING
**Primary visual:** `13_active_learning_safety_flow.png`

**Likely jury question:** Does the system automatically learn from uncertain samples?

**What it proves:** Low-confidence, OOD, conflict and image-quality cases can enter a human review queue; automatic labeling and retraining remain disabled.

**Speaker line:** Active learning-i autonomous retraining kimi qurmad?q. Riskli v? qeyri-m??yy?n n?mun?l?r human-review queue-ya d???r; auto-label v? auto-retrain qada?and?r.

**Do not claim:** Do not imply the system self-updates in production.

## 11. What is complete today?

**Section:** FINAL SCORECARD
**Primary visual:** `10_two_crop_final_scorecard.png`

**Likely jury question:** What are the final verified AI/ML results?

**What it proves:** Computer-side disease classification is closed for tomato and bell pepper, with model, test, explainability, ONNX and governance evidence.

**Speaker line:** Bug?nk? ba?lanm?? scope iki crop ???nd?r: tomato v? bell pepper. H?r ikisi ???n frozen test, explainability, ONNX parity v? registry evidence m?vcuddur.

**Do not claim:** Do not say the complete greenhouse product is finished.

## 12. What is intentionally not claimed yet?

**Section:** SCIENTIFIC BOUNDARY
**Primary visual:** `15_verified_vs_pending_matrix.png`

**Likely jury question:** Which parts still require hardware and greenhouse validation?

**What it proves:** Real greenhouse, calibrated water stress, Hailo runtime, physical closed loop and measured savings remain pending.

**Speaker line:** Layih?nin g?c? yaln?z y?ks?k metrikl?rd? deyil, s?but etm?diyimiz ?eyi claim etm?m?yimizd?dir. Bu s?tunda software t?r?fd? ba?lad???m?z hiss?l?ri, dig?r s?tunda is? real hardware g?l?nd?n sonra ?l??l?c?k hiss?l?ri ay?rm???q.

**Do not claim:** Do not claim 45% water saving, 30% energy saving, early stress detection hours, Hailo latency or <3 GB RAM until physically measured.

# Rapid-fire AI/ML Jury Questions

### Why YOLO11n?

We selected a lightweight Ultralytics classification architecture suitable for later edge deployment. Current ONNX parity is verified; Hailo runtime is not yet validated.

### Why not use test data during model selection?

Because that would bias the reported final estimate. Model selection was validation-only, followed by checkpoint freeze and one-time held-out evaluation.

### Is Grad-CAM proof of disease localization?

No. It is a qualitative attention diagnostic only. We do not claim pixel-level lesion segmentation.

### Did transfer learning beat the baseline?

No demonstrated advantage was observed on validation; both candidates reached identical validation accuracy.

### Can the current system irrigate autonomously?

No. Physical actuation is explicitly disabled in the current research-only software state.

### What happens for cucumber?

Cucumber is outside the current two-crop scope and has no registered model, so routing is blocked under the abstention policy.

### Does ONNX parity mean Hailo deployment is complete?

No. It proves export-level consistency only. HEF conversion, Pi/Hailo latency and memory remain hardware-stage tasks.
