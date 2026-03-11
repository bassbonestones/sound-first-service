#!/usr/bin/env python3
"""Audit capabilities.json for missing music21_detection rules."""
import json

with open('app/resources/capabilities.json', 'r') as f:
    data = json.load(f)

# Group by domain
by_domain = {}
for cap in data['capabilities']:
    domain = cap['domain']
    if domain not in by_domain:
        by_domain[domain] = {'has_detection': [], 'no_detection': []}
    
    if 'music21_detection' in cap:
        by_domain[domain]['has_detection'].append(cap['name'])
    else:
        by_domain[domain]['no_detection'].append(cap['name'])

print('CAPABILITIES BY DOMAIN - Missing music21_detection:')
print('='*60)
for domain in sorted(by_domain.keys()):
    info = by_domain[domain]
    if info['no_detection']:
        print(f'\n{domain}:')
        has = info['has_detection']
        print(f'  Has detection ({len(has)}): {has[:3]}...' if len(has) > 3 else f'  Has detection ({len(has)}): {has}')
        print(f'  MISSING detection ({len(info["no_detection"])}):')
        for name in info['no_detection']:
            print(f'    - {name}')

# Summary
total = len(data['capabilities'])
with_det = sum(len(info['has_detection']) for info in by_domain.values())
print(f'\n\nSUMMARY: {with_det}/{total} capabilities have music21_detection rules')
print(f'Missing: {total - with_det} capabilities')
