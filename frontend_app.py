"""Streamlit frontend that talks to the FastAPI backend for pipeline runs."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
import requests
import streamlit as st


DEFAULT_BACKEND_URL = os.environ.get("BACKEND_URL", "http://127.0.0.1:8000")


def _load_json(path: Path) -> Optional[Dict[str, Any]]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None


def _load_csv(path: Path) -> Optional[pd.DataFrame]:
    try:
        return pd.read_csv(path)
    except Exception:  # noqa: BLE001
        return None


def _metric_row(cols, items):
    for col, (label, value) in zip(cols, items):
        col.metric(label, value)


def _safe_exists(path: Path) -> Optional[Path]:
    return path if path.exists() else None


def _post_pipeline(file_path: Path, backend_url: str) -> dict:
    with file_path.open("rb") as handle:
        files = {"file": (file_path.name, handle, "application/octet-stream")}
        response = requests.post(f"{backend_url}/run", files=files)
        response.raise_for_status()
        return response.json()


# Base directory of frontend_app.py (i.e. GEMS/)
_GEMS_DIR = Path(__file__).resolve().parent


def _run_cli(cmd):
    proc = subprocess.run(cmd, cwd=_GEMS_DIR, capture_output=True, text=True)
    return proc.returncode, proc.stdout, proc.stderr


def _run_analyze_mvp(model_dir: Path, mode: str, custom_media_path: Optional[Path] = None):
    """Run analyze_mvp.py with the given mode and optional custom metabolite-IDs file.

    For custom mode the uploaded file is expected to contain metabolite IDs, one per line
    or comma-separated.  Its contents are forwarded as --metabolite-ids.
    """
    script = _GEMS_DIR / "scripts" / "analyze_mvp.py"
    cmd = [sys.executable, str(script), "--model-dir", str(model_dir), "--mode", mode]
    if mode == "custom" and custom_media_path is not None:
        # Parse metabolite IDs from the uploaded file (newline- or comma-separated)
        raw = custom_media_path.read_text(encoding="utf-8", errors="ignore")
        met_ids = ",".join(
            m.strip() for m in raw.replace("\n", ",").split(",") if m.strip()
        )
        if met_ids:
            cmd += ["--metabolite-ids", met_ids]
    rc, out, err = _run_cli(cmd)
    return rc, out, err


def _display_mvp_results(model_dir: Path, mode: str, mvp_rc: int, mvp_out: str):
    """Render the MVP analysis results for a single mode in a friendly card layout."""
    mode_labels = {
        "theoretical": "Theoretical Upper Bound",
        "preset": "Preset Conditions",
        "custom": "Custom Condition",
    }
    st.markdown(f"##### {mode_labels.get(mode, mode)}")

    if mvp_rc != 0:
        st.error(f"❌ analyze_mvp --mode {mode} failed (rc={mvp_rc})")
        return

    # Parse stdout for key metrics
    lines = mvp_out.strip().splitlines() if mvp_out else []
    kv: Dict[str, str] = {}
    list_items: List[str] = []
    capture_list = False
    for line in lines:
        if line.strip() == "Metabolites used:":
            capture_list = True
        elif capture_list and line.strip():
            list_items.append(line.strip())
        elif ":" in line and not capture_list:
            k, _, v = line.partition(":")
            k, v = k.strip(), v.strip()
            if k and v:
                kv[k] = v

    _METRIC_KEYS = {
        "bio2 rate": "bio2 growth rate",
        "Yield proxy": "Yield proxy",
        "Status": "Status",
        "Best bio2 rate": "Best bio2 rate",
        "Best yield proxy": "Best yield proxy",
        "Best condition": "Best condition",
        "Number of conditions": "# conditions",
        "Condition": "Condition",
    }
    metric_items = [(label, kv[k]) for k, label in _METRIC_KEYS.items() if k in kv]
    if metric_items:
        mcols = st.columns(min(len(metric_items), 4))
        for i, (label, value) in enumerate(metric_items):
            mcols[i % len(mcols)].metric(label, value)

    if list_items:
        st.markdown("**Metabolites used:**")
        st.write(", ".join(list_items))

    # Display mode-specific output files
    MODE_FILE_PREFIXES = {
        "theoretical": ["theoretical_upper_bound", "mvp_mode_comparison"],
        "preset": ["preset_benchmark", "mvp_mode_comparison"],
        "custom": ["custom_condition", "mvp_mode_comparison"],
    }
    prefixes = MODE_FILE_PREFIXES.get(mode, [])

    def _matches(p: Path) -> bool:
        return any(p.stem.startswith(pf) for pf in prefixes)

    mvp_files = sorted(p for p in model_dir.rglob("*") if p.is_file() and _matches(p))

    if not mvp_files:
        return

    img_files = [p for p in mvp_files if p.suffix.lower() in {".png", ".jpg", ".jpeg"}]
    if img_files:
        img_cols = st.columns(min(len(img_files), 2))
        for i, img_path in enumerate(img_files):
            with img_cols[i % len(img_cols)]:
                st.image(str(img_path), caption=img_path.name, use_container_width=True)

    json_files = [p for p in mvp_files if p.suffix.lower() == ".json"]
    for jp in json_files:
        data = _load_json(jp)
        if data is None:
            continue
        with st.expander(f"📄 {jp.name}", expanded=True):
            if isinstance(data, list):
                df_j = pd.DataFrame(data)
                if not df_j.empty:
                    st.dataframe(df_j)
            elif isinstance(data, dict):
                scalars = {k: v for k, v in data.items() if not isinstance(v, (list, dict))}
                lists = {k: v for k, v in data.items() if isinstance(v, list)}
                if scalars:
                    s_cols = st.columns(min(len(scalars), 4))
                    for i, (k, v) in enumerate(scalars.items()):
                        s_cols[i % len(s_cols)].metric(k, str(v))
                for k, lst in lists.items():
                    if lst:
                        st.caption(k)
                        st.dataframe(
                            pd.DataFrame(lst) if isinstance(lst[0], dict) else pd.DataFrame({k: lst})
                        )
            st.download_button(
                f"⬇️ Download {jp.name}",
                jp.read_bytes(),
                file_name=jp.name,
                key=f"dl_{mode}_{jp.stem}",
            )

    csv_files = [p for p in mvp_files if p.suffix.lower() == ".csv"]
    for cp in csv_files:
        df_c = _load_csv(cp)
        if df_c is not None:
            with st.expander(f"📊 {cp.name}", expanded=True):
                st.dataframe(df_c)
                st.download_button(
                    f"⬇️ Download {cp.name}",
                    cp.read_bytes(),
                    file_name=cp.name,
                    key=f"dl_{mode}_{cp.stem}",
                )


def main():
    st.set_page_config(page_title="Fungal ModelSEED Pipeline", layout="wide")
    st.title("Fungal ModelSEED Pipeline")
    st.caption("Upload a protein FASTA (.faa) and run the ModelSEED workflow")

    backend_url = DEFAULT_BACKEND_URL

    uploaded_file = st.file_uploader("Protein FASTA (.faa)", type=["faa"])

    st.markdown("---")
    st.markdown("#### MVP Analysis options")
    st.caption("Theoretical and Preset modes always run. Enable Custom to also run a user-defined condition.")

    add_custom = st.checkbox("Add custom condition", value=False)

    custom_media_file = None
    if add_custom:
        custom_media_file = st.file_uploader(
            "Custom metabolite IDs file",
            type=None,
            key="custom_media_uploader",
            help=(
                "Plain-text file containing metabolite IDs to test, one per line "
                "or comma-separated. Passed to analyze_mvp --mode custom --metabolite-ids."
            ),
        )

    st.markdown("---")

    run_clicked = st.button("Run pipeline", type="primary", disabled=uploaded_file is None)

    status_placeholder = st.empty()

    if run_clicked and uploaded_file is not None:
        with tempfile.NamedTemporaryFile(suffix=".faa", delete=False) as tmp:
            tmp.write(uploaded_file.read())
            tmp_path = Path(tmp.name)

        try:
            status_placeholder.info("Sending to backend…")
            result = _post_pipeline(tmp_path, backend_url)
        except Exception as exc:  # noqa: BLE001
            status_placeholder.error(f"Pipeline failed: {exc}")
            return
        finally:
            tmp_path.unlink(missing_ok=True)

        status_placeholder.success("Pipeline completed")

        st.subheader("Results")

        model_id = result.get("model_id")
        if not model_id:
            return

        model_dir = Path("data") / "models" / model_id
        st.markdown(f"**Model ID:** `{model_id}`")
        st.markdown(f"**Model directory:** `{model_dir}`")

        if not model_dir.exists():
            st.error("Model directory does not exist yet.")
            return

        files = [p for p in model_dir.rglob("*") if p.is_file()]
        files_sorted = sorted(files)
        st.markdown(f"Found {len(files_sorted)} files under `{model_dir}`")

        # Helper lookups
        def find(name: str) -> Optional[Path]:
            p = model_dir / name
            return p if p.exists() else None

        genome_summary = _safe_exists(Path("data") / "intermediate" / "genome_summary.json")
        model_summary_json = find("model_summary.json")
        gapfill_summary_json = find("gapfill_summary.json")
        model_overview_json = find("model_overview.json")
        baseline_json = find("baseline_optimization.json")
        exchanges_csv = find("exchanges.csv")
        media_screen_json = find("media_screen.json")
        media_screen_png = find("media_screen.png")
        media_screen_csv = find("media_screen.csv")
        exchange_diag_json = find("exchange_diagnosis.json")
        exchange_metabolites_csv = find("exchange_metabolites.csv")
        debug_growth_json = find("debug_growth.json")
        oracle_growth_json = find("oracle_growth.json")
        oracle_medium_json = find("oracle_medium_screen.json")
        oracle_medium_png = find("oracle_medium_screen.png")
        oracle_medium_csv = find("oracle_medium_screen.csv")
        bio2_json = find("bio2_benchmark.json")
        bio2_png = find("bio2_benchmark.png")
        bio2_csv = find("bio2_benchmark.csv")
        selected_condition_json = next(
            (p for p in files_sorted if p.name.startswith("selected_condition_") and p.suffix == ".json"),
            None,
        )

        # Load data
        genome_data = _load_json(genome_summary) if genome_summary else None
        model_data = _load_json(model_summary_json) if model_summary_json else None
        gapfill_data = _load_json(gapfill_summary_json) if gapfill_summary_json else None
        overview_data = _load_json(model_overview_json) if model_overview_json else None
        baseline_data = _load_json(baseline_json) if baseline_json else None
        exchanges_df = _load_csv(exchanges_csv) if exchanges_csv else None
        media_screen_data = _load_json(media_screen_json) if media_screen_json else None
        media_screen_df = _load_csv(media_screen_csv) if media_screen_csv else None
        exchange_diag_data = _load_json(exchange_diag_json) if exchange_diag_json else None
        exchange_met_df = _load_csv(exchange_metabolites_csv) if exchange_metabolites_csv else None
        debug_growth_data = _load_json(debug_growth_json) if debug_growth_json else None
        oracle_growth_data = _load_json(oracle_growth_json) if oracle_growth_json else None
        oracle_medium_data = _load_json(oracle_medium_json) if oracle_medium_json else None
        oracle_medium_df = _load_csv(oracle_medium_csv) if oracle_medium_csv else None
        bio2_data = _load_json(bio2_json) if bio2_json else None
        bio2_df = _load_csv(bio2_csv) if bio2_csv else None
        selected_condition_data = _load_json(selected_condition_json) if selected_condition_json else None

        # Hero summary (compact metrics)
        st.markdown("### Summary")
        hero_cols = st.columns(4)
        _metric_row(
            hero_cols,
            [
                ("Reactions", overview_data.get("n_reactions") if overview_data else "-"),
                ("Metabolites", overview_data.get("n_metabolites") if overview_data else "-"),
                ("Genes", overview_data.get("n_genes") if overview_data else "-"),
                (
                    "Objective",
                    baseline_data.get("objective_value") if baseline_data else "-",
                ),
            ],
        )

        # Tabs per step
        tabs = st.tabs(
            [
                "1 Genome",
                "2-4 Draft/Gapfill",
                "5 COBRA",
                "6 Media",
                "7 Exchange diag",
                "8 Growth debug",
                "9 Oracle growth",
                "10 Oracle medium",
                "11 bio2 benchmark",
                "12 Condition",
                "Files",
            ]
        )

        def preview_table(df: pd.DataFrame, n: int = 20):
            st.dataframe(df.head(n))

        # Step 1
        with tabs[0]:
            if genome_data:
                st.metric("Features", genome_data.get("n_features", "-"))
                st.caption("Genome summary (download for full details)")
                st.download_button(
                    "Download genome_summary.json",
                    genome_summary.read_bytes(),
                    file_name="genome_summary.json",
                )
            else:
                st.info("No genome_summary.json found.")

        # Steps 2-4
        with tabs[1]:
            cols = st.columns(3)
            _metric_row(
                cols,
                [
                    ("Reactions", model_data.get("n_reactions") if model_data else "-"),
                    ("Metabolites", model_data.get("n_metabolites") if model_data else "-"),
                    ("Genes", model_data.get("n_genes") if model_data else "-"),
                ],
            )
            if gapfill_data:
                st.write(
                    f"Gapfill attempted: {gapfill_data.get('gapfill_attempted')} | Success: {gapfill_data.get('gapfill_success')}"
                )
                st.write(
                    f"Reactions {gapfill_data.get('reactions_before')} → {gapfill_data.get('reactions_after')} | Metabolites {gapfill_data.get('metabolites_before')} → {gapfill_data.get('metabolites_after')}"
                )
            if (model_dir / "model.xml").exists():
                st.download_button(
                    "Download model.xml",
                    (model_dir / "model.xml").read_bytes(),
                    file_name="model.xml",
                )

        # Step 5
        with tabs[2]:
            if baseline_data:
                st.write(f"Baseline status: {baseline_data.get('status')} | Objective: {baseline_data.get('objective_value')}")
            if exchanges_df is not None:
                st.caption("Exchange reactions (first 20)")
                preview_table(exchanges_df)
            if model_overview_json:
                st.download_button(
                    "Download model_overview.json",
                    model_overview_json.read_bytes(),
                    file_name="model_overview.json",
                )

        # Step 6
        with tabs[3]:
            if media_screen_png and media_screen_png.exists():
                st.image(str(media_screen_png))
            if media_screen_df is not None:
                st.caption("Media screen (top 20)")
                preview_table(media_screen_df)

        # Step 7
        with tabs[4]:
            if exchange_met_df is not None:
                st.caption("Exchange metabolites (first 20)")
                preview_table(exchange_met_df)
            if exchange_diag_data:
                st.write(
                    f"Exchanges: {exchange_diag_data.get('n_exchanges')} | Carbon-containing: {exchange_diag_data.get('n_carbon_containing_exchanges')} | Plausible sources: {exchange_diag_data.get('n_plausible_carbon_sources')}"
                )

        # Step 8
        with tabs[5]:
            if debug_growth_data:
                st.write(
                    f"Objective: {debug_growth_data.get('objective', '-')}; Status: {debug_growth_data.get('optimization', {}).get('status', '-')}; Value: {debug_growth_data.get('optimization', {}).get('objective_value', '-') }"
                )
                ex_df = pd.DataFrame(debug_growth_data.get("first_20_exchanges", []))
                if not ex_df.empty:
                    st.caption("First 20 exchanges")
                    preview_table(ex_df)
            else:
                st.info("No debug_growth.json found.")

        # Step 9
        with tabs[6]:
            if oracle_growth_data:
                st.write(
                    f"Status: {oracle_growth_data.get('status', '-')} | Objective: {oracle_growth_data.get('objective_value', '-')} | Added boundaries: {oracle_growth_data.get('n_added_boundaries', 0)}"
                )
            else:
                st.info("No oracle_growth.json found.")

        # Step 10
        with tabs[7]:
            if oracle_medium_png and oracle_medium_png.exists():
                st.image(str(oracle_medium_png))
            if oracle_medium_df is not None:
                st.caption("Oracle medium screen (top 20)")
                preview_table(oracle_medium_df)

        # Step 11
        with tabs[8]:
            if bio2_png and bio2_png.exists():
                st.image(str(bio2_png))
            if bio2_df is not None:
                st.caption("bio2 benchmark (top 20)")
                preview_table(bio2_df)

        # Step 12
        with tabs[9]:
            if selected_condition_data:
                st.write(
                    f"Condition: {selected_condition_data.get('condition', '')} | Rank: {selected_condition_data.get('rank', '')} | Predicted growth: {selected_condition_data.get('predicted_growth', '')} | Status: {selected_condition_data.get('status', '')}"
                )
                mets = pd.DataFrame(selected_condition_data.get("metabolite_details", []))
                if not mets.empty:
                    preview_table(mets)
            else:
                st.info("No selected_condition_* files found.")

        # Files
        with tabs[10]:
            if files_sorted:
                selected = st.selectbox(
                    "Select any file to preview",
                    options=[str(p.relative_to(model_dir)) for p in files_sorted],
                )
                selected_path = model_dir / selected
                suffix = selected_path.suffix.lower()
                if suffix in {".csv", ".tsv"}:
                    df = pd.read_csv(selected_path, sep="\t" if suffix == ".tsv" else ",")
                    preview_table(df)
                elif suffix in {".json"}:
                    st.code(selected_path.read_text(encoding="utf-8", errors="ignore"), language="json")
                elif suffix in {".png", ".jpg", ".jpeg"}:
                    st.image(str(selected_path))
                else:
                    st.code(selected_path.read_text(encoding="utf-8", errors="ignore"), language="text")
            else:
                st.info("No files found.")

        # ── Run analyze_mvp after step 12: always theoretical + preset, optionally custom ──
        st.markdown("---")
        st.markdown("### MVP Analysis")

        modes_to_run: List[str] = ["theoretical", "preset"]
        custom_media_tmp: Optional[Path] = None

        if add_custom:
            if custom_media_file is not None:
                with tempfile.NamedTemporaryFile(
                    delete=False,
                    suffix=Path(custom_media_file.name).suffix or ".txt",
                ) as mt:
                    mt.write(custom_media_file.read())
                    custom_media_tmp = Path(mt.name)
                modes_to_run.append("custom")
            else:
                st.warning(
                    "⚠️ Custom condition enabled but no metabolite IDs file uploaded — "
                    "skipping custom mode."
                )

        mvp_results: Dict[str, tuple] = {}
        for mode in modes_to_run:
            with st.spinner(f"Running analyze_mvp --mode {mode}…"):
                rc, out, err = _run_analyze_mvp(
                    model_dir,
                    mode,
                    custom_media_tmp if mode == "custom" else None,
                )
            mvp_results[mode] = (rc, out)

        if custom_media_tmp is not None:
            custom_media_tmp.unlink(missing_ok=True)

        # One tab per mode
        tab_labels = [m.capitalize() for m in modes_to_run]
        mvp_tabs = st.tabs(tab_labels)
        for tab, mode in zip(mvp_tabs, modes_to_run):
            with tab:
                rc, out = mvp_results[mode]
                _display_mvp_results(model_dir, mode, rc, out)


if __name__ == "__main__":
    main()
