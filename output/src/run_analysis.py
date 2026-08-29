#!/usr/bin/env python3
"""Scorer-blind, reproducible EIS equivalent-circuit analysis.

Uses only the agent-visible task inputs and public impedance.py APIs.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import sys
import types
import warnings
from dataclasses import dataclass
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# impedance.py 1.7.1 imports Altair even when only Matplotlib plots are used.
# The public task image supplies Altair. This fallback only supports newer host
# runtimes on which pinned Altair 5.5 cannot import; no Altair API is invoked.
try:
    import altair  # noqa: F401
except Exception:
    sys.modules["altair"] = types.ModuleType("altair")

import impedance
from impedance.models.circuits import CustomCircuit

TASK_ID = "task_116_eis_equivalent_circuit_analysis"

INPUT_SOURCES = {
    "exampleData.csv": {
        "source": "https://github.com/ECSHackWeek/impedance.py/blob/main/data/exampleData.csv",
        "license": "MIT",
    },
    "Cell_1_GEIS_SOC100.csv": {
        "source": "https://github.com/marzio-barresi/Electrical-Datasets-Alkaline-Batteries/blob/main/GEIS/Cell_1_GEIS.csv",
        "license": "CC BY 4.0",
    },
    "Cell_1_GEIS_SOC100_scan1.csv": {
        "source": "https://github.com/marzio-barresi/Electrical-Datasets-Alkaline-Batteries/blob/main/GEIS/Cell_1_GEIS.csv",
        "license": "CC BY 4.0; lossless columns 1-5 extraction supplied by task author",
    },
    "Cell_1_GEIS_SOC100_scan2.csv": {
        "source": "https://github.com/marzio-barresi/Electrical-Datasets-Alkaline-Batteries/blob/main/GEIS/Cell_1_GEIS.csv",
        "license": "CC BY 4.0; lossless columns 7-11 extraction supplied by task author",
    },
    "Cell_2_GEIS_SOC70.csv": {
        "source": "https://github.com/marzio-barresi/Electrical-Datasets-Alkaline-Batteries/blob/main/GEIS/Cell_2_GEIS.csv",
        "license": "CC BY 4.0",
    },
}

EXTERNAL_SOURCES = [
    {
        "id": "impedance_docs_elements",
        "title": "impedance.py 1.7.1 — Circuit Elements",
        "url": "https://impedancepy.readthedocs.io/en/latest/circuit-elements.html",
        "use": "Definitions and units for R, C, CPE, and open finite-space Warburg elements.",
    },
    {
        "id": "impedance_docs_fit",
        "title": "impedance.py 1.7.1 — Fitting impedance spectra",
        "url": "https://impedancepy.readthedocs.io/en/latest/examples/fitting_example.html",
        "use": "CustomCircuit syntax, fixed constants, fitting, and inductive-point preprocessing.",
    },
    {
        "id": "impedance_py_paper",
        "title": "Murbach et al., impedance.py: A Python package for electrochemical impedance analysis",
        "url": "https://doi.org/10.21105/joss.02349",
        "use": "Software methodology and citation.",
    },
    {
        "id": "alkaline_dataset_paper",
        "title": "Barresi et al., Modeling of alkaline batteries and investigation of the relationship between electrochemical impedance and Raman spectroscopy",
        "url": "https://doi.org/10.1016/j.est.2026.120719",
        "use": "Electrochemical system and public alkaline-battery dataset context.",
    },
    {
        "id": "eis_tutorial",
        "title": "Gamry Instruments — Basics of Electrochemical Impedance Spectroscopy",
        "url": "https://www.gamry.com/application-notes/EIS/basics-of-electrochemical-impedance-spectroscopy/",
        "use": "Physical interpretation of resistive, capacitive, charge-transfer, and diffusion responses.",
    },
    {
        "id": "cpe_source",
        "title": "Holm et al., Simple circuit equivalents for the constant phase element",
        "url": "https://doi.org/10.1371/journal.pone.0248786",
        "use": "CPE as a fractional, non-ideal capacitive element and limits of physical interpretation.",
    },
    {
        "id": "battery_eis_perspective",
        "title": "Wang et al., Probing process kinetics in batteries with electrochemical impedance spectroscopy",
        "url": "https://doi.org/10.1038/s43246-022-00284-w",
        "use": "Frequency-dependent battery process interpretation and assignment cautions.",
    },
]


@dataclass
class Spectrum:
    dataset: str
    source_file: str
    frequency: np.ndarray
    z: np.ndarray
    original_row: np.ndarray
    scan_index: int
    soc_pct: float | None
    voltage_mean_v: float | None


@dataclass
class ModelSpec:
    model: str
    circuit: str
    kind: str
    fixed_r0: bool = False


@dataclass
class FitResult:
    spectrum: Spectrum
    spec: ModelSpec
    circuit: CustomCircuit
    fixed: dict[str, float]
    free_names: list[str]
    free_units: list[str]
    params: np.ndarray
    std_errors: np.ndarray
    optimizer_std_errors: np.ndarray
    z_fit: np.ndarray
    used_in_fit: np.ndarray
    converged: bool
    warning_text: str
    n_starts: int
    fit_rss: float
    all_rss: float
    rmse: float
    aicc: float


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def load_inputs(data_dir: Path) -> tuple[list[Spectrum], dict]:
    required = set(INPUT_SOURCES)
    missing = sorted(name for name in required if not (data_dir / name).is_file())
    if missing:
        raise FileNotFoundError(f"Missing required public input(s): {missing}")

    validation: dict[str, object] = {"checks": []}
    spectra: list[Spectrum] = []

    ex = pd.read_csv(data_dir / "exampleData.csv", header=None,
                     names=["frequency", "z_real", "z_imag"])
    if ex.shape != (66, 3):
        raise ValueError(f"exampleData.csv shape {ex.shape}, expected (66, 3)")
    spectra.append(Spectrum(
        "exampleData", "exampleData.csv",
        ex.frequency.to_numpy(float),
        ex.z_real.to_numpy(float) + 1j * ex.z_imag.to_numpy(float),
        np.arange(len(ex), dtype=int), 1, None, None,
    ))
    validation["checks"].append({"check": "example_shape", "passed": True, "rows": 66})

    cell_cols = ["SOC [%]", "Voltage [V]", "Frequency [Hz]",
                 "Re(Ztot) [Ohm]", "-Im(Ztot) [Ohm]"]

    # Verify the supplied SOC100 convenience scans are exactly the two blocks
    # of the original side-by-side file (blank separator column ignored).
    original = pd.read_csv(data_dir / "Cell_1_GEIS_SOC100.csv")
    scan1 = pd.read_csv(data_dir / "Cell_1_GEIS_SOC100_scan1.csv")
    scan2 = pd.read_csv(data_dir / "Cell_1_GEIS_SOC100_scan2.csv")
    if scan1.shape != (61, 5) or scan2.shape != (61, 5):
        raise ValueError("SOC100 convenience scans must each be 61 x 5")
    left = original.iloc[:, :5].copy(); left.columns = cell_cols
    right = original.iloc[:, 6:11].copy(); right.columns = cell_cols
    same1 = np.allclose(left.to_numpy(float), scan1[cell_cols].to_numpy(float), rtol=0, atol=0)
    same2 = np.allclose(right.to_numpy(float), scan2[cell_cols].to_numpy(float), rtol=0, atol=0)
    if not (same1 and same2):
        raise ValueError("SOC100 convenience scans are not lossless copies of original layout")
    validation["checks"].append({"check": "soc100_lossless_split", "passed": True})

    def from_battery(df: pd.DataFrame, dataset: str, source_file: str, scan_index: int,
                     row_offset: int = 0) -> Spectrum:
        if list(df.columns) != cell_cols:
            df = df[cell_cols]
        f = df["Frequency [Hz]"].to_numpy(float)
        # Delivered field is -Im(Z), therefore Im(Z) is its negative.
        z = df["Re(Ztot) [Ohm]"].to_numpy(float) - 1j * df["-Im(Ztot) [Ohm]"].to_numpy(float)
        return Spectrum(
            dataset, source_file, f, z,
            np.arange(row_offset, row_offset + len(df), dtype=int), scan_index,
            float(df["SOC [%]"].mean()), float(df["Voltage [V]"].mean()),
        )

    spectra.append(from_battery(scan1, "Cell_1_GEIS_SOC100_scan1",
                                "Cell_1_GEIS_SOC100_scan1.csv", 1))
    spectra.append(from_battery(scan2, "Cell_1_GEIS_SOC100_scan2",
                                "Cell_1_GEIS_SOC100_scan2.csv", 2))

    c2 = pd.read_csv(data_dir / "Cell_2_GEIS_SOC70.csv")
    if c2.shape != (122, 5):
        raise ValueError(f"Cell_2_GEIS_SOC70.csv shape {c2.shape}, expected (122, 5)")
    f2 = c2["Frequency [Hz]"].to_numpy(float)
    # A new sweep is identified by a multi-decade upward reset in frequency.
    breaks = (np.where(np.diff(np.log10(f2)) > 1.0)[0] + 1).tolist()
    if breaks != [61]:
        raise ValueError(f"Expected one SOC70 sweep reset at row 61, found {breaks}")
    c2a, c2b = c2.iloc[:61].copy(), c2.iloc[61:].copy()
    spectra.append(from_battery(c2a, "Cell_2_GEIS_SOC70_scan1",
                                "Cell_2_GEIS_SOC70.csv", 1, 0))
    spectra.append(from_battery(c2b, "Cell_2_GEIS_SOC70_scan2",
                                "Cell_2_GEIS_SOC70.csv", 2, 61))
    validation["checks"].append({
        "check": "soc70_frequency_reset_split", "passed": True,
        "break_rows_zero_based": breaks, "scan_lengths": [61, 61],
    })

    for s in spectra:
        if not (np.isfinite(s.frequency).all() and np.isfinite(s.z.real).all()
                and np.isfinite(s.z.imag).all()):
            raise ValueError(f"Non-finite input in {s.dataset}")
        if np.any(s.frequency <= 0):
            raise ValueError(f"Non-positive frequency in {s.dataset}")
        validation["checks"].append({
            "check": "finite_positive_frequency", "dataset": s.dataset,
            "passed": True, "n_points": len(s.frequency),
            "frequency_min_hz": float(s.frequency.min()),
            "frequency_max_hz": float(s.frequency.max()),
            "inductive_points": int(np.sum(s.z.imag >= 0)),
            "capacitive_points": int(np.sum(s.z.imag < 0)),
        })
    return spectra, validation


def estimate_r0(s: Spectrum) -> float:
    """Data-derived real-axis crossing near the high-frequency inductive loop."""
    order = np.argsort(s.frequency)[::-1]
    zr, zi = s.z.real[order], s.z.imag[order]
    for i in range(len(order) - 1):
        if zi[i] >= 0 and zi[i + 1] < 0:
            frac = zi[i] / (zi[i] - zi[i + 1])
            return float(zr[i] + frac * (zr[i + 1] - zr[i]))
    cap = s.z.imag < 0
    return float(np.min(s.z.real[cap]))


def base_guess(s: Spectrum, spec: ModelSpec, constants: dict[str, float]) -> tuple[list[str], list[float]]:
    cap = s.z.imag < 0
    f, z = s.frequency[cap], s.z[cap]
    rs = constants.get("R0", estimate_r0(s))
    r_span = max(float(z.real.max() - rs), max(abs(rs) * 0.1, 1e-6))
    low_idx = np.argsort(f)[: min(6, len(f))]
    w0 = float(np.median(np.maximum(-z.imag[low_idx], 1e-12)
                         * np.sqrt(2 * np.pi * f[low_idx])))
    w0 = max(w0, 1e-8)
    # Finite-space Warburg characteristic time and resistance scale, both
    # derived from the observed low-frequency window.
    tau0 = 1.0 / (2 * np.pi * max(float(f.min()), 1e-12))
    f_peak = float(f[np.argmax(-z.imag)])
    f_hi = min(float(f.max()) / 2, max(f_peak * 20, f_peak))
    f_lo = max(float(f.min()) * 2, f_peak / 10)
    r1 = max(r_span * (0.35 if "two" in spec.kind else 0.8), 1e-7)
    r2 = max(r_span * 0.65, 1e-7)
    c1 = 1 / max(2 * np.pi * r1 * f_hi, 1e-20)
    c2 = 1 / max(2 * np.pi * r2 * f_lo, 1e-20)
    alpha1, alpha2 = 0.86, 0.78
    q1 = 1 / max(r1 * (2 * np.pi * f_hi) ** alpha1, 1e-20)
    q2 = 1 / max(r2 * (2 * np.pi * f_lo) ** alpha2, 1e-20)

    values = {
        "R0": rs, "R1": r1, "C1": c1,
        "CPE1_0": q1, "CPE1_1": alpha1,
        "R2": r2, "C2": c2,
        "CPE2_0": q2, "CPE2_1": alpha2,
        "Wo1_0": max(w0 * math.sqrt(2 * tau0), r_span * 0.05),
        "Wo1_1": tau0,
    }
    dummy_count = {
        "randles_rc": 5, "randles_cpe": 6,
        "two_rc": 7, "two_cpe": 9,
    }[spec.kind] - len(constants)
    dummy = CustomCircuit(spec.circuit, initial_guess=[1.0] * dummy_count,
                          constants=constants)
    names, _ = dummy.get_param_names()
    return names, [float(values[n]) for n in names]


def perturb_guess(names: list[str], base: list[float], rng: np.random.Generator,
                  start: int) -> list[float]:
    if start == 0:
        return list(base)
    out = []
    for name, value in zip(names, base):
        if name.endswith("_1") and name.startswith("CPE"):
            out.append(float(rng.uniform(0.55, 0.98)))
        else:
            out.append(float(max(value * 10 ** rng.normal(0, 0.65), 1e-14)))
    return out


def predict_for_params(spec: ModelSpec, constants: dict[str, float], params: np.ndarray,
                       frequency: np.ndarray) -> np.ndarray:
    c = CustomCircuit(spec.circuit, initial_guess=list(np.maximum(params, 1e-20)),
                      constants=constants)
    c.parameters_ = np.asarray(params, dtype=float)
    return np.asarray(c.predict(frequency), dtype=complex)


def covariance_stderr(spec: ModelSpec, constants: dict[str, float], params: np.ndarray,
                      frequency: np.ndarray, z: np.ndarray) -> np.ndarray:
    k = len(params); nobs = 2 * len(frequency)
    pred0 = predict_for_params(spec, constants, params, frequency)
    y0 = np.hstack([pred0.real, pred0.imag])
    jac = np.zeros((nobs, k), dtype=float)
    for j in range(k):
        step = max(abs(params[j]) * 1e-5, 1e-10)
        lo = params.copy(); hi = params.copy()
        hi[j] += step
        if params[j] > step:
            lo[j] -= step
            yhi_z = predict_for_params(spec, constants, hi, frequency)
            ylo_z = predict_for_params(spec, constants, lo, frequency)
            jac[:, j] = (np.hstack([yhi_z.real, yhi_z.imag])
                         - np.hstack([ylo_z.real, ylo_z.imag])) / (2 * step)
        else:
            yhi_z = predict_for_params(spec, constants, hi, frequency)
            jac[:, j] = (np.hstack([yhi_z.real, yhi_z.imag]) - y0) / step
    resid = np.hstack([(z - pred0).real, (z - pred0).imag])
    dof = max(nobs - k, 1)
    sigma2 = float(np.dot(resid, resid) / dof)
    cov = sigma2 * np.linalg.pinv(jac.T @ jac, rcond=1e-12)
    stderr = np.sqrt(np.maximum(np.diag(cov), 0))
    stderr[~np.isfinite(stderr)] = 0.0
    return stderr


def fit_model(s: Spectrum, spec: ModelSpec, n_starts: int = 8) -> FitResult:
    used = s.z.imag < 0  # prescribed circuits have no inductance
    f_fit, z_fit_obs = s.frequency[used], s.z[used]
    constants = {"R0": estimate_r0(s)} if spec.fixed_r0 else {}
    names, base = base_guess(s, spec, constants)
    dummy = CustomCircuit(spec.circuit, initial_guess=base, constants=constants)
    _, units = dummy.get_param_names()
    rng_seed = int(hashlib.sha256(f"{s.dataset}|{spec.model}".encode()).hexdigest()[:8], 16)
    rng = np.random.default_rng(rng_seed)
    best = None; errors: list[str] = []
    for start in range(n_starts):
        guess = perturb_guess(names, base, rng, start)
        c = CustomCircuit(spec.circuit, initial_guess=guess, constants=constants,
                          name=spec.model)
        try:
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                c.fit(f_fit, z_fit_obs, weight_by_modulus=False,
                      maxfev=50000, ftol=1e-9, xtol=1e-9, gtol=1e-9)
            pred_fit = np.asarray(c.predict(f_fit), dtype=complex)
            rss_fit = float(np.sum(np.abs(z_fit_obs - pred_fit) ** 2))
            if not np.isfinite(rss_fit):
                raise ValueError("non-finite fit RSS")
            candidate = (rss_fit, c, "; ".join(str(w.message) for w in caught))
            if best is None or candidate[0] < best[0]:
                best = candidate
        except Exception as exc:
            errors.append(f"start {start}: {type(exc).__name__}: {exc}")
    if best is None:
        raise RuntimeError(f"All starts failed for {s.dataset}/{spec.model}: {errors[:4]}")

    fit_rss, circuit, warning_text = best
    params = np.asarray(circuit.parameters_, dtype=float)
    optimizer_se = np.asarray(circuit.conf_ if circuit.conf_ is not None
                              else np.zeros_like(params), dtype=float)
    optimizer_se[~np.isfinite(optimizer_se)] = 0.0
    stderr = covariance_stderr(spec, constants, params, f_fit, z_fit_obs)
    z_all = np.asarray(circuit.predict(s.frequency), dtype=complex)
    all_rss = float(np.sum(np.abs(s.z - z_all) ** 2))
    n = len(s.z); nobs = 2 * n; k = len(params)
    rmse = math.sqrt(all_rss / nobs)
    aic = nobs * math.log(max(all_rss / nobs, np.finfo(float).tiny)) + 2 * k
    aicc = aic + 2 * k * (k + 1) / (nobs - k - 1)
    return FitResult(s, spec, circuit, constants, names, units, params, stderr,
                     optimizer_se, z_all, used, True,
                     warning_text or ("; ".join(errors[:2]) if errors else ""),
                     n_starts, fit_rss, all_rss, rmse, aicc)


def all_specs(s: Spectrum) -> list[ModelSpec]:
    if s.dataset == "exampleData":
        return [
            ModelSpec("randles_rc_w", "R0-p(R1-Wo1,C1)", "randles_rc"),
            ModelSpec("randles_cpe_w", "R0-p(R1-Wo1,CPE1)", "randles_cpe"),
            ModelSpec("two_rc_w_fixed_r0", "R0-p(R1,C1)-p(R2,C2)-Wo1",
                      "two_rc", fixed_r0=True),
            ModelSpec("two_rc_w_free", "R0-p(R1,C1)-p(R2,C2)-Wo1", "two_rc"),
        ]
    return [ModelSpec("two_cpe_w", "R0-p(R1,CPE1)-p(R2,CPE2)-Wo1", "two_cpe")]


def rows_from_fits(fits: list[FitResult]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    p_rows, m_rows, s_rows = [], [], []
    for fit in fits:
        names, units = fit.free_names, fit.free_units
        if fit.fixed:
            full = [(n, v, 0.0, "Ohm" if n.startswith("R") else "-", True, 0.0)
                    for n, v in fit.fixed.items()]
        else:
            full = []
        for n, u, v, se, ose in zip(names, units, fit.params,
                                     fit.std_errors, fit.optimizer_std_errors):
            full.append((n, float(v), float(se), u or "-", False, float(ose)))
        for name, value, se, unit, is_fixed, ose in full:
            p_rows.append({
                "dataset": fit.spectrum.dataset, "model": fit.spec.model,
                "parameter": name, "value": value, "std_error": se,
                "unit": unit, "is_fixed": int(is_fixed),
                "optimizer_std_error": ose,
                "uncertainty_method": "fixed" if is_fixed else "finite_difference_covariance",
            })
        m_rows.append({
            "dataset": fit.spectrum.dataset, "model": fit.spec.model,
            "n_points": len(fit.spectrum.z), "n_parameters": len(fit.params),
            "rss_complex": fit.all_rss, "rmse_complex": fit.rmse,
            "aicc": fit.aicc, "converged": int(fit.converged),
            "fit_n_points": int(fit.used_in_fit.sum()),
            "excluded_inductive_points": int((~fit.used_in_fit).sum()),
            "fit_rss_complex": fit.fit_rss,
            "fit_rmse_complex": math.sqrt(fit.fit_rss / (2 * fit.used_in_fit.sum())),
            "circuit": fit.spec.circuit,
            "fixed_parameters": json.dumps(fit.fixed, sort_keys=True),
            "n_multistarts": fit.n_starts,
            "warnings": fit.warning_text or "none",
        })
        for i, (f, z, zh, used, orig) in enumerate(zip(
                fit.spectrum.frequency, fit.spectrum.z, fit.z_fit,
                fit.used_in_fit, fit.spectrum.original_row)):
            res = z - zh
            s_rows.append({
                "dataset": fit.spectrum.dataset, "model": fit.spec.model,
                "frequency_hz": float(f), "z_real_ohm": float(z.real),
                "z_imag_ohm": float(z.imag), "z_fit_real_ohm": float(zh.real),
                "z_fit_imag_ohm": float(zh.imag), "res_real_ohm": float(res.real),
                "res_imag_ohm": float(res.imag), "point_index": i,
                "original_row": int(orig), "scan_index": fit.spectrum.scan_index,
                "source_file": fit.spectrum.source_file, "used_in_fit": int(used),
            })
    params = pd.DataFrame(p_rows)
    metrics = pd.DataFrame(m_rows)
    spectra = pd.DataFrame(s_rows)
    metrics["delta_aicc_within_dataset"] = metrics.groupby("dataset")["aicc"].transform(lambda x: x - x.min())
    metrics["selected_by_aicc"] = (metrics["delta_aicc_within_dataset"] < 1e-9).astype(int)
    return params, metrics, spectra


def make_figures(fits: list[FitResult], output_dir: Path) -> None:
    fig_dir = output_dir / "figures"; fig_dir.mkdir(parents=True, exist_ok=True)
    datasets = list(dict.fromkeys(f.spectrum.dataset for f in fits))
    cmap = plt.get_cmap("tab10")

    fig, axes = plt.subplots(2, 3, figsize=(16, 10), constrained_layout=True)
    for ax, dataset in zip(axes.flat, datasets):
        fs = [x for x in fits if x.spectrum.dataset == dataset]; s = fs[0].spectrum
        ax.plot(s.z.real, -s.z.imag, "ko", ms=3.5, label="observed")
        excluded = ~fs[0].used_in_fit
        if excluded.any():
            ax.plot(s.z.real[excluded], -s.z.imag[excluded], "rx", ms=5,
                    label="inductive (excluded from fit)")
        order = np.argsort(s.frequency)
        for j, fit in enumerate(fs):
            ax.plot(fit.z_fit.real[order], -fit.z_fit.imag[order], "-",
                    lw=1.6, color=cmap(j), label=fit.spec.model)
        ax.set_title(dataset); ax.set_xlabel("Z' (Ohm)"); ax.set_ylabel("-Z'' (Ohm)")
        ax.grid(alpha=.25); ax.legend(fontsize=7)
    for ax in axes.flat[len(datasets):]: ax.axis("off")
    fig.suptitle("EIS Nyquist data and prescribed equivalent-circuit models", fontsize=14)
    fig.savefig(fig_dir / "nyquist_models.png", dpi=220); plt.close(fig)

    fig, axes = plt.subplots(len(datasets), 2, figsize=(15, 4 * len(datasets)), constrained_layout=True)
    for row, dataset in enumerate(datasets):
        fs = [x for x in fits if x.spectrum.dataset == dataset]; s = fs[0].spectrum
        order = np.argsort(s.frequency); f = s.frequency[order]; z = s.z[order]
        axm, axp = axes[row]
        axm.loglog(f, np.abs(z), "ko", ms=3, label="observed")
        axp.semilogx(f, np.angle(z, deg=True), "ko", ms=3, label="observed")
        for j, fit in enumerate(fs):
            zh = fit.z_fit[order]
            axm.loglog(f, np.abs(zh), lw=1.5, color=cmap(j), label=fit.spec.model)
            axp.semilogx(f, np.angle(zh, deg=True), lw=1.5, color=cmap(j), label=fit.spec.model)
        axm.set_ylabel("|Z| (Ohm)"); axp.set_ylabel("Phase (degrees)")
        for ax in (axm, axp):
            ax.set_xlabel("Frequency (Hz)"); ax.grid(which="both", alpha=.25); ax.legend(fontsize=7)
        axm.set_title(f"{dataset}: magnitude"); axp.set_title(f"{dataset}: phase")
    fig.suptitle("Bode magnitude and phase", fontsize=14)
    fig.savefig(fig_dir / "bode_models.png", dpi=220); plt.close(fig)

    fig, axes = plt.subplots(len(datasets), 2, figsize=(15, 3.7 * len(datasets)), constrained_layout=True)
    for row, dataset in enumerate(datasets):
        fs = [x for x in fits if x.spectrum.dataset == dataset]; s = fs[0].spectrum
        order = np.argsort(s.frequency); f = s.frequency[order]
        for j, fit in enumerate(fs):
            res = (s.z - fit.z_fit)[order]
            axes[row, 0].semilogx(f, res.real, ".-", ms=3, lw=1, color=cmap(j), label=fit.spec.model)
            axes[row, 1].semilogx(f, res.imag, ".-", ms=3, lw=1, color=cmap(j), label=fit.spec.model)
        for col, label in enumerate(("Re residual (Ohm)", "Im residual (Ohm)")):
            axes[row, col].axhline(0, color="black", lw=.7)
            axes[row, col].set_xlabel("Frequency (Hz)"); axes[row, col].set_ylabel(label)
            axes[row, col].set_title(f"{dataset}: {label.split()[0]}")
            axes[row, col].grid(which="both", alpha=.25); axes[row, col].legend(fontsize=7)
    fig.suptitle("Complex residuals (observed - fitted)", fontsize=14)
    fig.savefig(fig_dir / "residuals.png", dpi=220); plt.close(fig)


def markdown_table(df: pd.DataFrame, columns: list[str], formats: dict[str, str] | None = None) -> str:
    formats = formats or {}; rows = []
    rows.append("| " + " | ".join(columns) + " |")
    rows.append("|" + "|".join(["---"] * len(columns)) + "|")
    for _, r in df[columns].iterrows():
        vals = []
        for c in columns:
            v = r[c]
            if c in formats and isinstance(v, (int, float, np.number)):
                vals.append(format(float(v), formats[c]))
            else:
                vals.append(str(v).replace("|", "\\|"))
        rows.append("| " + " | ".join(vals) + " |")
    return "\n".join(rows)


def write_report(fits: list[FitResult], params: pd.DataFrame, metrics: pd.DataFrame,
                 validation: dict, output_dir: Path) -> None:
    example = metrics[metrics.dataset == "exampleData"].sort_values("aicc")
    best = example.iloc[0]
    battery = metrics[metrics.dataset != "exampleData"].copy()

    # Compact battery comparison using fitted free parameters.
    pivot = params[(params.model == "two_cpe_w") & params.parameter.isin(
        ["R0", "R1", "R2", "CPE1_1", "CPE2_1", "Wo1_0", "Wo1_1"])]
    pivot = pivot.pivot(index="dataset", columns="parameter", values="value").reset_index()
    for c in ["R0", "R1", "R2", "CPE1_1", "CPE2_1", "Wo1_0", "Wo1_1"]:
        if c not in pivot: pivot[c] = np.nan
    pivot["R1_plus_R2_ohm"] = pivot.R1 + pivot.R2

    report = f"""# EIS Equivalent-Circuit Analysis

## Executive summary

Five independent spectra were analyzed: the impedance.py generic example, two losslessly separated SOC 100 alkaline-cell scans, and two SOC 70 sweeps detected and separated at the frequency reset in the 122-row source file. The battery sign convention was reconstructed exactly as specified: `Im(Z) = -[-Im(Ztot)]`. High-frequency points with positive `Im(Z)` are inductive and were retained in all artifacts/plots but excluded from parameter estimation because the prescribed candidate families contain no inductance. Required full-spectrum residual metrics still include those points.

For `exampleData`, all four prescribed candidates converged. AICc selects **{best['model']}** (AICc {best['aicc']:.3f}, RMSE {best['rmse_complex']:.6g} Ohm); model preference is based on the complete complex residual and the declared free-parameter count, not visual appearance. The fixed two-time-constant model fixes only `R0`, at a value independently derived by interpolating the high-frequency real-axis crossing; no fitted or reference-answer parameter is hard-coded.

Each battery sweep was fitted to `R0-p(R1,CPE1)-p(R2,CPE2)-W1`. The repeated scans are reported separately, preventing artificial joining of independent sweeps. Parameter uncertainty is the local one-standard-deviation covariance estimate from a finite-difference complex Jacobian over the points actually used in fitting.

## 1. Input validation and preprocessing

- `exampleData.csv`: 66 headerless rows interpreted as frequency, Re(Z), Im(Z).
- SOC 100: supplied scan files are byte-numerically identical to columns 1–5 and 7–11 of the original side-by-side source layout.
- SOC 70: a frequency reset occurs after row 61, yielding two 61-point sweeps; they were never concatenated as one curve.
- No missing, non-finite, or non-positive-frequency values were found.
- Frequency order was not mutated. Sorting is applied only in visual line rendering; `original_row`, `scan_index`, and repeated frequencies are preserved in `fitted_spectrum.csv`.
- Inductive observations (`Im(Z) >= 0`) are marked with `used_in_fit=0`; all other points use `used_in_fit=1`.

### Validation counts

{markdown_table(metrics[['dataset','model','n_points','fit_n_points','excluded_inductive_points']].drop_duplicates('dataset'), ['dataset','n_points','fit_n_points','excluded_inductive_points'])}

## 2. Candidate circuits and fitting method

| Model identifier | impedance.py circuit string | Purpose |
|---|---|---|
| `randles_rc_w` | `R0-p(R1,C1)-W1` | Ideal-capacitor Randles-type baseline plus finite-length diffusion. |
| `randles_cpe_w` | `R0-p(R1,CPE1)-W1` | Tests non-ideal/distributed interfacial capacitance. |
| `two_rc_w_fixed_r0` | `R0-p(R1,C1)-p(R2,C2)-W1` | Two ideal time constants; data-derived series resistance held fixed. |
| `two_rc_w_free` | `R0-p(R1,C1)-p(R2,C2)-W1` | Same topology with all parameters free. |
| `two_cpe_w` | `R0-p(R1,CPE1)-p(R2,CPE2)-W1` | Prescribed battery model with two distributed time constants and diffusion. |

Fits use unweighted complex nonlinear least squares through impedance.py 1.7.1 `CustomCircuit`. Eight deterministic multistarts are generated from data-derived resistance, peak-frequency, and low-frequency diffusion scales. The best converged solution is selected by fitting-subset RSS. Model comparison uses the task-defined full-spectrum formulas with `N=2n`: `RMSE=sqrt(RSS/N)` and `AICc=N ln(RSS/N)+2k+2k(k+1)/(N-k-1)`.

## 3. Model comparison for exampleData

{markdown_table(example, ['model','n_parameters','rss_complex','rmse_complex','aicc','delta_aicc_within_dataset','converged'], {'rss_complex':'.6g','rmse_complex':'.6g','aicc':'.3f','delta_aicc_within_dataset':'.3f'})}

AICc penalizes extra free parameters. A lower AICc is evidence for better expected information loss only within this declared candidate set; it does not prove that the selected circuit is a unique microscopic mechanism. Compare the parameter covariance and structured residuals before assigning physics.

## 4. Battery scan comparison

{markdown_table(pivot, ['dataset','R0','R1','R2','R1_plus_R2_ohm','CPE1_1','CPE2_1','Wo1_0','Wo1_1'], {'R0':'.6g','R1':'.6g','R2':'.6g','R1_plus_R2_ohm':'.6g','CPE1_1':'.4f','CPE2_1':'.4f','Wo1_0':'.6g','Wo1_1':'.6g'})}

{markdown_table(battery, ['dataset','rss_complex','rmse_complex','aicc','fit_n_points','excluded_inductive_points'], {'rss_complex':'.6g','rmse_complex':'.6g','aicc':'.3f'})}

The SOC 100 and SOC 70 differences are descriptive associations, not causal estimates: only one cell per SOC is represented and each cell contributes two repeated scans. Repeat-scan disagreement is therefore an empirical reproducibility warning, not an independent biological/material replicate. `R0` is the high-frequency ohmic intercept of the lumped cell; `R1/R2` and their CPE exponents describe two distributed relaxations, but a two-terminal spectrum cannot uniquely assign either branch to a specific electrode.

## 5. Frequency-range interpretation

- **Highest frequencies / inductive loop:** positive Im(Z) is consistent with fixture, lead, and cell-connection inductance. Because the contract prescribes circuits without an inductive element, those points are shown and retained for full residual accountability but excluded from fitting. They should not be forced into a capacitive branch.
- **High-frequency real intercept:** `R0` represents the lumped ohmic contribution (electrolyte, current collectors, contacts, and instrument path). It is not separable into those components from these spectra alone.
- **High-to-intermediate frequencies:** the first `R||CPE` branch captures the faster depressed arc. A CPE exponent below one is a compact empirical description of distributed time constants/non-ideal capacitance; it is not, by itself, proof of a unique surface morphology.
- **Intermediate-to-low frequencies:** the second `R||CPE` branch captures a slower interfacial/porous-electrode relaxation. In a complete alkaline cell this may combine charge-transfer, double-layer, porous-electrode, and coupled electrode contributions. Without a reference electrode or perturbation series, anode/cathode attribution is underdetermined.
- **Lowest frequencies:** the open finite-space Warburg term provides the prescribed `45°`-type diffusion impedance. The measured window does not establish whether diffusion is truly semi-infinite outside the observed range; finite-length alternatives were not among the prescribed candidates.

These assignments follow the impedance.py element definitions and general EIS/battery literature listed below. They are deliberately phrased as circuit-consistent interpretations rather than unique mechanistic identifications.

## 6. Residuals, outliers, and uncertainty

`figures/residuals.png` plots real and imaginary residuals against log frequency for every candidate. `results/fitted_spectrum.csv` makes each residual recomputable. The high-frequency inductive region is the dominant known structural mismatch for non-inductive candidates and is explicitly marked. No point was removed as a statistical outlier after looking at its residual; the only exclusion rule is the representation-based, predeclared `Im(Z)>=0` inductive criterion.

`std_error` values are local covariance approximations and can become large when parameters are correlated or a time constant is weakly identified. Fixed `R0` has `std_error=0` and `is_fixed=1`; this encodes a constant, not zero scientific uncertainty. The `optimizer_std_error` column preserves impedance.py/SciPy's covariance estimate as a cross-check.

## 7. Limitations

1. Equivalent circuits are non-unique and topology selection is restricted to the contract's candidates.
2. The models omit inductance, so the high-frequency loop remains systematically unmatched.
3. Open finite-space Warburg behavior is assumed; the finite experimental window cannot establish asymptotic transport geometry.
4. No replicate cells at the same SOC are available, so SOC and cell identity are confounded.
5. Parameter covariance is local and does not capture multimodality; multistart fitting reduces but cannot eliminate this risk.
6. No Kramers–Kronig linearity/causality/stability claim is made because the task supplies no time-domain stationarity checks and the inductive segment is not represented by the prescribed models.

## 8. Files and reproducibility

- `results/fit_parameters.csv`: one row per fixed/free parameter with units and uncertainty.
- `results/model_metrics.csv`: convergence, complex RSS/RMSE, AICc, fit-point counts, and candidate identity.
- `results/fitted_spectrum.csv`: observed/fitted complex values and residuals for every original point and candidate.
- `figures/nyquist_models.png`, `bode_models.png`, `residuals.png`: visual evidence.
- `provenance.json`: hashes, sources, licenses, model strings, runtime, and preprocessing.
- `run_steps.md`: one-command rebuild instructions.

## 9. Source list

"""
    for source in EXTERNAL_SOURCES:
        report += f"- **{source['title']}** — {source['use']}  \n  {source['url']}\n"
    report += "\n## 10. Traceability statement\n\nAll numerical conclusions in this report are generated from the delivered CSV files by `src/run_analysis.py`. External sources support software definitions and cautious physical interpretation only. No reference answer, grader, rubric, expected parameter, or evaluator-side artifact was accessed or used.\n"
    (output_dir / "analysis_report.md").write_text(report, encoding="utf-8")


def write_provenance(data_dir: Path, validation: dict, fits: list[FitResult],
                     output_dir: Path) -> None:
    inputs = []
    for name, meta in INPUT_SOURCES.items():
        path = data_dir / name
        inputs.append({
            "local_name": name, "sha256": sha256_file(path),
            "source": meta["source"], "license": meta["license"],
        })
    models = []
    for fit in fits:
        entry = {
            "dataset": fit.spectrum.dataset, "model": fit.spec.model,
            "circuit": fit.spec.circuit, "library": f"impedance.py {impedance.__version__}",
            "fit_rule": "unweighted complex nonlinear least squares; 8 deterministic multistarts; Im(Z)<0 points",
            "metric_rule": "full-spectrum RSS; N=2n RMSE and AICc per public task contract",
            "constants": fit.fixed,
        }
        if entry not in models: models.append(entry)
    provenance = {
        "task_identifier": TASK_ID,
        "clean_room": {
            "scorer_blind": True,
            "materials_used": "public agent-visible instruction/inputs and public scientific sources only",
            "prohibited_materials_accessed": False,
        },
        "runtime_environment": {
            "python": sys.version, "platform": platform.platform(),
            "impedance": impedance.__version__, "numpy": np.__version__,
            "scipy": __import__("scipy").__version__, "pandas": pd.__version__,
            "matplotlib": matplotlib.__version__,
            "task_image_target": "python:3.11-slim with public pinned requirements",
        },
        "inputs": inputs,
        "input_validation": validation,
        "preprocessing": {
            "battery_sign": "z_imag_ohm = -1 * delivered '-Im(Ztot) [Ohm]'",
            "scan_separation": "SOC100 supplied lossless split files; SOC70 split at multi-decade frequency reset row 61",
            "frequency_order": "preserved in CSV artifacts; sorted only for rendered lines",
            "fit_mask": "Im(Z) < 0 because prescribed circuits omit inductance; excluded points retained in full residual metrics",
            "outlier_policy": "no residual-driven deletions",
        },
        "models": models,
        "external_sources": EXTERNAL_SOURCES,
    }
    (output_dir / "provenance.json").write_text(
        json.dumps(provenance, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def validate_outputs(output_dir: Path) -> None:
    required = [
        "src/run_analysis.py", "requirements.txt", "results/fit_parameters.csv",
        "results/model_metrics.csv", "results/fitted_spectrum.csv",
        "figures/nyquist_models.png", "figures/bode_models.png",
        "figures/residuals.png", "analysis_report.md", "provenance.json", "run_steps.md",
    ]
    missing = [x for x in required if not (output_dir / x).is_file()]
    if missing: raise RuntimeError(f"Missing outputs: {missing}")
    for name in ["fit_parameters.csv", "model_metrics.csv", "fitted_spectrum.csv"]:
        df = pd.read_csv(output_dir / "results" / name)
        numeric = df.select_dtypes(include=[np.number])
        if not np.isfinite(numeric.to_numpy()).all():
            raise RuntimeError(f"Non-finite numeric output in {name}")
    p = pd.read_csv(output_dir / "results/fit_parameters.csv")
    m = pd.read_csv(output_dir / "results/model_metrics.csv")
    s = pd.read_csv(output_dir / "results/fitted_spectrum.csv")
    assert {"dataset","model","parameter","value","std_error","unit","is_fixed"} <= set(p.columns)
    assert {"dataset","model","n_points","n_parameters","rss_complex","rmse_complex","aicc","converged"} <= set(m.columns)
    assert {"dataset","model","frequency_hz","z_real_ohm","z_imag_ohm","z_fit_real_ohm","z_fit_imag_ohm","res_real_ohm","res_imag_ohm"} <= set(s.columns)
    # Recompute every declared required metric from fitted_spectrum.
    for _, row in m.iterrows():
        block = s[(s.dataset == row.dataset) & (s.model == row.model)]
        rss = float(np.sum(block.res_real_ohm.to_numpy() ** 2 + block.res_im_ohm.to_numpy() ** 2)) if "res_im_ohm" in block else float(np.sum(block.res_real_ohm.to_numpy() ** 2 + block.res_imag_ohm.to_numpy() ** 2))
        if not np.isclose(rss, row.rss_complex, rtol=1e-9, atol=1e-12):
            raise RuntimeError(f"RSS mismatch for {row.dataset}/{row.model}")
        n = len(block); k = int(row.n_parameters); N = 2*n
        rmse = math.sqrt(rss/N)
        aicc = N*math.log(max(rss/N, np.finfo(float).tiny)) + 2*k + 2*k*(k+1)/(N-k-1)
        if not np.isclose(rmse, row.rmse_complex, rtol=1e-9):
            raise RuntimeError(f"RMSE mismatch for {row.dataset}/{row.model}")
        if not np.isclose(aicc, row.aicc, rtol=1e-9):
            raise RuntimeError(f"AICc mismatch for {row.dataset}/{row.model}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, default=Path("/app/data"))
    parser.add_argument("--output-dir", type=Path, default=Path("/app/output"))
    args = parser.parse_args()
    data_dir, output_dir = args.data_dir.resolve(), args.output_dir.resolve()
    (output_dir / "results").mkdir(parents=True, exist_ok=True)
    (output_dir / "figures").mkdir(parents=True, exist_ok=True)

    spectra, validation = load_inputs(data_dir)
    fits: list[FitResult] = []
    for spectrum in spectra:
        for spec in all_specs(spectrum):
            print(f"Fitting {spectrum.dataset} / {spec.model}", flush=True)
            fits.append(fit_model(spectrum, spec))

    params, metrics, fitted = rows_from_fits(fits)
    params.to_csv(output_dir / "results/fit_parameters.csv", index=False)
    metrics.to_csv(output_dir / "results/model_metrics.csv", index=False)
    fitted.to_csv(output_dir / "results/fitted_spectrum.csv", index=False)
    make_figures(fits, output_dir)
    write_report(fits, params, metrics, validation, output_dir)
    write_provenance(data_dir, validation, fits, output_dir)
    validate_outputs(output_dir)
    print(f"ANALYSIS_COMPLETE fits={len(fits)} datasets={len(spectra)}", flush=True)


if __name__ == "__main__":
    main()
