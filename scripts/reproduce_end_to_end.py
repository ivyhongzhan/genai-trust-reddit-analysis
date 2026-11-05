#!/usr/bin/env python3
"""Local release-ZIP to paper-numerics rerun; no downloads, sampling, or LLM calls.

Raw/record-level intermediates remain in a new local output directory. Never
commit or redistribute that directory. Reference tables are comparison targets,
not inputs to the new counts. Historical PASS anchors do not assert a new gate.
"""
import argparse
import csv
import hashlib
import importlib.metadata
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import traceback
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from reproduce_frozen_inputs import compare_csv, sha256
from reproduce_rq3 import generate as rq3_generate, write as write_csv
from reproduce_posthoc_association import calculate

ROOT = Path(__file__).resolve().parents[1]
COMMUNITIES = ['ChatGPTCoding', 'webdev', 'programming', 'GitHub', 'compsci']


def dump(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n', encoding='utf8')


def read(path):
    with path.open(newline='', encoding='utf8') as f:
        return list(csv.DictReader(f))


def pdf_compare(actual, reference):
    import fitz
    import numpy as np
    a, b = fitz.open(actual), fitz.open(reference)
    results = []
    if len(a) != len(b):
        return {'render_equal': False, 'reason': 'page count differs'}
    for x, y in zip(a, b):
        px, py = x.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False), y.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
        equal_size = (px.width, px.height) == (py.width, py.height)
        diff = None
        if equal_size:
            xa = np.frombuffer(px.samples, dtype=np.uint8)
            ya = np.frombuffer(py.samples, dtype=np.uint8)
            diff = int(np.count_nonzero(xa != ya))
        results.append({'same_dimensions': equal_size, 'changed_channels_at_144dpi': diff,
            'text_equal': x.get_text() == y.get_text()})
    differences = []
    if a.xref_length() == b.xref_length():
        for i in range(1, a.xref_length()):
            normalize = lambda text: re.sub(r'/CreationDate \([^)]*\)', '/CreationDate (RUN_TIME)', text)
            if normalize(a.xref_object(i)) != normalize(b.xref_object(i)) or a.xref_stream(i) != b.xref_stream(i):
                differences.append(i)
    else:
        differences = ['xref_length']
    return {'decoded_pdf_objects_equal_except_creation_date': not differences, 'differing_object_ids': differences,
        'byte_equal': sha256(actual) == sha256(reference),
        'render_equal': all(r['same_dimensions'] and r['changed_channels_at_144dpi'] == 0 for r in results),
        'pages': results, 'computed_sha256': sha256(actual), 'reference_sha256': sha256(reference),
        'computed_metadata': a.metadata, 'reference_metadata': b.metadata}


def verify_manuscript(manuscript, out, day15, day18, day20):
    """Audit every literal result fraction and Table 1 row; keep locatable evidence."""
    pooled = read(day15 / 'rq1_counts_prevalence_source.csv')
    local = read(day18 / 'community_descriptive_summary.csv')
    temporal = read(day20 / 'temporal_visualization_source.csv')
    candidates = []
    for r in pooled:
        candidates.append((int(r['count']), int(r['denominator_n']),
            [r['archive'], r['scope'], r['category']], float(r['within_archive_proportion'])))
    for r in temporal:
        if int(r['outcome_available_n']):
            candidates.append((int(r['count']), int(r['outcome_available_n']),
                [r['archive'], r['community'], r['half_year_utc'], r['category']], float(r['proportion'])))
    claims = []
    for name in ['main.tex', 'content.tex']:
        for line_no, line in enumerate((manuscript / name).read_text().splitlines(), 1):
            for match in re.finditer(r'(?<![\w])([\d,]+)/([\d,]+)(?:\s+(?:records\s+)?\(([\d.]+)\\%\))?', line):
                n, d = [int(x.replace(',', '')) for x in match.group(1, 2)]
                matches = [key for x, y, key, p in candidates if (x, y) == (n, d)]
                percentage = match.group(3)
                ok = bool(matches) and (percentage is None or f'{100*n/d:.1f}' == percentage)
                claims.append({'file': name, 'line': line_no, 'literal': match.group(0),
                    'matching_computed_cells': matches, 'match': ok})
    table = (manuscript / 'tables/table1.tex').read_text()
    regenerated_lines = []
    for category in dict.fromkeys(r['category'] for r in local):
        cells = [next(r for r in local if r['category'] == category and r['community'] == c) for c in COMMUNITIES]
        if '\\shortstack' in table:
            values = [r'\shortstack[r]{' + f"{int(r['count']):,}/{int(r['eligible_denominator_n']):,}" + r'\\(' + f"{float(r['proportion'])*100:.1f}" + r'\%)}' for r in cells]
        else:
            values = [f"{int(r['count']):,}/{int(r['eligible_denominator_n']):,}" for r in cells]
        line = category + ' & ' + ' & '.join(values) + r' \\'
        regenerated_lines.append(line)
        claims.append({'file': 'tables/table1.tex', 'category': category, 'literal': line, 'match': line in table})
    # Retain captions/notes, replacing all data rows mechanically from new counts.
    generated_table = table
    for line in regenerated_lines:
        category = line.split(' & ')[0]
        generated_table = re.sub(r'^' + re.escape(category) + r' & .*$', lambda _: line, generated_table, flags=re.M)
    (out / 'table1.tex').write_text(generated_table)
    (out / 'table1_computed_rows.tex').write_text('\n'.join(regenerated_lines) + '\n')
    # Explicit context checks cover interpretation, temporal sparsity and every
    # reported post-hoc contrast; fraction matching alone cannot establish these.
    index = {(r['archive'], r['scope'], r['category']): int(r['count']) for r in pooled}
    order = {c: index['classification', c, 'Trust'] > index['classification', c, 'Neither'] for c in ['ALL'] + COMMUNITIES}
    expected_order = {'ALL': False, 'ChatGPTCoding': True, 'webdev': False, 'programming': True, 'GitHub': False, 'compsci': False}
    claims.append({'claim': 'Trust exceeds Neither only in ChatGPTCoding and programming', 'computed': order, 'match': order == expected_order})
    ledger = read(day20 / 'temporal_cell_status_ledger.csv')
    for archive, community, n in [('classification', 'compsci', 2), ('dimensions', 'programming', 14), ('dimensions', 'compsci', 0)]:
        r = next(r for r in ledger if (r['archive'], r['community'], r['half_year_utc']) == (archive, community, '2023-H1'))
        claims.append({'claim': [archive, community, '2023-H1', 'outcome_available_n'], 'expected': n,
            'actual': int(r['outcome_available_n']), 'match': int(r['outcome_available_n']) == n,
            'availability': r['availability_status'], 'sufficiency': r['sufficiency_status']})
    association = calculate(day18 / 'community_descriptive_summary.csv')
    content = (manuscript / 'content.tex').read_text()
    revised = '137.516' in content or 'V=0.073' in content
    tindex = {(r['archive'], r['community'], r['half_year_utc'], r['category']): r for r in temporal}
    windows = [('classification', 'Trust', ['2023-H1','2023-H2','2024-H1','2024-H2','2025-H1'], ('41.1','46.6')), ('dimensions', 'Competence', ['2023-H1','2023-H2','2024-H1'], ('74.0','78.1')), ('dimensions', 'Competence', ['2024-H2','2025-H1'], ('68.1','68.8'))]
    for archive, category, periods, expected in windows:
        values = [float(tindex[archive,'ChatGPTCoding',h,category]['proportion'])*100 for h in periods]
        got = (f'{min(values):.1f}', f'{max(values):.1f}')
        claims.append({'claim':['ChatGPTCoding temporal range',archive,category,periods], 'expected':expected,'computed':got,'match':got==expected})
    # Newly reported pooled composition weight is independently computed.
    total=sum(int(r['count']) for r in local if r['archive']=='classification')
    ctotal=sum(int(r['count']) for r in local if r['archive']=='classification' and r['community']=='ChatGPTCoding')
    claims.append({'claim':'ChatGPTCoding canonical-label weight 62.6%', 'computed':ctotal/total,'match':f'{100*ctotal/total:.1f}'=='62.6'})
    # Check every percentage occurrence in the manuscript, including rounded
    # endpoints whose first value precedes a range rather than a percent sign.
    known_percentages = {f'{100*x/d:.1f}' for x,d,key,prop in candidates}
    known_percentages.add(f'{100*ctotal/total:.1f}')
    for name in ['main.tex','content.tex']:
        for line_no,line in enumerate((manuscript/name).read_text().splitlines(),1):
            for m in re.finditer(r'([0-9]+\.[0-9]+)\\%',line):
                claims.append({'file':name,'line':line_no,'percentage_literal':m.group(1),'match':m.group(1) in known_percentages})
    if revised:
        for key, expected in [('cramers_v', '0.073'), ('chi_square_descriptive', '137.516')]:
            claims.append({'claim': key, 'expected': expected, 'computed': association[key], 'match': f'{association[key]:.3f}' == expected})
        for c, expected in [('ALL', '-1.7'), ('ChatGPTCoding', '+5.4'), ('programming', '+7.4'), ('webdev', '-18.1'), ('GitHub', '-12.2'), ('compsci', '-22.5')]:
            value = association['trust_minus_neither_percentage_points'][c]
            claims.append({'claim': ['Trust-minus-Neither percentage points', c], 'expected': expected,
                'computed': value, 'match': f'{value:+.1f}' == expected})
    dump(out / 'manuscript_claims.json', {'status': 'PASS' if all(r['match'] for r in claims) else 'FAIL',
        'scope': 'All literal n/N occurrences in main/content, 85 Table 1 cells, ordering, reported sparse cells and revised association/contrasts. Bibliography and external-source claims are not replicated.',
        'percentage_occurrences':sum('percentage_literal' in r for r in claims),
        'fraction_occurrences': sum('line' in r and 'literal' in r for r in claims), 'table_cells': len(regenerated_lines)*5,
        'revised_posthoc_present': revised, 'claims': claims, 'association': association})
    return all(r['match'] for r in claims)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--research-root', type=Path, required=True)
    p.add_argument('--manuscript-root', type=Path, required=True)
    p.add_argument('--figure-qa-scripts', type=Path, required=True)
    p.add_argument('--output-dir', type=Path, required=True)
    a = p.parse_args()
    research, manuscript, out = a.research_root.resolve(), a.manuscript_root.resolve(), a.output_dir.resolve()
    if out.exists():
        p.error('output directory exists; refusing overwrite')
    # Reject destinations under any authoritative source or frozen directory.
    for protected in [research, ROOT / 'results', ROOT / 'figures', ROOT / 'provenance', manuscript]:
        if out == protected or protected in out.parents:
            p.error('output must be outside authoritative input and reference directories')
    out.mkdir(parents=True)
    os.chmod(out, 0o700)
    (out / 'logs').mkdir()
    env = os.environ.copy()
    env.update(MPLBACKEND='Agg', PYTHONDONTWRITEBYTECODE='1', FIGURE_QA_SCRIPTS=str(a.figure_qa_scripts.resolve()))
    checks, commands, input_inventory = {}, [], {}
    def record(path):
        path = path.resolve()
        input_inventory[str(path)] = {'sha256': sha256(path), 'bytes': path.stat().st_size}
    def run(name, command, allow_failure=False):
        start = datetime.now(timezone.utc).isoformat()
        with (out / 'logs' / (name + '.log')).open('w') as f:
            result = subprocess.run([str(x) for x in command], cwd=ROOT, env=env, stdout=f, stderr=subprocess.STDOUT)
        commands.append({'stage': name, 'argv': [str(x) for x in command], 'started_utc': start, 'returncode': result.returncode})
        dump(out / 'commands.json', commands)
        if result.returncode and not allow_failure:
            raise RuntimeError(f'{name} failed with exit {result.returncode}; see logs/{name}.log')
        return result.returncode
    def script(name, *args):
        return [sys.executable, ROOT / 'scripts' / name, *args]
    def compare(name, computed, reference, keys):
        record(reference)
        r = compare_csv(computed, reference, keys)
        r.update(computed_sha256=sha256(computed), reference_sha256=sha256(reference), byte_equal=sha256(computed)==sha256(reference))
        checks[name] = r
        return r['match']
    failure = None
    try:
        run('package_verification', script('verify_package.py'))
        freeze_path = ROOT / 'provenance/data_freeze_version_record.json'
        freeze = json.loads(freeze_path.read_text())
        frozen = research / 'outputs/day14_freeze/20260925_day14_archive_separated_freeze_v1'
        record(freeze_path)
        for name in ['classification_analytic_frozen.jsonl', 'dimensions_analytic_frozen.jsonl']:
            record(frozen / name)
            if sha256(frozen / name) != freeze['artifacts'][name]:
                raise ValueError('existing Day 14 input hash mismatch: ' + name)
        # Execute the remote branch's original program on verified original inputs first.
        run('existing_record_level_program', script('reproduce_frozen_inputs.py', '--classification', frozen/'classification_analytic_frozen.jsonl', '--dimensions', frozen/'dimensions_analytic_frozen.jsonl', '--output-dir', out/'verified_frozen_run'))
        checks['existing_record_level_program'] = {'match': json.loads((out/'verified_frozen_run/reproduction_report.json').read_text())['status']=='PASS'}
        download_manifest = research / 'archive/legacy_coding_assistant_design/developer-ai-trust/outputs/schema_audit/download_20260908T115000_014169Z/download_manifest.json'
        record(download_manifest)
        release = json.loads(download_manifest.read_text())
        raw = out / 'raw'
        raw.mkdir()
        raw_paths = {}
        for key, zipname, membername in [('classification_raw','Trust_Classification_json.zip','Trust_Classification_json/data_task1.json'), ('dimensions_raw','Dimensions_of_Trust_json.zip','Dimensions_of_Trust_json/data_task2.json')]:
            path = research / 'developer-ai-trust/data/raw' / zipname
            record(path)
            recorded = next(r for r in release['files'] if r['name']==zipname)
            if sha256(path) != recorded['sha256']:
                raise ValueError('release ZIP hash mismatch: ' + zipname)
            dest = raw / Path(membername).name
            with zipfile.ZipFile(path) as z, z.open(membername) as source, dest.open('xb') as target:
                shutil.copyfileobj(source, target)
            n = len(json.loads(dest.read_text()))
            want = freeze['inputs'][key]
            checks[key] = {'match': sha256(dest)==want['sha256'] and n==want['source_rows'], 'rows': n,
                'sha256': sha256(dest), 'expected_sha256': want['sha256'], 'archive_sha256': recorded['sha256'], 'member': membername}
            if not checks[key]['match']:
                raise ValueError('extracted raw input mismatch: ' + key)
            raw_paths[key] = dest
        classraw, dimraw = raw_paths['classification_raw'], raw_paths['dimensions_raw']
        run('day11', script('run_day11_encoding_qc.py', '--classification', classraw, '--dimensions', dimraw, '--output-dir', out/'day11'))
        encoding = out/'day11/primary_dimension_encoding.jsonl'
        checks['day11_encoding'] = {'match': sha256(encoding)==freeze['inputs']['day11_primary_encoding']['sha256'], 'rows': sum(1 for _ in encoding.open()), 'sha256': sha256(encoding)}
        if not checks['day11_encoding']['match']:
            raise ValueError('Day 11 encoding hash mismatch')
        rebuilt = out/'rebuilt_day14'
        run('day14', script('run_day14_freeze.py', '--classification', classraw, '--dimensions', dimraw, '--day11-encoding', encoding, '--output-dir', rebuilt))
        for name, want in freeze['artifacts'].items():
            record(frozen/name)
            checks['day14/'+name] = {'match': sha256(rebuilt/name)==want, 'sha256':sha256(rebuilt/name), 'expected_sha256': want}
        if not all(v['match'] for k,v in checks.items() if k.startswith('day14/')):
            raise ValueError('rebuilt Day 14 differs from freeze')
        for stage in ['day15', 'day18']:
            args = ['--classification',rebuilt/'classification_analytic_frozen.jsonl','--dimensions',rebuilt/'dimensions_analytic_frozen.jsonl','--freeze-record',freeze_path,'--output-dir',out/stage]
            if stage=='day18':
                args.extend(['--rq1-freeze-record',ROOT/'provenance/rq1_freeze_record.json'])
            run(stage, script('run_day15_rq1_counts.py' if stage=='day15' else 'run_day18_rq2_community.py', *args))
        run('day16', script('run_day16_rq1_display.py', '--day15-source',out/'day15/rq1_counts_prevalence_source.csv','--day15-manifest',out/'day15/run_manifest.json','--figure-skill-scripts',a.figure_qa_scripts,'--output-dir',out/'day16'))
        run('day17', script('run_day17_sensitivities.py','--classification-frozen',rebuilt/'classification_analytic_frozen.jsonl','--dimensions-raw',dimraw,'--day14-record',freeze_path,'--day11-manifest',out/'day11/run_manifest.json','--day11-field-qc',out/'day11/dimension_field_qc.csv','--day15-source',out/'day15/rq1_counts_prevalence_source.csv','--output-dir',out/'day17'))
        run('day20', script('run_day20_temporal.py','--research-root',research,'--freeze-dir',rebuilt,'--day19-dir',research/'outputs/day19_rq2_community/20260926_day19_rq2_community_v1','--output-dir',out/'day20'))
        rq3_generate(out/'day15', out/'day18', out/'day20', out/'rq3')
        comparisons = [
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
        for computed, reference, keys in comparisons:
            compare(computed, out/computed, ROOT/reference, keys)
        for stage, name, keys in [
            ('day17_rq1/20260926_day17_rq1_v1','denominator_sensitivity.csv',('archive','scope','field','category')),
        ]:
            # The historical sensitivity schema contains extra grouping fields;
            # byte identity is the stronger complete-artifact comparison.
            reference=research/'outputs'/stage/name
            record(reference)
            checks['day17/'+name]={'match':sha256(out/'day17'/name)==sha256(reference), 'sha256':sha256(out/'day17'/name), 'reference_sha256':sha256(reference)}
        for stage, pattern in [('day22_profiles/20260927_day22_profiles_v1','*profile*.csv'),('day23_heterogeneity/20260927_day23_heterogeneity_v1','*.csv'),('day24_rq3_display/20260927_day24_rq3_display_v1','*.csv')]:
            for reference in sorted((research/'outputs'/stage).glob(pattern)):
                rows=read(reference)
                keys=tuple(k for k in ['archive','scope','community','half_year_utc','category'] if k in rows[0])
                compare('rq3/'+reference.name, out/'rq3'/reference.name, reference, keys)
        run('manuscript_temporal', script('render_manuscript_temporal.py','--day20-dir',out/'day20','--output-dir',out/'manuscript_temporal'))
        # Regenerate the public exception ledger from new archive denominators;
        # preserve redaction instead of exporting a released record identifier.
        exception_rows=[]
        for r in read(out/'day18/community_denominator_ledger.csv'):
            dimensions=r['archive']=='dimensions'
            missing=int(r['missing_or_exception_n'])>0
            exception_rows.append({**r,'exception_ids':'[REDACTED_RECORD_ID]' if missing else '',
                'exception_status':'missing' if missing else 'none',
                'exception_treatment':('all primary-field rows parser-clean; no unknown output recoded as absence' if dimensions else 'retained in source accounting; excluded from category-share denominator; not recoded' if missing else 'no exception'),
                'multi_label':'true' if dimensions else 'false'})
        with (out/'day18/denominator_exception_ledger.csv').open('x',newline='',encoding='utf8') as handle:
            writer=csv.DictWriter(handle,fieldnames=list(exception_rows[0]),lineterminator='\n')
            writer.writeheader()
            writer.writerows(exception_rows)
        compare('day19/public_denominator_exception_ledger',out/'day18/denominator_exception_ledger.csv',ROOT/'results/denominator_exception_ledger.csv',('archive','community'))
        # Compare the historical private table without embedding its identifier in source.
        missing = [json.loads(line)['id'] for line in (rebuilt/'classification_analytic_frozen.jsonl').read_text().splitlines() if json.loads(line)['label_status'] == 'missing']
        if len(missing) != 1:
            raise ValueError('expected exactly one missing classification record')
        public_table = (out/'day16/rq1_table.md').read_text()
        marker = 'retains one missing label.'
        if public_table.count(marker) != 1:
            raise ValueError('unexpected public table note')
        private_table = public_table.replace(marker, 'retains one missing label (`' + missing[0] + '`).')
        original = research/'outputs/day16_rq1_display/20260926_day16_rq1_display_v2/rq1_table.md'
        record(original)
        checks['day16/original_rq1_table'] = {'match': hashlib.sha256(private_table.encode()).hexdigest() == sha256(original)}
        shutil.copy2(out/'day16/rq1_table.md', out/'day16/public_rq1_table.md')
        for derived,reference in [('day16/public_rq1_table.md','results/rq1_table.md'),('rq3/rq3_descriptive_table.md','results/rq3_descriptive_table.md')]:
            record(ROOT/reference)
            checks[derived]={'match':sha256(out/derived)==sha256(ROOT/reference),'sha256':sha256(out/derived),'reference_sha256':sha256(ROOT/reference)}
        (out/'paper').mkdir()
        checks['manuscript_claims']={'match':verify_manuscript(manuscript,out/'paper',out/'day15',out/'day18',out/'day20')}
        for name in ['main.tex','content.tex','tables/table1.tex','figures/figure1.tex','figures/figure2.tex','figures/figure3.tex']:
            record(manuscript/name)
        figure_checks={}
        for generated, packaged, papername in [('day16/rq1_figure.pdf','rq1_figure.pdf','figure1.pdf'),('day20/classification_temporal_visualization.pdf','classification_temporal_visualization.pdf','figure2.pdf'),('day20/dimensions_temporal_visualization.pdf','dimensions_temporal_visualization.pdf','figure3.pdf')]:
            computed=out/generated
            paper_computed = computed if papername=='figure1.pdf' else out/'manuscript_temporal'/papername
            record(ROOT/'figures'/packaged)
            record(manuscript/'figures'/papername)
            figure_checks[papername]={'frozen_reference':pdf_compare(computed,ROOT/'figures'/packaged),'manuscript_reference':pdf_compare(paper_computed,manuscript/'figures'/papername)}
            shutil.copy2(paper_computed,out/'paper'/papername)
            for tool, suffix, options in [('validate_figure.py','source_preflight',['--json']),('audit_pdf_text.py','pdf_text',['--min-pt','5','--json']),('audit_figure_collisions.py','collisions',['--json-out',out/'paper'/(papername+'.collision.json')])]:
                target=ROOT/'scripts'/('historical_figure_export.py' if papername=='figure1.pdf' else 'render_manuscript_temporal.py') if tool=='validate_figure.py' else paper_computed
                rc = run(papername+'_'+suffix,[sys.executable,a.figure_qa_scripts/tool,target,*options],allow_failure=True)
                checks['figure_qa/'+papername+'/'+suffix] = {'match':rc==0,'returncode':rc,'log':'logs/'+papername+'_'+suffix+'.log'}
        dump(out/'figure_comparisons.json',figure_checks)
        checks['paper_figures_render_equal']={'match':all(r['manuscript_reference']['render_equal'] for r in figure_checks.values())}
        # Check all authority anchors and source scripts again after computation.
        for path, before in input_inventory.items():
            if sha256(Path(path))!=before['sha256']:
                checks['immutable_inputs']={'match':False,'path':path}
        checks.setdefault('immutable_inputs',{'match':True})
        # Preserve full source and external QA dependency snapshots locally, so
        # environment hashes identify available executable code, not just names.
        shutil.copytree(ROOT/'scripts',out/'executed_source',ignore=shutil.ignore_patterns('__pycache__'))
        shutil.copytree(a.figure_qa_scripts,out/'qa_dependency_source',ignore=shutil.ignore_patterns('__pycache__'))
    except Exception:
        failure=traceback.format_exc()
        (out/'failure.log').write_text(failure)
    finally:
        dump(out/'input_inventory.json',input_inventory)
        dump(out/'environment.json',{'python':sys.version,'executable':sys.executable,'platform':platform.platform(),
            'packages':{d.metadata['Name']:d.version for d in importlib.metadata.distributions()},
            'MPLBACKEND':'Agg','figure_qa_scripts':str(a.figure_qa_scripts),
            'git_head':subprocess.run(['git','rev-parse','HEAD'],cwd=ROOT,text=True,capture_output=True).stdout.strip(),
            'scripts':{str(x.relative_to(ROOT)):sha256(x) for x in (ROOT/'scripts').glob('*.py')},
            'git_diff':subprocess.run(['git','diff','--stat'],cwd=ROOT,text=True,capture_output=True).stdout,
            'git_status':subprocess.run(['git','status','--short'],cwd=ROOT,text=True,capture_output=True).stdout,
            'qa_scripts':{x.name:sha256(x) for x in a.figure_qa_scripts.glob('*.py')}})
        dump(out/'output_inventory.json',{str(x.relative_to(out)):{'sha256':sha256(x),'bytes':x.stat().st_size} for x in sorted(out.rglob('*')) if x.is_file() and x.name not in ['output_inventory.json','report.json']})
        numeric_checks={k:v for k,v in checks.items() if not k.startswith('figure_qa/') and k!='paper_figures_render_equal'}
        numerical_status='PASS' if not failure and all(x.get('match',False) for x in numeric_checks.values()) else 'FAIL'
        status='FAIL' if failure or not all(x.get('match',False) for x in checks.values()) else 'PASS'
        report={'status':status,'numerical_status':numerical_status,'figure_render_status':'PASS' if checks.get('paper_figures_render_equal',{}).get('match') else 'FAIL_OR_NOT_RUN','scope':'Local release ZIPs through rebuilt Day 11/14 inputs, RQ1, community/temporal RQ2, RQ3 numerical sources, manuscript Table 1, main Figures 1–3, and revised descriptive association.',
            'not_established':['New download from public host (cached release ZIP hashes verified instead)','Exact uploaded submission PDF identity','Original Day 24 supporting-figure rendering code (not used by main manuscript)','Historical Day 17 final gate (script hardcodes absence of Day 16; not silently overridden)','External-study claims, construct validity, unavailable mixed-field estimand or annotation reliability'],
            'checks':checks,'failure':failure,'executed_utc':datetime.now(timezone.utc).isoformat()}
        dump(out/'report.json',report)
        print(status+': '+str(out/'report.json'))
        if failure: print(failure)
    return 0 if status=='PASS' else 1


if __name__=='__main__':
    sys.exit(main())
