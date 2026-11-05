#!/usr/bin/env python3
"""Rebuild archive-separated results and paper figures from public release ZIPs.

The output contains sensitive record-level intermediates; keep it private.
No LLM, sampling, collection, cross-archive join, or scientific freeze is run.
"""
import argparse
import csv
import hashlib
import importlib.metadata
import json
import os
import platform
import shutil
import subprocess
import sys
import traceback
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from reproduce_frozen_inputs import compare_csv, sha256
from reproduce_posthoc_association import calculate
from reproduce_rq3 import generate

ROOT = Path(__file__).resolve().parents[1]
QA = ROOT / 'vendor/nature_figure_qa'
ARCHIVES = {
    'classification_raw': ('Trust_Classification_json.zip', '270cea2a422d2930390a368f0049f34bf9566799583d218f6374ee84723458a7', 'Trust_Classification_json/data_task1.json'),
    'dimensions_raw': ('Dimensions_of_Trust_json.zip', '0bc2664683b0987c054be3bb172bf4e14a86c9bd8e4a7bf3e325e653cc057ffb', 'Dimensions_of_Trust_json/data_task2.json'),
}
COMPARISONS = [
 ('day15/rq1_counts_prevalence_source.csv','results/rq1_counts_prevalence_source.csv',('archive','scope','category')),
 ('day15/rq1_denominator_ledger.csv','results/rq1_denominator_ledger.csv',('archive','scope')),
 ('day16/rq1_table_source.csv','results/rq1_table_source.csv',('archive','scope','category')),
 ('day18/community_descriptive_summary.csv','results/final_community_table_source.csv',('archive','community','category')),
 ('day20/classification_temporal_summary.csv','results/classification_temporal_summary.csv',('archive','community','half_year_utc','category')),
 ('day20/dimensions_temporal_summary.csv','results/dimensions_temporal_summary.csv',('archive','community','half_year_utc','category')),
 ('day20/temporal_visualization_source.csv','results/temporal_visualization_source.csv',('archive','community','half_year_utc','category')),
 ('day20/temporal_cell_status_ledger.csv','results/temporal_cell_status_ledger.csv',('archive','community','half_year_utc')),
 ('rq3/rq3_descriptive_table_source.csv','results/rq3_descriptive_table_source.csv',('archive','community','category')),
]

def dump(p, data):
    p.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n', encoding='utf8')

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--zip-dir', type=Path, required=True, help='directory with the two original public ZIPs')
    parser.add_argument('--output-dir', type=Path, required=True, help='new private directory outside checkout')
    args = parser.parse_args()
    out, zips = args.output_dir.resolve(), args.zip_dir.resolve()
    if out.exists() or out == ROOT or ROOT in out.parents or out == zips or out in zips.parents or zips in out.parents:
        parser.error('output must be a new directory outside the checkout and ZIP directory')
    out.mkdir(parents=True, mode=0o700)
    os.chmod(out, 0o700)
    (out/'logs').mkdir()
    env = os.environ.copy()
    env.update(MPLBACKEND='Agg', PYTHONDONTWRITEBYTECODE='1', FIGURE_QA_SCRIPTS=str(QA))
    env['PATH'] = str(Path(sys.executable).parent) + os.pathsep + env.get('PATH', '')
    checks, commands, inputs = {}, [], {}
    def check(name, ok, **extra):
        checks[name] = {'match': bool(ok), **extra}
        if not ok:
            raise ValueError('failed check: '+name)
    def record(path):
        inputs[str(path)] = {'sha256':sha256(path), 'bytes':path.stat().st_size}
    def run(name, argv, required=True):
        start = datetime.now(timezone.utc).isoformat()
        with (out/'logs'/f'{name}.log').open('w') as log:
            p = subprocess.run([str(x) for x in argv], cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
        commands.append({'stage':name,'argv':[str(x) for x in argv], 'started_utc':start,'returncode':p.returncode})
        dump(out/'commands.json',commands)
        if required and p.returncode:
            raise RuntimeError(f'{name} returned {p.returncode}; see logs/{name}.log')
        return p.returncode
    def script(name,*values):
        return [sys.executable,ROOT/'scripts'/name,*values]
    failure = None
    try:
        run('package_verification',script('verify_package.py'))
        freeze_path=ROOT/'provenance/data_freeze_version_record.json'
        record(freeze_path)
        freeze=json.loads(freeze_path.read_text())
        references=json.loads((ROOT/'provenance/20261105_public_reference_hashes.json').read_text())
        raw=out/'raw'; raw.mkdir()
        paths={}
        for key,(name,expected,member) in ARCHIVES.items():
            archive=zips/name; record(archive)
            check('archive/'+key,sha256(archive)==expected,sha256=sha256(archive),expected_sha256=expected)
            target=raw/Path(member).name
            with zipfile.ZipFile(archive) as z, z.open(member) as source, target.open('xb') as dest:
                shutil.copyfileobj(source,dest)
            actual=sha256(target); rows=len(json.loads(target.read_text()))
            want=freeze['inputs'][key]
            check('raw/'+key,actual==want['sha256'] and rows==want['source_rows'],sha256=actual,expected_sha256=want['sha256'],rows=rows)
            paths[key]=target
        classraw,dimraw=paths['classification_raw'],paths['dimensions_raw']
        run('day11',script('run_day11_encoding_qc.py','--classification',classraw,'--dimensions',dimraw,'--output-dir',out/'day11'))
        encoding=out/'day11/primary_dimension_encoding.jsonl'
        check('day11/encoding',sha256(encoding)==freeze['inputs']['day11_primary_encoding']['sha256'],sha256=sha256(encoding))
        check('day11/qc',json.loads((out/'day11/qc_summary.json').read_text())['status']=='PASS')
        rebuilt=out/'day14'
        run('day14',script('run_day14_freeze.py','--classification',classraw,'--dimensions',dimraw,'--day11-encoding',encoding,'--output-dir',rebuilt))
        for name,expected in freeze['artifacts'].items():
            actual=sha256(rebuilt/name)
            check('day14/'+name,actual==expected,sha256=actual,expected_sha256=expected)
        for stage,name in [('day15','run_day15_rq1_counts.py'),('day18','run_day18_rq2_community.py')]:
            opts=['--classification',rebuilt/'classification_analytic_frozen.jsonl','--dimensions',rebuilt/'dimensions_analytic_frozen.jsonl','--freeze-record',freeze_path,'--output-dir',out/stage]
            if stage=='day18': opts += ['--rq1-freeze-record',ROOT/'provenance/rq1_freeze_record.json']
            run(stage,script(name,*opts))
            check(stage+'/qc',json.loads((out/stage/'qc_summary.json').read_text())['status']=='PASS')
        run('day16',script('run_day16_rq1_display.py','--day15-source',out/'day15/rq1_counts_prevalence_source.csv','--day15-manifest',out/'day15/run_manifest.json','--figure-skill-scripts',QA,'--output-dir',out/'day16'))
        run('day17',script('run_day17_sensitivities.py','--classification-frozen',rebuilt/'classification_analytic_frozen.jsonl','--dimensions-raw',dimraw,'--day14-record',freeze_path,'--day11-manifest',out/'day11/run_manifest.json','--day11-field-qc',out/'day11/dimension_field_qc.csv','--day15-source',out/'day15/rq1_counts_prevalence_source.csv','--output-dir',out/'day17'))
        sensitivity_qc=json.loads((out/'day17/qc_summary.json').read_text())
        check('day17/numerical_qc',sensitivity_qc['denominator_sensitivity_status']=='PASS' and sensitivity_qc['overall_status']=='BLOCKED',historical_overall_status=sensitivity_qc['overall_status'],reliability_status=sensitivity_qc['reliability_sensitivity_status'])
        run('day20',script('run_day20_temporal.py','--research-root',ROOT,'--freeze-dir',rebuilt,'--community-dir',out/'day18','--output-dir',out/'day20'))
        generate(out/'day15',out/'day18',out/'day20',out/'rq3')
        for computed,reference,keys in COMPARISONS:
            record(ROOT/reference)
            result=compare_csv(out/computed,ROOT/reference,keys)
            check('table/'+computed,result['match'],comparison=result,computed_sha256=sha256(out/computed),reference_sha256=sha256(ROOT/reference))
        for name,expected in references['aggregate_outputs'].items():
            actual=sha256(out/name)
            check('historical_hash/'+name,actual==expected,sha256=actual,expected_sha256=expected)
        check('rq1/public_table',sha256(out/'day16/rq1_table.md')==sha256(ROOT/'results/rq1_table.md'))
        # Compare each recorded manuscript fraction to the named newly computed cell.
        with (out/'day15/rq1_counts_prevalence_source.csv').open(newline='') as f:
            pooled={(r['archive'],r['scope'],r['category']):r for r in csv.DictReader(f)}
        with (out/'day20/temporal_visualization_source.csv').open(newline='') as f:
            temporal={(r['archive'],r['community'],r['half_year_utc'],r['category']):r for r in csv.DictReader(f)}
        fixture=json.loads((ROOT/'provenance/20261105_manuscript_fraction_claims.json').read_text())['claims']
        claim_checks=[]
        for claim in fixture:
            candidates=[]
            for key in claim['matching_cells']:
                cell=(pooled if len(key)==3 else temporal).get(tuple(key))
                if cell:
                    denominator=int(cell['denominator_n'] if len(key)==3 else cell['outcome_available_n'])
                    candidates.append(int(cell['count'])==claim['numerator'] and denominator==claim['denominator'])
            percent=claim['percentage']
            matches=any(candidates) and (percent is None or f"{100*claim['numerator']/claim['denominator']:.1f}"==percent)
            claim_checks.append({'source':claim['source'],'line':claim['line'],'match':matches})
        check('manuscript/fraction_occurrences',len(fixture)==20 and all(x['match'] for x in claim_checks),claims=claim_checks)
        for archive,category,periods,expected in [
            ('classification','Trust',['2023-H1','2023-H2','2024-H1','2024-H2','2025-H1'],('41.1','46.6')),
            ('dimensions','Competence',['2023-H1','2023-H2','2024-H1'],('74.0','78.1')),
            ('dimensions','Competence',['2024-H2','2025-H1'],('68.1','68.8'))]:
            vals=[100*float(temporal[(archive,'ChatGPTCoding',h,category)]['proportion']) for h in periods]
            got=(f'{min(vals):.1f}',f'{max(vals):.1f}')
            check('manuscript/range/'+archive+'/'+periods[0],got==expected,computed=got,expected=expected)
        association=calculate(out/'day18/community_descriptive_summary.csv')
        check('association',association['n']==8519 and f"{association['chi_square_descriptive']:.3f}"=='137.516' and f"{association['cramers_v']:.3f}"=='0.073',computed=association)
        run('manuscript_temporal',script('render_manuscript_temporal.py','--day20-dir',out/'day20','--output-dir',out/'manuscript_temporal'))
        paper=out/'paper';paper.mkdir()
        # Recreate the revised manuscript's 17-by-5 formatted numerical cells.
        with (out/'day18/community_descriptive_summary.csv').open(newline='') as f:
            local=list(csv.DictReader(f))
        communities=['ChatGPTCoding','webdev','programming','GitHub','compsci']
        table_rows=[]
        for category in dict.fromkeys(r['category'] for r in local):
            cells=[next(r for r in local if r['category']==category and r['community']==c) for c in communities]
            values=[r'\shortstack[r]{' + f"{int(r['count']):,}/{int(r['eligible_denominator_n']):,}" + r'\\(' + f"{float(r['proportion'])*100:.1f}" + r'\%)}' for r in cells]
            table_rows.append(category + ' & ' + ' & '.join(values) + r' \\')
        table_path=paper/'table1_computed_rows.tex'
        table_path.write_text('\n'.join(table_rows)+'\n')
        table_expected='497cc5b314344a32c1043b84d150d6784cc0b89a0269e1df8b56810d8eb7faa3'
        check('manuscript/table1_85_cells',len(table_rows)==17 and sha256(table_path)==table_expected,sha256=sha256(table_path),expected_sha256=table_expected)
        for number,source in [(1,out/'day16/rq1_figure_300dpi.pdf'),(2,out/'manuscript_temporal/figure2.pdf'),(3,out/'manuscript_temporal/figure3.pdf')]:
            shutil.copy2(source,paper/f'figure{number}.pdf')
            code=ROOT/'scripts'/('run_day16_rq1_display.py' if number==1 else 'render_manuscript_temporal.py')
            for label, tool, target, opts in [('source','validate_figure.py',code,['--json']),('text','audit_pdf_text.py',source,['--min-pt','5','--json']),('collision','audit_figure_collisions.py',source,['--json-out',paper/f'figure{number}_collision.json'])]:
                rc=run(f'figure{number}_{label}',[sys.executable,QA/tool,target,*opts],required=False)
                check(f'figure{number}/{label}',rc==0,returncode=rc)
        # A direct image-object measurement tests actual embedding, not a savefig argument.
        import fitz
        doc=fitz.open(paper/'figure1.pdf'); images=doc[0].get_image_info()
        dpi=[{'x':i['width']*72/(i['bbox'][2]-i['bbox'][0]),'y':i['height']*72/(i['bbox'][3]-i['bbox'][1])} for i in images if i['bbox'][2]>i['bbox'][0] and i['bbox'][3]>i['bbox'][1]]
        check('figure1/embedded_raster_dpi',bool(dpi) and all(min(x['x'],x['y'])>=300 for x in dpi),images=dpi)
        # Compare old-geometry paper renders against the earlier manuscript audit.
        for number,path in [(1,out/'day16/rq1_figure.pdf'),(2,paper/'figure2.pdf'),(3,paper/'figure3.pdf')]:
            d=fitz.open(path);pix=d[0].get_pixmap(matrix=fitz.Matrix(2,2),alpha=False)
            actual=hashlib.sha256(pix.samples).hexdigest();want=references['paper_figure_render_144dpi'][f'figure{number}']
            check(f'figure{number}/historical_render_144dpi',actual==want['sha256_pixels_144dpi'] and [pix.width,pix.height]==[want['width'],want['height']],sha256=actual,reference=want)
        for path,expected in inputs.items():
            check('immutable/'+path,sha256(Path(path))==expected['sha256'])
    except Exception:
        failure=traceback.format_exc();(out/'failure.log').write_text(failure)
    finally:
        dump(out/'input_inventory.json',inputs)
        dump(out/'environment.json',{'python':sys.version,'executable':sys.executable,'platform':platform.platform(),'packages':{d.metadata['Name']:d.version for d in importlib.metadata.distributions()},'git_head':subprocess.run(['git','rev-parse','HEAD'],cwd=ROOT,capture_output=True,text=True).stdout.strip(),'git_status':subprocess.run(['git','status','--short'],cwd=ROOT,capture_output=True,text=True).stdout,'scripts':{str(p.relative_to(ROOT)):sha256(p) for p in sorted((ROOT/'scripts').glob('*.py'))},'qa_scripts':{p.name:sha256(p) for p in sorted(QA.glob('*.py'))}})
        dump(out/'output_inventory.json',{str(p.relative_to(out)):{'sha256':sha256(p),'bytes':p.stat().st_size} for p in sorted(out.rglob('*')) if p.is_file() and p.name not in ('output_inventory.json','report.json')})
        status='PASS' if not failure and checks and all(x['match'] for x in checks.values()) else 'FAIL'
        dump(out/'report.json',{'status':status,'checks':checks,'failure':failure,'executed_utc':datetime.now(timezone.utc).isoformat(),'historical_day17_gate':'BLOCKED; not rerun or overridden','historical_figure1_source_preflight':'FAIL for original 200 dpi export; preserved separately','not_established':['Exact uploaded submission PDF identity','Day 24 supporting-figure rendering code','Original annotation reliability and construct validity','Complete manuscript prose or external-study claims']})
        print(status+': '+str(out/'report.json'))
        if failure: print(failure)
    return 0 if status=='PASS' else 1

if __name__=='__main__':
    sys.exit(main())
