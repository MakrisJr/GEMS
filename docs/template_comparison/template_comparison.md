# Template Comparison Report

Side-by-side comparison of the main MVP outputs for two template builds.

## Summary Table

| Metric | Core Template | Fungal Template |
| --- | --- | --- |
| Template | template_core (builtin) | fungi (local) |
| Reactions | 9 | 21 |
| Metabolites | 27 | 91 |
| Genes | 0 | 0 |
| Exchanges | 3 | 5 |
| Baseline objective | 0.0 | 0.0 |
| Theoretical biomass reaction | bio2 | bio1 |
| Theoretical upper bound | 21.44703119470687 | 16.666666666666664 |
| Theoretical yield proxy | 0.004170091354191296 | 0.003317559669795195 |
| Best preset condition | Full Precursor Set | Full Precursor Set |
| Best preset rate | 0.0 | 0.0 |
| Custom condition | compare_custom | compare_custom |
| Custom rate | 0.0 | 0.0 |
| Dead-end metabolites | 23 | 52 |
| Added validation boundaries | 21 | 45 |

## Main Output Files

- Core Template: `data/models/template_core_mvp_compare`
- Fungal Template: `data/models/fungi_template_mvp_compare`

## MVP Mode Comparison

<table>
  <tr>
    <th>Core Template</th>
    <th>Fungal Template</th>
  </tr>
  <tr>
    <td><img src="../../data/models/template_core_mvp_compare/mvp_mode_comparison.png" width="100%"></td>
    <td><img src="../../data/models/fungi_template_mvp_compare/mvp_mode_comparison.png" width="100%"></td>
  </tr>
</table>

## Theoretical Upper Bound Plot

<table>
  <tr>
    <th>Core Template</th>
    <th>Fungal Template</th>
  </tr>
  <tr>
    <td><img src="../../data/models/template_core_mvp_compare/theoretical_upper_bound.png" width="100%"></td>
    <td><img src="../../data/models/fungi_template_mvp_compare/theoretical_upper_bound.png" width="100%"></td>
  </tr>
</table>

## Preset Conditions Plot

<table>
  <tr>
    <th>Core Template</th>
    <th>Fungal Template</th>
  </tr>
  <tr>
    <td><img src="../../data/models/template_core_mvp_compare/preset_conditions.png" width="100%"></td>
    <td><img src="../../data/models/fungi_template_mvp_compare/preset_conditions.png" width="100%"></td>
  </tr>
</table>

## Custom Condition Plot

<table>
  <tr>
    <th>Core Template</th>
    <th>Fungal Template</th>
  </tr>
  <tr>
    <td><img src="../../data/models/template_core_mvp_compare/custom_condition_compare_custom.png" width="100%"></td>
    <td><img src="../../data/models/fungi_template_mvp_compare/custom_condition_compare_custom.png" width="100%"></td>
  </tr>
</table>

## Theoretical Validation Dashboard

<table>
  <tr>
    <th>Core Template</th>
    <th>Fungal Template</th>
  </tr>
  <tr>
    <td><img src="../../data/models/template_core_mvp_compare/theoretical_upper_bound_validation_dashboard.png" width="100%"></td>
    <td><img src="../../data/models/fungi_template_mvp_compare/theoretical_upper_bound_validation_dashboard.png" width="100%"></td>
  </tr>
</table>

## Notes

- The comparison uses the same input FASTA for both runs.
- Theoretical mode can use different biomass-like reactions if a template does not contain `bio2`.
- Preset and custom conditions are still draft-model screening tools, not wet-lab media recommendations.
