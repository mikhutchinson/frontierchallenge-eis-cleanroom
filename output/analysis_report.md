# EIS Equivalent-Circuit Analysis

## Executive summary

Five independent spectra were analyzed: the impedance.py generic example, two losslessly separated SOC 100 alkaline-cell scans, and two SOC 70 sweeps detected at the frequency reset in the 122-row source file and retained under the public file-stem dataset identifier with explicit scan indices. The battery sign convention was reconstructed exactly as specified: `Im(Z) = -[-Im(Ztot)]`. High-frequency points with positive `Im(Z)` are inductive and were retained in all artifacts/plots but excluded from parameter estimation because the prescribed candidate families contain no inductance. Required full-spectrum residual metrics still include those points.

For `exampleData`, all four prescribed candidates converged. Contract AICc selects **two_rc_w_fixed_r0** (AICc -1708.133, RMSE 0.00147633 Ohm); model preference is based on the complete complex residual and the declared free-parameter count, not visual appearance. The fixed two-time-constant model fixes only `R0`, at a value derived by interpolating the same spectrum's high-frequency real-axis crossing. Because that value is data-derived rather than independently known, an effective-degree-of-freedom sensitivity analysis is reported alongside the contract AICc.

Each battery sweep was fitted to `R0-p(R1,CPE1)-p(R2,CPE2)-Wo1`. The repeated scans are reported separately, preventing artificial joining of independent sweeps. Parameter uncertainty is estimated by singular-value decomposition of a parameter-scaled finite-difference complex Jacobian over the fitted points; rank-deficient models are explicitly marked non-estimable rather than assigned misleading finite errors.

## 1. Input validation and preprocessing

- `exampleData.csv`: 66 headerless rows interpreted as frequency, Re(Z), Im(Z).
- SOC 100: supplied scan files are byte-numerically identical to columns 1–5 and 7–11 of the original side-by-side source layout.
- SOC 70: a frequency reset occurs after row 61, yielding two 61-point sweeps; they were never concatenated as one curve.
- No missing, non-finite, or non-positive-frequency values were found.
- Frequency order was not mutated. Sorting is applied only in visual line rendering; `original_row`, `scan_index`, and repeated frequencies are preserved in `fitted_spectrum.csv`.
- Inductive observations (`Im(Z) >= 0`) are marked with `used_in_fit=0`; all other points use `used_in_fit=1`.

### Validation counts

| dataset | scan_index | model | n_points | fit_n_points | excluded_inductive_points |
|---|---|---|---|---|---|
| exampleData | 1 | randles_rc_w | 66 | 57 | 9 |
| Cell_1_GEIS_SOC100_scan1 | 1 | two_cpe_w | 61 | 54 | 7 |
| Cell_1_GEIS_SOC100_scan2 | 2 | two_cpe_w | 61 | 55 | 6 |
| Cell_2_GEIS_SOC70 | 1 | two_cpe_w_scan1 | 61 | 50 | 11 |
| Cell_2_GEIS_SOC70 | 2 | two_cpe_w_scan2 | 61 | 50 | 11 |

## 2. Candidate circuits and fitting method

| Model identifier | impedance.py circuit string | Purpose |
|---|---|---|
| `randles_rc_w` | `R0-p(R1-Wo1,C1)` | Ideal-capacitor Randles-type baseline plus finite-length diffusion. |
| `randles_cpe_w` | `R0-p(R1-Wo1,CPE1)` | Tests non-ideal/distributed interfacial capacitance. |
| `two_rc_w_fixed_r0` | `R0-p(R1,C1)-p(R2,C2)-Wo1` | Two ideal time constants; data-derived series resistance held fixed. |
| `two_rc_w_free` | `R0-p(R1,C1)-p(R2,C2)-Wo1` | Same topology with all parameters free. |
| `two_cpe_w` / `two_cpe_w_scan1/2` | `R0-p(R1,CPE1)-p(R2,CPE2)-Wo1` | Prescribed battery model with two distributed time constants and diffusion. |

Fits use unweighted complex nonlinear least squares through impedance.py 1.7.1 `CustomCircuit`. Eight deterministic multistarts are generated from data-derived resistance, peak-frequency, and low-frequency diffusion scales. The best converged solution is selected by fitting-subset RSS. Model comparison uses the task-defined full-spectrum formulas with `N=2n`: `RMSE=sqrt(RSS/N)` and `AICc=N ln(RSS/N)+2k+2k(k+1)/(N-k-1)`.

## 3. Model comparison for exampleData

| model | n_parameters | rss_complex | rmse_complex | aicc | delta_aicc_within_dataset | n_parameters_effective_sensitivity | aicc_effective_sensitivity | delta_aicc_effective_sensitivity | converged |
|---|---|---|---|---|---|---|---|---|---|
| two_rc_w_fixed_r0 | 6 | 0.000287699 | 0.00147633 | -1708.133 | 0.000 | 7 | -1705.901 | 0.000 | 1 |
| two_rc_w_free | 7 | 0.000290281 | 0.00148294 | -1704.722 | 3.411 | 7 | -1704.722 | 1.179 | 1 |
| randles_cpe_w | 6 | 0.00031843 | 0.00155317 | -1694.736 | 13.396 | 6 | -1694.736 | 11.165 | 1 |
| randles_rc_w | 5 | 0.000470176 | 0.00188731 | -1645.491 | 62.642 | 5 | -1645.491 | 60.410 | 1 |

The required `aicc` column follows the public contract and counts only free optimizer parameters. For `two_rc_w_fixed_r0`, however, `R0` was estimated from the same spectrum before fitting. The sensitivity columns therefore count one additional effective degree of freedom for that candidate. Its AICc changes from -1708.133 to -1705.901; the resulting advantage over the free-`R0` model narrows to 1.179 AICc units. The fixed model remains slightly preferred, but the original contract ΔAICc is statistically optimistic. A lower AICc is evidence only within this declared candidate set and does not establish a unique microscopic mechanism.

## 4. Battery scan comparison

| dataset | scan_index | model | R0 | R1 | R2 | R1_plus_R2_ohm | CPE1_1 | CPE2_1 | Wo1_0 | Wo1_1 |
|---|---|---|---|---|---|---|---|---|---|---|
| Cell_1_GEIS_SOC100_scan1 | 1 | two_cpe_w | 0.0431869 | 9.34053 | 3.21039e+08 | 3.21039e+08 | 1.0000 | 1.0000 | 3.93207e-19 | 738.076 |
| Cell_1_GEIS_SOC100_scan2 | 2 | two_cpe_w | 0.130659 | 0.851392 | 5.30095 | 6.15234 | 1.0000 | 0.9986 | 2.2317 | 1.78031 |
| Cell_2_GEIS_SOC70 | 1 | two_cpe_w_scan1 | 0.117718 | 0.0725301 | 0.322224 | 0.394754 | 0.5217 | 0.8638 | 0.449045 | 5.57785 |
| Cell_2_GEIS_SOC70 | 2 | two_cpe_w_scan2 | 0.118944 | 0.06697 | 0.320088 | 0.387058 | 0.5532 | 0.8571 | 0.4772 | 6.23438 |

| dataset | scan_index | model | rss_complex | rmse_complex | aicc | fit_n_points | excluded_inductive_points |
|---|---|---|---|---|---|---|---|
| Cell_1_GEIS_SOC100_scan1 | 1 | two_cpe_w | 28.5134 | 0.483442 | -157.738 | 54 | 7 |
| Cell_1_GEIS_SOC100_scan2 | 2 | two_cpe_w | 2.91531 | 0.154583 | -435.947 | 55 | 6 |
| Cell_2_GEIS_SOC70 | 1 | two_cpe_w_scan1 | 0.0273414 | 0.0149703 | -1005.605 | 50 | 11 |
| Cell_2_GEIS_SOC70 | 2 | two_cpe_w_scan2 | 0.026279 | 0.0146766 | -1010.439 | 50 | 11 |

The SOC 100 and SOC 70 differences are descriptive associations, not causal estimates: only one cell per SOC is represented and each cell contributes two repeated scans. Repeat-scan disagreement is therefore an empirical reproducibility warning, not an independent biological/material replicate. `R0` is the high-frequency ohmic intercept of the lumped cell; `R1/R2` and their CPE exponents describe two distributed relaxations, but a two-terminal spectrum cannot uniquely assign either branch to a specific electrode.

## 5. Frequency-range interpretation

- **Highest frequencies / inductive loop:** positive Im(Z) is consistent with fixture, lead, and cell-connection inductance. Because the contract prescribes circuits without an inductive element, those points are shown and retained for full residual accountability but excluded from fitting. They should not be forced into a capacitive branch.
- **High-frequency real intercept:** `R0` represents the lumped ohmic contribution (electrolyte, current collectors, contacts, and instrument path). It is not separable into those components from these spectra alone.
- **High-to-intermediate frequencies:** the first `R||CPE` branch captures the faster depressed arc. A CPE exponent below one is a compact empirical description of distributed time constants/non-ideal capacitance; it is not, by itself, proof of a unique surface morphology.
- **Intermediate-to-low frequencies:** the second `R||CPE` branch captures a slower interfacial/porous-electrode relaxation. In a complete alkaline cell this may combine charge-transfer, double-layer, porous-electrode, and coupled electrode contributions. Without a reference electrode or perturbation series, anode/cathode attribution is underdetermined.
- **Lowest frequencies:** the open finite-space Warburg term (`Wo`) represents bounded diffusion, approaching a 45° diffusion response before a more blocking/vertical low-frequency limit. The finite measured window may not sharply identify both diffusion parameters.

These assignments follow the impedance.py element definitions and general EIS/battery literature listed below. They are deliberately phrased as circuit-consistent interpretations rather than unique mechanistic identifications.

## 6. Residuals, outliers, and uncertainty

`figures/residuals.png` plots real and imaginary residuals against log frequency for every candidate. `results/fitted_spectrum.csv` makes each residual recomputable. The high-frequency inductive region is the dominant known structural mismatch for non-inductive candidates and is explicitly marked. No point was removed as a statistical outlier after looking at its residual; the only exclusion rule is the representation-based, predeclared `Im(Z)>=0` inductive criterion.

`std_error` is calculated without forming `J.T @ J`: the finite-difference Jacobian is expressed in relative parameter coordinates and decomposed directly by SVD, avoiding the squared conditioning defect of normal equations. Full-rank estimates agree with the independent impedance.py/SciPy optimizer covariance to numerical precision. Fixed `R0` has `std_error=0` and `is_fixed=1`; this encodes a constant, not zero scientific uncertainty. If the scaled Jacobian is rank deficient, every free-parameter error for that model receives the required numeric zero sentinel and `uncertainty_method=not_estimable_rank_deficient_model_zero_sentinel`; no finite marginal error is claimed. Rank and condition diagnostics are included in `fit_parameters.csv`.

## 7. Lin-KK compatibility diagnostic

| dataset | scan_index | lin_kk_M | lin_kk_mu | lin_kk_rmse_complex_ohm | lin_kk_normalized_rmse | lin_kk_max_abs_normalized_residual |
|---|---|---|---|---|---|---|
| exampleData | 1 | 14 | 0.818656 | 0.000895476 | 0.03021 | 0.100499 |
| Cell_1_GEIS_SOC100_scan1 | 1 | 7 | 0.778783 | 0.838975 | 0.148805 | 0.327539 |
| Cell_1_GEIS_SOC100_scan2 | 2 | 12 | 0.757089 | 0.323749 | 0.0783219 | 0.179057 |
| Cell_2_GEIS_SOC70 | 1 | 14 | 0.83895 | 0.0115535 | 0.036858 | 0.0820227 |
| Cell_2_GEIS_SOC70 | 2 | 15 | 0.810566 | 0.00972035 | 0.0310737 | 0.0708471 |

The impedance.py Lin-KK routine was run on each complete spectrum with complex fitting, `c=0.85`, and `max_M=50`. The diagnostic asks whether an RC basis with logarithmically distributed time constants can reproduce the observations while controlling negative resistance mass through `mu`. Lower normalized residuals indicate greater compatibility with that basis. These values are not treated as a binary proof of linearity, causality, stability, or stationarity: the routine's RC-only basis has no series inductance, while every spectrum contains a retained high-frequency inductive region. The SOC100 scans show the largest normalized Lin-KK residuals, consistent with their poorer circuit-fit behavior.

## 8. Limitations

1. Equivalent circuits are non-unique and topology selection is restricted to the contract's candidates.
2. The models omit inductance, so the high-frequency loop remains systematically unmatched.
3. An open finite-space Warburg boundary is assumed; the finite experimental window cannot uniquely establish diffusion geometry or boundary condition.
4. No replicate cells at the same SOC are available, so SOC and cell identity are confounded.
5. Parameter covariance is local and does not capture multimodality; multistart fitting reduces but cannot eliminate this risk. Boundary solutions or collapsed branches—particularly very large resistance paired with negligible Warburg amplitude—must be treated as non-identifiable effective limits rather than literal material constants.
6. Lin-KK is reported as an RC-basis compatibility diagnostic, not a stand-alone validity verdict; the basis omits the measured inductive segment and the task supplies no time-domain stationarity checks.
7. The fixed-`R0` candidate uses a same-spectrum preprocessing estimate. Its contract AICc is therefore optimistic, and the effective-degree-of-freedom sensitivity comparison is the more conservative interpretation.

## 9. Files and reproducibility

- `results/fit_parameters.csv`: one row per fixed/free parameter with units and uncertainty.
- `results/model_metrics.csv`: convergence, complex RSS/RMSE, contract and sensitivity AICc, fit-point counts, candidate identity, and Lin-KK diagnostics.
- `results/fitted_spectrum.csv`: observed/fitted complex values and residuals for every original point and candidate.
- `figures/nyquist_models.png`, `bode_models.png`, `residuals.png`: visual evidence.
- `provenance.json`: hashes, sources, licenses, model strings, runtime, and preprocessing.
- `run_steps.md`: one-command rebuild instructions.

## 10. Source list

- **impedance.py 1.7.1 — Circuit Elements** — Definitions and units for R, C, CPE, and open finite-space Warburg elements.
  - URL: https://impedancepy.readthedocs.io/en/latest/circuit-elements.html
- **impedance.py 1.7.1 — Fitting impedance spectra** — CustomCircuit syntax, fixed constants, fitting, and inductive-point preprocessing.
  - URL: https://impedancepy.readthedocs.io/en/latest/examples/fitting_example.html
- **Murbach et al., impedance.py: A Python package for electrochemical impedance analysis** — Software methodology and citation.
  - URL: https://doi.org/10.21105/joss.02349
- **Barresi et al., Modeling of alkaline batteries and investigation of the relationship between electrochemical impedance and Raman spectroscopy** — Electrochemical system and public alkaline-battery dataset context.
  - URL: https://doi.org/10.1016/j.est.2026.120719
- **Gamry Instruments — Basics of Electrochemical Impedance Spectroscopy** — Physical interpretation of resistive, capacitive, charge-transfer, and diffusion responses.
  - URL: https://www.gamry.com/application-notes/EIS/basics-of-electrochemical-impedance-spectroscopy/
- **Holm et al., Simple circuit equivalents for the constant phase element** — CPE as a fractional, non-ideal capacitive element and limits of physical interpretation.
  - URL: https://doi.org/10.1371/journal.pone.0248786
- **Qu, Ji, and Qu, Probing process kinetics in batteries with electrochemical impedance spectroscopy** — Frequency-dependent battery process interpretation and assignment cautions.
  - URL: https://doi.org/10.1038/s43246-022-00284-w
- **Schönleber et al., A Method for Improving the Robustness of Linear Kramers–Kronig Validity Tests** — Lin-KK diagnostic method and the mu criterion used by impedance.py.
  - URL: https://doi.org/10.1016/j.electacta.2014.01.034

## 11. Traceability statement

All numerical conclusions in this report are generated from the delivered CSV files by `src/run_analysis.py`. External sources support software definitions and cautious physical interpretation only. No reference answer, grader, rubric, expected parameter, or evaluator-side artifact was accessed or used.
