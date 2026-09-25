import unittest

import numpy as np

from src.visual_features import (
    FEATURE_VECTOR_NAMES,
    build_visual_baseline_signature,
    extract_visual_features,
)


class TestVisualFeatures(unittest.TestCase):

    def test_feature_vector_schema_is_stable(self):

        image = np.full(
            (16, 16, 3),
            128,
            dtype=np.uint8,
        )

        result = extract_visual_features(
            image,
            visual_confidence=0.9,
            confidence_source="classification",
        )

        self.assertEqual(
            result["feature_vector"]["length"],
            len(FEATURE_VECTOR_NAMES),
        )

        self.assertEqual(
            result["feature_vector"]["names"],
            FEATURE_VECTOR_NAMES,
        )

        self.assertTrue(
            np.all(
                np.isfinite(
                    result[
                        "feature_vector"
                    ][
                        "values"
                    ]
                )
            )
        )


    def test_constant_rgb_statistics(self):

        image = np.zeros(
            (10, 10, 3),
            dtype=np.uint8,
        )

        image[
            ...,
            0
        ] = 255

        result = extract_visual_features(
            image,
            visual_confidence=0.75,
            confidence_source="classification",
        )

        rgb_mean = result[
            "color_statistics"
        ][
            "rgb_mean"
        ]

        self.assertAlmostEqual(
            rgb_mean[0],
            1.0,
            places=8,
        )

        self.assertAlmostEqual(
            rgb_mean[1],
            0.0,
            places=8,
        )

        self.assertAlmostEqual(
            rgb_mean[2],
            0.0,
            places=8,
        )


    def test_affected_leaf_area_ratio(self):

        image = np.full(
            (4, 4, 3),
            100,
            dtype=np.uint8,
        )

        leaf = np.zeros(
            (4, 4),
            dtype=bool,
        )

        leaf[
            :2,
            :
        ] = True

        affected = np.zeros(
            (4, 4),
            dtype=bool,
        )

        affected[
            0,
            :
        ] = True

        result = extract_visual_features(
            image,
            visual_confidence=0.8,
            confidence_source="future_detection",
            leaf_mask=leaf,
            affected_mask=affected,
        )

        area = result[
            "affected_area"
        ]

        self.assertTrue(
            area[
                "affected_leaf_area_available"
            ]
        )

        self.assertAlmostEqual(
            area[
                "affected_leaf_area_ratio"
            ],
            0.5,
            places=8,
        )

        self.assertEqual(
            area[
                "source"
            ],
            "VALIDATED_LEAF_AND_AFFECTED_MASKS",
        )


    def test_no_fake_leaf_ratio_without_leaf_mask(self):

        image = np.full(
            (4, 4, 3),
            100,
            dtype=np.uint8,
        )

        affected = np.zeros(
            (4, 4),
            dtype=bool,
        )

        affected[
            :2,
            :
        ] = True

        result = extract_visual_features(
            image,
            visual_confidence=0.8,
            confidence_source="classification",
            affected_mask=affected,
        )

        area = result[
            "affected_area"
        ]

        self.assertIsNone(
            area[
                "affected_leaf_area_ratio"
            ]
        )

        self.assertFalse(
            area[
                "affected_leaf_area_available"
            ]
        )

        self.assertAlmostEqual(
            area[
                "affected_image_area_ratio"
            ],
            0.5,
            places=8,
        )


    def test_identical_baseline_has_zero_change(self):

        image = np.full(
            (20, 20, 3),
            160,
            dtype=np.uint8,
        )

        first = extract_visual_features(
            image,
            visual_confidence=0.95,
            confidence_source="classification",
        )

        baseline = build_visual_baseline_signature(
            first
        )

        second = extract_visual_features(
            image,
            visual_confidence=0.95,
            confidence_source="classification",
            baseline_signature=baseline,
        )

        change = second[
            "relative_visual_change"
        ]

        self.assertTrue(
            change[
                "available"
            ]
        )

        self.assertAlmostEqual(
            change[
                "score"
            ],
            0.0,
            places=12,
        )


    def test_changed_image_has_positive_change(self):

        baseline_image = np.full(
            (20, 20, 3),
            50,
            dtype=np.uint8,
        )

        changed_image = np.full(
            (20, 20, 3),
            220,
            dtype=np.uint8,
        )

        first = extract_visual_features(
            baseline_image,
            visual_confidence=0.9,
            confidence_source="classification",
        )

        baseline = build_visual_baseline_signature(
            first
        )

        second = extract_visual_features(
            changed_image,
            visual_confidence=0.9,
            confidence_source="classification",
            baseline_signature=baseline,
        )

        self.assertGreater(
            second[
                "relative_visual_change"
            ][
                "score"
            ],
            0.0,
        )


    def test_invalid_confidence_is_blocked(self):

        image = np.full(
            (10, 10, 3),
            100,
            dtype=np.uint8,
        )

        with self.assertRaises(
            ValueError
        ):
            extract_visual_features(
                image,
                visual_confidence=1.5,
                confidence_source="classification",
            )


    def test_invalid_roi_is_blocked(self):

        image = np.full(
            (10, 10, 3),
            100,
            dtype=np.uint8,
        )

        with self.assertRaises(
            ValueError
        ):
            extract_visual_features(
                image,
                visual_confidence=0.5,
                confidence_source="classification",
                roi_xyxy=(5, 5, 3, 9),
            )


if __name__ == "__main__":
    unittest.main()
