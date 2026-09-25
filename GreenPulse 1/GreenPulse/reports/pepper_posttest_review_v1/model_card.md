# GreenPulse Pepper Model v1

## Model

Architecture: YOLO11n-cls

Task: Bell pepper disease classification

Classes:
- bacterial_spot
- healthy

Initialization:
GreenPulse tomato classification checkpoint.

Transfer learning advantage:
Not demonstrated by the validation comparison.

## Final held-out test

Dataset: PlantVillage

Images: 371

Claimed leaf groups: 51

Accuracy: 0.9811

Macro F1: 0.9802

False negatives: 7

False positives: 0

Leaf groups containing errors:
2

High-confidence errors:
3

## Interpretation

Seven bacterial-spot images were classified
as healthy.

The errors occurred across two claimed
leaf groups.

The evaluation uses controlled PlantVillage
images, not independent greenhouse images.

Claimed leaf-group separation is documented,
but physical plant identity is not verified.

## Deployment limitations

Real greenhouse validation: PENDING

Early water-stress detection: NOT VALIDATED

Raspberry Pi/Hailo deployment: PENDING

Autonomous physical actuation: DISABLED

This checkpoint is a research candidate,
not an operationally approved model.

## Test-set policy

The original held-out test has been consumed
for final evaluation.

It must not be reused for selecting new
hyperparameters, thresholds or checkpoints.

Future improvements require a new experiment
and appropriate independent evaluation data.
