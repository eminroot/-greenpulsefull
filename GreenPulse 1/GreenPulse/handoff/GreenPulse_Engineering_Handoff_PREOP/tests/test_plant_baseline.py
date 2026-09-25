import unittest

import numpy as np

from src.plant_baseline import (
    build_plant_baseline,
    compute_plant_delta,
)

from src.visual_features import (
    extract_visual_features,
)


def make_visual(
    value,
    confidence=0.9,
    leaf_mask=None,
    affected_mask=None,
):

    image = np.full(
        (12, 12, 3),
        value,
        dtype=np.uint8,
    )

    return extract_visual_features(
        image,
        visual_confidence=confidence,
        confidence_source="classification",
        leaf_mask=leaf_mask,
        affected_mask=affected_mask,
    )


class TestPlantBaseline(unittest.TestCase):

    def test_requires_exactly_one_identity(self):

        with self.assertRaises(
            ValueError
        ):
            build_plant_baseline(
                [],
            )

        with self.assertRaises(
            ValueError
        ):
            build_plant_baseline(
                [],
                plant_id="P01",
                cohort_id="C01",
            )


    def test_insufficient_healthy_observations_blocked(self):

        observations = [
            {
                "observation_id": "O1",
                "plant_id": "P01",
                "is_healthy": True,
                "visual_features": make_visual(100),
            },
            {
                "observation_id": "O2",
                "plant_id": "P01",
                "is_healthy": True,
                "visual_features": make_visual(105),
            },
        ]

        with self.assertRaises(
            ValueError
        ):
            build_plant_baseline(
                observations,
                plant_id="P01",
                min_healthy_observations=3,
            )


    def test_unhealthy_observations_not_used(self):

        observations = [
            {
                "observation_id": "H1",
                "plant_id": "P01",
                "is_healthy": True,
                "visual_features": make_visual(100),
            },
            {
                "observation_id": "H2",
                "plant_id": "P01",
                "is_healthy": True,
                "visual_features": make_visual(100),
            },
            {
                "observation_id": "H3",
                "plant_id": "P01",
                "is_healthy": True,
                "visual_features": make_visual(100),
            },
            {
                "observation_id": "S1",
                "plant_id": "P01",
                "is_healthy": False,
                "visual_features": make_visual(250),
            },
        ]

        baseline = build_plant_baseline(
            observations,
            plant_id="P01",
        )

        self.assertEqual(
            baseline[
                "healthy_observation_count"
            ],
            3,
        )

        self.assertEqual(
            baseline[
                "provenance"
            ][
                "observation_ids"
            ],
            ["H1", "H2", "H3"],
        )


    def test_plant_filter_is_enforced(self):

        observations = []

        for i in range(3):

            observations.append({
                "observation_id": f"P01_{i}",
                "plant_id": "P01",
                "is_healthy": True,
                "visual_features": make_visual(100),
            })

            observations.append({
                "observation_id": f"P02_{i}",
                "plant_id": "P02",
                "is_healthy": True,
                "visual_features": make_visual(220),
            })

        baseline = build_plant_baseline(
            observations,
            plant_id="P01",
        )

        self.assertEqual(
            baseline[
                "healthy_observation_count"
            ],
            3,
        )

        self.assertTrue(
            all(
                item.startswith("P01_")
                for item in baseline[
                    "provenance"
                ][
                    "observation_ids"
                ]
            )
        )


    def test_identical_current_observation_has_zero_delta(self):

        visual = make_visual(
            120,
            confidence=0.8,
        )

        observations = [
            {
                "observation_id": f"O{i}",
                "plant_id": "P01",
                "is_healthy": True,
                "visual_features": visual,
            }
            for i in range(3)
        ]

        baseline = build_plant_baseline(
            observations,
            plant_id="P01",
        )

        delta = compute_plant_delta(
            visual,
            baseline,
        )

        self.assertAlmostEqual(
            delta[
                "color_delta"
            ][
                "score"
            ],
            0.0,
            places=12,
        )

        self.assertAlmostEqual(
            delta[
                "texture_delta"
            ][
                "score"
            ],
            0.0,
            places=12,
        )

        self.assertAlmostEqual(
            delta[
                "confidence_delta"
            ][
                "absolute"
            ],
            0.0,
            places=12,
        )


    def test_changed_image_produces_positive_color_delta(self):

        observations = [
            {
                "observation_id": f"O{i}",
                "plant_id": "P01",
                "is_healthy": True,
                "visual_features": make_visual(40),
            }
            for i in range(3)
        ]

        baseline = build_plant_baseline(
            observations,
            plant_id="P01",
        )

        current = make_visual(
            220
        )

        delta = compute_plant_delta(
            current,
            baseline,
        )

        self.assertGreater(
            delta[
                "color_delta"
            ][
                "score"
            ],
            0.0,
        )


    def test_affected_area_delta_unavailable_without_validated_masks(self):

        observations = [
            {
                "observation_id": f"O{i}",
                "plant_id": "P01",
                "is_healthy": True,
                "visual_features": make_visual(100),
            }
            for i in range(3)
        ]

        baseline = build_plant_baseline(
            observations,
            plant_id="P01",
        )

        current = make_visual(
            120
        )

        delta = compute_plant_delta(
            current,
            baseline,
        )

        self.assertFalse(
            delta[
                "affected_area_delta"
            ][
                "available"
            ]
        )

        self.assertIsNone(
            delta[
                "affected_area_delta"
            ][
                "absolute"
            ]
        )


    def test_affected_area_delta_with_validated_masks(self):

        leaf = np.ones(
            (12, 12),
            dtype=bool,
        )

        healthy_affected = np.zeros(
            (12, 12),
            dtype=bool,
        )

        healthy_affected[
            0,
            :6
        ] = True

        current_affected = np.zeros(
            (12, 12),
            dtype=bool,
        )

        current_affected[
            :3,
            :
        ] = True

        observations = [
            {
                "observation_id": f"O{i}",
                "plant_id": "P01",
                "is_healthy": True,
                "visual_features": make_visual(
                    100,
                    leaf_mask=leaf,
                    affected_mask=healthy_affected,
                ),
            }
            for i in range(3)
        ]

        baseline = build_plant_baseline(
            observations,
            plant_id="P01",
        )

        current = make_visual(
            100,
            leaf_mask=leaf,
            affected_mask=current_affected,
        )

        delta = compute_plant_delta(
            current,
            baseline,
        )

        self.assertTrue(
            delta[
                "affected_area_delta"
            ][
                "available"
            ]
        )

        self.assertGreater(
            delta[
                "affected_area_delta"
            ][
                "absolute"
            ],
            0.0,
        )


    def test_baseline_is_reproducible_across_input_order(self):

        observations = [
            {
                "observation_id": "O1",
                "plant_id": "P01",
                "is_healthy": True,
                "visual_features": make_visual(
                    90,
                    confidence=0.7,
                ),
            },
            {
                "observation_id": "O2",
                "plant_id": "P01",
                "is_healthy": True,
                "visual_features": make_visual(
                    120,
                    confidence=0.8,
                ),
            },
            {
                "observation_id": "O3",
                "plant_id": "P01",
                "is_healthy": True,
                "visual_features": make_visual(
                    150,
                    confidence=0.9,
                ),
            },
        ]

        a = build_plant_baseline(
            observations,
            plant_id="P01",
        )

        b = build_plant_baseline(
            list(
                reversed(
                    observations
                )
            ),
            plant_id="P01",
        )

        self.assertEqual(
            a[
                "color_baseline"
            ],
            b[
                "color_baseline"
            ],
        )

        self.assertEqual(
            a[
                "texture_baseline"
            ],
            b[
                "texture_baseline"
            ],
        )

        self.assertEqual(
            a[
                "confidence_baseline"
            ],
            b[
                "confidence_baseline"
            ],
        )


if __name__ == "__main__":
    unittest.main()