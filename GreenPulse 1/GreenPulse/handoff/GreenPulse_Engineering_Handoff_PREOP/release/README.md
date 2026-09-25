# GreenPulse AI/ML Release Handoff

## Status

This directory is a **pre-operational software handoff package**.

It is not evidence of a completed Hailo deployment, Raspberry Pi 5 + AI HAT+ validation,
physical actuator validation, real greenhouse validation, or final Git/GitHub release provenance.

## Package

- Edge ONNX release candidates
- Master inference/API service references
- Fusion, forecasting and decision module references
- Configuration and test directories
- Backend handoff
- Frontend field dictionary
- Hardware handoff
- JSON schemas
- Example payloads
- Install/start scripts

## Important blockers

Final operational release remains blocked until the required external/hardware work is completed,
including Engineer 1 Hailo approval, HEF generation and parity validation, Pi 5 + AI HAT+ testing,
real hardware end-to-end testing, and final Git/GitHub provenance.

## Install

Run:

    powershell -ExecutionPolicy Bypass -File release/install.ps1

The installation script deliberately refuses to claim reproducible installation until the final
dependency lock file exists.

## Start

Run:

    powershell -ExecutionPolicy Bypass -File release/start.ps1

The start script uses the existing project virtual environment and attempts to launch the FastAPI
application only when required runtime components are available.
