
import unittest

import torch
import torch.nn as nn

from src.vision_explainability import (
    compute_gradcam_from_module,
    find_last_conv2d
)


class TinyClassifier(nn.Module):

    def __init__(self):
        super().__init__()

        self.features = nn.Sequential(
            nn.Conv2d(
                3, 4,
                kernel_size=3,
                padding=1
            ),
            nn.ReLU(),
            nn.Conv2d(
                4, 8,
                kernel_size=3,
                padding=1
            ),
            nn.ReLU()
        )

        self.pool = (
            nn.AdaptiveAvgPool2d(
                (1, 1)
            )
        )

        self.fc = nn.Linear(
            8, 2
        )

    def forward(self, x):
        x = self.features(x)
        x = self.pool(x)
        x = torch.flatten(
            x, 1
        )
        return self.fc(x)


class ExplainabilityTests(unittest.TestCase):

    def setUp(self):
        torch.manual_seed(2026)

        self.model = (
            TinyClassifier()
        )

        self.image = torch.randn(
            1, 3, 32, 32
        )

    def test_01_last_conv_found(self):

        layer = find_last_conv2d(
            self.model
        )

        self.assertIsInstance(
            layer,
            nn.Conv2d
        )

        self.assertEqual(
            layer.out_channels,
            8
        )

    def test_02_gradcam_shape(self):

        result = (
            compute_gradcam_from_module(
                self.model,
                self.image
            )
        )

        self.assertEqual(
            result["heatmap"].shape,
            (32, 32)
        )

    def test_03_gradcam_range(self):

        result = (
            compute_gradcam_from_module(
                self.model,
                self.image
            )
        )

        heatmap = result[
            "heatmap"
        ]

        self.assertGreaterEqual(
            float(heatmap.min()),
            0.0
        )

        self.assertLessEqual(
            float(heatmap.max()),
            1.0
        )

    def test_04_prediction_valid(self):

        result = (
            compute_gradcam_from_module(
                self.model,
                self.image
            )
        )

        self.assertIn(
            result["predicted_class"],
            (0, 1)
        )

        self.assertGreaterEqual(
            result["confidence"],
            0.0
        )

        self.assertLessEqual(
            result["confidence"],
            1.0
        )

    def test_05_explicit_target(self):

        result = (
            compute_gradcam_from_module(
                self.model,
                self.image,
                target_class=1
            )
        )

        self.assertEqual(
            result["target_class"],
            1
        )

    def test_06_invalid_target_rejected(self):

        with self.assertRaisesRegex(
            ValueError,
            "INVALID_TARGET_CLASS"
        ):
            compute_gradcam_from_module(
                self.model,
                self.image,
                target_class=99
            )

    def test_07_bad_input_rejected(self):

        bad = torch.randn(
            3, 32, 32
        )

        with self.assertRaisesRegex(
            ValueError,
            "EXPECTED_1X3XHXW_TENSOR"
        ):
            compute_gradcam_from_module(
                self.model,
                bad
            )


    def test_08_frozen_model_supported(self):

        for parameter in (
            self.model.parameters()
        ):
            parameter.requires_grad_(
                False
            )

        result = (
            compute_gradcam_from_module(
                self.model,
                self.image
            )
        )

        self.assertEqual(
            result["heatmap"].shape,
            (32, 32)
        )

        self.assertTrue(
            all(
                parameter.grad is None
                for parameter
                in self.model.parameters()
            )
        )


if __name__ == "__main__":
    unittest.main()
