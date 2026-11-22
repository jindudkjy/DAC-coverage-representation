"""Independent measurement-domain weather-support reconstruction.
Input provenance: MAIN_climate_hourly_2015_2024.csv and MAIN_material_support_bounds.csv.
Not sorption capacity, energy, or adsorption-process productivity.
"""
import argparse
from pathlib import Path
import numpy as np
import pandas as pd

EXTENSIONS=('T_low_minus_5C','T_high_plus_5C','RH_low_minus_5pp','RH_high_plus_5pp')
def compute(weather,bounds,raw):
    import re
    def norm(x): return re.sub(r'[^a-z0-9]+','',str(x).lower())
    raw=raw.copy();raw['_key']=raw['material'].map(norm)
    rh_by_temp={(k,float(t)):(float(g.RH_pct.min()),float(g.RH_pct.max())) for (k,t),g in raw.groupby(['_key','T_C'])}

    # Input is explicitly sorted, and adjacent transitions must be exactly one hour apart.
    weather=weather.sort_values(['city','timestamp_utc'],kind='stable').reset_index(drop=True)
    cities, city_ix=np.unique(weather.city.to_numpy(),return_inverse=True)
    t=weather.temperature_C.to_numpy(float);rh=weather.RH_pct.to_numpy(float)
    dt=pd.to_datetime(weather.timestamp_utc,utc=True).to_numpy()
    eligible=(city_ix[1:]==city_ix[:-1])&((dt[1:]-dt[:-1])==np.timedelta64(1,'h'))
    eligible&=np.isfinite(t[1:])&np.isfinite(t[:-1])&np.isfinite(rh[1:])&np.isfinite(rh[:-1])
    transition_city=city_ix[1:]
    total_by_city=np.bincount(transition_city[eligible],minlength=len(cities))
    if not (total_by_city>0).all(): raise ValueError('Location with no eligible transition')
    total=total_by_city.sum()
    def support(tlo,thi,rlo,rhi):
        state=(t>=tlo)&(t<=thi)&(rh>=rlo)&(rh<=rhi)
        transitions=state[1:] & state[:-1] & eligible
        bycity=np.bincount(transition_city[transitions],minlength=len(cities))
        return bycity.sum()/total,bycity/total_by_city
    rows=[]
    for b in bounds.itertuples(index=False):
        low,mid,high,rlo,rhi=float(b.Tlow),float(b.Tref),float(b.Thigh),float(b.Rmin),float(b.Rmax)
        for branch,tl,th in [('lower',low,mid),('upper',mid,high)]:
            # Common measured RH intersection of the two endpoint isotherms.
            end1=rh_by_temp[(norm(b.material),tl)];end2=rh_by_temp[(norm(b.material),th)]
            rlo=max(end1[0],end2[0]);rhi=min(end1[1],end2[1])
            if rlo>=rhi: raise ValueError('Empty RH intersection for '+str(b.material))
            base,base_city=support(tl,th,rlo,rhi)
            for direction in EXTENSIONS:
                if direction=='T_low_minus_5C': cand=(tl-5,th,rlo,rhi)
                elif direction=='T_high_plus_5C': cand=(tl,th+5,rlo,rhi)
                elif direction=='RH_low_minus_5pp': cand=(tl,th,max(0,rlo-5),rhi)
                else: cand=(tl,th,rlo,min(100,rhi+5))
                v,v_city=support(*cand)
                locdiff=(v_city-base_city)*100
                rows.append(dict(material=b.material,branch=branch,T_low=tl,T_high=th,RH_low=rlo,RH_high=rhi,extension=direction,baseline_transition_coverage=base,candidate_transition_coverage=v,gain_percentage_points=(v-base)*100,median_location_gain_pp=float(np.median(locdiff)),max_location_gain_pp=float(np.max(locdiff))))
    return pd.DataFrame(rows),dict(n_rows=len(weather),n_locations=len(cities),n_eligible_transitions=int(total))

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--input-dir',type=Path,default=Path('/mnt/data'));ap.add_argument('--output-dir',type=Path,required=True);args=ap.parse_args()
    a=args.input_dir;out=args.output_dir;out.mkdir(parents=True,exist_ok=True)
    weather=pd.read_csv(a/'MAIN_climate_hourly_2015_2024.csv')
    bounds=pd.read_csv(a/'MAIN_material_support_bounds.csv')
    raw=pd.read_excel(a/'MAIN_equilibrium_dataset_master.xlsx',sheet_name='06_RAW_QRHT',header=2)
    got,stats=compute(weather,bounds,raw)
    got.to_csv(out/'measurement_domain_extension_recomputed.csv',index=False,float_format='%.16g')
    got[['material','branch','T_low','T_high','RH_low','RH_high']].drop_duplicates().to_csv(out/'measurement_support_branch_bounds_from_master.csv',index=False)
    refpath=a/'immediate_boundary_extension_coverage_native1h.csv'
    if refpath.exists():
        ref=pd.read_csv(refpath)
        keys=['material','branch','T_low','T_high','RH_low','RH_high','extension']
        numeric=['baseline_transition_coverage','candidate_transition_coverage','gain_percentage_points','median_location_gain_pp','max_location_gain_pp']
        joined=got.merge(ref,on=keys,validate='one_to_one',suffixes=('_new','_frozen'),indicator=True)
        if len(joined)!=len(ref) or len(joined)!=len(got) or not (joined._merge=='both').all():raise AssertionError('Row keys mismatch')
        errs={key:float(np.max(np.abs(joined[key+'_new']-joined[key+'_frozen']))) for key in numeric}
        audit=pd.DataFrame([{'quantity':k,'max_abs_error':v,'pass_at_1e_minus_9':v<1e-9} for k,v in errs.items()]);audit.to_csv(out/'measurement_domain_extension_regression.csv',index=False)
        print('AUDIT',stats,'ROWS',len(got),'ERRORS',errs)
        if not all(v<1e-9 for v in errs.values()):raise AssertionError('Coverage regression failed')
    else:print('computed without reference CSV',stats)
if __name__=='__main__':main()
