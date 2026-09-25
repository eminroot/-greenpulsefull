
import argparse
import json
import sys

from pathlib import Path

from src.real_data_staging import (
    stage_multimodal_candidate
)


MAX_METADATA_BYTES = 65536


def main():
    parser = argparse.ArgumentParser(
        description=(
            "GreenPulse offline hardware data intake. "
            "Does not authenticate devices."
        )
    )

    parser.add_argument(
        "--image",
        required=True
    )

    parser.add_argument(
        "--metadata",
        required=True
    )

    parser.add_argument(
        "--staging-dir",
        default=None
    )

    args = parser.parse_args()

    try:
        metadata_path = Path(args.metadata)

        if not metadata_path.is_file():
            raise FileNotFoundError(
                "Metadata file not found."
            )

        if (
            metadata_path.stat().st_size
            > MAX_METADATA_BYTES
        ):
            raise ValueError(
                "Metadata exceeds size limit."
            )

        metadata = json.loads(
            metadata_path.read_text(
                encoding="utf-8-sig"
            )
        )

        result = stage_multimodal_candidate(
            image_path=args.image,
            metadata=metadata,
            staging_dir=args.staging_dir
        )

    except (
        OSError,
        ValueError,
        KeyError
    ) as exc:
        print(
            json.dumps({
                "status": "REJECTED",
                "error_type": type(exc).__name__,
                "detail": str(exc)
            }),
            file=sys.stderr
        )

        return 2

    print(
        json.dumps(
            result,
            indent=2,
            allow_nan=False
        )
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
