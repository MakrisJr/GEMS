import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import json
import requests
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from pathlib import Path

from backend.config import STRAINS, TARGET_GROWTH, TARGET_BIOMASS, TARGET_BYPRODUCTS, TARGET_SCORE, ALL_TARGETS
from backend.data_loader import load_combined, get_dataset_stats
from backend.model_trainer import train_all, get_training_metadata
from backend.recommender import recommend
from backend.lab_exporter import recommendations_to_excel
from backend.data_ingestion import ingest_results
from backend.retrainer import retrain, get_retrain_history, compare_rounds, get_current_round

st.set_page_config(page_title="GEMS", page_icon="🍄", layout="wide")

DATA_MODELS_DIR = Path(__file__).resolve().parent / "data" / "models"

# ── Session state init ──────────────────────────
if "recs" not in st.session_state:
    st.session_state["recs"] = {}

# ── Sidebar ────────────────────────────────────
with st.sidebar:
    st.title("🍄 GEMS")
    st.caption("Fungal Growth Optimizer")
    st.divider()
    meta = get_training_metadata()
    df = load_combined()
    stats = get_dataset_stats(df)
    st.markdown(f"**Model:** {'✅ Trained' if meta else '❌ Not trained'}")
    st.markdown(f"**Dataset:** {stats['total_rows']} rows ({stats['synthetic_rows']} synthetic, {stats['real_rows']} real)")
    st.markdown(f"**Round:** {get_current_round()}")

# ── Helper utilities ────────────────────────────

def _model_dir(model_id: str) -> Path:
    return DATA_MODELS_DIR / model_id


def _show_image_or_missing(path: Path, caption: str = "") -> None:
    if path.exists():
        st.image(str(path), caption=caption, use_container_width=True)
    else:
        st.info(f"📂 Image not yet available: `{path.name}`")


def _show_text_or_missing(path: Path) -> None:
    if path.exists():
        st.code(path.read_text(encoding="utf-8"), language="text")
    else:
        st.info(f"📂 Text file not yet available: `{path.name}`")


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
        st.info(f"📂 CSV not yet available: `{path.name}`")


def _show_json_or_missing(path: Path) -> dict:
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception as e:
            st.error(f"Could not read JSON `{path.name}`: {e}")
    return {}


# ── Top-level tabs ──────────────────────────────
gem_tab, ml_tab = st.tabs(["🧫 GEM Pipeline", "🤖 ML Recommender"])

# ════════════════════════════════════════════════
# TAB A: GEM PIPELINE
# ════════════════════════════════════════════════
with gem_tab:
    st.header("GEM Pipeline — MVP Flow")
    st.caption(
        "Pipeline order follows the official MVP entry points: "
        "Build Draft Model → Theoretical Upper Bound → Preset Conditions → Custom Condition → Validation"
    )

    # ── Upload & Run section ────────────────────────
    st.subheader("▲ Upload & Run")

    uploaded_faa = st.file_uploader("Upload protein FASTA (.faa)", type=["faa", "fasta"])

    if uploaded_faa is not None:
        st.markdown("**Analysis options** — select what to run:")

        col_opt1, col_opt2 = st.columns(2)
        with col_opt1:
            run_theoretical = st.checkbox(
                "✅ Run Theoretical Upper Bound",
                value=True,
                disabled=True,
                help="Part of the default MVP pipeline — always runs.",
            )
            run_preset = st.checkbox(
                "✅ Run Preset Conditions",
                value=True,
                disabled=True,
                help="Part of the default MVP pipeline — always runs.",
            )
        with col_opt2:
            run_validation = st.checkbox(
                "✅ Run Validation",
                value=True,
                disabled=True,
                help="Part of the default MVP pipeline — always runs.",
            )
            run_custom = st.checkbox(
                "Run Custom Condition",
                value=False,
                key="run_custom_opt",
                help="Optional — define a custom media condition to test.",
            )

        # Custom condition inputs
        custom_condition_name = ""
        custom_preset_seed_run = "rich_debug_medium"
        custom_metabolite_ids_run = ""
        if run_custom:
            st.markdown("**Custom Condition settings:**")
            c1, c2 = st.columns(2)
            with c1:
                custom_condition_name = st.text_input(
                    "Condition name",
                    value="my_condition",
                    key="run_custom_cond_name",
                )
            with c2:
                custom_preset_seed_run = st.text_input(
                    "Preset seed",
                    value="rich_debug_medium",
                    key="run_custom_seed",
                )
            custom_metabolite_ids_run = st.text_area(
                "Metabolite IDs (comma-separated, optional)",
                placeholder="cpd00001, cpd00067",
                key="run_custom_mets",
            )

        use_rast = st.checkbox(
            "Use RAST annotations (optional, slower)",
            value=False,
            key="run_use_rast",
        )

        if st.button("▶ Run Pipeline", type="primary"):
            try:
                with st.spinner("Running pipeline…"):
                    # 2. POST to /run with file as multipart upload
                    files = {"file": (uploaded_faa.name, uploaded_faa.getvalue(), "application/octet-stream")}
                    data = {"use_rast": "true" if use_rast else "false"}
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
                            custom_payload["metabolite_ids"] = custom_metabolite_ids_run.strip()
                        custom_resp = requests.post(
                            "http://localhost:8000/run/custom",
                            data=custom_payload,
                            timeout=300,
                        )
                        custom_resp.raise_for_status()

                st.success(f"Pipeline complete! Model ID: {model_id}")
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
    st.subheader("📂 View Results for a Model")

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
            "Select Model",
            available_models,
            index=default_idx,
            key="gem_model_select",
        )
    else:
        st.warning("No models found in `data/models/`. Run the pipeline first.")
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
            "📋 Step 1 — Draft Model",
            "📈 Step 2 — Theoretical Upper Bound",
            "🧪 Step 3 — Preset Conditions",
            "✏️ Step 4 — Custom Condition",
            "✅ Step 5 — Validation",
            "🔧 Full Pipeline Files",
        ])

        # ── Sub-tab 1: Draft Model Overview ────────
        # Corresponds to: run_mvp_pipeline.py
        # Outputs: mvp_summary.json, mvp_mode_comparison.png
        with sub_overview:
            st.subheader("Step 1 — Build & Export the Draft Model")
            st.caption(
                "Run the MVP pipeline to load the protein FASTA, annotate with RAST, "
                "build the draft metabolic model, gapfill, and export it. "
                "Command: `python scripts/run_mvp_pipeline.py --input protein.faa --model-id MODEL_ID --use-rast`"
            )

            summary_path = mdir / "mvp_summary.json"
            summary = _show_json_or_missing(summary_path)

            if summary:
                cols = st.columns(4)
                card_items = [
                    ("Model ID", summary.get("model_id", selected_model)),
                    ("Reactions", summary.get("reactions", "—")),
                    ("Metabolites", summary.get("metabolites", "—")),
                    ("Genes", summary.get("genes", "—")),
                    ("Exchanges", summary.get("exchanges", "—")),
                    ("Baseline Status", summary.get("baseline_status", "—")),
                    ("Baseline Objective", summary.get("baseline_objective_value", "—")),
                ]
                for i, (label, value) in enumerate(card_items):
                    with cols[i % 4]:
                        st.metric(label=label, value=str(value))
            else:
                st.info("📂 Summary not yet available (`mvp_summary.json`). Run the MVP pipeline first.")

            st.divider()
            st.subheader("Mode Comparison Plot")
            st.caption("Visualises how the model performs across all three analysis modes (theoretical, preset, custom).")
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
            st.subheader("Step 2 — Theoretical Upper Bound")
            st.caption(
                "Best-case benchmark — not a wet-lab medium recommendation. "
                "All exchange reactions are opened to find the maximum possible biomass flux. "
                "Command: `python scripts/analyze_mvp.py --model-dir data/models/MODEL_ID --mode theoretical`"
            )

            _show_image_or_missing(
                mdir / "theoretical_upper_bound.png",
                caption="Theoretical Upper Bound Plot",
            )

            txt_path = mdir / "theoretical_upper_bound.txt"
            if txt_path.exists():
                text_content = txt_path.read_text(encoding="utf-8")
                lines = [ln.strip() for ln in text_content.splitlines() if ln.strip()]

                summary_keys = {
                    "Condition": None,
                    "Status": None,
                    "Predicted bio2 rate": None,
                    "Yield proxy": None,
                    "Temporary boundaries added": None,
                }
                for line in lines:
                    for key in summary_keys:
                        if key.lower() in line.lower() and ":" in line:
                            summary_keys[key] = line.split(":", 1)[1].strip()

                filled = {k: v for k, v in summary_keys.items() if v}
                if filled:
                    st.subheader("Summary")
                    s_cols = st.columns(len(filled))
                    for i, (k, v) in enumerate(filled.items()):
                        s_cols[i].metric(label=k, value=v)
                else:
                    _show_text_or_missing(txt_path)
            else:
                st.info("📂 Text file not yet available: `theoretical_upper_bound.txt`")

            st.subheader("Boundary Conditions Table")
            st.caption("Exchange reactions activated in the theoretical upper-bound run.")
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
            st.subheader("Step 3 — Preset Conditions")
            st.caption(
                "Comparison library for the draft model — tests a curated set of standard media "
                "conditions (e.g. rich, minimal, complex) against the model. "
                "Command: `python scripts/analyze_mvp.py --model-dir data/models/MODEL_ID --mode preset`"
            )

            _show_image_or_missing(
                mdir / "preset_conditions.png",
                caption="Preset Conditions Comparison",
            )

            st.subheader("Preset Conditions Table")
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

            st.subheader("Preset Conditions Summary")
            _show_text_or_missing(mdir / "preset_conditions.txt")

        # ── Sub-tab 4: Custom Condition ─────────────
        # Corresponds to: analyze_mvp.py --mode custom --from-preset ... --condition-name ...
        # Official label: "Custom Condition"
        # Meaning: user-defined comparison condition
        # Outputs: custom_condition_<name>.png, custom_condition_<name>.json,
        #          custom_condition_<name>.txt
        with sub_custom:
            st.subheader("Step 4 — Custom Condition")
            st.caption(
                "User-defined comparison condition — start from a preset medium and modify it. "
                "Command: `python scripts/analyze_mvp.py --model-dir data/models/MODEL_ID "
                "--mode custom --from-preset rich_debug_medium --condition-name CONDITION_NAME`"
            )

            cond_name = st.text_input(
                "Custom condition name",
                value="my_condition",
                key="custom_cond_name",
            )
            preset_seed = st.selectbox(
                "Preset seed",
                ["rich_debug_medium", "minimal_glucose", "complex_medium"],
                key="custom_preset_seed",
            )
            metabolite_ids = st.text_area(
                "Metabolite IDs (one per line)",
                placeholder="cpd00001\ncpd00067",
                key="custom_metabolite_ids",
            )

            safe_name = cond_name.replace(" ", "_") if cond_name else "my_condition"

            custom_png = mdir / f"custom_condition_{safe_name}.png"
            custom_json = mdir / f"custom_condition_{safe_name}.json"
            custom_txt = mdir / f"custom_condition_{safe_name}.txt"

            _show_image_or_missing(custom_png, caption=f"Custom Condition: {safe_name}")

            custom_data = _show_json_or_missing(custom_json)
            if custom_data:
                st.subheader("Custom Condition Summary")
                summary_fields = ["condition", "status", "bio2_rate", "yield_proxy"]
                s_cols = st.columns(len(summary_fields))
                for i, field in enumerate(summary_fields):
                    val = custom_data.get(field, "—")
                    s_cols[i].metric(label=field.replace("_", " ").title(), value=str(val))

                if "metabolites" in custom_data:
                    st.subheader("Metabolites")
                    st.dataframe(
                        pd.DataFrame(custom_data["metabolites"]),
                        use_container_width=True,
                        hide_index=True,
                    )
            else:
                st.info(f"📂 Custom condition output not yet available for `{safe_name}`.")

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
            st.subheader("Step 5 — Validation")
            st.caption(
                "Draft-model quality checks — confirms FBA solvability, identifies dead-end metabolites, "
                "runs exchange FVA and gene essentiality analysis. "
                "Command: `python scripts/validate_mvp.py --model-dir data/models/MODEL_ID` "
                "and `python scripts/validate_mvp.py --model-dir data/models/MODEL_ID "
                "--mode theoretical_upper_bound --biomass-reaction bio2`"
            )

            _show_image_or_missing(
                mdir / "theoretical_upper_bound_validation_dashboard.png",
                caption="Validation Dashboard",
            )

            val_txt = mdir / "theoretical_upper_bound_validation_summary.txt"
            val_json_path = mdir / "theoretical_upper_bound_validation_summary.json"

            val_data = _show_json_or_missing(val_json_path)
            if val_data:
                val_fields = [
                    ("FBA Status", val_data.get("fba_status", "—")),
                    ("Objective Value", val_data.get("objective_value", "—")),
                    ("Dead-end Metabolites", val_data.get("dead_end_metabolites", "—")),
                    ("Produced Only", val_data.get("produced_only", "—")),
                    ("Consumed Only", val_data.get("consumed_only", "—")),
                    ("Exchange Reactions Tested", val_data.get("exchange_reactions_tested", "—")),
                    ("Gene Essentiality Status", val_data.get("gene_essentiality_status", "—")),
                    ("Essential Genes Found", val_data.get("essential_genes_found", "—")),
                ]
                v_cols = st.columns(4)
                for i, (label, value) in enumerate(val_fields):
                    v_cols[i % 4].metric(label=label, value=str(value))
            else:
                st.info("📂 Validation JSON not yet available.")

            st.subheader("Validation Text Summary")
            _show_text_or_missing(val_txt)

            st.divider()
            st.subheader("Detailed Validation Tables")

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
            st.subheader("Full Pipeline Intermediate Files")
            st.caption(
                "Intermediate outputs from all 12 pipeline steps, shown in execution order "
                "as described in installation.txt. Useful for troubleshooting and deeper analysis."
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
                    with st.expander(f"🔢 Step {step_num} — {step_label}"):
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
                    "No intermediate pipeline files found yet for this model. "
                    "Run the full pipeline (steps 1–12) to generate them."
                )

            st.divider()
            st.subheader("All files in model directory")
            if mdir.exists():
                all_files = sorted(mdir.iterdir())
                for f in all_files:
                    st.text(f"  {f.name}  ({f.stat().st_size:,} bytes)" if f.is_file() else f"  📁 {f.name}/")
            else:
                st.info("Model directory does not exist yet.")


# ════════════════════════════════════════════════
# TAB B: ML RECOMMENDER  (all existing ML functionality preserved)
# ════════════════════════════════════════════════
with ml_tab:
    with st.expander("ℹ️ How it works", expanded=False):
        st.markdown("""
**ℹ️ How the ML Recommender works**

1. **Train** — Learns from historical fungal growth experiments (carbon source, nitrogen, pH, temperature, etc.) to predict whether a given media condition supports growth.

2. **Recommend** — Given a new condition, ranks the most similar successful media conditions from the training data and suggests the top candidates.

3. **Retrain** — Upload new lab results as a CSV to continuously improve the model.

---
The underlying model uses a **Random Forest classifier** trained on tabular growth data.
Features include nutrient composition, environmental parameters, and strain metadata.
""")

    ml_train, ml_recs, ml_upload = st.tabs(["🤖 Train", "🔬 Recommendations", "🔄 Upload & Retrain"])

    # ── ML sub-tab 1: TRAIN ───────────────────────
    with ml_train:
        st.header("Train ML Models")

        if st.button("Train Model", type="primary", use_container_width=True):
            with st.spinner("Training… (1–2 min)"):
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
            st.subheader("Best Model per Target")
            st.dataframe(pd.DataFrame(best_rows), use_container_width=True, hide_index=True)

            fig = px.bar(
                df_scores,
                x="Target",
                y="CV R²",
                color="Model",
                barmode="group",
                title="Cross-Validation R² by Target & Model",
                color_discrete_sequence=px.colors.qualitative.Set2,
            )
            fig.update_layout(yaxis_range=[0, 1], height=350, margin=dict(t=40, b=10))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No model trained yet. Click 'Train Model' to begin.")

    # ── ML sub-tab 2: RECOMMENDATIONS ─────────────
    with ml_recs:
        st.header("Get Recommendations")

        meta = get_training_metadata()
        if not meta:
            st.warning("Please train the model first (Train tab).")
        else:
            col1, col2 = st.columns([2, 1])
            with col1:
                strain = st.selectbox("Strain", STRAINS)
            with col2:
                top_n = st.slider("Top N", 3, 10, 5)

            if st.button("Get Recommendations", type="primary"):
                with st.spinner("Evaluating 2,000 candidate conditions…"):
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
                        "📥 Download Lab Sheet (Excel)",
                        data=excel_bytes,
                        file_name=fname,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    )
                except Exception as e:
                    st.error(f"Export error: {e}")

    # ── ML sub-tab 3: UPLOAD & RETRAIN ────────────
    with ml_upload:
        st.header("Upload Results & Retrain")

        st.subheader("1 — Upload Lab Results")
        uploaded = st.file_uploader("Upload filled lab results CSV", type=["csv"])

        if uploaded:
            try:
                upload_df = pd.read_csv(uploaded)
                st.write(f"Loaded {len(upload_df)} rows, {len(upload_df.columns)} columns")
                st.dataframe(upload_df.head(), use_container_width=True)

                if st.button("✅ Validate & Ingest", type="primary"):
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

        st.subheader("2 — Retrain Model")
        df2 = load_combined()
        stats2 = get_dataset_stats(df2)
        st.caption(
            f"Dataset: {stats2['total_rows']} rows — {stats2['synthetic_rows']} synthetic, {stats2['real_rows']} real"
        )

        desc = st.text_input("Round description (optional)", placeholder="e.g. After first lab batch")
        if st.button("🔄 Retrain with All Data", type="primary"):
            with st.spinner("Retraining…"):
                try:
                    new_meta = retrain(description=desc)
                    st.success(f"Retrain complete! Round {get_current_round()}")
                    st.rerun()
                except Exception as e:
                    st.error(f"Retrain failed: {e}")

        history = compare_rounds()
        if history:
            st.subheader("Training History")
            st.dataframe(pd.DataFrame(history), use_container_width=True, hide_index=True)
