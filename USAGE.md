# UI + API quickstart

## FastAPI backend

Run inside the project root (`GEMS/`). Ensure Python 3.10+ is available.

```bash
python -m venv .venv
.venv\\Scripts\\activate  # Windows
# source .venv/bin/activate  # Linux/macOS
pip install -r requirements.txt

uvicorn backend.main:app --reload --port 8000
```

### Endpoints

- `GET /health` — health check
- `POST /run` — multipart file field `file` (.faa), optional query `model_id`, `use_rast` (bool)

Response includes model_id, per-step stdout/stderr/returncode.

## Streamlit frontend

In a second shell with the same venv activated:

```bash
streamlit run frontend_app.py
```

Set the backend URL in the input (defaults to `http://127.0.0.1:8000`). Upload a protein FASTA (.faa) to run the pipeline and inspect step logs.

## Notes and assumptions

- Uses existing scripts under `scripts/` and ModelSEED database already present in the repo.
- Saves uploads to a temp file only; outputs land under `data/models/<model_id>/` per scripts.
- RAST is enabled by default (`use_rast=true`); disable via query param.
