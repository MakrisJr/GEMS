import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import json
import requests
import streamlit as st
import pandas as pd
from datetime import datetime
from pathlib import Path

PLOTLY_IMPORT_ERROR = None
try:
    import plotly.express as px
except Exception as exc:
    px = None
    PLOTLY_IMPORT_ERROR = exc

ML_BACKEND_ERROR = None

try:
    from backend.config import (
        STRAINS,
        TARGET_GROWTH,
        TARGET_BIOMASS,
        TARGET_BYPRODUCTS,
        TARGET_SCORE,
        ALL_TARGETS,
    )
    from backend.data_loader import load_combined, get_dataset_stats
    from backend.model_trainer import train_all, get_training_metadata, get_latest_feature_importances
    from backend.recommender import recommend
    from backend.lab_exporter import recommendations_to_excel
    from backend.data_ingestion import ingest_results
    from backend.retrainer import retrain, get_retrain_history, compare_rounds, get_current_round
except Exception as exc:
    ML_BACKEND_ERROR = exc
    STRAINS = []
    TARGET_GROWTH = TARGET_BIOMASS = TARGET_BYPRODUCTS = TARGET_SCORE = None
    ALL_TARGETS = []

    def load_combined():
        return pd.DataFrame()

    def get_dataset_stats(_df):
        return {"total_rows": 0, "synthetic_rows": 0, "real_rows": 0}

    def get_training_metadata():
        return None

    def get_latest_feature_importances():
        return {}

    def get_current_round():
        return 0

    def compare_rounds():
        return []

    def get_retrain_history():
        return []

    def _raise_ml_backend_error(*_args, **_kwargs):
        raise RuntimeError(
            "ML recommender dependencies are unavailable in this environment. "
            f"Original import error: {ML_BACKEND_ERROR}"
        )

    train_all = _raise_ml_backend_error
    recommend = _raise_ml_backend_error
    recommendations_to_excel = _raise_ml_backend_error
    ingest_results = _raise_ml_backend_error
    retrain = _raise_ml_backend_error

if ML_BACKEND_ERROR is None and px is None:
    ML_BACKEND_ERROR = RuntimeError(
        f"plotly is unavailable in this environment: {PLOTLY_IMPORT_ERROR}"
    )

st.set_page_config(page_title="Fungal GEM Media Optimisation", layout="wide")

DATA_MODELS_DIR = Path(__file__).resolve().parent / "data" / "models"
PIPELINE_MAP_PATH = Path(__file__).resolve().parent / "docs" / "pipeline_metro_map_nf_metro.svg"
EXPERIMENTAL_DIR = Path(__file__).resolve().parent / "Experimental"
EXPERIMENTAL_RESULTS_DIR = EXPERIMENTAL_DIR / "Results A_oryzae"

TEMPLATE_OPTIONS = {
    "Core Template (built-in)": ("template_core", "builtin"),
    "Fungal Template (local ModelSEEDDatabase)": ("fungi", "local"),
}

CUSTOM_PRESET_OPTIONS = {
    "full_precursor_set": "Full Precursor Set / Full Biomass Support",
    "rich_debug_medium": "Rich Debug Medium / Balanced Biomass Support",
    "lower_tca_rescue": "Lower TCA Rescue / Recycling Core Support",
    "upper_sugar_only": "Upper Sugar Only / Reactants Only",
    "energy_redox_only": "Energy Redox Only",
}

TARGET_LABELS = {
    TARGET_GROWTH: "Growth rate",
    TARGET_BIOMASS: "Biomass",
    TARGET_BYPRODUCTS: "Byproducts",
    TARGET_SCORE: "Overall score",
}

# ── Session state init ──────────────────────────
if "recs" not in st.session_state:
    st.session_state["recs"] = {}

# ── Sidebar ────────────────────────────────────
with st.sidebar:
    st.title("Fungal GEM Media Optimisation")
    st.caption("Draft-model media optimisation workflow")
    st.divider()
    meta = get_training_metadata()
    df = load_combined()
    stats = get_dataset_stats(df)
    st.markdown(f"**Model status:** {'Trained' if meta else 'Not trained'}")
    st.markdown(
        f"**Dataset:** {stats['total_rows']} rows "
        f"({stats['synthetic_rows']} synthetic, {stats['real_rows']} experimental)"
    )
    st.markdown(f"**Training round:** {get_current_round()}")

# ── Helper utilities ────────────────────────────

def _model_dir(model_id: str) -> Path:
    return DATA_MODELS_DIR / model_id


def _show_image_or_missing(path: Path, caption: str = "") -> None:
    if not path.exists():
        st.info(f"Image not yet available: `{path.name}`")
        return

    st.image(str(path), caption=caption, use_container_width=True)


def _show_text_or_missing(path: Path) -> None:
    if path.exists():
        st.code(path.read_text(encoding="utf-8"), language="text")
    else:
        st.info(f"Text file not yet available: `{path.name}`")


def _show_csv_or_missing(path: Path, columns: list[str] | None = None) -> None:
    if path.exists():
        try:
            df_tmp = pd.read_csv(path)
            if columns:
                present = [c for c in columns if c in df_tmp.columns]
                if present:
                    df_tmp = df_tmp[present]
            st.dataframe(df_tmp, use_container_width=True, hide_index=True)
        except Exception as e:
            st.error(f"Could not read CSV `{path.name}`: {e}")
    else:
        st.info(f"Table not yet available: `{path.name}`")


def _show_json_or_missing(path: Path) -> dict:
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception as e:
            st.error(f"Could not read JSON `{path.name}`: {e}")
    return {}


def _read_csv_or_empty(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except Exception as e:
        st.error(f"Could not read CSV `{path.name}`: {e}")
        return pd.DataFrame()


# ── Top-level tabs ──────────────────────────────
gem_tab, experimental_tab, ml_tab = st.tabs(
    ["Model workflow", "Experimental analysis", "ML recommender"]
)

# ════════════════════════════════════════════════
# TAB A: GEM PIPELINE
# ════════════════════════════════════════════════
with gem_tab:
    st.header("Fungal GEM media optimisation")
    st.caption(
        "Draft-model workflow for reconstruction, media benchmarking, and validation."
    )
    st.caption(
        "Pipeline order: draft model build, theoretical upper bound, preset condition benchmark, "
        "optional custom condition, and validation."
    )
    st.subheader("Pipeline overview")
    st.caption("Current MVP workflow shown as the official draft build and analysis path.")
    _show_image_or_missing(
        PIPELINE_MAP_PATH,
        caption="Fungal GEM MVP pipeline",
    )

    # ── Upload & Run section ────────────────────────
    st.subheader("Input")

    uploaded_faa = st.file_uploader("Protein FASTA (.faa)", type=["faa", "fasta"])

    if uploaded_faa is not None:
        st.markdown("**Analysis settings**")

        col_opt1, col_opt2 = st.columns(2)
        with col_opt1:
            run_theoretical = st.checkbox(
                "Theoretical upper bound",
                value=True,
                disabled=True,
                help="Included in the default workflow.",
            )
            run_preset = st.checkbox(
                "Preset conditions",
                value=True,
                disabled=True,
                help="Included in the default workflow.",
            )
        with col_opt2:
            run_validation = st.checkbox(
                "Validation",
                value=True,
                disabled=True,
                help="Included in the default workflow.",
            )
            run_custom = st.checkbox(
                "Custom condition",
                value=False,
                key="run_custom_opt",
                help="Optional. Evaluate one user-defined condition.",
            )

        # Custom condition inputs
        custom_condition_name = ""
        custom_preset_seed_run = "rich_debug_medium"
        custom_metabolite_ids_run = ""
        if run_custom:
            st.markdown("**Custom condition settings**")
            c1, c2 = st.columns(2)
            with c1:
                custom_condition_name = st.text_input(
                    "Condition name",
                    value="my_condition",
                    key="run_custom_cond_name",
                )
            with c2:
                custom_preset_seed_run = st.selectbox(
                    "Starting preset",
                    list(CUSTOM_PRESET_OPTIONS),
                    format_func=lambda key: f"{CUSTOM_PRESET_OPTIONS[key]} ({key})",
                    key="run_custom_seed",
                )
            custom_metabolite_ids_run = st.text_area(
                "Additional metabolite IDs (optional)",
                placeholder="cpd00001, cpd00067",
                key="run_custom_mets",
            )

        use_rast = st.checkbox(
            "Use RAST annotation (recommended, slower)",
            value=True,
            key="run_use_rast",
        )

        template_label = st.selectbox(
            "Template",
            list(TEMPLATE_OPTIONS),
            index=0,
            help="Select the reconstruction template for the draft model.",
            key="run_template_choice",
        )
        template_name, template_source = TEMPLATE_OPTIONS[template_label]

        if st.button("Run workflow", type="primary"):
            try:
                with st.spinner("Running workflow..."):
                    # 2. POST to /run with file as multipart upload
                    files = {"file": (uploaded_faa.name, uploaded_faa.getvalue(), "application/octet-stream")}
                    data = {
                        "use_rast": "true" if use_rast else "false",
                        "template_name": template_name,
                        "template_source": template_source,
                    }
                    run_resp = requests.post(
                        "http://localhost:8000/run",
                        files=files,
                        data=data,
                        timeout=600,
                    )
                    run_resp.raise_for_status()
                    run_data = run_resp.json()
                    model_id = run_data.get("model_id", "")

                    # 3. Optional: POST to /run/custom
                    if run_custom and custom_condition_name:
                        custom_payload = {
                            "model_id": model_id,
                            "condition_name": custom_condition_name,
                            "preset_seed": custom_preset_seed_run,
                        }
                        if custom_metabolite_ids_run.strip():
                            cleaned_metabolites = ",".join(
                                part.strip()
                                for part in custom_metabolite_ids_run.replace("\n", ",").split(",")
                                if part.strip()
                            )
                            custom_payload["metabolite_ids"] = cleaned_metabolites
                        custom_resp = requests.post(
                            "http://localhost:8000/run/custom",
                            data=custom_payload,
                            timeout=300,
                        )
                        custom_resp.raise_for_status()

                st.success(f"Workflow complete. Model ID: {model_id}")
                st.session_state["gem_model_id"] = model_id

            except requests.exceptions.ConnectionError:
                st.error(
                    "Backend not running. Start with: "
                    "`uvicorn backend.main:app --reload`"
                )
            except requests.exceptions.HTTPError as exc:
                try:
                    detail = exc.response.json().get("detail", str(exc))
                except Exception:
                    detail = str(exc)
                st.error(f"Pipeline error: {detail}")
            except Exception as exc:
                st.error(f"Unexpected error: {exc}")

    st.divider()

    # ── Model selector ──────────────────────────────
    st.subheader("Model information")

    available_models = sorted(
        [d.name for d in DATA_MODELS_DIR.iterdir() if d.is_dir() and d.name != ".gitkeep"]
    ) if DATA_MODELS_DIR.exists() else []

    if available_models:
        # Auto-select the most recently run model from session state if it exists
        default_idx = 0
        session_model = st.session_state.get("gem_model_id", "")
        if session_model and session_model in available_models:
            default_idx = available_models.index(session_model)
        selected_model = st.selectbox(
            "Current model",
            available_models,
            index=default_idx,
            key="gem_model_select",
        )
    else:
        st.warning("No model outputs found in `data/models/`. Run the workflow first.")
        selected_model = None

    if selected_model:
        mdir = _model_dir(selected_model)

        # Sub-tabs in pipeline execution order (mirrors installation.txt MVP flow)
        (
            sub_overview,
            sub_theoretical,
            sub_preset,
            sub_custom,
            sub_validation,
            sub_advanced,
        ) = st.tabs([
            "Step 1 - Draft model",
            "Step 2 - Theoretical upper bound",
            "Step 3 - Preset conditions",
            "Step 4 - Custom condition",
            "Step 5 - Validation",
            "Pipeline files",
        ])

        # ── Sub-tab 1: Draft Model Overview ────────
        # Corresponds to: run_mvp_pipeline.py
        # Outputs: mvp_summary.json, mvp_mode_comparison.png
        with sub_overview:
            st.subheader("Step 1 - Build and export the draft model")
            st.caption(
                "Load the protein FASTA, annotate with RAST if selected, reconstruct the draft model, "
                "attempt gapfilling, and export the result. "
                "Command: `python scripts/run_mvp_pipeline.py --input protein.faa --model-id MODEL_ID --use-rast`"
            )

            summary_path = mdir / "mvp_summary.json"
            summary = _show_json_or_missing(summary_path)

            if summary:
                cols = st.columns(4)
                card_items = [
                    ("Model ID", summary.get("model_id", selected_model)),
                    ("Template", summary.get("template_name", "—")),
                    ("Template Source", summary.get("template_source", "—")),
                    ("Reactions", summary.get("n_reactions", "—")),
                    ("Metabolites", summary.get("n_metabolites", "—")),
                    ("Genes", summary.get("n_genes", "—")),
                    ("Exchanges", summary.get("n_exchanges", "—")),
                    ("Baseline Status", summary.get("baseline_status", "—")),
                    ("Baseline Objective", summary.get("baseline_objective_value", "—")),
                ]
                for i, (label, value) in enumerate(card_items):
                    with cols[i % 4]:
                        st.metric(label=label, value=str(value))
            else:
                st.info("Summary not yet available (`mvp_summary.json`). Run the workflow first.")

            st.divider()
            st.subheader("Mode comparison")
            st.caption("Comparison of theoretical, preset, and custom-condition outputs.")
            _show_image_or_missing(
                mdir / "mvp_mode_comparison.png",
                caption="MVP Mode Comparison",
            )

        # ── Sub-tab 2: Theoretical Upper Bound ─────
        # Corresponds to: analyze_mvp.py --mode theoretical
        # Official label: "Theoretical Upper Bound"
        # Meaning: best-case benchmark, not a wet-lab medium recommendation
        # Outputs: theoretical_upper_bound.png, theoretical_upper_bound.txt,
        #          theoretical_upper_bound_conditions.csv
        with sub_theoretical:
            st.subheader("Step 2 - Theoretical upper bound")
            st.caption(
                "Best-case benchmark, not a wet-lab medium recommendation. "
                "Temporary biomass-support boundaries are added around the selected biomass-like reaction "
                "to estimate the maximum possible draft-model flux. "
                "Command: `python scripts/analyze_mvp.py --model-dir data/models/MODEL_ID --mode theoretical`"
            )

            _show_image_or_missing(
                mdir / "theoretical_upper_bound.png",
                caption="Theoretical upper bound",
            )

            theo_json = _show_json_or_missing(mdir / "theoretical_upper_bound.json")
            if theo_json:
                st.subheader("Summary")
                metrics = [
                    ("Condition", theo_json.get("display_name", theo_json.get("condition", "—"))),
                    ("Biomass Reaction", theo_json.get("biomass_reaction_id", "—")),
                    ("Status", theo_json.get("status", "—")),
                    ("Predicted Rate", theo_json.get("bio2_rate", "—")),
                    ("Yield Proxy", theo_json.get("bio2_yield_on_total_added_flux", "—")),
                    ("Added Boundaries", theo_json.get("n_added_boundaries", "—")),
                ]
                s_cols = st.columns(3)
                for i, (label, value) in enumerate(metrics):
                    s_cols[i % 3].metric(label=label, value=str(value))
            else:
                st.info("Summary not yet available: `theoretical_upper_bound.json`")

            with st.expander("Text summary"):
                _show_text_or_missing(mdir / "theoretical_upper_bound.txt")

            st.subheader("Boundary condition table")
            st.caption("Temporary biomass-support boundaries used in the optimised theoretical run.")
            _show_csv_or_missing(
                mdir / "theoretical_upper_bound_conditions.csv",
                columns=["metabolite_name", "metabolite_id", "boundary_id", "flux", "abs_flux"],
            )

        # ── Sub-tab 3: Preset Conditions ───────────
        # Corresponds to: analyze_mvp.py --mode preset
        # Official label: "Preset Conditions"
        # Meaning: comparison library for the draft model
        # Outputs: preset_conditions.png, preset_conditions.csv, preset_conditions.txt
        with sub_preset:
            st.subheader("Step 3 - Preset conditions")
            st.caption(
                "Comparison library for the draft model. Tests a small model-specific set of "
                "biomass-support conditions derived from the current biomass reaction. "
                "Command: `python scripts/analyze_mvp.py --model-dir data/models/MODEL_ID --mode preset`"
            )

            _show_image_or_missing(
                mdir / "preset_conditions.png",
                caption="Preset condition comparison",
            )

            st.subheader("Preset condition table")
            _show_csv_or_missing(
                mdir / "preset_conditions.csv",
                columns=[
                    "display_name",
                    "description",
                    "bio2_rate",
                    "bio2_yield_on_total_added_flux",
                    "status",
                    "n_added_boundaries",
                ],
            )

            st.subheader("Preset condition summary")
            _show_text_or_missing(mdir / "preset_conditions.txt")

        # ── Sub-tab 4: Custom Condition ─────────────
        # Corresponds to: analyze_mvp.py --mode custom --from-preset ... --condition-name ...
        # Official label: "Custom Condition"
        # Meaning: user-defined comparison condition
        # Outputs: custom_condition_<name>.png, custom_condition_<name>.json,
        #          custom_condition_<name>.txt
        with sub_custom:
            st.subheader("Step 4 - Custom condition")
            st.caption(
                "User-defined comparison condition. Start from a preset and optionally modify it. "
                "Command: `python scripts/analyze_mvp.py --model-dir data/models/MODEL_ID "
                "--mode custom --from-preset rich_debug_medium --condition-name CONDITION_NAME`"
            )

            cond_name = st.text_input(
                "Custom condition name",
                value="my_condition",
                key="custom_cond_name",
            )
            preset_seed = st.selectbox(
                "Starting preset",
                list(CUSTOM_PRESET_OPTIONS),
                format_func=lambda key: f"{CUSTOM_PRESET_OPTIONS[key]} ({key})",
                key="custom_preset_seed",
            )
            metabolite_ids = st.text_area(
                "Metabolite IDs (comma-separated or one per line)",
                placeholder="cpd00001, cpd00067",
                key="custom_metabolite_ids",
            )

            safe_name = cond_name.replace(" ", "_") if cond_name else "my_condition"

            custom_png = mdir / f"custom_condition_{safe_name}.png"
            custom_json = mdir / f"custom_condition_{safe_name}.json"
            custom_txt = mdir / f"custom_condition_{safe_name}.txt"

            _show_image_or_missing(custom_png, caption=f"Custom condition: {safe_name}")

            custom_data = _show_json_or_missing(custom_json)
            if custom_data:
                st.subheader("Custom condition summary")
                summary_fields = [
                    ("Condition", custom_data.get("display_name", custom_data.get("condition", "—"))),
                    ("Status", custom_data.get("status", "—")),
                    ("Predicted Rate", custom_data.get("bio2_rate", "—")),
                    ("Yield Proxy", custom_data.get("bio2_yield_on_total_added_flux", "—")),
                ]
                s_cols = st.columns(len(summary_fields))
                for i, (label, value) in enumerate(summary_fields):
                    s_cols[i].metric(label=label, value=str(value))

                if custom_data.get("metabolite_ids"):
                    st.subheader("Metabolites")
                    st.dataframe(
                        pd.DataFrame({"metabolite_id": custom_data["metabolite_ids"]}),
                        use_container_width=True,
                        hide_index=True,
                    )
            else:
                st.info(f"Custom-condition output not yet available for `{safe_name}`.")

            _show_text_or_missing(custom_txt)

        # ── Sub-tab 5: Validation ───────────────────
        # Corresponds to: validate_mvp.py and validate_mvp.py --mode theoretical_upper_bound
        # Official label: "Validation"
        # Meaning: draft-model quality checks
        # Outputs: theoretical_upper_bound_validation_dashboard.png,
        #          theoretical_upper_bound_validation_summary.json/txt,
        #          theoretical_upper_bound_dead_end_metabolites.csv,
        #          theoretical_upper_bound_exchange_fva.csv,
        #          theoretical_upper_bound_gene_essentiality.csv
        with sub_validation:
            st.subheader("Step 5 - Validation")
            st.caption(
                "Draft-model quality checks. Confirms FBA solvability, identifies dead-end metabolites, "
                "runs exchange FVA and gene essentiality analysis. "
                "Command: `python scripts/validate_mvp.py --model-dir data/models/MODEL_ID` "
                "and `python scripts/validate_mvp.py --model-dir data/models/MODEL_ID "
                "--mode theoretical_upper_bound --biomass-reaction bio2`"
            )

            _show_image_or_missing(
                mdir / "theoretical_upper_bound_validation_dashboard.png",
                caption="Validation dashboard",
            )

            val_txt = mdir / "theoretical_upper_bound_validation_summary.txt"
            val_json_path = mdir / "theoretical_upper_bound_validation_summary.json"

            val_data = _show_json_or_missing(val_json_path)
            if val_data:
                fba = val_data.get("fba", {})
                dead_end = val_data.get("dead_end_metabolites", {})
                exchange_fva = val_data.get("exchange_fva", {})
                gene_essentiality = val_data.get("gene_essentiality", {})
                validation_context = val_data.get("validation_context", {})
                val_fields = [
                    ("Biomass Reaction", validation_context.get("biomass_reaction_id", "—")),
                    ("FBA Status", fba.get("status", "—")),
                    ("Objective Value", fba.get("objective_value", "—")),
                    ("Dead-end Metabolites", dead_end.get("n_dead_end_metabolites", "—")),
                    ("Produced Only", dead_end.get("n_produced_only", "—")),
                    ("Consumed Only", dead_end.get("n_consumed_only", "—")),
                    ("Exchange Reactions Tested", exchange_fva.get("n_exchange_reactions", "—")),
                    ("Gene Essentiality Status", gene_essentiality.get("status", "—")),
                    ("Essential Genes Found", gene_essentiality.get("n_essential_genes", "—")),
                ]
                v_cols = st.columns(4)
                for i, (label, value) in enumerate(val_fields):
                    v_cols[i % 4].metric(label=label, value=str(value))
            else:
                st.info("Validation summary not yet available.")

            st.subheader("Validation summary")
            _show_text_or_missing(val_txt)

            st.divider()
            st.subheader("Detailed validation tables")

            dead_end_path = mdir / "theoretical_upper_bound_dead_end_metabolites.csv"
            fva_path = mdir / "theoretical_upper_bound_exchange_fva.csv"
            gene_ess_path = mdir / "theoretical_upper_bound_gene_essentiality.csv"

            with st.expander("Dead-end Metabolites"):
                _show_csv_or_missing(dead_end_path)

            with st.expander("Exchange FVA"):
                _show_csv_or_missing(fva_path)

            with st.expander("Gene Essentiality"):
                _show_csv_or_missing(gene_ess_path)

        # ── Sub-tab 6: Full Pipeline Files ──────────
        # Shows all 12 pipeline steps in order, using the exact filenames from
        # the "Important output files" section of installation.txt
        with sub_advanced:
            st.subheader("Pipeline files")
            st.caption(
                "Intermediate outputs from the full workflow, shown in execution order. "
                "Useful for troubleshooting and detailed inspection."
            )

            # Steps in pipeline order (matches installation.txt steps 1–12)
            pipeline_steps = [
                # (step_number, step_label, [list of (filename, ext)])
                (1, "Detect Input Type — prepare_input.py",
                    [("data/intermediate/genome_summary.json", "json")]),
                (2, "Load Protein FASTA — first_modelseed_step.py",
                    [("data/intermediate/genome_summary.json", "json")]),
                (3, "Build Draft Model with RAST — build_draft_model.py",
                    [("model_summary.json", "json"),
                     ("model_summary.txt", "text")]),
                (4, "Gapfill & Export — gapfill_and_export_model.py",
                    [("gapfill_summary.json", "json"),
                     ("gapfill_summary.txt", "text")]),
                (5, "COBRA Inspection — inspect_with_cobra.py",
                    [("model_overview.json", "json"),
                     ("exchanges.csv", "csv"),
                     ("baseline_optimization.json", "json"),
                     ("cobra_inspection.txt", "text")]),
                (6, "First-Pass Media Screen — screen_media.py",
                    [("media_screen.csv", "csv"),
                     ("media_screen.json", "json"),
                     ("media_screen.png", "image"),
                     ("media_screen.txt", "text")]),
                (7, "Diagnose Exchange Space — diagnose_exchange_space.py",
                    [("exchange_metabolites.csv", "csv"),
                     ("exchange_diagnosis.json", "json"),
                     ("exchange_diagnosis.txt", "text")]),
                (8, "Growth Debugging — debug_growth.py",
                    [("debug_growth.json", "json"),
                     ("debug_growth.txt", "text")]),
                (9, "Oracle Growth Check — run_oracle_growth.py",
                    [("oracle_growth.json", "json"),
                     ("oracle_growth.txt", "text")]),
                (10, "Oracle-Derived Debug Media — screen_oracle_medium.py",
                    [("oracle_medium_screen.csv", "csv"),
                     ("oracle_medium_screen.json", "json"),
                     ("oracle_medium_screen.png", "image"),
                     ("oracle_medium_screen.txt", "text")]),
                (11, "Benchmark bio2 Rate — benchmark_bio2.py",
                    [("bio2_benchmark.csv", "csv"),
                     ("bio2_benchmark.json", "json"),
                     ("bio2_benchmark.png", "image"),
                     ("bio2_benchmark.txt", "text")]),
                (12, "Inspect Oracle Condition — inspect_oracle_condition.py",
                    [("selected_condition_central_carbon_precursors.json", "json"),
                     ("selected_condition_central_carbon_precursors.txt", "text")]),
            ]

            found_any = False
            for step_num, step_label, file_list in pipeline_steps:
                # Check if any file for this step exists
                step_files = []
                for fname, ftype in file_list:
                    # Genome-loading step references intermediate dir, others are in mdir
                    if fname.startswith("data/intermediate/"):
                        candidate = DATA_MODELS_DIR.parent / fname.split("data/", 1)[1]
                    else:
                        candidate = mdir / fname
                    if candidate.exists():
                        step_files.append((candidate, fname, ftype))

                if step_files:
                    found_any = True
                    with st.expander(f"Step {step_num} - {step_label}"):
                        for candidate, fname, ftype in step_files:
                            st.markdown(f"**`{Path(fname).name}`**")
                            if ftype == "csv":
                                _show_csv_or_missing(candidate)
                            elif ftype == "image":
                                _show_image_or_missing(candidate, caption=Path(fname).name)
                            else:
                                _show_text_or_missing(candidate)

            if not found_any:
                st.info(
                    "No intermediate workflow files found yet for this model. "
                    "Run the full pipeline (steps 1–12) to generate them."
                )

            st.divider()
            st.subheader("All files in model directory")
            if mdir.exists():
                all_files = sorted(mdir.iterdir())
                for f in all_files:
                    st.text(f"  {f.name}  ({f.stat().st_size:,} bytes)" if f.is_file() else f"  {f.name}/")
            else:
                st.info("Model directory does not exist yet.")


# ════════════════════════════════════════════════
# TAB B: EXPERIMENTAL ANALYSIS
# ════════════════════════════════════════════════
with experimental_tab:
    st.header("Experimental analysis / Geometry-aware optimisation")

    exp_ranked = _read_csv_or_empty(EXPERIMENTAL_RESULTS_DIR / "predicted_ranked_scenarios.csv")
    exp_industrial = _read_csv_or_empty(
        EXPERIMENTAL_RESULTS_DIR / "predicted_ranked_scenarios_industrial.csv"
    )
    exp_importance = _read_csv_or_empty(EXPERIMENTAL_RESULTS_DIR / "feature_importances.csv")

    metric_cols = st.columns(4)
    overall_best = exp_ranked.iloc[0] if not exp_ranked.empty else None
    industrial_best = exp_industrial.iloc[0] if not exp_industrial.empty else None
    top_feature = exp_importance.iloc[0] if not exp_importance.empty else None

    metric_cols[0].metric(
        "Reference model",
        "A. oryzae",
    )
    metric_cols[1].metric(
        "Scenarios ranked",
        str(len(exp_ranked)) if not exp_ranked.empty else "—",
    )
    metric_cols[2].metric(
        "Best overall score",
        (
            f"{overall_best['overall_rank_score']:.4f}"
            if overall_best is not None and "overall_rank_score" in overall_best
            else "—"
        ),
    )
    metric_cols[3].metric(
        "Best industrial score",
        (
            f"{industrial_best['industrial_score']:.4f}"
            if industrial_best is not None and "industrial_score" in industrial_best
            else "—"
        ),
    )

    summary_cols = st.columns(3)
    summary_cols[0].metric(
        "Top overall scenario",
        (
            f"Scenario {int(overall_best['scenario'])}"
            if overall_best is not None and "scenario" in overall_best
            else "—"
        ),
    )
    summary_cols[1].metric(
        "Top industrial scenario",
        (
            f"Scenario {int(industrial_best['scenario'])}"
            if industrial_best is not None and "scenario" in industrial_best
            else "—"
        ),
    )
    summary_cols[2].metric(
        "Top feature",
        (
            str(top_feature["feature"]).replace("num__", "")
            if top_feature is not None and "feature" in top_feature
            else "—"
        ),
    )

    st.subheader("Regional summary")
    _show_text_or_missing(EXPERIMENTAL_RESULTS_DIR / "top_region_summary.txt")

    st.subheader("Tradeoff plots")
    plot_col1, plot_col2 = st.columns(2)
    with plot_col1:
        _show_image_or_missing(
            EXPERIMENTAL_RESULTS_DIR / "pareto_growth_vs_byproduct.png",
            caption="Growth vs byproduct Pareto tradeoff",
        )
    with plot_col2:
        _show_image_or_missing(
            EXPERIMENTAL_RESULTS_DIR / "plot_industrial_tradeoff.png",
            caption="Industrial score tradeoff",
        )

    st.subheader("Ranked scenarios")
    st.caption("Top candidate conditions ranked by the experimental surrogate model.")
    _show_csv_or_missing(
        EXPERIMENTAL_RESULTS_DIR / "predicted_ranked_scenarios.csv",
        columns=[
            "scenario",
            "search_stage",
            "glucose",
            "ammonium",
            "phosphate",
            "sulfate",
            "temperature",
            "pH",
            "mixing",
            "growth",
            "biomass_flux_mean",
            "byproduct_total",
            "overall_rank_score",
        ],
    )

    st.subheader("Industrial ranking")
    st.caption("Top scenarios after adding industrial scoring terms.")
    _show_csv_or_missing(
        EXPERIMENTAL_RESULTS_DIR / "predicted_ranked_scenarios_industrial.csv",
        columns=[
            "scenario",
            "search_stage",
            "glucose",
            "ammonium",
            "phosphate",
            "sulfate",
            "temperature",
            "pH",
            "mixing",
            "growth",
            "economic_score",
            "morphology_score",
            "meatiness_score",
            "industrial_score",
        ],
    )

    st.subheader("Feature importance")
    st.caption("Most influential variables in the experimental surrogate model.")
    _show_csv_or_missing(
        EXPERIMENTAL_RESULTS_DIR / "feature_importances.csv",
        columns=["feature", "importance"],
    )

    with st.expander("Processed dataset preview"):
        _show_csv_or_missing(
            EXPERIMENTAL_RESULTS_DIR / "dataset_postprocessed.csv",
            columns=[
                "scenario",
                "search_stage",
                "growth",
                "fva_range",
                "log_volume",
                "anisotropy_log",
                "biomass_flux_mean",
                "byproduct_total",
                "overall_rank_score",
                "industrial_score",
            ],
        )


# ════════════════════════════════════════════════
# TAB C: ML RECOMMENDER  (all existing ML functionality preserved)
# ════════════════════════════════════════════════
with ml_tab:
    if ML_BACKEND_ERROR is not None:
        st.warning(
            "The ML recommender tab is unavailable in this environment because its optional "
            f"dependencies could not be imported: {ML_BACKEND_ERROR}"
        )
        st.caption(
            "The GEM pipeline tab still works. Install the missing ML dependencies to re-enable "
            "training and recommendation features."
        )
    else:
        with st.expander("How it works", expanded=False):
            st.markdown("""
**How the ML recommender works**

1. **Train** — Learns from historical fungal growth experiments to predict whether a given media condition supports growth.

2. **Recommend** — Ranks candidate media conditions based on similarity to successful conditions in the training data.

3. **Retrain** — Incorporates new laboratory results to update the model.

---
The underlying model uses a **Random Forest classifier** trained on tabular growth data.
Features include nutrient composition, environmental parameters, and strain metadata.
""")

        ml_train, ml_recs, ml_upload = st.tabs(["Train", "Recommendations", "Upload and retrain"])

        # ── ML sub-tab 1: TRAIN ───────────────────────
        with ml_train:
            st.header("Train models")

            if st.button("Train model", type="primary", use_container_width=True):
                with st.spinner("Training... (1–2 min)"):
                    try:
                        meta = train_all()
                        st.success("Training complete!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Training failed: {e}")

            meta = get_training_metadata()
            if meta:
                st.caption(f"Last trained: {meta.get('timestamp', '')[:19].replace('T', ' ')} UTC  |  {meta['n_samples']} samples")

                rows = []
                for target, info in meta["targets"].items():
                    for mtype, score in info["cv_r2_scores"].items():
                        rows.append({"Target": target, "Model": mtype, "CV R²": round(score, 3)})
                df_scores = pd.DataFrame(rows)

                best_rows = [
                    {"Target": t, "Best Model": info["best_model_type"], "CV R²": round(info["best_cv_r2"], 3)}
                    for t, info in meta["targets"].items()
                ]
                st.subheader("Best model per target")
                st.dataframe(pd.DataFrame(best_rows), use_container_width=True, hide_index=True)

                fig = px.bar(
                    df_scores,
                    x="Target",
                    y="CV R²",
                    color="Model",
                    barmode="group",
                    title="Cross-validation R² by target and model",
                    color_discrete_sequence=px.colors.qualitative.Set2,
                )
                fig.update_layout(yaxis_range=[0, 1], height=350, margin=dict(t=40, b=10))
                st.plotly_chart(fig, use_container_width=True)

                feature_importances = get_latest_feature_importances()
                if feature_importances:
                    st.subheader("Feature Importance")
                    st.caption(
                        "Model-derived feature importance for the best saved model for each target. "
                        "For tree-based models, values reflect split-based importance rather than linear coefficients."
                    )

                    importance_tabs = st.tabs(
                        [TARGET_LABELS.get(target, target) for target in ALL_TARGETS if target in feature_importances]
                    )

                    for tab, target in zip(
                        importance_tabs,
                        [target for target in ALL_TARGETS if target in feature_importances],
                    ):
                        with tab:
                            info = feature_importances[target]
                            imp_df = pd.DataFrame(info["features"])
                            plot_df = imp_df.sort_values("importance", ascending=True)
                            fig_imp = px.bar(
                                plot_df,
                                x="importance",
                                y="feature",
                                orientation="h",
                                title=(
                                    f"{TARGET_LABELS.get(target, target)} "
                                    f"({info['model_type']}, {info['importance_type']})"
                                ),
                                labels={"importance": "Importance", "feature": "Feature"},
                                color="importance",
                                color_continuous_scale="Blues",
                            )
                            fig_imp.update_layout(
                                height=520,
                                margin=dict(t=50, b=10),
                                coloraxis_showscale=False,
                            )
                            st.plotly_chart(fig_imp, use_container_width=True)
                            st.dataframe(
                                imp_df.rename(
                                    columns={"feature": "Feature", "importance": "Importance"}
                                ),
                                use_container_width=True,
                                hide_index=True,
                            )
            else:
                st.info("No model has been trained yet. Select `Train model` to begin.")

        # ── ML sub-tab 2: RECOMMENDATIONS ─────────────
        with ml_recs:
            st.header("Recommendations")

            meta = get_training_metadata()
            if not meta:
                st.warning("Train the model first in the `Train` tab.")
            else:
                col1, col2 = st.columns([2, 1])
                with col1:
                    strain = st.selectbox("Strain", STRAINS)
                with col2:
                    top_n = st.slider("Number of recommendations", 3, 10, 5)

                if st.button("Generate recommendations", type="primary"):
                    with st.spinner("Evaluating 2,000 candidate conditions..."):
                        try:
                            recs = recommend(strain, top_n=top_n)
                            st.session_state["recs"][strain] = recs
                        except Exception as e:
                            st.error(f"Failed: {e}")

                recs = st.session_state["recs"].get(strain)
                if recs:
                    all_recs = recs["exploit"] + recs["explore"]

                    table_rows = []
                    for r in all_recs:
                        table_rows.append({
                            "Rank": r["rank"],
                            "Type": r["run_type"].upper(),
                            "Score": round(r["predicted_score"], 4),
                            "Growth (h⁻¹)": round(r["predicted_growth_rate"], 5),
                            "Biomass (g/L)": round(r["predicted_biomass"], 3),
                            "Byproducts (g/L)": round(r["predicted_byproducts"], 3),
                            "Uncertainty": round(r["uncertainty_score"], 4),
                            "pH": round(r.get("pH", 0), 2),
                            "Temp (°C)": round(r.get("temperature_C", 0), 1),
                            "Carbon Source": r.get("carbon_source", ""),
                            "N Source": r.get("nitrogen_source", ""),
                        })
                    st.dataframe(pd.DataFrame(table_rows), use_container_width=True, hide_index=True)

                    df_r = pd.DataFrame(table_rows)
                    fig2 = px.scatter(
                        df_r,
                        x="Uncertainty",
                        y="Score",
                        text="Rank",
                        color="Type",
                        title="Predicted Score vs Uncertainty",
                        color_discrete_map={"EXPLOIT": "#2196F3", "EXPLORE": "#FF9800"},
                    )
                    fig2.update_traces(textposition="top center", marker_size=10)
                    fig2.update_layout(height=320, margin=dict(t=40, b=10))
                    st.plotly_chart(fig2, use_container_width=True)

                    try:
                        excel_bytes = recommendations_to_excel(recs)
                        fname = f"lab_sheet_{strain.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.xlsx"
                        st.download_button(
                            "Download lab sheet (Excel)",
                            data=excel_bytes,
                            file_name=fname,
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        )
                    except Exception as e:
                        st.error(f"Export error: {e}")

        # ── ML sub-tab 3: UPLOAD & RETRAIN ────────────
        with ml_upload:
            st.header("Upload results and retrain")

            st.subheader("1 - Upload laboratory results")
            uploaded = st.file_uploader("Laboratory results CSV", type=["csv"])

            if uploaded:
                try:
                    upload_df = pd.read_csv(uploaded)
                    st.write(f"Loaded {len(upload_df)} rows and {len(upload_df.columns)} columns")
                    st.dataframe(upload_df.head(), use_container_width=True)

                    if st.button("Validate and ingest", type="primary"):
                        current_round = get_current_round()
                        ok, msg, updated = ingest_results(upload_df, current_round + 1)
                        if ok:
                            st.success(msg)
                            st.cache_data.clear()
                            st.rerun()
                        else:
                            st.error(msg)
                except Exception as e:
                    st.error(f"Could not read file: {e}")

            st.subheader("2 - Retrain model")
            df2 = load_combined()
            stats2 = get_dataset_stats(df2)
            st.caption(
                f"Dataset: {stats2['total_rows']} rows — {stats2['synthetic_rows']} synthetic, {stats2['real_rows']} experimental"
            )

            desc = st.text_input("Round description (optional)", placeholder="e.g. After first laboratory batch")
            if st.button("Retrain with all data", type="primary"):
                with st.spinner("Retraining..."):
                    try:
                        new_meta = retrain(description=desc)
                        st.success(f"Retrain complete! Round {get_current_round()}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Retrain failed: {e}")

            history = compare_rounds()
            if history:
                st.subheader("Training history")
                st.dataframe(pd.DataFrame(history), use_container_width=True, hide_index=True)
