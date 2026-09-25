# GreenPulse Hardware Intake v0.1.0

## Purpose

This package defines the initial file-based interface
between the hardware team and GreenPulse AI/ML.

It does not implement live ESP32 communication,
physical pump control or verified sensor acquisition.

## Primary hardware

- Raspberry Pi 5, 16 GB
- Raspberry Pi AI HAT+, 26 TOPS
- ESP32-CAM with OV2640

The main irrigation pump is the selected
12V DC micro submersible pump.

The Gikfun peristaltic pump is reserved for
controlled dosing. Its operational role and
calibration require separate validation.

Neither pump may be connected directly to
Raspberry Pi GPIO pins.

## Required image input

Provide a genuine JPEG or PNG image.

Maximum file size: 8 MB.

The image SHA-256 must match the metadata.

The current metadata contract identifies
ESP32-CAM + OV2640 as the intended camera.

Declaring this camera model does not authenticate
the physical device.

## Required metadata

Use the following existing contract:

configs/real_multimodal_sample_schema_v1.json

Required information includes:

- sample_id
- plant_id
- session_id
- camera.device_id
- camera.captured_at
- camera.image_sha256
- sensor.device_id
- sensor.observed_at
- soil_moisture_pct
- air_temperature_c
- relative_humidity_pct

Sensor values must use the documented units.

Camera and sensor timestamps require time zones.

The provisional pairing tolerance is 120 seconds.
This value has not been field-validated.

## Running the intake

Run from the GreenPulse project root:

python -m scripts.stage_hardware_candidate --image IMAGE.jpg --metadata METADATA.json

For isolated tests, additionally specify:

--staging-dir PATH

## Interpretation

STAGED means that the file and metadata passed
the implemented intake checks.

It does not mean that:

- the camera was physically authenticated;
- sensor calibration was independently verified;
- the observations are scientifically labelled;
- the data is approved for model training;
- any physical intervention is authorized.

Inspect intake_report.json for blocking reasons.

A timestamp mismatch can be staged and flagged.
It must not silently become a valid training pair.

## Items requiring hardware-team confirmation

1. ESP32-CAM communication protocol.
2. Camera identification and trusted timestamps.
3. Exact environmental sensor models.
4. Sensor calibration procedure.
5. Pump driver, power supply and electrical protection.
6. Physical emergency-stop and safety mechanisms.
7. Ventilation hardware, if included.

The final live communication protocol will be
versioned separately from this offline intake.

## Current safety state

Real irrigation: DISABLED.
Real dosing: DISABLED.
Automatic training approval: DISABLED.
Physical device authentication: NOT IMPLEMENTED.
