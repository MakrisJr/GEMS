# Template Comparison Report

Side-by-side comparison of the main MVP outputs for two template builds.

## Summary Table

| Metric | Core Template + RAST | Fungal Template + RAST |
| --- | --- | --- |
| Template | template_core (builtin) | fungi (local) |
| Reactions | 112 | 928 |
| Metabolites | 119 | 1121 |
| Genes | 164 | 635 |
| Exchanges | 13 | 29 |
| Baseline objective | 0.0 | 0.0 |
| Theoretical biomass reaction | bio2 | bio1 |
| Theoretical upper bound | 66.65535545483192 | 33.333333333333336 |
| Theoretical yield proxy | 0.0056860019161826475 | 0.004433556020975969 |
| Best preset condition | Full Precursor Set | Full Biomass Support |
| Best preset rate | 31.79062272001634 | 33.333333333333336 |
| Custom condition | compare_custom | compare_custom |
| Custom rate | 31.790622720016415 | 31.226115864376748 |
| Dead-end metabolites | 24 | 181 |
| Added validation boundaries | 21 | 6 |

## Main Output Files

- Core Template + RAST: `data/models/template_core_mvp_compare_rast`
- Fungal Template + RAST: `data/models/fungi_template_mvp_compare_rast`

## MVP Mode Comparison

<table>
  <tr>
    <th>Core Template + RAST</th>
    <th>Fungal Template + RAST</th>
  </tr>
  <tr>
    <td><img src="../../data/models/template_core_mvp_compare_rast/mvp_mode_comparison.png" width="100%"></td>
    <td><img src="../../data/models/fungi_template_mvp_compare_rast/mvp_mode_comparison.png" width="100%"></td>
  </tr>
</table>

## Theoretical Upper Bound Plot

<table>
  <tr>
    <th>Core Template + RAST</th>
    <th>Fungal Template + RAST</th>
  </tr>
  <tr>
    <td><img src="../../data/models/template_core_mvp_compare_rast/theoretical_upper_bound.png" width="100%"></td>
    <td><img src="../../data/models/fungi_template_mvp_compare_rast/theoretical_upper_bound.png" width="100%"></td>
  </tr>
</table>

## Preset Conditions Plot

<table>
  <tr>
    <th>Core Template + RAST</th>
    <th>Fungal Template + RAST</th>
  </tr>
  <tr>
    <td><img src="../../data/models/template_core_mvp_compare_rast/preset_conditions.png" width="100%"></td>
    <td><img src="../../data/models/fungi_template_mvp_compare_rast/preset_conditions.png" width="100%"></td>
  </tr>
</table>

## Custom Condition Plot

<table>
  <tr>
    <th>Core Template + RAST</th>
    <th>Fungal Template + RAST</th>
  </tr>
  <tr>
    <td><img src="../../data/models/template_core_mvp_compare_rast/custom_condition_compare_custom.png" width="100%"></td>
    <td><img src="../../data/models/fungi_template_mvp_compare_rast/custom_condition_compare_custom.png" width="100%"></td>
  </tr>
</table>

## Theoretical Validation Dashboard

<table>
  <tr>
    <th>Core Template + RAST</th>
    <th>Fungal Template + RAST</th>
  </tr>
  <tr>
    <td><img src="../../data/models/template_core_mvp_compare_rast/theoretical_upper_bound_validation_dashboard.png" width="100%"></td>
    <td><img src="../../data/models/fungi_template_mvp_compare_rast/theoretical_upper_bound_validation_dashboard.png" width="100%"></td>
  </tr>
</table>

## Notes

- The comparison uses the same input FASTA for both runs.
- Theoretical mode can use different biomass-like reactions if a template does not contain `bio2`.
- Preset and custom conditions are still draft-model screening tools, not wet-lab media recommendations.
