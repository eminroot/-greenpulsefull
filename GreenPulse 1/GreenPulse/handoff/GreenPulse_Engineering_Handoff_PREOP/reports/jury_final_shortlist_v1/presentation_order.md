# GreenPulse — Final AI/ML Jury Visual Order

## Main 7 visuals

### 1. SYSTEM_ARCHITECTURE

**File:** `reports/jury_final_shortlist_v1/main_deck/S01_end_to_end_ai_architecture.png`

**Jury message:** GreenPulse is a modular AI/ML system, not merely a standalone classifier.

**Speaker cue:** We separated vision inference, sensor contracts, registry routing, safety, active learning, audit and hardware handoff into explicit modules.

### 2. SCIENTIFIC_VALIDATION

**File:** `reports/jury_final_shortlist_v1/main_deck/S02_frozen_test_protocol.png`

**Jury message:** Final metrics were protected from test-set leakage.

**Speaker cue:** Model selection stopped at validation. The final checkpoint was frozen before the held-out test was exposed, and the test was consumed once.

### 3. PRIMARY_MODEL_EVIDENCE

**File:** `reports/jury_final_shortlist_v1/main_deck/S03_tomato_final_confusion_matrix.png`

**Jury message:** The 10-class tomato classifier is evaluated on 2,737 frozen-test images, not only on validation.

**Speaker cue:** Tomato final-test accuracy is 99.1597%, Macro F1 is 0.989933, with 23 errors.

### 4. EXPLAINABILITY

**File:** `reports/jury_final_shortlist_v1/main_deck/S04_tomato_gradcam.png`

**Jury message:** Model attention can be qualitatively inspected.

**Speaker cue:** These are validation-only Grad-CAM diagnostics. We use them for visual inspection, not as lesion segmentation or causal evidence.

### 5. TRANSFER_LEARNING_EVIDENCE

**File:** `reports/jury_final_shortlist_v1/main_deck/S05_pepper_transfer_vs_generic.png`

**Jury message:** Transfer learning was tested against a generic baseline rather than assumed to be superior.

**Speaker cue:** Both candidates achieved identical final validation accuracy, so we explicitly do not claim a demonstrated transfer-learning advantage.

### 6. EDGE_EXPORT_EVIDENCE

**File:** `reports/jury_final_shortlist_v1/main_deck/S06_onnx_parity.png`

**Jury message:** Export to ONNX preserves classifier behavior.

**Speaker cue:** Both crops maintained Top-1 parity after ONNX export, with extremely small probability differences.

### 7. FINAL_RESULT

**File:** `reports/jury_final_shortlist_v1/main_deck/S07_final_two_crop_scorecard.png`

**Jury message:** The current verified computer-side scope is complete for tomato and bell pepper.

**Speaker cue:** Tomato reaches 99.16% final-test accuracy and pepper 98.11%, while deployment remains research-only and physical actuation remains disabled.

## Terminology guardrail

- The implemented vision task is **YOLO11n classification**, not object detection.
- Grad-CAM is qualitative explainability, not lesion segmentation.
- ONNX parity is export validation, not Hailo deployment validation.
- Current deployment mode is **RESEARCH_ONLY**.
- Physical actuation remains **DISABLED**.

## Q&A backup

- `reports/jury_final_shortlist_v1/backup_qa/B01_01_tomato_training_evidence.png`
- `reports/jury_final_shortlist_v1/backup_qa/B02_04_pepper_final_confusion_matrix.png`
- `reports/jury_final_shortlist_v1/backup_qa/B03_05_tomato_error_pairs.png`
- `reports/jury_final_shortlist_v1/backup_qa/B04_06_tomato_confidence_profile.png`
- `reports/jury_final_shortlist_v1/backup_qa/B05_08_pepper_gradcam_evidence.png`
- `reports/jury_final_shortlist_v1/backup_qa/B06_13_active_learning_safety_flow.png`
- `reports/jury_final_shortlist_v1/backup_qa/B07_14_registry_routing_safety_gate.png`
- `reports/jury_final_shortlist_v1/backup_qa/B08_15_verified_vs_pending_matrix.png`
- `reports/jury_final_shortlist_v1/backup_qa/B09_16_model_lifecycle_traceability.png`