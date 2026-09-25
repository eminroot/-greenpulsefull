import json
import math
import sys
from copy import deepcopy
from datetime import datetime, timezone, timedelta
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

sys.path.insert(0, str(Path("src").resolve()))
from sensor_validator import validate_sensor

SCHEMA_PATH = Path("configs/sensor_schema_v1.json")
SAMPLE_PATH = Path("tests/fixtures/sensor_valid_simulated.json")

schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
sample = json.loads(SAMPLE_PATH.read_text(encoding="utf-8"))

Draft202012Validator.check_schema(schema)

validator = Draft202012Validator(
    schema,
    format_checker=FormatChecker()
)

# Yenilənmiş vaxt: nümunə fayl köhnəlsə də test işləsin.
sample["timestamp"] = datetime.now(timezone.utc).isoformat()

def check(name, packet, expected_schema, expected_status):
    schema_valid = validator.is_valid(packet)
    status, reason = validate_sensor(packet)

    assert schema_valid == expected_schema, (
        f"{name}: unexpected schema result"
    )
    assert status == expected_status, (
        f"{name}: expected {expected_status}, got {status}"
    )

    print(f"PASS: {name} -> {status}")

print("\nGREENPULSE SENSOR CONTRACT TESTS")
print("--------------------------------")

# 1. Düzgün məlumat
check("VALID_PACKET", sample, True, "VALID_SIMULATED")

# 2. Çatışmayan sensor məlumatı
packet = deepcopy(sample)
del packet["temperature_c"]
check("MISSING_FIELD", packet, False, "MISSING")

# 3. Qeyri-mümkün rütubət
packet = deepcopy(sample)
packet["humidity_pct"] = 150
check("INVALID_HUMIDITY", packet, False, "INVALID")

# 4. Yanlış timestamp
packet = deepcopy(sample)
packet["timestamp"] = "not-a-date"
check("INVALID_TIMESTAMP", packet, False, "INVALID")

# 5. İcazəsiz əlavə məlumat
packet = deepcopy(sample)
packet["unexpected_field"] = 123

assert not validator.is_valid(packet)
print("PASS: UNEXPECTED_FIELD -> REJECTED_BY_SCHEMA")

# 6. Yanlış kalibrləmə tipi
packet = deepcopy(sample)
packet["soil_calibrated"] = "true"
check("INVALID_CALIBRATION_TYPE", packet, False, "INVALID")

# 7. NaN yoxlaması
packet = deepcopy(sample)
packet["soil_moisture_pct"] = float("nan")

status, _ = validate_sensor(packet)
assert status == "INVALID"

try:
    json.dumps(packet, allow_nan=False)
    raise AssertionError("NaN must not be serialized")
except ValueError:
    pass

print("PASS: NAN_VALUE -> REJECTED")

# 8. Köhnəlmiş sensor məlumatı
packet = deepcopy(sample)
packet["timestamp"] = (
    datetime.now(timezone.utc) - timedelta(minutes=10)
).isoformat()

check("STALE_SENSOR", packet, True, "STALE")

print("--------------------------------")
print("ALL 8 SENSOR CONTRACT TESTS PASSED")
