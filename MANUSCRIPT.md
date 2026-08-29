# Reproducible Equivalent-Circuit Analysis of Reference and Alkaline-Battery Impedance Spectra

## Abstract

Electrochemical impedance spectroscopy (EIS) can separate processes that overlap in the time domain, but interpretation depends strongly on preprocessing, circuit topology, parameter identifiability, and the treatment of repeated scans. This study presents a reproducible equivalent-circuit analysis of one reference spectrum and four alkaline-battery spectra. The reference dataset was evaluated with four prescribed circuit families: an ideal-capacitor Randles-type model, a constant-phase-element variant, and two two-time-constant models with either fixed or free series resistance. Each battery sweep was fitted with two distributed relaxation branches and an open finite-space Warburg element. Fits used unweighted complex nonlinear least squares, eight deterministic data-derived multistarts, and full-spectrum model comparison by complex residual sum of squares, root-mean-square error, and corrected Akaike information criterion (AICc). Five independent spectra produced eight converged fits, 61 parameter records, and 508 fitted-spectrum records. For the reference spectrum, the two-time-constant model with fixed series resistance was preferred (AICc −1708.133; complex RMSE 0.001476 Ω), followed by its free-resistance counterpart (ΔAICc 3.411). The two SOC 70 sweeps gave closely matched fitted resistances and low residual error, whereas the SOC 100 sweeps disagreed substantially, including one weakly identified boundary solution. The analysis therefore supports descriptive circuit-level comparison but not unique electrode-level or causal attribution. Every reported value is traceable to machine-readable artifacts, independently validated metric recomputation, input hashes, and a clean Python 3.11 rebuild.

## Introduction

Electrochemical impedance spectroscopy probes a system over a range of perturbation frequencies and represents the response as a complex impedance, \(Z(\omega)=Z'(\omega)+jZ''(\omega)\). Distinct frequency regions may reflect ohmic losses, interfacial relaxation, distributed capacitive behavior, porous-electrode effects, and diffusion. Equivalent circuits provide a compact way to describe those regions, but they do not by themselves establish a unique microscopic mechanism. Different circuit topologies may reproduce the same spectrum, parameter estimates may be correlated, and apparently precise solutions may lie on poorly identified boundaries.

These limitations become especially important in complete batteries. A two-terminal measurement combines contributions from both electrodes, the electrolyte, current collectors, contacts, and the measurement path. Without a reference electrode, a controlled perturbation series, or replicate cells at each state of charge, fitted branches cannot be assigned uniquely to individual physical processes. High-frequency inductive behavior also presents a practical modeling problem when the prescribed candidate circuits contain no inductive element.

The present analysis had three objectives. First, it compared four specified equivalent-circuit candidates on a standard `impedance.py` example spectrum using a common complex-residual and AICc framework. Second, it fitted a prescribed two-CPE, two-time-constant, finite-diffusion model to repeated alkaline-battery sweeps at nominal SOC 100 and SOC 70. Third, it produced a fully auditable artifact bundle in which preprocessing, model definitions, parameter estimates, residuals, figures, provenance, and reproduction instructions could be checked independently.

## Methods

### Data sources and integrity

Five independent spectra were analyzed. The reference spectrum, [`exampleData.csv`](data/exampleData.csv), contains 66 headerless observations of frequency, real impedance, and imaginary impedance. The alkaline-battery data were derived from the public dataset associated with Barresi and colleagues. Two SOC 100 scans were supplied as lossless extractions of the first and second side-by-side scan blocks in the source file. The SOC 70 source contains 122 rows; a multi-decade frequency reset after row 61 separates it into two 61-point sweeps.

Input SHA-256 hashes, source URLs, and license information are recorded in [`output/provenance.json`](output/provenance.json). The complete input boundary is additionally recorded in [`AGENT_VISIBLE_FILE_HASHES.json`](AGENT_VISIBLE_FILE_HASHES.json). Input checks confirmed positive frequencies and finite required values. Original row order and repeated frequencies were retained in the exported data.

### Sign convention, scan separation, and fitting mask

The delivered battery quantity `-Im(Ztot)` was converted according to the task convention:

\[
Z''=-[-\operatorname{Im}(Z_{tot})].
\]

The SOC 70 sweeps were fitted separately and retained under the public source-file identifier `Cell_2_GEIS_SOC70`, with `scan_index` and model identifiers distinguishing the two sweeps. This avoids both artificial concatenation and loss of source traceability.

The prescribed circuits contain no inductive element. Observations with \(Z''\ge 0\), corresponding to the high-frequency inductive region, were therefore excluded from parameter estimation. They were not discarded: each remains in [`output/results/fitted_spectrum.csv`](output/results/fitted_spectrum.csv), is marked by `used_in_fit=0`, appears in the figures, and contributes to the declared full-spectrum residual metrics. No residual-driven outlier deletion was performed.

### Equivalent circuits

The reference spectrum was fitted with four candidate models implemented through `impedance.py` 1.7.1 `CustomCircuit`:

1. Ideal-capacitor Randles-type model with open finite-space diffusion: `R0-p(R1-Wo1,C1)`.
2. Constant-phase-element variant: `R0-p(R1-Wo1,CPE1)`.
3. Two ideal relaxation branches with fixed series resistance: `R0-p(R1,C1)-p(R2,C2)-Wo1`.
4. The same two-relaxation topology with free series resistance.

For the fixed-resistance model, \(R_0=0.0156881726\ \Omega\) was derived from interpolation of the high-frequency real-axis crossing. No fitted reference parameter was embedded in the analysis.

Each battery sweep was fitted with

`R0-p(R1,CPE1)-p(R2,CPE2)-Wo1`,

where `CPE1` and `CPE2` represent distributed, non-ideal capacitive relaxations and `Wo1` is the open finite-space Warburg element. The exact model strings and constants are preserved in [`output/results/model_metrics.csv`](output/results/model_metrics.csv) and [`output/provenance.json`](output/provenance.json).

### Optimization and uncertainty

Fits used unweighted complex nonlinear least squares. Eight deterministic multistarts were generated from data-derived resistance scales, peak-frequency estimates, and low-frequency diffusion scales. The converged solution with the lowest fitting-subset complex residual sum of squares was retained.

Local parameter uncertainty was estimated from a finite-difference complex Jacobian over the observations used in fitting. Both the locally calculated standard error and the optimizer covariance estimate are reported in [`output/results/fit_parameters.csv`](output/results/fit_parameters.csv). A zero associated with a fixed parameter is explicitly marked `is_fixed=1`. A zero arising from a rank-deficient or zero-sensitivity direction is labeled `not_estimable_rank_deficient_zero_sentinel` and is not interpreted as perfect precision.

### Model-comparison statistics

Metrics were calculated on the complete spectrum, including the retained inductive observations. With \(n\) complex observations and \(N=2n\) scalar residual components,

\[
\mathrm{RSS}=\sum_i\left[(Z'_i-\hat Z'_i)^2+(Z''_i-\hat Z''_i)^2\right],
\]

\[
\mathrm{RMSE}=\sqrt{\mathrm{RSS}/N},
\]

and

\[
\mathrm{AICc}=N\ln(\mathrm{RSS}/N)+2k+\frac{2k(k+1)}{N-k-1},
\]

where \(k\) is the number of free parameters. AICc comparisons were restricted to candidates fitted to the same dataset.

### Reproducibility and validation

The analysis is implemented in [`output/src/run_analysis.py`](output/src/run_analysis.py), with pinned dependencies in [`output/requirements.txt`](output/requirements.txt) and one-command instructions in [`output/run_steps.md`](output/run_steps.md). An independent validator, [`tools/validate_submission.py`](tools/validate_submission.py), checks required paths, schema and row counts, finite values, metric recomputation, dataset identifiers, provenance hashes, and PNG integrity. A fresh CPython 3.11.15 environment rebuilt both an isolated output tree and the canonical bundle. Hashes for all eight generated scientific artifacts matched exactly between rebuilds.

## Results

### Data accounting and convergence

All eight prescribed fits converged. The final bundle contains 61 parameter rows and 508 pointwise fitted-spectrum rows. The reference spectrum contributed 66 observations, of which 57 were used for estimation. The two SOC 100 scans contributed 61 observations each, with 54 and 55 used for fitting. Each SOC 70 scan contributed 61 observations, with 50 used for fitting. The remaining points in each spectrum were retained as high-frequency inductive observations.

Detailed fit status and point accounting are available in [`output/results/model_metrics.csv`](output/results/model_metrics.csv). Pointwise observed values, predictions, residuals, original row indices, scan indices, and fitting-mask indicators are available in [`output/results/fitted_spectrum.csv`](output/results/fitted_spectrum.csv).

### Reference-spectrum model comparison

All four reference-spectrum candidates converged. The fixed-\(R_0\), two-time-constant model gave the lowest AICc:

| Model | Free parameters | Complex RSS | Complex RMSE (Ω) | AICc | ΔAICc |
|---|---:|---:|---:|---:|---:|
| Two RC + `Wo`, fixed \(R_0\) | 6 | 0.000287699 | 0.00147633 | −1708.133 | 0.000 |
| Two RC + `Wo`, free \(R_0\) | 7 | 0.000290281 | 0.00148294 | −1704.722 | 3.411 |
| Randles CPE + `Wo` | 6 | 0.000318430 | 0.00155317 | −1694.736 | 13.396 |
| Randles RC + `Wo` | 5 | 0.000470176 | 0.00188731 | −1645.491 | 62.642 |

The free-\(R_0\) model achieved a slightly lower residual on the fitting subset but did not improve full-spectrum error enough to overcome the additional AICc penalty. The CPE Randles model substantially improved on the ideal-capacitor Randles baseline, but the two-time-constant candidates were better supported within the specified model set.

### Battery spectra

The two SOC 70 sweeps were internally consistent. Their fitted series resistances were 0.117718 and 0.118944 Ω, and the sums \(R_1+R_2\) were 0.394754 and 0.387058 Ω. Their full-spectrum complex RMSE values were 0.014970 and 0.014677 Ω, respectively. The close agreement between repeated sweeps suggests good within-file repeatability for those circuit-level summaries.

The SOC 100 scans were less consistent. The second scan produced \(R_0=0.130659\ \Omega\), \(R_1+R_2=6.15234\ \Omega\), and a full-spectrum complex RMSE of 0.154583 Ω. The first scan produced a much larger effective second-branch resistance, a negligible Warburg amplitude, and a complex RMSE of 0.483442 Ω. This combination is characteristic of a collapsed or weakly identified parameter direction rather than a credible literal resistance of the cell. The numerical result is retained in the artifact table but qualified accordingly.

Complete fitted values, units, fixed/free status, and uncertainty fields are reported in [`output/results/fit_parameters.csv`](output/results/fit_parameters.csv).

### Visual and residual evidence

The fitted curves and residual structure are documented in:

- [`output/figures/nyquist_models.png`](output/figures/nyquist_models.png)
- [`output/figures/bode_models.png`](output/figures/bode_models.png)
- [`output/figures/residuals.png`](output/figures/residuals.png)

The principal systematic mismatch occurs in the high-frequency inductive region, as expected for candidate circuits without an inductive element. The residual figure also makes the poor SOC 100 scan-1 identification visible rather than concealing it through point removal or axis selection.

## Discussion

The reference-spectrum comparison supports two resolvable ideal relaxation times in addition to series resistance and finite-length diffusion. Fixing the series resistance at an independently derived high-frequency crossing yielded the best AICc and a modest advantage over allowing it to vary. This is a statistical preference within the supplied candidate family. It does not establish that the fitted branches correspond uniquely to two discrete electrochemical mechanisms.

The CPE Randles candidate performed better than its ideal-capacitor counterpart, consistent with a depressed arc or distributed relaxation. A CPE exponent below unity can summarize heterogeneity, porosity, nonuniform current distribution, or a distribution of time constants, but the exponent alone cannot distinguish among these causes. The same caution applies to the two CPE branches used for the battery spectra.

The SOC 70 sweeps showed strong repeatability at the level of fitted series resistance, combined branch resistance, and residual error. In contrast, the SOC 100 scans differed markedly. Because the dataset contains one cell at each nominal SOC and repeated scans are not independent cell replicates, the difference cannot be attributed causally to state of charge. Cell identity, measurement history, nonstationarity, and scan-specific model identifiability remain confounded.

The high-frequency inductive loop was handled explicitly rather than absorbed into an unrelated capacitive branch. Excluding those points from estimation is consistent with fitting a non-inductive candidate family, while retaining them in full-spectrum residual metrics prevents the omission from artificially improving the reported model performance. A future unrestricted analysis could compare otherwise identical topologies with an explicit series inductance.

The open finite-space Warburg element represents bounded diffusion and approaches a finite-length low-frequency response. Its use is appropriate to the prescribed model family, but the available frequency window does not uniquely determine diffusion geometry or boundary condition. Several parameters, particularly in SOC 100 scan 1, lie in correlated or rank-deficient directions. Multistart optimization reduces sensitivity to initialization but cannot resolve structural non-identifiability.

The analysis has four main limitations. First, equivalent circuits are non-unique. Second, the candidate set omits inductance despite an observed inductive segment. Third, there are no replicate cells at the same SOC, so between-cell and SOC effects cannot be separated. Fourth, local covariance estimates do not characterize multimodal uncertainty. Profile likelihoods, bootstrap resampling, Bayesian posterior exploration, explicit inductive candidates, and replicate-cell experiments would provide a stronger basis for mechanistic inference.

## Conclusion

A complete and reproducible equivalent-circuit analysis was obtained for one reference spectrum and four alkaline-battery sweeps. Eight models converged, and the fixed-series-resistance two-time-constant model was preferred for the reference spectrum by AICc. The SOC 70 sweeps were closely reproducible, whereas the SOC 100 sweeps exposed substantial disagreement and one weakly identified boundary solution. These findings support careful circuit-level description but not unique mechanistic or state-of-charge attribution.

The principal contribution is the combination of numerical analysis with explicit traceability. Every parameter, metric, residual, figure, preprocessing decision, and source assertion is represented in a machine-readable artifact. Independent validation, pinned dependencies, provenance hashes, and an exact clean rebuild make the result inspectable and reproducible without relying on undocumented analytical judgment.

## Artifact availability

The complete analysis bundle is located under [`output/`](output/):

- Scientific report: [`output/analysis_report.md`](output/analysis_report.md)
- Parameter estimates: [`output/results/fit_parameters.csv`](output/results/fit_parameters.csv)
- Model metrics: [`output/results/model_metrics.csv`](output/results/model_metrics.csv)
- Pointwise fits and residuals: [`output/results/fitted_spectrum.csv`](output/results/fitted_spectrum.csv)
- Nyquist figure: [`output/figures/nyquist_models.png`](output/figures/nyquist_models.png)
- Bode figure: [`output/figures/bode_models.png`](output/figures/bode_models.png)
- Residual figure: [`output/figures/residuals.png`](output/figures/residuals.png)
- Analysis source: [`output/src/run_analysis.py`](output/src/run_analysis.py)
- Reproduction instructions: [`output/run_steps.md`](output/run_steps.md)
- Pinned environment: [`output/requirements.txt`](output/requirements.txt)
- Provenance: [`output/provenance.json`](output/provenance.json)
- Independent validator: [`tools/validate_submission.py`](tools/validate_submission.py)
- Output hash manifest: [`OUTPUT_FILE_HASHES.json`](OUTPUT_FILE_HASHES.json)

## References

1. Murbach MD, Gerwe B, Dawson-Elli N, Tsui L. impedance.py: A Python package for electrochemical impedance analysis. *Journal of Open Source Software*. 2020;5(52):2349. https://doi.org/10.21105/joss.02349
2. impedance.py developers. Circuit Elements—impedance.py 1.7.1 documentation. https://impedancepy.readthedocs.io/en/latest/circuit-elements.html
3. impedance.py developers. Fitting impedance spectra—impedance.py 1.7.1 documentation. https://impedancepy.readthedocs.io/en/latest/examples/fitting_example.html
4. Barresi M, et al. Modeling of alkaline batteries and investigation of the relationship between electrochemical impedance and Raman spectroscopy. *Journal of Energy Storage*. 2026;120719. https://doi.org/10.1016/j.est.2026.120719
5. Holm S, Holm T, Martinsen ØG. Simple circuit equivalents for the constant phase element. *PLOS ONE*. 2021;16(3):e0248786. https://doi.org/10.1371/journal.pone.0248786
6. Wang Q, et al. Probing process kinetics in batteries with electrochemical impedance spectroscopy. *Communications Engineering*. 2022;1:41. https://doi.org/10.1038/s43246-022-00284-w
7. Gamry Instruments. Basics of Electrochemical Impedance Spectroscopy. https://www.gamry.com/application-notes/EIS/basics-of-electrochemical-impedance-spectroscopy/
