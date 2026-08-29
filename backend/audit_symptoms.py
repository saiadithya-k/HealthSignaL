import json

# Symptoms
with open('app/core/symptoms_master.json') as f:
    d = json.load(f)

symptoms = d.get('symptoms', d) if isinstance(d, dict) else d
print(f'Total symptoms: {len(symptoms)}')
ids = [s['id'] for s in symptoms]
print(f'Unique IDs: {len(set(ids))}')
names = [s['name'] for s in symptoms]
print(f'Unique names: {len(set(names))}')
missing = [f'S{i:03d}' for i in range(1, 258) if f'S{i:03d}' not in ids]
print(f'Missing IDs from S001-S257: {missing[:10] if missing else "None"}')
dups = [id for id in ids if ids.count(id) > 1]
print(f'Duplicate IDs: {list(set(dups))}')
cats = set(s.get('category', '') for s in symptoms)
print(f'Categories: {cats}')
# Check severity levels
sev = set(s.get('severity', '') for s in symptoms)
print(f'Severity levels: {sev}')
print(f'First few IDs: {ids[:5]}')
print(f'ID range: {min(ids)} to {max(ids)}')
