import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

from backend.config import STRAINS, TARGET_GROWTH, TARGET_BIOMASS, TARGET_BYPRODUCTS, TARGET_SCORE, ALL_TARGETS
from backend.data_loader import load_combined, get_dataset_stats
from backend.model_trainer import train_all, get_training_metadata
from backend.recommender import recommend
from backend.lab_exporter import recommendations_to_excel
from backend.data_ingestion import ingest_results
from backend.retrainer import retrain, get_retrain_history, compare_rounds, get_current_round

st.set_page_config(page_title="GEMS", page_icon="🍄", layout="wide")

# Session state init
if "recs" not in st.session_state:
    st.session_state["recs"] = {}

# ── Sidebar ────────────────────────────────
with st.sidebar:
    st.title("🍄 GEMS")
    st.caption("Fungal Growth Optimizer")
    st.divider()
    # Status from metadata + dataset stats
    meta = get_training_metadata()
    df = load_combined()
    stats = get_dataset_stats(df)
    st.markdown(f"**Model:** {'✅ Trained' if meta else '❌ Not trained'}")
    st.markdown(f"**Dataset:** {stats['total_rows']} rows ({stats['synthetic_rows']} synthetic, {stats['real_rows']} real)")
    st.markdown(f"**Round:** {get_current_round()}")

# ── Tabs ────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["🤖 Train", "🔬 Recommendations", "🔄 Upload & Retrain"])

# ── TAB 1: TRAIN ─────────────────────────────
with tab1:
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
        # show timestamp
        st.caption(f"Last trained: {meta.get('timestamp', '')[:19].replace('T', ' ')} UTC  |  {meta['n_samples']} samples")

        # Build CV scores table
        rows = []
        for target, info in meta["targets"].items():
            for mtype, score in info["cv_r2_scores"].items():
                rows.append({"Target": target, "Model": mtype, "CV R²": round(score, 3)})
        df_scores = pd.DataFrame(rows)

        # Best model table
        best_rows = [
            {"Target": t, "Best Model": info["best_model_type"], "CV R²": round(info["best_cv_r2"], 3)}
            for t, info in meta["targets"].items()
        ]
        st.subheader("Best Model per Target")
        st.dataframe(pd.DataFrame(best_rows), use_container_width=True, hide_index=True)

        # Chart: grouped bar of CV R² by target
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

# ── TAB 2: RECOMMENDATIONS ────────────────────
with tab2:
    st.header("Get Recommendations")

    meta = get_training_metadata()
    if not meta:
        st.warning("Please train the model first (Tab 1).")
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

            # Results table
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

            # Score vs uncertainty scatter
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

            # Download
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

# ── TAB 3: UPLOAD & RETRAIN ───────────────────
with tab3:
    st.header("Upload Results & Retrain")

    # Upload section
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

    # Retrain section
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

    # History
    history = compare_rounds()
    if history:
        st.subheader("Training History")
        st.dataframe(pd.DataFrame(history), use_container_width=True, hide_index=True)
