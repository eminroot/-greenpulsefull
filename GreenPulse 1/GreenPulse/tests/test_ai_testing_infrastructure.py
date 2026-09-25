import copy
import sqlite3
import unittest

from src.ai_testing_infrastructure import (
    EXPECTED_REFERENCE_BEHAVIOR,
    REFERENCE_FIXTURE_VERSION,
    SCHEMA_VERSION,
    STAGE_ORDER,
    load_reference_fixture,
    run_reference_e2e,
)

from src.data_logging_audit import (
    initialize_audit_schema,
)


FIXTURE = (
    "tests/fixtures/"
    "layer49_reference_input_v1.json"
)


class TestAITestingInfrastructure(
    unittest.TestCase
):

    def setUp(self):

        self.reference = (
            load_reference_fixture(
                FIXTURE
            )
        )


    def new_connection(self):

        conn = sqlite3.connect(
            ":memory:"
        )

        initialize_audit_schema(
            conn
        )

        return conn


    def test_schema_version(self):

        self.assertEqual(
            SCHEMA_VERSION,
            "greenpulse.ai_testing_infrastructure.v1",
        )


    def test_reference_fixture_version(self):

        self.assertEqual(
            self.reference[
                "schema_version"
            ],
            REFERENCE_FIXTURE_VERSION,
        )


    def test_reference_sensor_is_simulated(self):

        self.assertEqual(
            self.reference[
                "sensor"
            ][
                "source"
            ],
            "SIMULATED",
        )


    def test_stage_order_exact(self):

        self.assertEqual(
            STAGE_ORDER,
            (
                "image",
                "yolo",
                "fusion",
                "risk",
                "forecast",
                "decision",
                "api",
                "database",
                "simulated_hardware",
            ),
        )


    def test_complete_reference_e2e_runs(self):

        conn = self.new_connection()

        try:

            result = run_reference_e2e(
                conn,
                self.reference,
            )

        finally:

            conn.close()


        self.assertEqual(
            result[
                "stage_order"
            ],
            list(
                STAGE_ORDER
            ),
        )


    def test_yolo_stage_is_explicit_test_double(self):

        conn = self.new_connection()

        try:

            result = run_reference_e2e(
                conn,
                self.reference,
            )

        finally:

            conn.close()


        vision = result[
            "behavior"
        ][
            "vision"
        ]


        self.assertEqual(
            vision[
                "execution_mode"
            ],
            "DETERMINISTIC_TEST_DOUBLE",
        )

        self.assertFalse(
            vision[
                "real_model_inference"
            ]
        )


    def test_database_command_trace_complete(self):

        conn = self.new_connection()

        try:

            result = run_reference_e2e(
                conn,
                self.reference,
            )


            self.assertTrue(
                result[
                    "database"
                ][
                    "required_lineage_complete"
                ]
            )


            command_count = conn.execute(
                """
                SELECT COUNT(*)
                FROM commands
                """
            ).fetchone()[0]


            self.assertEqual(
                command_count,
                1,
            )


        finally:

            conn.close()


    def test_api_precedes_database_and_hardware(self):

        stages = list(
            STAGE_ORDER
        )


        self.assertLess(
            stages.index(
                "api"
            ),
            stages.index(
                "database"
            ),
        )

        self.assertLess(
            stages.index(
                "database"
            ),
            stages.index(
                "simulated_hardware"
            ),
        )


    def test_simulated_hardware_never_claims_physical_actuation(self):

        conn = self.new_connection()

        try:

            result = run_reference_e2e(
                conn,
                self.reference,
            )

        finally:

            conn.close()


        hardware = result[
            "behavior"
        ][
            "hardware"
        ]


        self.assertEqual(
            hardware[
                "status"
            ],
            "SIMULATED_ACK",
        )

        self.assertFalse(
            hardware[
                "physical_actuation"
            ]
        )


    def test_fixed_reference_regression_behavior(self):

        conn = self.new_connection()

        try:

            result = run_reference_e2e(
                conn,
                self.reference,
            )

        finally:

            conn.close()


        self.assertEqual(
            result[
                "behavior"
            ],
            EXPECTED_REFERENCE_BEHAVIOR,
        )


    def test_reference_run_is_deterministic(self):

        conn1 = self.new_connection()
        conn2 = self.new_connection()


        try:

            first = run_reference_e2e(
                conn1,
                self.reference,
            )

            second = run_reference_e2e(
                conn2,
                self.reference,
            )

        finally:

            conn1.close()
            conn2.close()


        self.assertEqual(
            first[
                "behavior"
            ],
            second[
                "behavior"
            ],
        )

        self.assertEqual(
            first[
                "stage_order"
            ],
            second[
                "stage_order"
            ],
        )


    def test_reference_input_not_mutated_and_real_execution_blocked(self):

        original = copy.deepcopy(
            self.reference
        )

        conn = self.new_connection()


        try:

            result = run_reference_e2e(
                conn,
                self.reference,
            )

        finally:

            conn.close()


        self.assertEqual(
            self.reference,
            original,
        )


        boundary = result[
            "execution_boundary"
        ]


        self.assertFalse(
            boundary[
                "real_yolo_inference"
            ]
        )

        self.assertFalse(
            boundary[
                "real_hardware_actuation"
            ]
        )


    def test_non_simulated_sensor_rejected(self):

        reference = copy.deepcopy(
            self.reference
        )

        reference[
            "sensor"
        ][
            "source"
        ] = "REAL"


        conn = self.new_connection()


        try:

            with self.assertRaises(
                ValueError
            ):

                run_reference_e2e(
                    conn,
                    reference,
                )

        finally:

            conn.close()


if __name__ == "__main__":
    unittest.main()