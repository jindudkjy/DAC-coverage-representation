import numpy as np, pandas as pd, math, os
from scipy.stats import kendalltau
from numba import njit

CLIMATE='/mnt/data/contldf/climate_hourly_2015_2024.csv'
MASTER='/mnt/data/p0/q_RH_T_master_cycle08_audited_20261010(2).xlsx'
IRA='/mnt/data/contldf/validation_IRA_RHT.csv'
OUT='/mnt/data/contldf/results'
os.makedirs(OUT,exist_ok=True)

# ---- load material data ----
raw=pd.read_excel(MASTER,'Raw_Data')
mg=raw[raw['Material'].astype(str).eq('Mg0.55Al-CO3_PEI(30)')][['T_C','RH_pct','q_mmol_g']].copy()
mg=mg.rename(columns={'T_C':'temperature_C','RH_pct':'rh_pct'}).sort_values(['temperature_C','rh_pct'])
ira=pd.read_csv(IRA)[['temperature_C','rh_pct','q_mmol_g']].copy().sort_values(['temperature_C','rh_pct'])
materials={'Mg0.55Al-CO3_PEI(30)':mg,'IRA-900-C':ira}

# Exactly the panel anchors used in the manuscript.
anchors={
 'Mg0.55Al-CO3_PEI(30)':(-20.0,-5.0,25.0),
 'IRA-900-C':(15.0,25.0,35.0),
}

# ---- climate ----
clim=pd.read_csv(CLIMATE,usecols=['climate_class','city','timestamp_utc','temperature_C','RH_pct'])
clim['timestamp_utc']=pd.to_datetime(clim['timestamp_utc'],utc=True,errors='coerce')
clim=clim.dropna().sort_values(['climate_class','city','timestamp_utc']).reset_index(drop=True)
groups=[]
for (cc,city),g in clim.groupby(['climate_class','city'],sort=False):
    groups.append((str(cc),str(city),g['temperature_C'].to_numpy(np.float64),g['RH_pct'].to_numpy(np.float64)))
print('climates',len(groups),'hours each',len(groups[0][2]))

# ---- slice interpolation helpers ----
def slice_data(d,T):
    z=d[np.isclose(d.temperature_C,T)].sort_values('rh_pct')
    return z.rh_pct.to_numpy(float),z.q_mmol_g.to_numpy(float)

def interp_slice(rh, xr, yr):
    return np.interp(rh,xr,yr)

def targets_for_group(Tarr,RHarr,d,T1,T2,Tref):
    x1,y1=slice_data(d,T1); x2,y2=slice_data(d,T2); xr,yr=slice_data(d,Tref)
    Rlo=max(x1.min(),x2.min(),xr.min()); Rhi=min(x1.max(),x2.max(),xr.max())
    # actual support at hourly points
    supported=(Tarr>=T1)&(Tarr<=T2)&(RHarr>=Rlo)&(RHarr<=Rhi)
    # capped coordinates for boundary scenario and safe interpolation
    Tc=np.clip(Tarr,T1,T2); Rc=np.clip(RHarr,Rlo,Rhi)
    q1=np.interp(Rc,x1,y1); q2=np.interp(Rc,x2,y2)
    if abs(T2-T1)<1e-12:
        qfull=q1.copy()
    else:
        w=(Tc-T1)/(T2-T1)
        qfull=q1+w*(q2-q1)
    qsingle=np.interp(Rc,xr,yr)
    return supported,Tc,qfull,qsingle,float(Rlo),float(Rhi)

@njit(cache=True)
def simulate_two_pass(Tkin, target_full, target_single, supported, tau_h, Ea_kJmol, Tref_C, scenario):
    # scenario 0: unsupported gap -> state hold
    # scenario 1: unsupported gap -> boundary-capped q* dynamics
    n=len(Tkin)
    kref=1.0/max(tau_h,1e-12)
    Ea=Ea_kJmol*1000.0
    R=8.314462618
    TrefK=Tref_C+273.15
    # deterministic initial state; first pass serves as 10-y spin-up to periodic replay
    qf=target_full[0]
    qs=target_single[0]
    # pass 1 spin-up over full 10-y record
    for i in range(1,n):
        active=supported[i]
        if active or scenario==1:
            if Ea_kJmol==0.0:
                kT=kref
            else:
                TK=Tkin[i]+273.15
                kT=kref*np.exp(-(Ea/R)*(1.0/TK-1.0/TrefK))
            a=1.0-np.exp(-kT)
            qf=qf+a*(target_full[i]-qf)
            qs=qs+a*(target_single[i]-qs)
    # pass 2; score only transitions whose two observed endpoints are supported
    Hf=0.0; Hs=0.0; Hfeq=0.0; Hseq=0.0; nscore=0
    prev_qf=qf; prev_qs=qs
    # At replay start, state carried continuously from end of pass1 to first hour target.
    # Update hour 0 under same rule; no score across record boundary.
    if supported[0] or scenario==1:
        if Ea_kJmol==0.0:
            kT=kref
        else:
            TK=Tkin[0]+273.15
            kT=kref*np.exp(-(Ea/R)*(1.0/TK-1.0/TrefK))
        a=1.0-np.exp(-kT)
        qf=qf+a*(target_full[0]-qf)
        qs=qs+a*(target_single[0]-qs)
    prev_qf=qf; prev_qs=qs
    for i in range(1,n):
        oldf=qf; olds=qs
        active=supported[i]
        if active or scenario==1:
            if Ea_kJmol==0.0:
                kT=kref
            else:
                TK=Tkin[i]+273.15
                kT=kref*np.exp(-(Ea/R)*(1.0/TK-1.0/TrefK))
            a=1.0-np.exp(-kT)
            qf=qf+a*(target_full[i]-qf)
            qs=qs+a*(target_single[i]-qs)
        # else states hold exactly
        if supported[i-1] and supported[i]:
            Hf += 0.5*abs(qf-oldf)
            Hs += 0.5*abs(qs-olds)
            Hfeq += 0.5*abs(target_full[i]-target_full[i-1])
            Hseq += 0.5*abs(target_single[i]-target_single[i-1])
            nscore += 1
    return Hf,Hs,Hfeq,Hseq,nscore

TAUS=[0.25,0.5,1.0,3.0,6.0,12.0]
EAS=[0.0,25.0,50.0]
SCENARIOS={0:'state_hold',1:'boundary_capped'}

# precompute targets for each material/branch/climate
prep={}
bounds=[]
for m,d in materials.items():
    Tlow,Tref,Thigh=anchors[m]
    for branch,(T1,T2) in {'lower':(Tlow,Tref),'upper':(Tref,Thigh)}.items():
        for cc,city,T,RH in groups:
            sup,Tc,qf,qs,Rlo,Rhi=targets_for_group(T,RH,d,T1,T2,Tref)
            prep[(m,branch,cc,city)]=(sup,Tc,qf,qs)
        bounds.append(dict(material=m,branch=branch,Tlo=T1,Thi=T2,Tref=Tref,Rlo=Rlo,Rhi=Rhi))
pd.DataFrame(bounds).to_csv(os.path.join(OUT,'continuous_LDF_branch_bounds.csv'),index=False)

rows=[]
for m,d in materials.items():
    Tlow,Tref,Thigh=anchors[m]
    for branch in ['lower','upper']:
        for scen,scname in SCENARIOS.items():
            for tau in TAUS:
                for Ea in EAS:
                    for cc,city,T,RH in groups:
                        sup,Tc,qf_t,qs_t=prep[(m,branch,cc,city)]
                        Hf,Hs,Hfeq,Hseq,N=simulate_two_pass(Tc,qf_t,qs_t,sup,tau,Ea,Tref,scen)
                        rows.append(dict(material=m,branch=branch,scenario=scname,tau_h=tau,Ea_kJmol=Ea,
                                         climate_class=cc,city=city,H_full_LDF=Hf,H_single_LDF=Hs,
                                         H_full_eq=Hfeq,H_single_eq=Hseq,n_scored=N,
                                         supported_hour_fraction=float(sup.mean())))
                    print('done',m,branch,scname,tau,Ea)
res=pd.DataFrame(rows)
res.to_csv(os.path.join(OUT,'continuous_LDF_climate_scores.csv'),index=False)

summ=[]
for keys,g in res.groupby(['material','branch','scenario','tau_h','Ea_kJmol'],sort=False):
    m,b,s,tau,Ea=keys
    ok=(g.n_scored>0)&np.isfinite(g.H_full_LDF)&np.isfinite(g.H_single_LDF)
    z=g.loc[ok]
    def kt(a,b):
        return float(kendalltau(a,b,variant='b').statistic) if len(a)>=5 else np.nan
    eq_sf=kt(z.H_single_eq,z.H_full_eq)
    dyn_sf=kt(z.H_single_LDF,z.H_full_LDF)
    eq_dyn=kt(z.H_full_eq,z.H_full_LDF)
    single_eq_dyn=kt(z.H_single_eq,z.H_single_LDF)
    summ.append(dict(material=m,branch=b,scenario=s,tau_h=tau,Ea_kJmol=Ea,n_climates=len(z),
                     kendall_equilibrium_full_vs_fullLDF=eq_dyn,
                     kendall_equilibrium_single_vs_singleLDF=single_eq_dyn,
                     kendall_singleLDF_vs_fullLDF=dyn_sf,
                     kendall_eq_single_vs_full=eq_sf,
                     delta_dynamic_minus_equilibrium=dyn_sf-eq_sf,
                     median_supported_hour_fraction=float(z.supported_hour_fraction.median()),
                     median_n_scored=float(z.n_scored.median())))
sumdf=pd.DataFrame(summ)
sumdf.to_csv(os.path.join(OUT,'continuous_LDF_rank_summary.csv'),index=False)

# scenario disagreement and concise slow summaries
wide=sumdf.pivot_table(index=['material','branch','tau_h','Ea_kJmol'],columns='scenario',
                       values=['kendall_equilibrium_full_vs_fullLDF','kendall_singleLDF_vs_fullLDF','delta_dynamic_minus_equilibrium']).reset_index()
wide.columns=['__'.join([str(x) for x in c if str(x)!='']) if isinstance(c,tuple) else c for c in wide.columns]
for metric in ['kendall_equilibrium_full_vs_fullLDF','kendall_singleLDF_vs_fullLDF','delta_dynamic_minus_equilibrium']:
    a=metric+'__state_hold'; b=metric+'__boundary_capped'
    if a in wide and b in wide: wide['absdiff__'+metric]=np.abs(wide[a]-wide[b])
wide.to_csv(os.path.join(OUT,'continuous_LDF_scenario_difference.csv'),index=False)

# pass/fail style summary for fast vs slow
summary2=[]
for regime,taus in [('fast',[0.25,0.5,1.0]),('slow',[3.0,6.0,12.0])]:
    z=sumdf[sumdf.tau_h.isin(taus)]
    summary2.append(dict(regime=regime,n_cases=len(z),
        min_kendall_eq_full_vs_fullLDF=float(z.kendall_equilibrium_full_vs_fullLDF.min()),
        median_kendall_eq_full_vs_fullLDF=float(z.kendall_equilibrium_full_vs_fullLDF.median()),
        min_kendall_singleLDF_vs_fullLDF=float(z.kendall_singleLDF_vs_fullLDF.min()),
        max_abs_delta_dynamic_minus_equilibrium=float(np.abs(z.delta_dynamic_minus_equilibrium).max()),
        max_gap_scenario_difference=float(wide[wide.tau_h.isin(taus)]['absdiff__kendall_equilibrium_full_vs_fullLDF'].max())
    ))
pd.DataFrame(summary2).to_csv(os.path.join(OUT,'continuous_LDF_regime_summary.csv'),index=False)

print('\nREGIME SUMMARY')
print(pd.DataFrame(summary2).to_string(index=False))
print('\nSLOW CASES')
print(sumdf[sumdf.tau_h>=3].sort_values(['material','branch','Ea_kJmol','tau_h','scenario']).to_string(index=False))
