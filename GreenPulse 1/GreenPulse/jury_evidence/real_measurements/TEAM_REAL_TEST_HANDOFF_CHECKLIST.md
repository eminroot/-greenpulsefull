# GreenPulse — Real Test Team Handoff Checklist

## IMPORTANT

This package is for **REAL measurements only**.

Do not enter synthetic, guessed or presentation-only values.

Do not modify the frozen Tomato/Pepper final test sets.

Do not claim Hailo, physical hardware, water saving or operational validation until the corresponding real test is completed.

---

# 1. Backend / AI Developer

## A. SENSOR ONLY vs VISION ONLY vs FUSION

Fill:

`jury_evidence/real_measurements/templates/ablation_real.csv`

Use the **same real labeled samples** for all three modes.

Required final metrics:

- Precision
- Recall
- F1
- False Positive Rate
- False Negative Rate

Do not claim multimodal superiority unless the measured Fusion result actually demonstrates it.

---

## B. Single Frame vs Temporal Verification

Fill:

`jury_evidence/real_measurements/templates/temporal_real.csv`

Use real time-ordered observations.

Compare:

`Single Frame Decision — Temporal Verified Decision`

Return false-positive / false-negative behavior as well as F1.

---

## C. Forecast vs Naive Baseline

Fill:

`jury_evidence/real_measurements/templates/forecast_real.csv`

Required outputs:

- MAE
- RMSE
- Forecast vs naive baseline
- Actionable lead time
- False alarm rate

Forecast benefit must not be claimed unless measured results support it.

---

# 2. Hardware / Edge Engineer

## Mandatory prerequisites

Before declaring Hailo deployment complete:

- Engineer 1 approval
- Selected ONNX model
- Hailo conversion toolchain
- Generated HEF
- Raspberry Pi 5
- AI HAT+
- Final sensor models
- Safe actuator driver/power interface

---

## A. ONNX — Hailo Parity

Fill:

`jury_evidence/real_measurements/templates/hailo_onnx_parity_real.csv`

Run the **same reference samples** through both runtimes.

Return:

- Prediction match
- ONNX confidence
- Hailo confidence
- Absolute confidence difference

---

## B. Real Edge Benchmark

Fill:

`jury_evidence/real_measurements/templates/edge_benchmark_real.csv`

Measure:

- Preprocessing latency
- Hailo inference latency
- Postprocessing latency
- Fusion latency
- Forecast latency
- Decision latency
- API latency
- End-to-end latency
- RAM
- Peak RAM
- CPU
- Accelerator utilization where available
- Device temperature

---

## C. Long-Run Stability

Fill:

`jury_evidence/real_measurements/templates/long_run_stability_real.csv`

Run:

1. 30-minute test
2. 1-hour test
3. Multi-hour test

Monitor:

- RAM growth
- Peak RAM
- CPU
- Temperature
- DB growth
- Model crash
- API crash
- Camera timeout
- Sensor timeout

**Do not claim <3 GB compliance before the real stability run proves it.**

---

## D. Physical Hardware / ACK

Fill:

`jury_evidence/real_measurements/templates/hardware_actions_real.csv`

Test actual:

`AI command — hardware request — physical action — ACK / FAIL / TIMEOUT`

Rules:

- TIMEOUT — success.
- Simulated ACK — real ACK.
- Never drive the pump directly from Raspberry Pi GPIO.
- Unsafe or uncertain state must not cause blind actuation.

---

# 3. Sustainability / Joint Integration Test

Fill:

`jury_evidence/real_measurements/templates/sustainability_real.csv`

Collect:

- Measured water usage
- Validated baseline water usage
- Intervention count
- Energy measurement / documented estimate
- Baseline energy where applicable
- Emissions factor + source where carbon calculation is used

Rules:

- No validated baseline — no water-saving claim.
- Estimated — measured.
- No documented emissions methodology — no carbon-saving claim.

---

# 4. What must be returned to the AI owner

Return the following together:

- Completed measurement CSV files
- Original raw logs
- Exact model versions
- HEF file + SHA256
- Runtime/toolchain versions
- Sensor model list
- Wiring / pin mapping
- Pump driver / power specification
- Photos or video of the physical setup
- Failed runs and anomalies — do not delete them

After the real data is returned, the GreenPulse Jury Visual Pack v2 will generate:

- Hailo latency waterfall
- ONNX vs Hailo parity
- RAM / CPU / temperature stability
- SENSOR vs VISION vs FUSION
- Precision / Recall / F1 / FPR / FNR
- Single-frame vs Temporal
- Actual vs Forecast vs Naive
- Forecast lead-time
- ACK / FAIL / TIMEOUT
- Water/resource efficiency visuals
