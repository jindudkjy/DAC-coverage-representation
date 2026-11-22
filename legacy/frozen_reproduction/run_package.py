"""Run the three independent tasks against the curated Drive package.
Stages symbolic links to ORIGINAL frozen files; never overwrites source data.
`--root`: path to DAC_manuscript_SI_complete_reproducibility_package_20261119
"""
import argparse,sys,subprocess,tempfile,os
from pathlib import Path

NEEDED={
 'measurement_domain_extension_reproduction':['MAIN_climate_hourly_2015_2024.csv','MAIN_material_support_bounds.csv','MAIN_equilibrium_dataset_master.xlsx','immediate_boundary_extension_coverage_native1h.csv'],
 'IRA_shared_support_score_regression':['IRA_environmental_common_support_climate_scores.csv','IRA_environmental_common_support_transfer_summary.csv'],
 'manuscript_figures_reproduction':['MAIN_magnitude_rank_fidelity_panel_summary.csv','SI_rh_null_classC_bootstrap.csv','SI_added_temperature_held_interior.csv','Mg_LWT_analogue_held_interior_summary.csv','SI_temperature_correction_family_summary.csv','SI_kinetic_rank_summary.csv','IRA_environmental_common_support_transfer_summary.csv','ImCOF_wholeH_wholeY_transfer_summary.csv']}
PREFERRED=['01_canonical_inputs','03_equilibrium_H_results','04_process_HY_results','05_SI_figures_and_data','06_provenance_and_audits','08_reproduction_code_and_outputs']

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--root',required=True,type=Path);ap.add_argument('--target',choices=['all','coverage','IRA','figures'],default='all');ap.add_argument('--output-dir',type=Path,default=None);a=ap.parse_args()
 root=a.root.expanduser().resolve()
 out=a.output_dir or root/'08_reproduction_code_and_outputs'/'reproduced_outputs'
 out.mkdir(parents=True,exist_ok=True)
 tasks=['measurement_domain_extension_reproduction','IRA_shared_support_score_regression','manuscript_figures_reproduction']
 if a.target!='all':tasks=[{'coverage':tasks[0],'IRA':tasks[1],'figures':tasks[2]}[a.target]]
 with tempfile.TemporaryDirectory(prefix='dac_repro_inputs_') as temp:
  stage=Path(temp)
  for name in sorted(set(sum((NEEDED[x] for x in tasks),[]))):
   hits=[]
   for folder in PREFERRED:
    p=root/folder/name
    if p.is_file():hits.append(p)
   if not hits:raise FileNotFoundError(f'{name} missing in package (search other existing Drive folders and copy exact source)')
   # Priority by listed canonical folder order, to avoid accidental versions.
   os.symlink(hits[0],stage/name)
  for task in tasks:
   script=Path(__file__).parent/(task+'.py')
   cmd=[sys.executable,str(script),'--input-dir',str(stage),'--output-dir',str(out)]
   print('RUN',task,flush=True);subprocess.run(cmd,check=True)
 print('ALL REQUESTED TASKS COMPLETE. Hourly IRA process Y generation was NOT performed.')
if __name__=='__main__':main()
