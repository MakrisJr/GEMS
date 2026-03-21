"""FastAPI app — GEM pipeline API.

The /run endpoint executes the 4-step default MVP pipeline and returns
model_id plus per-step status.  A /run/custom endpoint handles the optional
custom-condition step.  The /health endpoint remains unchanged.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .pipeline_runner import PipelineRunner, generate_model_id, save_upload


app = FastAPI(title="GEMS — Fungal GEM Pipeline API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Pydantic models ─────────────────────────────

class StepResponse(BaseModel):
    name: str
    cmd: str
    returncode: int
    stdout: str
    stderr: str
    succeeded: bool


class PipelineResponse(BaseModel):
    model_id: str
    mvp_flow_succeeded: bool
    steps: List[StepResponse]
    all_succeeded: bool


class CustomConditionResponse(BaseModel):
    model_id: str
    condition_name: str
    step: StepResponse


# ── GEM Pipeline endpoints ──────────────────────

@app.post("/run", response_model=PipelineResponse)
async def run_pipeline(
    file: UploadFile = File(...),
    model_id: Optional[str] = None,
    use_rast: bool = Form(False),
    template_name: str = Form("template_core"),
    template_source: str = Form("builtin"),
):
    """Run the 4-step default MVP pipeline.

    Steps executed:
        1. run_mvp_pipeline.py
        2. analyze_mvp.py --mode theoretical
        3. analyze_mvp.py --mode preset
        4. validate_mvp.py --mode theoretical_upper_bound --biomass-reaction bio2

    Returns model_id and per-step status so callers can load output files
    from data/models/<model_id>/.
    """
    if not file.filename.endswith(".faa"):
        raise ValueError("Only .faa protein FASTA files are supported.")

    contents = await file.read()
    model_id = generate_model_id(model_id)
    
    # Save uploaded file to data/raw/uploads/<filename>
    uploads_dir = Path(__file__).parent.parent / "data" / "raw" / "uploads"
    uploads_dir.mkdir(parents=True, exist_ok=True)
    upload_path = uploads_dir / file.filename
    
    save_upload(upload_path, contents)

    runner = PipelineRunner(
        use_rast=use_rast,
        template_name=template_name,
        template_source=template_source,
    )
    steps = runner.run(upload_path, model_id=model_id)

    step_responses = [
        StepResponse(
            name=s.name,
            cmd=s.cmd,
            returncode=s.returncode,
            stdout=s.stdout,
            stderr=s.stderr,
            succeeded=s.succeeded,
        )
        for s in steps
    ]

    mvp_succeeded = all(s.succeeded for s in steps) and len(steps) == 4

    return PipelineResponse(
        model_id=model_id,
        mvp_flow_succeeded=mvp_succeeded,
        steps=step_responses,
        all_succeeded=all(s.succeeded for s in steps),
    )


@app.post("/run/custom", response_model=CustomConditionResponse)
async def run_custom_condition(
    model_id: str = Form(...),
    condition_name: str = Form(...),
    preset_seed: str = Form("rich_debug_medium"),
    metabolite_ids: Optional[str] = Form(None),
    use_rast: bool = Form(True),
):
    """Run the optional custom-condition analysis step.

    Parameters
    ----------
    model_id:
        The model to run the analysis on (must already exist under data/models/).
    condition_name:
        Name for the custom condition (used in output filenames).
    preset_seed:
        Starting preset to seed the condition (default: rich_debug_medium).
    metabolite_ids:
        Comma-separated metabolite IDs to add to the condition (optional).
    """
    met_list: Optional[List[str]] = None
    if metabolite_ids:
        met_list = [m.strip() for m in metabolite_ids.split(",") if m.strip()]

    runner = PipelineRunner(use_rast=use_rast)
    result = runner.run_custom_condition(
        model_id=model_id,
        condition_name=condition_name,
        preset_seed=preset_seed,
        metabolite_ids=met_list,
    )

    step_resp = StepResponse(
        name=result.name,
        cmd=result.cmd,
        returncode=result.returncode,
        stdout=result.stdout,
        stderr=result.stderr,
        succeeded=result.succeeded,
    )

    return CustomConditionResponse(
        model_id=model_id,
        condition_name=condition_name,
        step=step_resp,
    )


@app.get("/health")
def health():
    return {"status": "ok"}
