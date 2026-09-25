from pathlib import Path
import csv
import sys


ROOT = Path(__file__).resolve().parents[2]

BASE = (
    ROOT
    / "jury_evidence"
    / "real_measurements"
    / "templates"
)


expected = {
    "edge_benchmark_real.csv": 18,
    "hailo_onnx_parity_real.csv": 9,
    "long_run_stability_real.csv": 11,
    "ablation_real.csv": 5,
    "temporal_real.csv": 5,
    "forecast_real.csv": 9,
    "hardware_actions_real.csv": 8,
    "sustainability_real.csv": 11,
}


print("=" * 88)
print("GREENPULSE REAL MEASUREMENT KIT VALIDATION")
print("=" * 88)


all_ok = True


for filename, expected_columns in expected.items():

    path = BASE / filename

    if not path.is_file():

        print(
            filename,
            ": MISSING"
        )

        all_ok = False
        continue

    with path.open(
        newline="",
        encoding="utf-8",
    ) as stream:

        rows = list(
            csv.reader(
                stream
            )
        )

    if not rows:

        print(
            filename,
            ": EMPTY / INVALID"
        )

        all_ok = False
        continue

    column_count = len(
        rows[0]
    )

    data_rows = max(
        0,
        len(rows) - 1,
    )

    structure_ok = (
        column_count
        == expected_columns
    )

    print(
        filename,
        ":",
        "STRUCTURE_OK"
        if structure_ok
        else "STRUCTURE_ERROR",
        "| columns:",
        column_count,
        "| real data rows:",
        data_rows,
    )

    if not structure_ok:
        all_ok = False


print("=" * 88)

if not all_ok:
    print("MEASUREMENT KIT VALIDATION: FAILED")
    sys.exit(1)

print("MEASUREMENT KIT STRUCTURE: COMPLETE")
print("REAL MEASUREMENT DATA COLLECTED: NO")
print("JURY REAL-METRIC VISUALS READY TO GENERATE: NO")
print("=" * 88)
