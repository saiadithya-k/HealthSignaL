import json
import os

CORE_DIR = os.path.join(os.path.dirname(__file__), "..", "app", "core")
DIS_PATH = os.path.join(CORE_DIR, "disease_reference.json")
SYM_PATH = os.path.join(CORE_DIR, "symptoms_master.json")
SYN_PATH = os.path.join(CORE_DIR, "syndrome_master.json")

with open(DIS_PATH, "r", encoding="utf-8") as f:
    dis_data = json.load(f)

with open(SYM_PATH, "r", encoding="utf-8") as f:
    sym_data = json.load(f)

with open(SYN_PATH, "r", encoding="utf-8") as f:
    syn_data = json.load(f)

symptoms_map = {s["symptom_id"]: s for s in sym_data.get("symptoms", [])}
syndromes_map = {s["code"]: s for s in syn_data.get("syndromes", [])}

print(f"Loaded {len(dis_data.get('conditions', []))} conditions")
print(f"Loaded {len(symptoms_map)} symptoms")
print(f"Loaded {len(syndromes_map)} syndromes")

for c in dis_data.get("conditions", [])[:15]:
    print(c.get("disease_id"), c.get("name"), "->", c.get("primary_syndrome"))
