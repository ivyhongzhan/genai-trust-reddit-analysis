#!/usr/bin/env python3
"""Verify package integrity and frozen aggregate facts without re-running analyses."""
from __future__ import annotations
import csv, hashlib, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = {
    "results/rq1_counts_prevalence_source.csv": "3d9f410c10ecc4fe401fb2ca2bfae9d35f6280aeb07ab90d1a869398976fd5ff",
    "results/rq1_denominator_ledger.csv": "8d32cc46f805ee9f83e716e0d9dc78e050c586130f6b4c42c5a020a5d63136e4",
    "results/rq1_table_source.csv": "cdfedf14d94bcecc453bdb447bcac5278bd4d03c1d26625b23428b07ec92c260",
    "results/final_community_table_source.csv": "7df9dce6f053f510d32f94e0f102b887cc4c2b2c9a9d666cd53b26439e9c2302",
    "results/classification_temporal_summary.csv": "7ca7b80ed49959422c54619de5261256d5855207ab69537d4b41ceb3c1a7e15b",
    "results/dimensions_temporal_summary.csv": "35bcc654738cf27ff9da99d594efbc0ada119804b255e6f3f631a2da2514f1fa",
    "results/temporal_visualization_source.csv": "4e195013b692a9c9f45d6cd57b9a624bd6b4ceadc58174b72dfbb909fd879e6d",
    "results/temporal_cell_status_ledger.csv": "421355a7c4ec04c8092fe732d8c5fb9cc720f93fea462012dd4d526537b9914b",
    "results/rq3_descriptive_table_source.csv": "7094dfa88567c659dd91d1915c8213df57926db8ca3432d2e8cc86a99373eca5",
    "figures/rq1_figure.pdf": "51bf8d940db4cbf4adaaca5102c9bc94e8a7418c272f4b9d084d8cf43a37c7f3",
    "figures/classification_temporal_visualization.pdf": "e258e8cdb8b730ca5978c75f8e40c09283f740bbe6b13d8fac64534dcc3cb4db",
    "figures/dimensions_temporal_visualization.pdf": "c9b2ffde190cb7dbb69e81ca152f87457f3540d088b753a3d3aa2b81d4cb3a29",
}

def sha(path: Path) -> str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''): h.update(block)
    return h.hexdigest()

def read_rows(path: Path):
    with path.open(newline='',encoding='utf-8') as f: return list(csv.DictReader(f))

def verify() -> list[str]:
    errors=[]
    for rel,want in EXPECTED.items():
        p=ROOT/rel
        if not p.is_file(): errors.append(f"missing {rel}")
        elif sha(p)!=want: errors.append(f"hash mismatch {rel}")
    rows=read_rows(ROOT/'results/rq1_counts_prevalence_source.csv')
    by={(r['archive'],r['scope'],r['category']):r for r in rows}
    checks=[
      (len(rows)==102,'RQ1 source row count'),
      (by['classification','ALL','Trust']['count']=='3408','classification Trust numerator'),
      (by['classification','ALL','Trust']['denominator_n']=='8519','classification label denominator'),
      (by['classification','ALL','Neither']['count']=='3555','classification Neither numerator'),
      (by['dimensions','ALL','Competence']['count']=='3506','dimensions Competence numerator'),
      (by['dimensions','ALL','Competence']['denominator_n']=='4964','dimensions source denominator'),
      (by['classification','ChatGPTCoding','Trust']['within_archive_proportion'].startswith('0.4313'),'ChatGPTCoding Trust share'),
      (by['classification','programming','Trust']['within_archive_proportion'].startswith('0.4619'),'programming Trust share'),
    ]
    errors.extend(f"failed {label}" for ok,label in checks if not ok)
    temporal=read_rows(ROOT/'results/temporal_cell_status_ledger.csv')
    periods={r.get('half_year_utc') or r.get('half_year') for r in temporal}
    if '2022-H2' not in periods: errors.append('temporal context 2022-H2 missing')
    if not {'2023-H1','2023-H2','2024-H1','2024-H2','2025-H1'} <= periods: errors.append('primary temporal window incomplete')
    source=json.loads((ROOT/'provenance/source_chain.json').read_text())
    if 'complete raw-data-to-paper rerun was not established' not in (ROOT/'README.md').read_text(): errors.append('README omits rerun boundary')
    if source['submission_identity']['status'].startswith('Exact uploaded PDF not established') is False: errors.append('submission uncertainty missing')
    return errors

if __name__=='__main__':
    problems=verify()
    if problems:
        print('FAIL')
        print('\n'.join(f'- {x}' for x in problems))
        raise SystemExit(1)
    print(f'PASS: {len(EXPECTED)} frozen-file hashes and scientific checks verified; no raw analysis executed.')
