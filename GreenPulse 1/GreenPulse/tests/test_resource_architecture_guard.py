import tempfile
import unittest
from pathlib import Path

from src.resource_architecture_guard import (
    SCHEMA_VERSION,
    assess_resource_architecture,
)


def make_repo(
    root,
    *,
    temporal_window=5,
    llm=False,
    video=False,
):

    root = Path(
        root
    )

    src = (
        root
        / "src"
    )

    src.mkdir(
        parents=True
    )


    (
        src
        / "api.py"
    ).write_text(
        "import sqlite3\n"
        "from fastapi import FastAPI\n",
        encoding="utf-8",
    )


    (
        src
        / "temporal_intelligence.py"
    ).write_text(
        (
            "def analyze(window_size="
            + str(
                temporal_window
            )
            + "):\n"
            "    return window_size\n"
        ),
        encoding="utf-8",
    )


    extra = ""


    if llm:

        extra += (
            "from transformers import AutoModel\n"
        )


    if video:

        extra += (
            "video_buffer = []\n"
        )


    (
        src
        / "pipeline.py"
    ).write_text(
        extra
        + "def run():\n"
        + "    return None\n",
        encoding="utf-8",
    )


class TestResourceArchitectureGuard(
    unittest.TestCase
):

    def test_schema_version(self):

        self.assertEqual(
            SCHEMA_VERSION,
            "greenpulse.resource_architecture_guard.v1",
        )


    def test_clean_lightweight_architecture_passes(self):

        with tempfile.TemporaryDirectory() as tmp:

            make_repo(
                tmp
            )

            result = assess_resource_architecture(
                Path(
                    tmp
                )
            )


        self.assertTrue(
            result[
                "software_resource_guard_pass"
            ]
        )


    def test_small_temporal_window_verified(self):

        with tempfile.TemporaryDirectory() as tmp:

            make_repo(
                tmp,
                temporal_window=5,
            )

            result = assess_resource_architecture(
                Path(
                    tmp
                )
            )


        self.assertEqual(
            result[
                "temporal_window_default"
            ],
            5,
        )

        self.assertTrue(
            result[
                "small_temporal_buffer_verified"
            ]
        )


    def test_large_temporal_window_fails_guard(self):

        with tempfile.TemporaryDirectory() as tmp:

            make_repo(
                tmp,
                temporal_window=1000,
            )

            result = assess_resource_architecture(
                Path(
                    tmp
                )
            )


        self.assertFalse(
            result[
                "small_temporal_buffer_verified"
            ]
        )

        self.assertFalse(
            result[
                "software_resource_guard_pass"
            ]
        )


    def test_llm_import_detected(self):

        with tempfile.TemporaryDirectory() as tmp:

            make_repo(
                tmp,
                llm=True,
            )

            result = assess_resource_architecture(
                Path(
                    tmp
                )
            )


        self.assertTrue(
            result[
                "local_llm_import_detected"
            ]
        )

        self.assertFalse(
            result[
                "software_resource_guard_pass"
            ]
        )


    def test_video_buffer_detected(self):

        with tempfile.TemporaryDirectory() as tmp:

            make_repo(
                tmp,
                video=True,
            )

            result = assess_resource_architecture(
                Path(
                    tmp
                )
            )


        self.assertTrue(
            result[
                "large_video_buffer_detected"
            ]
        )

        self.assertFalse(
            result[
                "software_resource_guard_pass"
            ]
        )


    def test_sqlite_required(self):

        with tempfile.TemporaryDirectory() as tmp:

            make_repo(
                tmp
            )

            (
                Path(
                    tmp
                )
                / "src"
                / "api.py"
            ).write_text(
                "from fastapi import FastAPI\n",
                encoding="utf-8",
            )

            result = assess_resource_architecture(
                Path(
                    tmp
                )
            )


        self.assertFalse(
            result[
                "sqlite_present"
            ]
        )


    def test_fastapi_required(self):

        with tempfile.TemporaryDirectory() as tmp:

            make_repo(
                tmp
            )

            (
                Path(
                    tmp
                )
                / "src"
                / "api.py"
            ).write_text(
                "import sqlite3\n",
                encoding="utf-8",
            )

            result = assess_resource_architecture(
                Path(
                    tmp
                )
            )


        self.assertFalse(
            result[
                "fastapi_present"
            ]
        )


    def test_source_guard_never_claims_runtime_acceptance(self):

        with tempfile.TemporaryDirectory() as tmp:

            make_repo(
                tmp
            )

            result = assess_resource_architecture(
                Path(
                    tmp
                )
            )


        self.assertFalse(
            result[
                "runtime_ram_acceptance_verified"
            ]
        )

        self.assertFalse(
            result[
                "layer42_complete"
            ]
        )



    def test_keyword_only_temporal_window_detected(self):

        with tempfile.TemporaryDirectory() as tmp:

            root = Path(
                tmp
            )

            src = (
                root
                / "src"
            )

            src.mkdir(
                parents=True
            )


            (
                src
                / "api.py"
            ).write_text(
                "import sqlite3\n"
                "from fastapi import FastAPI\n",
                encoding="utf-8",
            )


            (
                src
                / "temporal_intelligence.py"
            ).write_text(
                "def analyze(*, window_size: int = 5):\n"
                "    return window_size\n",
                encoding="utf-8",
            )


            (
                src
                / "pipeline.py"
            ).write_text(
                "def run():\n"
                "    return None\n",
                encoding="utf-8",
            )


            result = assess_resource_architecture(
                root
            )


        self.assertEqual(
            result[
                "temporal_window_default"
            ],
            5,
        )

        self.assertTrue(
            result[
                "small_temporal_buffer_verified"
            ]
        )


    def test_video_terms_inside_strings_do_not_count_as_buffer(self):

        with tempfile.TemporaryDirectory() as tmp:

            root = Path(
                tmp
            )

            src = (
                root
                / "src"
            )

            src.mkdir(
                parents=True
            )


            (
                src
                / "api.py"
            ).write_text(
                "import sqlite3\n"
                "from fastapi import FastAPI\n",
                encoding="utf-8",
            )


            (
                src
                / "temporal_intelligence.py"
            ).write_text(
                "def analyze(*, window_size: int = 5):\n"
                "    return window_size\n",
                encoding="utf-8",
            )


            (
                src
                / "pipeline.py"
            ).write_text(
                'TERMS = ("video_buffer", "frame_buffer")\n'
                "def run():\n"
                "    return TERMS\n",
                encoding="utf-8",
            )


            result = assess_resource_architecture(
                root
            )


        self.assertFalse(
            result[
                "large_video_buffer_detected"
            ]
        )

        self.assertTrue(
            result[
                "single_frame_architecture_supported"
            ]
        )


if __name__ == "__main__":
    unittest.main()