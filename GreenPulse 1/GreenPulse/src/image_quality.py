
from io import BytesIO

import cv2
import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError


QUALITY_VERSION = "0.1.0"
MIN_RESOLUTION = 96


def check_image_quality(image_bytes):
    """
    Conservative image quality checks.

    Blur score is diagnostic only until thresholds
    are validated on real greenhouse images.
    """

    try:
        with Image.open(BytesIO(image_bytes)) as original:
            image = ImageOps.exif_transpose(
                original
            ).convert("RGB")

            width, height = image.size

            if (
                width < MIN_RESOLUTION
                or height < MIN_RESOLUTION
            ):
                return {
                    "status": "IMAGE_INVALID",
                    "reason": "RESOLUTION_TOO_LOW",
                    "width": width,
                    "height": height,
                    "eligible_for_inference": False
                }

            pixels = np.asarray(image)
            gray = cv2.cvtColor(
                pixels,
                cv2.COLOR_RGB2GRAY
            )

            brightness = float(gray.mean())
            dark_fraction = float(
                np.mean(gray < 16)
            )
            bright_fraction = float(
                np.mean(gray > 239)
            )

            blur_score = float(
                cv2.Laplacian(
                    gray,
                    cv2.CV_64F
                ).var()
            )

    except (
        UnidentifiedImageError,
        OSError,
        ValueError,
        TypeError,
        cv2.error
    ):
        return {
            "status": "IMAGE_INVALID",
            "reason": "IMAGE_DECODING_FAILED",
            "eligible_for_inference": False
        }

    status = "IMAGE_OK"
    reason = None

    # Conservative checks for extreme exposure only.
    if brightness < 12 and dark_fraction > 0.98:
        status = "IMAGE_TOO_DARK"
        reason = "EXTREME_UNDEREXPOSURE"

    elif brightness > 243 and bright_fraction > 0.98:
        status = "IMAGE_OVEREXPOSED"
        reason = "EXTREME_OVEREXPOSURE"

    return {
        "quality_version": QUALITY_VERSION,
        "status": status,
        "reason": reason,
        "eligible_for_inference": status == "IMAGE_OK",
        "width": width,
        "height": height,
        "brightness": round(brightness, 3),
        "dark_fraction": round(dark_fraction, 4),
        "bright_fraction": round(bright_fraction, 4),
        "blur_score": round(blur_score, 3),
        "blur_threshold_validated": False
    }
