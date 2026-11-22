"""Rebuild IRA location-pair H/Y ordering from saved climate-level scores.
NOTE: This is NOT hourly adsorption/kinetics Y regeneration; frozen Y is an input.
"""
import argparse
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import kendalltau,spearmanr

def compute(scores):
    rows=[];details=[]
    for (branch,support),g in scores.groupby(['branch','support_treatment'],sort=False):
        g=g.dropna(subset=['H_single','H_tensor','Y_single','Y_tensor']).sort_values('climate').reset_index(drop=True)
        n=len(g);counts=dict(n_Hsafe_Ysafe=0,n_Hsafe_Yrev=0,n_Hrev_Ysafe=0,n_Hrev_Yrev=0)
        for i in range(n):
            for j in range(i+1,n):
                x,y=g.iloc[i],g.iloc[j]
                hds=float(x.H_single-y.H_single);hdt=float(x.H_tensor-y.H_tensor)
                yds=float(x.Y_single-y.Y_single);ydt=float(x.Y_tensor-y.Y_tensor)
                if not all(abs(z)>1e-12 for z in [hds,hdt,yds,ydt]): raise ValueError('Tied location pair; special handling required')
                hr=(hds*hdt<0);yr=(yds*ydt<0)
                state=('n_Hrev_' if hr else 'n_Hsafe_')+('Yrev' if yr else 'Ysafe')
                counts[state]+=1
                details.append(dict(branch=branch,support_treatment=support,climate_a=x.climate,climate_b=y.climate,H_reversed=hr,Y_reversed=yr,joint_class=state))
        row=dict(branch=branch,support_treatment=support,n_common_finite_climates=n,n_pairs=n*(n-1)//2,**counts)
        for suffix in ['H','Y']:
            row['tau_'+suffix+'_single_tensor']=kendalltau(g[suffix+'_single'],g[suffix+'_tensor']).statistic
            row['rho_'+suffix+'_single_tensor']=spearmanr(g[suffix+'_single'],g[suffix+'_tensor']).statistic
        rows.append(row)
    return pd.DataFrame(rows),pd.DataFrame(details)

def main():
    p=argparse.ArgumentParser();p.add_argument('--input-dir',type=Path,default=Path('/mnt/data'));p.add_argument('--output-dir',type=Path,required=True);a=p.parse_args()
    a.output_dir.mkdir(parents=True,exist_ok=True)
    scores=pd.read_csv(a.input_dir/'IRA_environmental_common_support_climate_scores.csv')
    computed,pairs=compute(scores)
    computed.to_csv(a.output_dir/'IRA_shared_support_pairwise_recomputed_summary.csv',index=False)
    pairs.to_csv(a.output_dir/'IRA_shared_support_pairwise_recomputed_pairs.csv',index=False)
    frozen=pd.read_csv(a.input_dir/'IRA_environmental_common_support_transfer_summary.csv')
    cols=['n_common_finite_climates','n_pairs','n_Hsafe_Ysafe','n_Hsafe_Yrev','n_Hrev_Ysafe','n_Hrev_Yrev','tau_H_single_tensor','tau_Y_single_tensor','rho_H_single_tensor','rho_Y_single_tensor']
    m=computed.merge(frozen,on=['branch','support_treatment'],validate='one_to_one',suffixes=('_calc','_frozen'))
    if len(m)!=4:raise AssertionError('Four comparisons expected')
    report=[]
    for c in cols:
        v=float(np.max(np.abs(m[c+'_calc']-m[c+'_frozen'])))
        report.append(dict(column=c,max_abs_error=v,pass_at_1e_minus_9=v<1e-9))
    audit=pd.DataFrame(report);audit.to_csv(a.output_dir/'IRA_shared_support_pairwise_regression.csv',index=False)
    print('ROWS',len(computed),'PAIRS',len(pairs),'MAX_ERROR',audit.max_abs_error.max(),'COUNTS',computed[['branch','support_treatment','n_Hsafe_Yrev']].to_dict('records'))
    if not audit.pass_at_1e_minus_9.all():raise AssertionError('IRA score-pair regression failure')
if __name__=='__main__':main()
