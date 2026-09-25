import ast
import unittest
from pathlib import Path

from src.api import app


REQUIRED_ROUTES = {
    "/status",
    "/latest",
    "/events",
    "/plants/{plant_id}",
    "/model/info",
    "/inference",
    "/sensors",
}


class TestAIGatewayAPIContract(
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

        self.assertTrue(
            REQUIRED_ROUTES.issubset(
                routes
            )
        )


    def test_openapi_schema_generates(self):

        schema = app.openapi()

        self.assertIsInstance(
            schema,
            dict,
        )

        self.assertIn(
            "openapi",
            schema,
        )

        self.assertIn(
            "paths",
            schema,
        )


    def test_required_routes_documented_in_openapi(self):

        schema = app.openapi()

        paths = set(
            schema[
                "paths"
            ]
        )

        self.assertTrue(
            REQUIRED_ROUTES.issubset(
                paths
            )
        )


    def test_fastapi_application_is_versioned(self):

        self.assertIsInstance(
            app.version,
            str,
        )

        self.assertTrue(
            app.version.strip()
        )


    def test_api_does_not_directly_import_vision_model(self):

        path = Path(
            "src/api.py"
        )

        tree = ast.parse(
            path.read_text(
                encoding="utf-8-sig"
            )
        )

        direct_import = False

        for node in tree.body:

            if isinstance(
                node,
                ast.ImportFrom,
            ):

                if (
                    node.module
                    == "src.vision_inference"
                ):

                    direct_import = True

        self.assertFalse(
            direct_import
        )


    def test_api_has_no_legacy_get_vision_factory(self):

        text = Path(
            "src/api.py"
        ).read_text(
            encoding="utf-8-sig"
        )

        self.assertNotIn(
            "def get_vision(",
            text,
        )

        self.assertNotIn(
            "get_vision().predict",
            text,
        )


    def test_gateway_service_is_used(self):

        text = Path(
            "src/api.py"
        ).read_text(
            encoding="utf-8-sig"
        )

        self.assertIn(
            "run_diagnostic_vision",
            text,
        )

        self.assertIn(
            "get_recent_event_view",
            text,
        )

        self.assertIn(
            "get_recent_sensor_view",
            text,
        )

        self.assertIn(
            "get_model_registry_info",
            text,
        )


    def test_model_info_endpoint_does_not_require_model_load(self):

        from src.api import model_info

        result = model_info()

        self.assertIn(
            "schema_version",
            result,
        )

        self.assertFalse(
            result[
                "actuation_authorized"
            ]
        )

        self.assertFalse(
            result[
                "scientific_guardrails"
            ][
                "model_files_loaded"
            ]
        )


    def test_model_info_exposes_no_artifact_paths(self):

        from src.api import model_info

        result = model_info()

        serialized = str(
            result
        ).lower()

        self.assertNotIn(
            "pytorch_path",
            serialized,
        )

        self.assertNotIn(
            "onnx_path",
            serialized,
        )


    def test_gateway_contract_never_authorizes_physical_action(self):

        from src.api import model_info

        result = model_info()

        self.assertFalse(
            result[
                "scientific_guardrails"
            ][
                "physical_action_authorized"
            ]
        )


if __name__ == "__main__":
    unittest.main()