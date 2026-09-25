import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException

from src.api import (
    app,
    hardware_action,
    hardware_actions,
)

from src.hardware_ack_state import (
    normalize_simulated_ack,
)

from src.hardware_action_audit import (
    store_action_state,
)

from src.ai_gateway_service import (
    get_hardware_action_view,
    get_recent_hardware_action_view,
)


COMMAND_ID = (
    "123e4567-e89b-12d3-a456-426614174000"
)

OBSERVATION_ID = (
    "223e4567-e89b-12d3-a456-426614174000"
)


def canonical_state():

    return normalize_simulated_ack(
        {
            "simulator_version":
                "0.2.0",

            "command_id":
                COMMAND_ID,

            "observation_id":
                OBSERVATION_ID,

            "plant_id":
                "TEST-P01",

            "target":
                "MAIN_IRRIGATION_PUMP",

            "status":
                "SIMULATED_EXECUTED",

            "error_code":
                None,

            "timestamp":
                "2026-09-24T12:00:00+00:00",

            "simulated":
                True,

            "physical_actuation":
                False,

            "real_hardware_ack":
                None,
        }
    )


class TestHardwareActionBackend(
    unittest.TestCase
):

    def test_required_routes_exist(self):

        routes = {
            route.path
            for route in app.routes
            if hasattr(
                route,
                "path",
            )
        }

        self.assertIn(
            "/actions",
            routes,
        )

        self.assertIn(
            "/actions/{command_id}",
            routes,
        )


    def test_routes_are_documented_in_openapi(self):

        paths = app.openapi()[
            "paths"
        ]

        self.assertIn(
            "/actions",
            paths,
        )

        self.assertIn(
            "/actions/{command_id}",
            paths,
        )


    @patch(
        "src.api.get_recent_hardware_action_view"
    )
    def test_collection_endpoint_returns_gateway_contract(
        self,
        mock_view,
    ):

        mock_view.return_value = {
            "schema_version":
                (
                    "greenpulse."
                    "hardware_action_state_collection.v1"
                ),

            "count":
                0,

            "actions":
                [],

            "real_hardware_ack_validated":
                False,

            "physical_actuation_claimed":
                False,
        }

        result = hardware_actions(
            limit=20
        )

        self.assertEqual(
            result[
                "count"
            ],
            0,
        )

        self.assertFalse(
            result[
                "real_hardware_ack_validated"
            ]
        )


    @patch(
        "src.api.get_hardware_action_view"
    )
    def test_detail_endpoint_returns_gateway_contract(
        self,
        mock_view,
    ):

        mock_view.return_value = {
            "schema_version":
                (
                    "greenpulse."
                    "hardware_action_state_view.v1"
                ),

            "action": {
                "command_id":
                    COMMAND_ID,
            },

            "real_hardware_ack_validated":
                False,

            "physical_actuation_claimed":
                False,
        }

        result = hardware_action(
            COMMAND_ID
        )

        self.assertEqual(
            result[
                "action"
            ][
                "command_id"
            ],
            COMMAND_ID,
        )


    @patch(
        "src.api.get_hardware_action_view"
    )
    def test_missing_detail_returns_404(
        self,
        mock_view,
    ):

        mock_view.return_value = None

        with self.assertRaises(
            HTTPException
        ) as context:

            hardware_action(
                COMMAND_ID
            )

        self.assertEqual(
            context.exception.status_code,
            404,
        )


    def test_gateway_collection_reads_canonical_audit(
        self,
    ):

        with tempfile.TemporaryDirectory() as tmp:

            db = Path(tmp) / "audit.db"

            store_action_state(
                canonical_state(),
                db_path=db,
            )

            result = (
                get_recent_hardware_action_view(
                    limit=20,
                    database_path=db,
                )
            )

        self.assertEqual(
            result[
                "count"
            ],
            1,
        )

        self.assertEqual(
            result[
                "actions"
            ][0][
                "action_state"
            ],
            "EXECUTED",
        )


    def test_gateway_detail_reads_by_command_id(
        self,
    ):

        with tempfile.TemporaryDirectory() as tmp:

            db = Path(tmp) / "audit.db"

            store_action_state(
                canonical_state(),
                db_path=db,
            )

            result = get_hardware_action_view(
                COMMAND_ID,
                database_path=db,
            )

        self.assertEqual(
            result[
                "action"
            ][
                "command_id"
            ],
            COMMAND_ID,
        )


    def test_backend_preserves_simulation_truth(
        self,
    ):

        with tempfile.TemporaryDirectory() as tmp:

            db = Path(tmp) / "audit.db"

            store_action_state(
                canonical_state(),
                db_path=db,
            )

            result = get_hardware_action_view(
                COMMAND_ID,
                database_path=db,
            )

        action = result[
            "action"
        ]

        self.assertTrue(
            action[
                "simulated"
            ]
        )

        self.assertFalse(
            action[
                "real_hardware_ack_validated"
            ]
        )

        self.assertFalse(
            action[
                "physical_actuation"
            ]
        )


if __name__ == "__main__":
    unittest.main()