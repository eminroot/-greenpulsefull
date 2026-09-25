from __future__ import annotations

from pathlib import Path
from typing import Any

import ast


SCHEMA_VERSION = (
    "greenpulse.resource_architecture_guard.v1"
)


BANNED_LLM_IMPORT_PREFIXES = (
    "transformers",
    "langchain",
    "llama_cpp",
    "ollama",
)


VIDEO_BUFFER_TOKENS = (
    "VideoCapture",
    "video_buffer",
    "frame_buffer",
    "read_video",
    "frames.append",
)


def _read_python_tree(
    path: Path,
) -> ast.AST:

    return ast.parse(
        path.read_text(
            encoding="utf-8-sig"
        )
    )


def _imports_from_tree(
    tree: ast.AST,
) -> set[str]:

    imports = set()


    for node in ast.walk(
        tree
    ):

        if isinstance(
            node,
            ast.Import,
        ):

            for alias in node.names:

                imports.add(
                    alias.name
                )


        elif isinstance(
            node,
            ast.ImportFrom,
        ):

            if node.module:

                imports.add(
                    node.module
                )


    return imports


def _default_window_size(
    tree: ast.AST,
) -> int | None:

    for node in ast.walk(
        tree
    ):

        if not isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            ),
        ):

            continue


        positional_args = (
            list(
                node.args.posonlyargs
            )
            + list(
                node.args.args
            )
        )

        positional_defaults = list(
            node.args.defaults
        )


        if positional_defaults:

            offset = (
                len(
                    positional_args
                )
                - len(
                    positional_defaults
                )
            )


            for index, default in enumerate(
                positional_defaults
            ):

                arg = positional_args[
                    offset
                    + index
                ]


                if (
                    arg.arg
                    == "window_size"
                    and isinstance(
                        default,
                        ast.Constant,
                    )
                    and isinstance(
                        default.value,
                        int,
                    )
                ):

                    return int(
                        default.value
                    )


        for arg, default in zip(
            node.args.kwonlyargs,
            node.args.kw_defaults,
        ):

            if (
                arg.arg
                == "window_size"
                and isinstance(
                    default,
                    ast.Constant,
                )
                and isinstance(
                    default.value,
                    int,
                )
            ):

                return int(
                    default.value
                )


    return None


def _video_usage_hits(
    tree: ast.AST,
    relative_file: str,
) -> list[dict[str, str]]:

    hits = []


    watched_names = {
        "VideoCapture",
        "video_buffer",
        "frame_buffer",
        "read_video",
    }


    for node in ast.walk(
        tree
    ):

        token = None


        if (
            isinstance(
                node,
                ast.Name,
            )
            and node.id
            in watched_names
        ):

            token = node.id


        elif (
            isinstance(
                node,
                ast.Attribute,
            )
            and node.attr
            in watched_names
        ):

            token = node.attr


        elif (
            isinstance(
                node,
                ast.Attribute,
            )
            and node.attr
            == "append"
            and isinstance(
                node.value,
                ast.Name,
            )
            and node.value.id
            == "frames"
        ):

            token = "frames.append"


        if token is not None:

            hit = {
                "file":
                    relative_file,

                "token":
                    token,
            }


            if hit not in hits:

                hits.append(
                    hit
                )


    return hits


def assess_resource_architecture(
    root: Path,
) -> dict[str, Any]:

    root = Path(
        root
    ).resolve()


    src = (
        root
        / "src"
    )


    if not src.is_dir():

        raise FileNotFoundError(
            "src directory missing."
        )


    python_files = sorted(
        path

        for path in src.rglob(
            "*.py"
        )

        if path.is_file()
    )


    all_imports = set()

    video_hits = []

    llm_import_hits = []


    for path in python_files:

        text = path.read_text(
            encoding="utf-8-sig",
            errors="ignore",
        )

        tree = ast.parse(
            text
        )

        imports = _imports_from_tree(
            tree
        )

        all_imports.update(
            imports
        )


        for imported in imports:

            if any(
                imported == prefix
                or imported.startswith(
                    prefix + "."
                )

                for prefix
                in BANNED_LLM_IMPORT_PREFIXES
            ):

                llm_import_hits.append(
                    {
                        "file":
                            str(
                                path.relative_to(
                                    root
                                )
                            ).replace(
                                "\\",
                                "/",
                            ),

                        "import":
                            imported,
                    }
                )


        relative_file = str(
            path.relative_to(
                root
            )
        ).replace(
            "\\",
            "/",
        )


        video_hits.extend(
            _video_usage_hits(
                tree,
                relative_file,
            )
        )


    temporal_path = (
        src
        / "temporal_intelligence.py"
    )


    temporal_window = None


    if temporal_path.is_file():

        temporal_window = (
            _default_window_size(
                _read_python_tree(
                    temporal_path
                )
            )
        )


    single_frame_supported = (
        len(
            video_hits
        )
        == 0
    )


    no_large_video_buffer = (
        len(
            video_hits
        )
        == 0
    )


    small_temporal_buffer = (
        temporal_window
        is not None
        and 3
        <= temporal_window
        <= 10
    )


    sqlite_present = any(
        imported == "sqlite3"

        for imported
        in all_imports
    )


    fastapi_present = any(
        imported == "fastapi"
        or imported.startswith(
            "fastapi."
        )

        for imported
        in all_imports
    )


    local_llm_absent = (
        len(
            llm_import_hits
        )
        == 0
    )


    software_guard_pass = all(
        (
            single_frame_supported,
            no_large_video_buffer,
            small_temporal_buffer,
            sqlite_present,
            fastapi_present,
            local_llm_absent,
        )
    )


    return {
        "schema_version":
            SCHEMA_VERSION,

        "python_file_count":
            len(
                python_files
            ),

        "single_frame_architecture_supported":
            single_frame_supported,

        "large_video_buffer_detected":
            not no_large_video_buffer,

        "video_buffer_hits":
            video_hits,

        "temporal_window_default":
            temporal_window,

        "small_temporal_buffer_verified":
            small_temporal_buffer,

        "sqlite_present":
            sqlite_present,

        "fastapi_present":
            fastapi_present,

        "local_llm_import_detected":
            not local_llm_absent,

        "local_llm_import_hits":
            llm_import_hits,

        "software_resource_guard_pass":
            software_guard_pass,

        "runtime_ram_acceptance_verified":
            False,

        "raspberry_pi_5_measured":
            False,

        "hailo_runtime_measured":
            False,

        "layer42_complete":
            False,

        "scientific_guardrails": {
            "source_scan_equals_runtime_ram_proof":
                False,

            "desktop_source_scan_equals_pi5_validation":
                False,

            "absence_of_video_api_equals_complete_memory_proof":
                False,

            "software_guard_pass_equals_under_3gb_acceptance":
                False,
        },
    }