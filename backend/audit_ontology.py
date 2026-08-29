import json

# Symptoms
with open('app/core/symptoms_master.json') as f:
    d = json.load(f)
symptoms = d.get('symptoms', [])
sym_ids = set(s['symptom_id'] for s in symptoms)

# Syndrome master - get all syndrome codes
with open('app/core/syndrome_master.json') as f:
    sd = json.load(f)
syndromes = sd if isinstance(sd, list) else sd.get('syndromes', [])
# Syndromes have both numeric IDs and string codes
syn_numeric_ids = set(s.get('syndrome_id', '') for s in syndromes)
syn_names_set = set(s.get('name','') for s in syndromes)
# Get the syndrome "code" field (slug used in disease_reference.json)
syn_codes = set()
for s in syndromes:
    code = s.get('code', s.get('syndrome_code', ''))
    if code:
        syn_codes.add(code)
print(f'Syndrome numeric IDs: {len(syn_numeric_ids)}')
print(f'Syndrome codes available: {sorted(syn_codes)}')

print()
print('=== DISEASE REFERENCE ===')
with open('app/core/disease_reference.json') as f:
    dr = json.load(f)

# Structure
print(f'Keys at top level: {list(dr.keys()) if isinstance(dr, dict) else "list"}')
conditions = dr.get('conditions', [])
print(f'Total conditions: {len(conditions)}')
con_ids = [c.get('condition_id','') for c in conditions]
print(f'Unique condition IDs: {len(set(con_ids))}')
missing = [f'C{i:03d}' for i in range(1,106) if f'C{i:03d}' not in con_ids]
print(f'Missing C001-C105: {missing if missing else "None"}')
dups = [id for id in con_ids if con_ids.count(id)>1]
print(f'Duplicate IDs: {list(set(dups))}')

# Check dangling symptom references
dangling_syms = set()
for c in conditions:
    for sid in c.get('symptom_ids', []):
        if sid not in sym_ids:
            dangling_syms.add(sid)
print(f'Dangling symptom refs: {sorted(dangling_syms)[:20]}')

# Check dangling syndrome references - note disease uses string names not SYN001 IDs
dangling_syns = set()
for c in conditions:
    for syn_id in c.get('syndrome_ids', []):
        # These are string codes like 'upper_respiratory_infection'
        if syn_id not in syn_codes:
            dangling_syns.add(syn_id)
print(f'Syndrome refs in diseases (sample): {c.get("syndrome_ids",[])}')
print(f'Dangling syndrome refs: {sorted(dangling_syns)[:20]}')

# Check categories
cats = set(c.get('category','') for c in conditions)
print(f'Disease categories: {sorted(cats)}')
