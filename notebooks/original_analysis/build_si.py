from docx import Document
from docx.shared import Inches,Pt,RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT,WD_CELL_VERTICAL_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from pathlib import Path
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

base=Path('/mnt/data')
source=base/'Supporting_Information_whichequilibriuminformationmatters_Mg_added_pipelineFig_ArialBold_dashed(3).docx'
out=base/'Supporting_Information_submission_integrated_20261119.docx'
coverage=pd.read_csv(base/'immediate_boundary_extension_coverage_native1h.csv')
ira=pd.read_csv(base/'IRA_environmental_common_support_transfer_summary.csv')
im=pd.read_csv(base/'ImCOF_wholeH_wholeY_transfer_summary.csv')
assert len(ira)==4 and len(im)==2
assert list(ira.n_Hsafe_Yrev)==[186,146,17,9]
assert list(im.n_Hsafe_Yrev)==[49,13]

# Source-derived figure 1: coverage opportunities (one measurement boundary changed at a time)
items=[('IRA lower','IRA-900-C','lower'),('Al2O3 upper','Al2O3_TEPA(20)','upper'),('PEI-30 upper','PEI-30wt','upper')]
rows=[]
for label,mat,branch in items:
 x=coverage[(coverage.material==mat)&(coverage.branch==branch)]
 rows.append((label,float(x[x.extension.str.contains('T_low_minus_5C' if branch=='lower' else 'T_high_plus_5C')].gain_percentage_points.iloc[0]),float(x[x.extension=='RH_high_plus_5pp'].gain_percentage_points.iloc[0])))
fig,ax=plt.subplots(figsize=(7.2,3.25))
xs=range(len(rows)); w=.34
ax.bar([x-w/2 for x in xs],[r[1] for r in rows],width=w,label='5 C outward temperature extension')
ax.bar([x+w/2 for x in xs],[r[2] for r in rows],width=w,label='5 pp upper-RH extension')
ax.set_xticks(list(xs),[r[0] for r in rows]);ax.set_ylabel('Pooled supported-transition gain (pp)')
ax.legend(frameon=False,fontsize=8,ncol=1);ax.grid(axis='y',alpha=.2)
fig.tight_layout();fig.savefig(base/'SI_Fig_S5_boundary_extension.png',dpi=220);plt.close(fig)

# Source-derived figure 2: counts in IRA environmental process audit
fig,ax=plt.subplots(figsize=(7.2,3.15))
labels=['Lower','Upper']; pos=[0,1]
ax.bar([i-.18 for i in pos],[186,146],width=.34,label='Representation-specific support')
ax.bar([i+.18 for i in pos],[17,9],width=.34,label='Shared hourly support')
for i,(a,b) in enumerate([(186,17),(146,9)]):
 ax.text(i-.18,a+3,str(a),ha='center',fontsize=8)
 ax.text(i+.18,b+3,str(b),ha='center',fontsize=8)
ax.set_ylim(0,218);ax.set_xticks(pos,labels);ax.set_ylabel('H-stable / modeled-Y-reversed pairs (of 595)')
ax.legend(frameon=False,fontsize=8)
fig.tight_layout();fig.savefig(base/'SI_Fig_S6_IRA_common_hour.png',dpi=220);plt.close(fig)

d=Document(source)
old_sec=next(p for p in d.paragraphs if p.text.strip()=='S6. Data and code provenance')
old_sec.text='S8. Data and code provenance'
old_cap=next(p for p in d.paragraphs if p.text.strip().startswith('Table S11. Analysis provenance map.'))
old_cap.text=old_cap.text.replace('Table S11.','Table S14.',1)

# append and relocate chunks just before old S8 heading
old_anchor=old_sec._element
nodes=[]
def add_p(text='',kind='body'):
 p=d.add_paragraph()
 if kind=='heading':
  p.style=d.styles['Heading 2'] if 'Heading 2' in d.styles else d.styles['Normal']
  p.paragraph_format.space_before=Pt(12);p.paragraph_format.space_after=Pt(5)
 elif kind=='subheading':
  p.paragraph_format.space_before=Pt(8);p.paragraph_format.space_after=Pt(4)
  for r in p.runs:r.bold=True
 else:
  p.paragraph_format.space_after=Pt(5)
 p.add_run(text)
 if kind=='subheading':p.runs[0].bold=True
 nodes.append(p._element)
 return p

def add_table(headers,rows,widths=None):
 t=d.add_table(rows=1,cols=len(headers)); t.style='Table Grid';t.alignment=WD_TABLE_ALIGNMENT.CENTER
 for i,head in enumerate(headers):
  cell=t.rows[0].cells[i];cell.text=str(head)
  for p in cell.paragraphs:
   for run in p.runs:run.bold=True;run.font.size=Pt(8)
 for row in rows:
  cells=t.add_row().cells
  for j,val in enumerate(row):
   cells[j].text=str(val)
   cells[j].vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER
   for p in cells[j].paragraphs:
    p.paragraph_format.space_after=Pt(1)
    for rr in p.runs:rr.font.size=Pt(8)
 if widths:
  for row in t.rows:
   for i,w in enumerate(widths):row.cells[i].width=Inches(w)
 t.rows[0]._tr.get_or_add_trPr().append(OxmlElement('w:tblHeader'))
 nodes.append(t._element)
 return t

def add_fig(path,caption):
 p=d.add_paragraph();p.alignment=WD_ALIGN_PARAGRAPH.CENTER
 p.add_run().add_picture(str(base/path),width=Inches(5.9));nodes.append(p._element)
 add_p(caption)

add_p('S6. Measurement-domain extensions and weather coverage','heading')
add_p('The native hourly weather support is determined by the measured temperature and relative-humidity ranges shared by the isotherms within each material-temperature interval. A consecutive hourly transition is counted when both endpoints fall inside that domain. Pooled transition coverage divides the supported-transition count summed across the 36 locations by the total number of eligible consecutive-hour transitions. Each boundary extension changes one limit while retaining the other limits and the original weather trajectories.')
add_p('Temperature extensions move the lower boundary of a lower-temperature interval by 5 °C toward colder weather, or the upper boundary of an upper-temperature interval by 5 °C toward warmer weather. The RH upper boundary is extended by five percentage points, up to 100%. The changes count newly supported weather transitions. Equilibrium CO₂ loadings in the additional region were not estimated.')
add_p('Table S11. Selected immediate single-boundary extensions of native 1 h pooled transition coverage. Changes are absolute percentage points (pp); identical measured-domain bounds give identical weather-coverage values.')
rows=[
 ('Al₂O₃-TEPA / MIL-101-TEPA / MgAl-PEI','lower (−20 to −5 °C)','0.620','0.010','0.225'),
 ('ImCOF-TAEA / LWT-bPPI5','lower (−20 to 5 °C)','2.911','0.010','0.874'),
 ('PEI-30/40/50wt','lower (−20 to 5 °C)','4.870','0.034','1.374'),
 ('IRA-900-C','lower (15 to 25 °C)','15.352','6.797','2.118'),
 ('Al₂O₃-TEPA / MIL-101-TEPA / MgAl-PEI','upper (−5 to 25 °C)','19.960','6.157','4.484'),
 ('ImCOF-TAEA / LWT-bPPI5','upper (5 to 25 °C)','17.475','6.157','3.786'),
 ('PEI-30/40/50wt','upper (5 to 35 °C)','41.222','2.521','7.166'),
 ('IRA-900-C','upper (25 to 35 °C)','12.992','1.443','2.414')]
add_table(['Material(s)','Interval','Baseline (%)','Temperature gain (pp)','Upper RH gain (pp)'],rows,[2,1.2,.8,1,1])
add_p('The complete source table, immediate_boundary_extension_coverage_native1h.csv, retains all nine formulations, both temperature intervals, and both RH boundaries. A temperature-extension curve and its 5 °C milestones are supplied as supplementary machine-readable data. These coverage changes describe the sampled weather-domain geometry; they do not establish a change in sorption capacity, process yield, or optimal experimental design.')
add_fig('SI_Fig_S5_boundary_extension.png','Fig. S5. Native-hour pooled transition-coverage gains for selected measured-domain boundary extensions. Each bar changes one boundary while holding the other three limits fixed. The full table contains all material–interval combinations.')

add_p('S7. Equilibrium versus modeled-release location-pair reversals','heading')
add_p('For each eligible location pair, an ordering reversal is recorded separately for cumulative equilibrium-loading variation H and modeled CO₂ release Y when the equilibrium representation changes from single-isotherm to temperature-resolved. The four joint outcomes distinguish pairs that are unchanged in both, reversed only in H, reversed only in Y, or reversed in both. These are descriptive counts over correlated pairs of the prespecified location panel.')
add_p('S7.1. IRA-900-C: weather-driven moisture release','subheading')
add_p('The representation-specific-support calculation evaluates each model over its own supported weather sequence. The shared-hour calculation uses the intersection of finite single-isotherm and temperature-resolved q* states and propagates the sorbent history over that sequence using the same LDF time constant of 1 h and the same out-of-domain hold convention. Both treatments use 35 common finite locations (595 pairs). The common-hour intervention changes which weather states and kinetic history are included in the modeled release.')
add_p('Table S12. IRA-900-C joint H–Y pairwise outcomes for the weather-driven moisture-release calculation (595 eligible pairs per row). The four cell counts sum to 595.')
add_table(['Interval','Weather support','Neither','H only','Y only','Both'],[
 ('Lower','Representation-specific',396,12,186,1),('Upper','Representation-specific',427,18,146,4),('Lower','Shared hourly',565,7,17,6),('Upper','Shared hourly',564,9,9,13)], [1,1.55,.68,.68,.68,.68])
add_p('With representation-specific support, 186 lower-interval and 146 upper-interval pairs retained their H ordering but reversed modeled release. On shared hourly support the corresponding counts were 17 and 9. The counts are grounded in IRA_environmental_common_support_transfer_summary.csv and the associated pairwise/source-regression files in HY_process_common_hour_and_kinetic_audit_v2. A time-constant sweep of 0.25–6 h changes the remaining Y-only reversal counts; this sweep is a prescribed kinetic sensitivity, not independent process validation.')
add_fig('SI_Fig_S6_IRA_common_hour.png','Fig. S6. IRA-900-C location pairs with unchanged H ordering and reversed modeled-release ordering under representation-specific and shared-hour support. The support intervention also recomputes the kinetic history.')
add_p('S7.2. ImCOF-TAEA: whole-range H and modeled regeneration','subheading')
add_p('The whole-range H–Y comparison uses verified full-range single-isotherm and temperature-resolved loading functions, with 30 common modeled locations (435 pairs). In the fixed 80 °C regeneration condition, modeled CO₂ release reverses for 56 pairs, seven of which also reverse in H. Under modeled weather-dependent solar regeneration, 13 pairs reverse in release, none of which reverse in H. The representation-related H reversal count is 25 in both conditions.')
add_p('Table S13. ImCOF-TAEA whole-range H and modeled-release pairwise outcomes (435 eligible location pairs per row).')
add_table(['Modeled regeneration','Neither','H only','Y only','Both'],[
 ('Fixed 80 °C',361,18,49,7),('Weather-dependent solar',397,25,13,0)], [2.5,.8,.8,.8,.8])
add_p('The whole-range H, aligned-score and pairwise outputs are retained in ImCOF_wholeH_Y_transfer_verified_v3. The regression manifest reports a passing P0 equilibrium check and a passing saved-process-Y schema/cycle-count check. The solar thermal forcing is model-derived using PADAC 13X information, rather than measured ImCOF reactor temperatures. Therefore these are within-model process comparisons and not independent experimental validation. The hourly support used for H differs from the modeled-cycle support used for Y.')
add_p('S7.3. Machine-readable source map','subheading')
add_p('Coverage calculations: REPOSITORY/MAIN_climate_hourly_2015_2024.csv and REPOSITORY/MAIN_material_support_bounds.csv; retained outputs in REPOSITORY/SI_submission_evidence_20261119. Pairwise H sensitivity: REPOSITORY/MAIN_temperature_correction_pairwise.csv and the retained vulnerable-pair CSVs. IRA: process_fidelity_runs/20261115_192400_v1.6.5-climate-cache-key-fix/HY_process_common_hour_and_kinetic_audit_v2. ImCOF: the same frozen run under ImCOF_wholeH_Y_transfer_verified_v3. Output CSVs and figure-source PNGs are archived with this SI.')

# Place elements directly before original S8, preserving original tables, figures and drawing relationships.
for node in nodes: old_anchor.addprevious(node)
d.save(out)
print('OUTPUT',out,'bytes',out.stat().st_size,'new_blocks',len(nodes))
print('figs',[(x.name,x.stat().st_size) for x in base.glob('SI_Fig_S*.png')])
