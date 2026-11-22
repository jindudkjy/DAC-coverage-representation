"""Source-data reconstructions for manuscript Fig. 2--7 (not artwork-identical).
No synthesized experimental points. Original figure production code is not claimed.
"""
from pathlib import Path
import argparse,json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

def read(inp,name):
 p=inp/(name+'.csv')
 if not p.exists():raise FileNotFoundError(p)
 return pd.read_csv(p)
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--input-dir',type=Path,default=Path('/mnt/data'));ap.add_argument('--output-dir',type=Path,required=True);a=ap.parse_args();o=a.output_dir;o.mkdir(parents=True,exist_ok=True)
 plt.rcParams.update({'font.size':9,'axes.spines.top':False,'axes.spines.right':False,'figure.dpi':150,'savefig.dpi':200})
 manifest=[]
 def save(num,fig,sources,note):
  filename=f'Fig{num}_reconstructed_from_frozen_CSV.png'
  fig.savefig(o/filename,bbox_inches='tight');plt.close(fig)
  manifest.append(dict(figure=num,output=filename,source_files='; '.join(sources),status='SOURCE_DATA_REPLOT_NOT_ARTWORK_REGRESSION',note=note))
 # Fig2: median metrics by branch and temporal mode
 d=read(a.input_dir,'MAIN_magnitude_rank_fidelity_panel_summary');fig,ax=plt.subplots(figsize=(7.5,4.5))
 for branch,g in d.groupby('branch'):
  ax.scatter(g.median_relative_H_error,g.median_kendall_tau,label=branch,s=60)
  for r in g.itertuples():ax.annotate(r.temporal_mode.replace('subsample_','').replace('average_','avg'),(r.median_relative_H_error,r.median_kendall_tau),fontsize=6,xytext=(3,3),textcoords='offset points')
 ax.set(xlabel='Median relative H error',ylabel='Median Kendall tau',title='Fig. 2 source-data reconstruction');ax.legend();fig.tight_layout();save(2,fig,['MAIN_magnitude_rank_fidelity_panel_summary.csv'],'Medians only; original manuscript individual panel structure not asserted.')
 # Fig3: class-C bootstrap delta rho by temporal mode and branch
 d=read(a.input_dir,'SI_rh_null_classC_bootstrap');fig,ax=plt.subplots(figsize=(8,4))
 for branch,g in d.groupby('branch'):
  s=g.groupby('temporal_mode').delta_rho_tensor.median().sort_index()
  ax.plot(s.index,s.values,'o-',label=branch)
 ax.axhline(0,color='0.4',lw=.7);ax.tick_params(axis='x',labelrotation=30);ax.set(ylabel='Median Class-C delta rho (Tensor)',title='Fig. 3 source-data reconstruction');ax.legend();fig.tight_layout();save(3,fig,['SI_rh_null_classC_bootstrap.csv'],'Subset of A/B/C information-hierarchy original figure; Class-C observed values only.')
 # Fig4: added temperature held interior LWT and Mg
 l=read(a.input_dir,'SI_added_temperature_held_interior');m=read(a.input_dir,'Mg_LWT_analogue_held_interior_summary');fig,axes=plt.subplots(1,2,figsize=(10.6,4.4))
 g=l[(l.material=='LWT-bPPI5')&(l.support_mode=='matched')].sort_values(['branch','temporal_mode']);
 for branch,h in g.groupby('branch'):
  axes[0].plot(h.temporal_mode,h.delta_tau,'o-',label=branch)
 axes[0].axhline(0,color='0.5',lw=.8);axes[0].set(title='LWT held-interior comparison',ylabel='Delta Kendall tau');axes[0].tick_params(axis='x',rotation=45);axes[0].legend()
 m=m.sort_values('temporal_mode');axes[1].plot(m.temporal_mode,m.delta_tau,'o-',label='Mg analogue');axes[1].axhline(0,color='0.5',lw=.8);axes[1].set(title='Mg analogue held-interior',ylabel='Delta Kendall tau');axes[1].tick_params(axis='x',rotation=45);fig.suptitle('Fig. 4 source-data reconstruction');fig.tight_layout();save(4,fig,['SI_added_temperature_held_interior.csv','Mg_LWT_analogue_held_interior_summary.csv'],'Mg bootstrap uncertainty stored separately; do not infer individual climate uncertainty from this summary.')
 # Fig5: family correction magnitude, margin threat / reversal
 d=read(a.input_dir,'SI_temperature_correction_family_summary');d=d[d.margin_filter==0].sort_values('family_primary');fig,axs=plt.subplots(1,2,figsize=(10.5,4.5))
 axs[0].bar(d.family_primary,d.median_C_rel_Hbar);axs[0].set(ylabel='Median correction / mean H',title='Correction magnitude')
 x=np.arange(len(d));axs[1].bar(x-.18,d.frac_margin_threat,width=.36,label='Threat');axs[1].bar(x+.18,d.reversal_fraction,width=.36,label='Reversal');axs[1].set_xticks(x,d.family_primary,rotation=60,ha='right');axs[1].set(title='Pairwise ordering consequence',ylabel='Pair fraction');axs[1].legend()
 axs[0].tick_params(axis='x',rotation=60);fig.suptitle('Fig. 5 source-data reconstruction');fig.tight_layout();save(5,fig,['SI_temperature_correction_family_summary.csv'],'Family summary only; not full pairwise permutation panels.')
 # Fig6: equilibrium vs LDF Kendall and sensitivity for operating time constants
 d=read(a.input_dir,'SI_kinetic_rank_summary');fig,axs=plt.subplots(1,2,figsize=(9.5,4.1))
 for scenario,g in d.groupby('scenario'):
  ss=g.groupby('tau_h').kendall_equilibrium_full_vs_fullLDF.median().sort_index();axs[0].plot(ss.index,ss.values,'o-',label=scenario)
  ss=g.groupby('tau_h').kendall_singleLDF_vs_fullLDF.median().sort_index();axs[1].plot(ss.index,ss.values,'o-',label=scenario)
 for ax in axs:ax.set(xlabel='Assumed time constant (h)',ylabel='Median Kendall tau');ax.legend(fontsize=7)
 axs[0].set_title('Equilibrium vs finite-rate');axs[1].set_title('Single vs Tensor under finite-rate');fig.suptitle('Fig. 6 source-data reconstruction');fig.tight_layout();save(6,fig,['SI_kinetic_rank_summary.csv'],'Aggregated kinetic sensitivity, not a full reproduction of original four-panel continuous-memory figure.')
 # Fig7: exact per-pair fractions from retained final classifications
 ira=read(a.input_dir,'IRA_environmental_common_support_transfer_summary');im=read(a.input_dir,'ImCOF_wholeH_wholeY_transfer_summary')
 rr=[]
 for x in ira.itertuples():rr.append(dict(label=f'IRA {x.branch} {x.support_treatment}',N=x.n_pairs,Yonly=x.n_Hsafe_Yrev,Honly=x.n_Hrev_Ysafe,Both=x.n_Hrev_Yrev))
 for x in im.itertuples():rr.append(dict(label=f'ImCOF {x.operating_mode}',N=x.n_all_pairs,Yonly=x.n_Hsafe_Yrev,Honly=x.n_Hrev_Ysafe,Both=x.n_Hrev_Yrev))
 t=pd.DataFrame(rr);t.to_csv(o/'Fig7_source_data_reconstructed.csv',index=False)
 fig,ax=plt.subplots(figsize=(10,4.8));x=np.arange(len(t));w=.3
 ax.bar(x-w,t.Yonly/t.N,width=w,label='Y-only reversal');ax.bar(x,t.Honly/t.N,width=w,label='H-only reversal');ax.bar(x+w,t.Both/t.N,width=w,label='Both reversed')
 ax.set_xticks(x,t.label,rotation=35,ha='right');ax.set(ylabel='Fraction of strict location pairs',title='Fig. 7 H/Y reversal source-data reconstruction');ax.legend();fig.tight_layout();save(7,fig,['IRA_environmental_common_support_transfer_summary.csv','ImCOF_wholeH_wholeY_transfer_summary.csv'],'Includes IRA original and shared hour plus ImCOF active and solar; H-only,Y-only,both counts sourced from frozen classifications.')
 pd.DataFrame(manifest).to_csv(o/'figure_reconstruction_manifest.csv',index=False)
 print('Created',len(manifest),'figure reconstructions')
if __name__=='__main__':main()
