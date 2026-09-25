
import hashlib
import json
import math

from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

from PIL import Image
from ultralytics import YOLO


IMAGENET_MEAN = (
    0.485,
    0.456,
    0.406
)

IMAGENET_STD = (
    0.229,
    0.224,
    0.225
)


def sha256_file(path):
    digest = hashlib.sha256()

    with Path(path).open("rb") as stream:
        for block in iter(
            lambda: stream.read(1024 * 1024),
            b""
        ):
            digest.update(block)

    return digest.hexdigest()


def find_last_conv2d(model):

    layers = [
        module
        for module in model.modules()
        if isinstance(
            module,
            nn.Conv2d
        )
    ]

    if not layers:
        raise ValueError(
            "NO_CONV2D_LAYER_FOUND"
        )

    return layers[-1]


def _extract_logits(output):

    if (
        isinstance(output, torch.Tensor)
        and output.ndim == 2
    ):
        return output

    if isinstance(
        output,
        (tuple, list)
    ):
        candidates = []

        for item in output:
            if (
                isinstance(item, torch.Tensor)
                and item.ndim == 2
            ):
                candidates.append(item)

        if candidates:
            # Ultralytics classification inference
            # may return probabilities + logits.
            return candidates[-1]

    raise ValueError(
        "UNSUPPORTED_CLASSIFICATION_OUTPUT"
    )


def preprocess_rgb_image(
    image_path,
    imgsz=224
):

    """
    Ultralytics classification preprocessing parity:

        Resize(shorter edge -> imgsz)
        CenterCrop(imgsz)
        ToTensor()
        identity normalization

    This intentionally does NOT apply ImageNet
    mean/std normalization.
    """

    from torchvision.transforms import (
        CenterCrop,
        Compose,
        InterpolationMode,
        Normalize,
        Resize,
        ToTensor
    )

    path = Path(
        image_path
    )

    if not path.is_file():
        raise FileNotFoundError(
            path
        )


    if (
        not isinstance(imgsz, int)
        or isinstance(imgsz, bool)
        or imgsz < 32
    ):
        raise ValueError(
            "INVALID_IMGSZ"
        )


    with Image.open(path) as image:

        image = image.convert(
            "RGB"
        )

        width, height = image.size

        if (
            width < 32
            or height < 32
        ):
            raise ValueError(
                "IMAGE_TOO_SMALL"
            )


        transform = Compose([
            Resize(
                size=imgsz,
                interpolation=(
                    InterpolationMode.BILINEAR
                ),
                antialias=True
            ),

            CenterCrop(
                size=(
                    imgsz,
                    imgsz
                )
            ),

            ToTensor(),

            Normalize(
                mean=(
                    0.0,
                    0.0,
                    0.0
                ),
                std=(
                    1.0,
                    1.0,
                    1.0
                )
            )
        ])


        tensor = transform(
            image
        ).unsqueeze(0)


    if (
        tensor.ndim != 4
        or tensor.shape[0] != 1
        or tensor.shape[1] != 3
    ):
        raise ValueError(
            "INVALID_PREPROCESSED_TENSOR"
        )


    if not torch.isfinite(
        tensor
    ).all():
        raise ValueError(
            "NONFINITE_INPUT"
        )


    return tensor


def compute_gradcam_from_module(
    model,
    image_tensor,
    target_class=None
):

    if (
        not isinstance(
            image_tensor,
            torch.Tensor
        )
        or image_tensor.ndim != 4
        or image_tensor.shape[0] != 1
        or image_tensor.shape[1] != 3
    ):
        raise ValueError(
            "EXPECTED_1X3XHXW_TENSOR"
        )

    if not torch.isfinite(
        image_tensor
    ).all():
        raise ValueError(
            "NONFINITE_INPUT"
        )

    model.eval()

    # Released inference checkpoints may have
    # all parameters frozen (requires_grad=False).
    # Grad-CAM still needs a computation graph.
    #
    # Enabling gradient tracking on a detached
    # input creates that graph without modifying,
    # unfreezing or training model parameters.
    image_tensor = (
        image_tensor
        .detach()
        .clone()
        .requires_grad_(True)
    )

    conv = find_last_conv2d(
        model
    )

    stored = {}

    def forward_hook(
        module,
        inputs,
        output
    ):
        if not isinstance(
            output,
            torch.Tensor
        ):
            raise ValueError(
                "INVALID_CONV_OUTPUT"
            )

        stored["activation"] = output

        output.register_hook(
            lambda grad:
                stored.__setitem__(
                    "gradient",
                    grad
                )
        )

    handle = conv.register_forward_hook(
        forward_hook
    )

    try:

        model.zero_grad(
            set_to_none=True
        )

        output = model(
            image_tensor
        )

        logits = _extract_logits(
            output
        )

        if logits.shape[0] != 1:
            raise ValueError(
                "INVALID_BATCH_OUTPUT"
            )

        class_count = logits.shape[1]

        probabilities = torch.softmax(
            logits,
            dim=1
        )

        predicted_class = int(
            probabilities.argmax(
                dim=1
            ).item()
        )

        if target_class is None:
            target_class = predicted_class

        if (
            not isinstance(
                target_class,
                int
            )
            or isinstance(
                target_class,
                bool
            )
            or target_class < 0
            or target_class >= class_count
        ):
            raise ValueError(
                "INVALID_TARGET_CLASS"
            )

        score = logits[
            0,
            target_class
        ]

        score.backward()

        if (
            "activation"
            not in stored
            or "gradient"
            not in stored
        ):
            raise RuntimeError(
                "GRADCAM_HOOK_FAILURE"
            )

        activation = stored[
            "activation"
        ]

        gradient = stored[
            "gradient"
        ]

        weights = gradient.mean(
            dim=(2, 3),
            keepdim=True
        )

        cam = (
            weights * activation
        ).sum(
            dim=1,
            keepdim=True
        )

        cam = torch.relu(cam)

        cam = F.interpolate(
            cam,
            size=image_tensor.shape[-2:],
            mode="bilinear",
            align_corners=False
        )

        cam = cam[
            0, 0
        ].detach().cpu()

        minimum = float(
            cam.min()
        )

        maximum = float(
            cam.max()
        )

        if not (
            math.isfinite(minimum)
            and math.isfinite(maximum)
        ):
            raise ValueError(
                "NONFINITE_GRADCAM"
            )

        if maximum > minimum:
            cam = (
                cam - minimum
            ) / (
                maximum - minimum
            )
        else:
            cam = torch.zeros_like(
                cam
            )

        confidence = float(
            probabilities[
                0,
                predicted_class
            ].detach().cpu()
        )

        return {
            "heatmap":
                cam.numpy(),
            "predicted_class":
                predicted_class,
            "target_class":
                target_class,
            "confidence":
                confidence
        }

    finally:
        handle.remove()


def explain_ultralytics_classifier(
    checkpoint,
    image_path,
    output_directory,
    imgsz=224,
    target_class=None
):

    checkpoint = Path(
        checkpoint
    ).resolve()

    image_path = Path(
        image_path
    ).resolve()

    output_directory = Path(
        output_directory
    )

    if output_directory.exists():
        raise FileExistsError(
            output_directory
        )

    model_wrapper = YOLO(
        str(checkpoint)
    )

    if model_wrapper.task != "classify":
        raise ValueError(
            "MODEL_IS_NOT_CLASSIFIER"
        )

    class_names = [
        model_wrapper.names[i]
        for i in sorted(
            model_wrapper.names
        )
    ]

    tensor = preprocess_rgb_image(
        image_path,
        imgsz=imgsz
    )

    result = compute_gradcam_from_module(
        model_wrapper.model,
        tensor,
        target_class=target_class
    )

    output_directory.mkdir(
        parents=True,
        exist_ok=False
    )

    heatmap = (
        result["heatmap"]
        * 255.0
    ).round().clip(
        0, 255
    ).astype(
        np.uint8
    )

    heatmap_image = Image.fromarray(
        heatmap,
        mode="L"
    )

    with Image.open(
        image_path
    ) as original:

        original = original.convert(
            "RGB"
        )

        heatmap_full = heatmap_image.resize(
            original.size,
            Image.Resampling.BILINEAR
        )

        heat_array = np.asarray(
            heatmap_full,
            dtype=np.uint8
        )

        color_array = np.zeros(
            (
                heat_array.shape[0],
                heat_array.shape[1],
                3
            ),
            dtype=np.uint8
        )

        color_array[:, :, 0] = (
            heat_array
        )

        heat_rgb = Image.fromarray(
            color_array,
            mode="RGB"
        )

        overlay = Image.blend(
            original,
            heat_rgb,
            alpha=0.35
        )

    heatmap_path = (
        output_directory
        / "gradcam_heatmap.png"
    )

    overlay_path = (
        output_directory
        / "gradcam_overlay.png"
    )

    metadata_path = (
        output_directory
        / "metadata.json"
    )

    heatmap_image.save(
        heatmap_path
    )

    overlay.save(
        overlay_path
    )

    metadata = {
        "version": "1.0",
        "generated_at_utc":
            datetime.now(
                timezone.utc
            ).isoformat(),

        "method": "GRAD_CAM",

        "checkpoint_sha256":
            sha256_file(
                checkpoint
            ),

        "image_sha256":
            sha256_file(
                image_path
            ),

        "image_path":
            str(image_path),

        "imgsz": imgsz,

        "class_names":
            class_names,

        "predicted_class_id":
            result[
                "predicted_class"
            ],

        "predicted_class_name":
            class_names[
                result[
                    "predicted_class"
                ]
            ],

        "target_class_id":
            result[
                "target_class"
            ],

        "target_class_name":
            class_names[
                result[
                    "target_class"
                ]
            ],

        "confidence":
            result[
                "confidence"
            ],

        "explanation_type":
            "QUALITATIVE_DIAGNOSTIC",

        "pixel_level_localization_validated":
            False,

        "causal_explanation":
            False,

        "real_greenhouse_validation":
            False,

        "operational_decision_allowed":
            False,

        "physical_actuation_allowed":
            False
    }

    metadata_path.write_text(
        json.dumps(
            metadata,
            indent=2,
            allow_nan=False
        ) + "\n",
        encoding="utf-8"
    )

    return metadata
