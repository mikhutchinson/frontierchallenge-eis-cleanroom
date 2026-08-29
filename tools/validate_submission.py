#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, math
from pathlib import Path
import numpy as np
import pandas as pd
from PIL import Image

REQUIRED = [
    'src/run_analysis.py','requirements.txt','results/fit_parameters.csv',
    'results/model_metrics.csv','results/fitted_spectrum.csv',
    'figures/nyquist_models.png','figures/bode_models.png','figures/residuals.png',
    'analysis_report.md','provenance.json','run_steps.md',
]

def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()

def main() -> int:
    ap=argparse.ArgumentParser(); ap.add_argument('--root',type=Path,default=Path('.'))
    a=ap.parse_args(); root=a.root.resolve(); out=root/'output'
    missing=[p for p in REQUIRED if not (out/p).is_file()]
    assert not missing, missing
    p=pd.read_csv(out/'results/fit_parameters.csv')
    m=pd.read_csv(out/'results/model_metrics.csv')
    s=pd.read_csv(out/'results/fitted_spectrum.csv')
    assert {'dataset','model','parameter','value','std_error','unit','is_fixed'} <= set(p)
    assert {'dataset','model','n_points','n_parameters','rss_complex','rmse_complex','aicc','converged'} <= set(m)
    assert {'dataset','model','frequency_hz','z_real_ohm','z_imag_ohm','z_fit_real_ohm','z_fit_imag_ohm','res_real_ohm','res_imag_ohm'} <= set(s)
    for name,df in [('parameters',p),('metrics',m),('spectrum',s)]:
        assert np.isfinite(df.select_dtypes(include=[np.number]).to_numpy()).all(), name
    expected_models={
        'exampleData': {'randles_rc_w','randles_cpe_w','two_rc_w_fixed_r0','two_rc_w_free'},
        'Cell_1_GEIS_SOC100_scan1': {'two_cpe_w'},
        'Cell_1_GEIS_SOC100_scan2': {'two_cpe_w'},
        'Cell_2_GEIS_SOC70': {'two_cpe_w_scan1', 'two_cpe_w_scan2'},
    }
    assert len(m)==8, len(m)
    for d,mods in expected_models.items(): assert set(m.loc[m.dataset==d,'model'])==mods, d
    assert {"scan_index", "source_file"} <= set(m)
    assert all(r.dataset == Path(r.source_file).stem for r in m.itertuples()), "dataset/source stem"
    assert set(m.loc[m.dataset == "Cell_2_GEIS_SOC70", "scan_index"]) == {1, 2}
    assert len(s)==508, len(s)
    for _,r in m.iterrows():
        b=s[(s.dataset==r.dataset)&(s.model==r.model)]
        rss=float(np.sum(b.res_real_ohm**2+b.res_imag_ohm**2)); N=2*len(b); k=int(r.n_parameters)
        rmse=math.sqrt(rss/N); aicc=N*math.log(rss/N)+2*k+2*k*(k+1)/(N-k-1)
        assert np.isclose(rss,r.rss_complex,rtol=1e-9,atol=1e-12), (r.dataset,r.model,'rss')
        assert np.isclose(rmse,r.rmse_complex,rtol=1e-9), (r.dataset,r.model,'rmse')
        assert np.isclose(aicc,r.aicc,rtol=1e-9), (r.dataset,r.model,'aicc')
    assert (p.std_error>=0).all()
    fixed=p[p.is_fixed.astype(bool)]; assert len(fixed)>=1 and (fixed.parameter=='R0').any()
    assert {'optimizer_std_error','uncertainty_method','uncertainty_rank',
            'uncertainty_n_parameters','uncertainty_condition_number',
            'uncertainty_condition_is_infinite'} <= set(p)
    free=p[~p.is_fixed.astype(bool)]
    full_rank=free.uncertainty_rank==free.uncertainty_n_parameters
    assert np.allclose(free.loc[full_rank,'std_error'],
                       free.loc[full_rank,'optimizer_std_error'],rtol=2e-3,atol=1e-10)
    rank_def=free[~full_rank]
    assert len(rank_def)>0 and (rank_def.std_error==0).all()
    assert (rank_def.uncertainty_condition_is_infinite==1).all()
    assert set(rank_def.uncertainty_method)=={'not_estimable_rank_deficient_model_zero_sentinel'}
    assert {'n_parameters_effective_sensitivity','aicc_effective_sensitivity',
            'delta_aicc_effective_sensitivity','lin_kk_M','lin_kk_mu',
            'lin_kk_rmse_complex_ohm','lin_kk_normalized_rmse',
            'lin_kk_max_abs_normalized_residual'} <= set(m)
    for _,r in m.iterrows():
        b=s[(s.dataset==r.dataset)&(s.model==r.model)]
        rss=float(np.sum(b.res_real_ohm**2+b.res_imag_ohm**2)); N=2*len(b)
        ke=int(r.n_parameters_effective_sensitivity)
        ae=N*math.log(rss/N)+2*ke+2*ke*(ke+1)/(N-ke-1)
        assert np.isclose(ae,r.aicc_effective_sensitivity,rtol=1e-9)
    fixed_metric=m[m.model=='two_rc_w_fixed_r0'].iloc[0]
    assert fixed_metric.n_parameters_effective_sensitivity==fixed_metric.n_parameters+1
    prov=json.loads((out/'provenance.json').read_text())
    assert prov['task_identifier']=='task_116_eis_equivalent_circuit_analysis'
    assert prov['clean_room']['scorer_blind'] is True
    assert prov['clean_room']['prohibited_materials_accessed'] is False
    assert len(prov['inputs'])==5
    assert len(prov['lin_kk_diagnostics'])==5
    assert {(x['dataset'],x['scan_index']) for x in prov['lin_kk_diagnostics']} == {
        ('exampleData',1),('Cell_1_GEIS_SOC100_scan1',1),
        ('Cell_1_GEIS_SOC100_scan2',2),('Cell_2_GEIS_SOC70',1),
        ('Cell_2_GEIS_SOC70',2)}
    for x in prov['inputs']:
        assert sha(root/'data'/x['local_name'])==x['sha256']
        assert x['source'].startswith('https://') and x['license'].strip()
    hashes=json.loads((root/'AGENT_VISIBLE_FILE_HASHES.json').read_text())
    hmap={Path(x['path']).name:x['sha256'] for x in hashes if '/environment/data/' in x['path'] and x['path'].endswith('.csv')}
    for name in hmap: assert sha(root/'data'/name)==hmap[name], name
    for f in ['nyquist_models.png','bode_models.png','residuals.png']:
        with Image.open(out/'figures'/f) as im:
            assert im.format=='PNG' and im.width>=1000 and im.height>=700, (f,im.size)
            im.verify()
    report=(out/'analysis_report.md').read_text()
    for section in ['Input validation','Model comparison','Battery scan comparison','Frequency-range interpretation','Residuals, outliers, and uncertainty','Lin-KK compatibility diagnostic','Limitations','Source list','Traceability statement']:
        assert section.lower() in report.lower(), section
    assert 'Qu, Ji, and Qu' in report and 'Wang et al.' not in report
    assert 'statistically optimistic' in report
    manifest=[]
    for fp in sorted(out.rglob('*')):
        if fp.is_file(): manifest.append({'path':str(fp.relative_to(out)),'bytes':fp.stat().st_size,'sha256':sha(fp)})
    (root/'OUTPUT_FILE_HASHES.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(f'VALIDATION_OK required={len(REQUIRED)} metrics={len(m)} parameters={len(p)} spectrum_rows={len(s)} outputs={len(manifest)}')
    return 0
if __name__=='__main__': raise SystemExit(main())
