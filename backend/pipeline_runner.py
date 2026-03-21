"""Lightweight orchestrator to run the existing fungal ModelSEED pipeline steps.

This module wraps the CLI scripts under ``scripts/`` so they can be invoked from
the FastAPI service. It keeps everything local and avoids adding new project
files outside ``data/``.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import List, Sequence


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
DATA_DIR = PROJECT_ROOT / "data"
RAW_UPLOADS_DIR = DATA_DIR / "raw" / "uploads"


@dataclass
class StepResult:
    name: str
    cmd: str
    returncode: int
    stdout: str
    stderr: str

    @property
    def succeeded(self) -> bool:
        return self.returncode == 0


class PipelineRunner:
    """Orchestrate the scripted pipeline for a protein FASTA input."""

    def __init__(self, use_rast: bool = True):
        self.use_rast = use_rast
        RAW_UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _run_step(name: str, cmd: Sequence[str]) -> StepResult:
        process = subprocess.run(
            cmd,
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
        )
        return StepResult(
            name=name,
            cmd=" ".join(cmd),
            returncode=process.returncode,
            stdout=process.stdout,
            stderr=process.stderr,
        )

    def run(self, input_faa: Path, model_id: str) -> List[StepResult]:
        python = sys.executable
        model_dir = DATA_DIR / "models" / model_id
        steps: List[StepResult] = []

        media_library = PROJECT_ROOT / "config" / "media_library.yml"

        commands: list[tuple[str, List[str]]] = [
            (
                "prepare_input",
                [python, str(SCRIPTS_DIR / "prepare_input.py"), "--input", str(input_faa)],
            ),
            (
                "first_modelseed_step",
                [
                    python,
                    str(SCRIPTS_DIR / "first_modelseed_step.py"),
                    "--input",
                    str(input_faa),
                    *(["--use-rast"] if self.use_rast else []),
                ],
            ),
            (
                "build_draft_model",
                [
                    python,
                    str(SCRIPTS_DIR / "build_draft_model.py"),
                    "--input",
                    str(input_faa),
                    "--model-id",
                    model_id,
                    *(["--use-rast"] if self.use_rast else []),
                ],
            ),
            (
                "gapfill_and_export_model",
                [
                    python,
                    str(SCRIPTS_DIR / "gapfill_and_export_model.py"),
                    "--model-dir",
                    str(model_dir),
                ],
            ),
            (
                "inspect_with_cobra",
                [
                    python,
                    str(SCRIPTS_DIR / "inspect_with_cobra.py"),
                    "--model-dir",
                    str(model_dir),
                ],
            ),
            (
                "screen_media",
                [
                    python,
                    str(SCRIPTS_DIR / "screen_media.py"),
                    "--model-dir",
                    str(model_dir),
                    "--media",
                    str(media_library),
                ],
            ),
            (
                "diagnose_exchange_space",
                [
                    python,
                    str(SCRIPTS_DIR / "diagnose_exchange_space.py"),
                    "--model-dir",
                    str(model_dir),
                ],
            ),
            (
                "debug_growth",
                [
                    python,
                    str(SCRIPTS_DIR / "debug_growth.py"),
                    "--model-dir",
                    str(model_dir),
                ],
            ),
            (
                "run_oracle_growth",
                [
                    python,
                    str(SCRIPTS_DIR / "run_oracle_growth.py"),
                    "--model-dir",
                    str(model_dir),
                ],
            ),
            (
                "screen_oracle_medium",
                [
                    python,
                    str(SCRIPTS_DIR / "screen_oracle_medium.py"),
                    "--model-dir",
                    str(model_dir),
                ],
            ),
            (
                "benchmark_bio2",
                [
                    python,
                    str(SCRIPTS_DIR / "benchmark_bio2.py"),
                    "--model-dir",
                    str(model_dir),
                ],
            ),
            (
                "inspect_oracle_condition",
                [
                    python,
                    str(SCRIPTS_DIR / "inspect_oracle_condition.py"),
                    "--model-dir",
                    str(model_dir),
                    "--condition",
                    "central_carbon_precursors",
                ],
            ),
        ]

        for name, cmd in commands:
            result = self._run_step(name, cmd)
            steps.append(result)
            if result.returncode != 0:
                break

        return steps


def save_upload(upload_path: Path, contents: bytes) -> Path:
    RAW_UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    upload_path.write_bytes(contents)
    return upload_path


def generate_model_id(prefix: str | None = None) -> str:
    base = prefix.strip().replace(" ", "_") if prefix else "model"
    return f"{base}_{uuid.uuid4().hex[:8]}"
