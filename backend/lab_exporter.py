"""Generate lab-ready Excel sheets from recommendations."""
import pandas as pd
import numpy as np
from io import BytesIO
from datetime import datetime
from typing import List, Dict, Any
from .config import ALL_FEATURES, NUMERIC_FEATURES


def recommendations_to_excel(recs: Dict[str, Any], n_replicates: int = 3) -> bytes:
    """
    Convert recommendations dict (from recommender.recommend()) to an Excel workbook.

    Sheets:
    1. Summary       - strain, date, top recommendations ranked
    2. Conditions    - full condition parameters for each recommended run
    3. Lab Template  - blank table for scientists to fill in observed results

    Returns bytes of the .xlsx file.
    """
    strain = recs["strain"]
    all_recs = recs["exploit"] + recs["explore"]
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:

        # --- Sheet 1: Summary ---
        summary_rows = []
        for r in all_recs:
            summary_rows.append({
                "Rank":              r["rank"],
                "Run Type":          r["run_type"].upper(),
                "Condition ID":      f"COND-{r['rank']:02d}",
                "Predicted Score":   round(r["predicted_score"], 4),
                "Predicted Growth (h-1)": round(r["predicted_growth_rate"], 5),
                "Predicted Biomass (g/L)": round(r["predicted_biomass"], 3),
                "Predicted Byproducts (g/L)": round(r["predicted_byproducts"], 3),
                "Uncertainty (score)": round(r["uncertainty_score"], 4),
                "Notes": "",
            })
        df_summary = pd.DataFrame(summary_rows)
        df_summary.insert(0, "Strain", strain)
        df_summary.insert(1, "Generated", timestamp)
        df_summary.to_excel(writer, sheet_name="Summary", index=False)

        # --- Sheet 2: Conditions ---
        cond_rows = []
        for r in all_recs:
            row = {"Condition ID": f"COND-{r['rank']:02d}", "Strain": strain, "Run Type": r["run_type"].upper()}
            for feat in ALL_FEATURES:
                if feat in r:
                    row[feat] = r[feat]
            for k in ["predicted_score", "predicted_growth_rate", "predicted_biomass",
                       "predicted_byproducts", "uncertainty_score"]:
                row[k] = round(r[k], 5)
            cond_rows.append(row)
        pd.DataFrame(cond_rows).to_excel(writer, sheet_name="Conditions", index=False)

        # --- Sheet 3: Lab Template ---
        template_rows = []
        for r in all_recs:
            for rep in range(1, n_replicates + 1):
                row = {
                    "Condition ID":       f"COND-{r['rank']:02d}",
                    "Replicate":          rep,
                    "Batch ID":           "",
                    "Experiment Date":    "",
                    "Strain":             strain,
                    "Predicted Score":    round(r["predicted_score"], 4),
                }
                # Condition parameters (pre-filled)
                for feat in ALL_FEATURES:
                    if feat in r:
                        row[feat] = r[feat]
                # Observation columns (blank for lab to fill)
                row["observed_growth_rate_h_inv"] = ""
                row["observed_biomass_g_L"]        = ""
                row["observed_byproducts_g_L"]     = ""
                row["notes"]                       = ""
                template_rows.append(row)
        pd.DataFrame(template_rows).to_excel(writer, sheet_name="Lab Template", index=False)

    return buf.getvalue()
