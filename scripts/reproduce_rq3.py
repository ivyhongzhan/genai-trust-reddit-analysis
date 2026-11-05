#!/usr/bin/env python3
"""Regenerate locked RQ3 row projections and pairings from new Day 15/18/20 outputs."""
import argparse
import csv
from pathlib import Path


def read(path):
    with path.open(newline='', encoding='utf8') as f:
        return list(csv.DictReader(f))


def write(path, rows):
    with path.open('x', newline='', encoding='utf8') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def generate(day15, day18, day20, out):
    out.mkdir(parents=True, exist_ok=False)
    aggregate = read(day15 / 'rq1_counts_prevalence_source.csv')
    community = read(day18 / 'community_descriptive_summary.csv')
    pairs = []
    for archive in ['classification', 'dimensions']:
        pooled = [r for r in aggregate if r['archive'] == archive and r['scope'] == 'ALL']
        local = [r for r in community if r['archive'] == archive]
        write(out / ('aggregate_' + archive + '_profile.csv'), pooled)
        write(out / ('community_' + archive + '_profiles.csv'), local)
        temporal = read(day20 / (archive + '_temporal_summary.csv'))
        write(out / ('temporal_' + archive + '_profiles.csv'), temporal)
        index = {r['category']: r for r in pooled}
        paired = []
        for r in local:
            a = index[r['category']]
            paired.append(dict(archive=archive, category_type=r['category_type'], category=r['category'],
                community=r['community'], aggregate_scope='ALL', aggregate_count=a['count'],
                aggregate_denominator_type=a['denominator_type'], aggregate_denominator_n=a['denominator_n'],
                aggregate_within_archive_proportion=a['within_archive_proportion'], community_count=r['count'],
                community_denominator_type=r['denominator_type'], community_eligible_denominator_n=r['eligible_denominator_n'],
                community_proportion_fraction=r['proportion_fraction'], community_proportion=r['proportion'],
                community_missing_or_exception_n=r['missing_or_exception_n'], field=r['field']))
        write(out / (archive + '_community_heterogeneity_summary.csv'), paired)
        write(out / (archive + '_aggregate_vs_community_figure_source.csv'), paired)
        pairs.extend(paired)
    write(out / 'rq3_descriptive_table_source.csv', pairs)
    # Preserve the original table's literal presentation; every data cell comes from the new pairing.
    text = '# Table 3 — Archive-separated aggregate and community descriptive profiles\n\n'
    text += 'Frozen archive-specific values are displayed side by side. All counts, denominators, stored proportions, and exception counts are copied from the Day 23 PASS pairings; no comparison value is calculated.\n\n'
    for archive, title in [('classification', 'Released classification profile'), ('dimensions', 'Released dimension profile')]:
        text += '## ' + title + '\n\n'
        text += '| Category | Community | Aggregate count | Aggregate denominator | Aggregate stored proportion | Community count | Community denominator | Community stored fraction | Community stored proportion | Missing or exception count | Field |\n'
        text += '|---|---|---:|---|---:|---:|---|---|---:|---:|---|\n'
        for r in pairs:
            if r['archive'] != archive:
                continue
            values = [r['category'], r['community'], r['aggregate_count'], r['aggregate_denominator_type'] + ': ' + r['aggregate_denominator_n'], r['aggregate_within_archive_proportion'], r['community_count'], r['community_denominator_type'] + ': ' + r['community_eligible_denominator_n'], r['community_proportion_fraction'], r['community_proportion'], r['community_missing_or_exception_n'], r['field']]
            text += '| ' + ' | '.join(values) + ' |\n'
        text += '\n'
    (out / 'rq3_descriptive_table.md').write_text(text.rstrip() + '\n', encoding='utf8')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ['day15', 'day18', 'day20', 'output-dir']:
        p.add_argument('--' + name, type=Path, required=True)
    a = p.parse_args()
    generate(a.day15, a.day18, a.day20, a.output_dir)
