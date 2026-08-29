import csv
import json
import os

print("=== DATA VOLUME AUDIT ===")
nodes = ['inst-a', 'inst-b', 'inst-c', 'inst-d']
total = 0
for node in nodes:
    path = f'../data/{node}/data.csv'
    with open(path) as f:
        rows = list(csv.DictReader(f))
    total += len(rows)
    cols = list(rows[0].keys()) if rows else []
    # Get date range
    dates = sorted(set(r.get('date','') for r in rows if r.get('date','')))
    print(f'{node}: {len(rows)} rows, {len(cols)} columns, date range: {dates[0] if dates else "?"} to {dates[-1] if dates else "?"}')
    
    # Check metadata
    meta_path = f'../data/{node}/metadata.json'
    if os.path.exists(meta_path):
        with open(meta_path) as f:
            meta = json.load(f)
        print(f'  metadata: {meta}')
    
    # Check for PII
    pii_fields = ['patient_id', 'name', 'phone', 'email', 'address', 'ssn', 'consent_token']
    found_pii = [f for f in pii_fields if f in cols]
    print(f'  PII fields found: {found_pii if found_pii else "NONE"}')
    print(f'  columns: {cols}')
    print()

print(f'TOTAL RECORDS: {total}')

print()
print('=== SOURCE DISTRIBUTION ===')
all_sources = {}
for node in nodes:
    path = f'../data/{node}/data.csv'
    with open(path) as f:
        rows = list(csv.DictReader(f))
    for row in rows:
        src = row.get('source','')
        all_sources[src] = all_sources.get(src, 0) + 1
print(f'Sources: {all_sources}')

print()
print('=== SYNDROME DISTRIBUTION ===')
all_syndromes = {}
for node in nodes:
    path = f'../data/{node}/data.csv'
    with open(path) as f:
        rows = list(csv.DictReader(f))
    for row in rows:
        syn = row.get('syndrome', row.get('syndrome_code',''))
        if syn:
            all_syndromes[syn] = all_syndromes.get(syn, 0) + 1
print(f'Syndromes ({len(all_syndromes)} unique):')
for k,v in sorted(all_syndromes.items(), key=lambda x: -x[1])[:20]:
    print(f'  {k}: {v}')
