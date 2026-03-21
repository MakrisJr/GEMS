"""FastAPI app that exposes endpoints for uploading a protein FASTA and running the pipeline."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import List

from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .pipeline_runner import PipelineRunner, generate_model_id, save_upload


app = FastAPI(title="Fungal ModelSEED Pipeline API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class StepResponse(BaseModel):
    name: str
    cmd: str
    returncode: int
    stdout: str
    stderr: str
    succeeded: bool


class PipelineResponse(BaseModel):
    model_id: str
    steps: List[StepResponse]
    all_succeeded: bool


@app.post("/run", response_model=PipelineResponse)
async def run_pipeline(file: UploadFile = File(...), model_id: str | None = None, use_rast: bool = True):
    contents = await file.read()

    if not file.filename.endswith(".faa"):
        raise ValueError("Only .faa protein FASTA files are supported.")

    model_id = generate_model_id(model_id)
    temp_dir = Path(tempfile.mkdtemp(prefix="upload_faa_"))
    upload_path = temp_dir / file.filename

    save_upload(upload_path, contents)

    runner = PipelineRunner(use_rast=use_rast)
    steps = runner.run(upload_path, model_id=model_id)

    step_responses = [
        StepResponse(
            name=step.name,
            cmd=step.cmd,
            returncode=step.returncode,
            stdout=step.stdout,
            stderr=step.stderr,
            succeeded=step.succeeded,
        )
        for step in steps
    ]

    return PipelineResponse(
        model_id=model_id,
        steps=step_responses,
        all_succeeded=all(step.succeeded for step in steps),
    )


@app.get("/health")
def health():
    return {"status": "ok"}
