"""Presentation-only layout: preserve every frozen community/half-year cell."""
import argparse, os
from pathlib import Path
import csv,json,hashlib,sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize
sys.path.insert(0, os.environ['FIGURE_QA_SCRIPTS'])
from audit_panel_alignment import require_matplotlib_panel_alignment
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--day20-dir', type=Path, required=True)
parser.add_argument('--output-dir', type=Path, required=True)
args=parser.parse_args()
BASE=args.day20_dir
OUT=args.output_dir
OUT.mkdir(parents=True, exist_ok=False)
QA=OUT/'qa'
QA.mkdir()
COMMS=['ChatGPTCoding','webdev','programming','GitHub','compsci']
PERIODS=['2022-H2','2023-H1','2023-H2','2024-H1','2024-H2','2025-H1']
DIMS=['Competence','Reliability','Familiarity','Integrity','Transparency','Benevolence','Incompetence','Unreliability','Unfamiliarity','Dishonesty','Deception','Opaqueness','Malevolence']
plt.rcParams.update({'font.family':'sans-serif','font.sans-serif':['Arial','DejaVu Sans'],'font.size':7.5,'pdf.fonttype':42,'svg.fonttype':'none','axes.linewidth':.55})
results={}
for number,archive,cats in [(2,'classification',['Trust','Distrust','Both','Neither']),(3,'dimensions',DIMS)]:
 source=BASE/f'{archive}_temporal_summary.csv';rows=list(csv.DictReader(source.open()))
 assert len(rows)==len(COMMS)*len(PERIODS)*len(cats)
 index={(r['community'],r['half_year_utc'],r['category']):r for r in rows}
 assert len(index)==len(rows)
 fig,axs=plt.subplots(2,3,figsize=(5.4,6.1 if number==3 else 3.65))
 fig.subplots_adjust(left=.185,right=.995,top=.93,bottom=.17 if number==3 else .23,wspace=.13,hspace=.31 if number==3 else .58)
 cmap=plt.get_cmap('Blues').copy();cmap.set_bad('#737373');norm=Normalize(0,1)
 active=[];matrices=[]
 for j,community in enumerate(COMMS):
  ax=axs.flat[j];active.append(ax);mat=[]
  for cat in cats:
   line=[]
   for period in PERIODS:
    r=index[(community,period,cat)];n=int(r['outcome_available_n']);val=float(r['proportion']) if r['proportion'] else np.nan
    assert (n==0)==np.isnan(val)
    if n: assert abs(val-int(r['count'])/n)<1e-13
    line.append(val)
   mat.append(line)
  matrices.append(mat)
  im=ax.imshow(mat,cmap=cmap,norm=norm,interpolation='nearest',aspect='auto')
  ax.text(0,1.045,chr(97+j),transform=ax.transAxes,fontweight='bold',fontsize=8,va='bottom')
  ax.set_title(community,loc='left',x=.115,fontsize=7.5,fontweight='bold',pad=10)
  ax.set_yticks(range(len(cats)));ax.set_yticklabels(cats if j%3==0 else ['']*len(cats),fontsize=7.1)
  ax.tick_params(axis='both',length=0,pad=3)
  labels=[]
  for k,period in enumerate(PERIODS):
   r=index[(community,period,cats[0])];n=int(r['outcome_available_n'])
   if r['period_role']=='partial_coverage_context_only': ax.axvspan(k-.5,k+.5,color='#737373',alpha=.16,lw=0)
   elif r['sufficiency_status']=='insufficient_n_lt_20':ax.axvspan(k-.5,k+.5,color='#B64342',alpha=.10,lw=0)
   labels.append(period[:4]+'\n'+period[-2:])
  ax.set_xticks(range(6));ax.set_xticklabels(labels,fontsize=6.4)
  for k,label in enumerate(ax.get_xticklabels()):
   r=index[(community,PERIODS[k],cats[0])]
   if int(r['outcome_available_n'])==0:label.set_color('#4D4D4D')
   elif r['sufficiency_status']=='insufficient_n_lt_20':label.set_color('#B64342');label.set_fontweight('bold')
   elif r['period_role']=='partial_coverage_context_only':label.set_color('#737373')
  ax.set_xlim(-.5,5.5)
 axs[1,2].set_axis_off()
 cax=fig.add_axes([.3,.065 if number==3 else .10,.55,.017 if number==3 else .025]);cb=fig.colorbar(im,cax=cax,orientation='horizontal',ticks=[0,.25,.5,.75,1]);cb.ax.set_xticklabels(['0%','25%','50%','75%','100%']);cb.ax.tick_params(labelsize=7,length=2);cb.set_label('Within-cell proportion',fontsize=7,labelpad=3)
 fig.canvas.draw()
 require_matplotlib_panel_alignment(fig,axes=active,panel_ids=list('abcde'),row_groups=[list('abc'),list('de')],column_groups=[['a','d'],['b','e']],json_out=str(QA/f'figure{number}_readable.alignment.json'),overlay_svg=str(QA/f'figure{number}_readable.alignment.svg'),tolerance_pt=1.5,require_panel_labels=True,strict=True)
 fig.savefig(OUT/f'figure{number}.pdf')
 fig.savefig(OUT/f'figure{number}.svg')
 fig.savefig(OUT/f'figure{number}.png',dpi=600)
 plt.close(fig)
 results[archive]={'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'cells':len(rows),'all_count_proportion_status_values_preserved':True,'layout':'3 panels above 2; same prespecified order; shared scale','minimum_font_pt':6.4,'dimension_order':cats}
(QA/'readable_temporal_verification.json').write_text(json.dumps(results,indent=2))
