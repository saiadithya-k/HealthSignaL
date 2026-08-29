import json
import os

CORE_DIR = os.path.join(os.path.dirname(__file__), "..", "app", "core")
DIS_PATH = os.path.join(CORE_DIR, "disease_reference.json")
SYM_PATH = os.path.join(CORE_DIR, "symptoms_master.json")
SYN_PATH = os.path.join(CORE_DIR, "syndrome_master.json")

def main():
    with open(DIS_PATH, "r", encoding="utf-8") as f:
        dis_data = json.load(f)

    with open(SYM_PATH, "r", encoding="utf-8") as f:
        sym_data = json.load(f)

    with open(SYN_PATH, "r", encoding="utf-8") as f:
        syn_data = json.load(f)

    valid_sym_ids = set(s["symptom_id"] for s in sym_data.get("symptoms", []))
    valid_syn_codes = set(s["code"] for s in syn_data.get("syndromes", []))

    raw_conditions = dis_data.get("conditions", [])
    print(f"Auditing and enriching {len(raw_conditions)} conditions...")

    enriched_conditions = []

    for idx, c in enumerate(raw_conditions, 1):
        # 1. Condition ID (Standardize to C001-C105, keep disease_id aligned)
        cond_id = f"C{idx:03d}"
        old_id = c.get("disease_id", cond_id)
        name = c.get("name") or c.get("condition_name")
        category = c.get("category", "General Clinical")

        # 2. Symptoms
        sym_ids = c.get("symptom_ids") or c.get("key_symptoms") or []
        # Verify symptoms
        validated_sym_ids = []
        for s in sym_ids:
            if s in valid_sym_ids:
                validated_sym_ids.append(s)
            else:
                print(f"Warning: Unknown symptom ID {s} in {name}")

        # Ensure at least 2-4 key symptoms
        if not validated_sym_ids:
            validated_sym_ids = ["S001", "S006"]

        # 3. Syndromes
        prim_syn = c.get("primary_syndrome", "acute_febrile_illness")
        sec_syns = c.get("secondary_syndromes", [])
        syn_ids = list(set([prim_syn] + sec_syns))

        # 4. Epidemiological attributes based on category and syndromes
        cat_lower = category.lower()
        name_lower = name.lower()
        prim_syn_lower = prim_syn.lower()

        # Severity
        if any(w in name_lower or w in prim_syn_lower for w in ["shock", "hemorrhagic", "encephalitis", "rabies", "meningitis", "anthrax", "botulism", "sepsis", "failure", "infarction", "poisoning", "severe"]):
            severity = "severe"
        elif any(w in name_lower or w in prim_syn_lower for w in ["pneumonia", "typhoid", "dengue", "cholera", "leptospiral", "malaria", "hepatitis", "croup"]):
            severity = "moderate_to_severe"
        elif any(w in name_lower or w in prim_syn_lower for w in ["cold", "rhinitis", "mild", "folliculitis", "pharyngitis", "otitis", "sinusitis"]):
            severity = "mild"
        else:
            severity = "mild_to_moderate"

        # Seasonality
        if any(w in cat_lower or w in name_lower for w in ["influenza", "cold", "rsv", "croup", "pneumonia", "winter"]):
            seasonality = "seasonal_winter"
        elif any(w in cat_lower or w in name_lower for w in ["vector", "dengue", "chikungunya", "malaria", "zika", "leptospirosis", "monsoon"]):
            seasonality = "seasonal_monsoon"
        elif any(w in cat_lower or w in name_lower for w in ["allergic", "pollinosis", "rhinitis"]):
            seasonality = "seasonal_spring_autumn"
        elif any(w in cat_lower or w in name_lower for w in ["heat", "sunstroke", "food poisoning"]):
            seasonality = "seasonal_summer"
        else:
            seasonality = "year_round"

        # Transmission Pattern
        if any(w in cat_lower or w in name_lower for w in ["vector", "dengue", "malaria", "chikungunya", "zika", "filariasis", "west nile", "japanese encephalitis"]):
            transmission = "vector_borne"
        elif any(w in cat_lower or w in name_lower for w in ["airborne", "respiratory", "influenza", "covid", "tuberculosis", "measles", "droplet"]):
            transmission = "respiratory_droplet"
        elif any(w in cat_lower or w in name_lower for w in ["waterborne", "cholera", "enteric", "rotavirus", "norovirus", "typhoid", "dysentery", "fecal"]):
            transmission = "fecal_oral_waterborne"
        elif any(w in cat_lower or w in name_lower for w in ["zoonotic", "rabies", "anthrax", "brucellosis", "leptospira"]):
            transmission = "zoonotic_direct_contact"
        elif any(w in cat_lower or w in name_lower for w in ["foodborne", "botulism", "toxin", "staphylococcal enterotoxin"]):
            transmission = "foodborne_ingestion"
        elif any(w in cat_lower or w in name_lower for w in ["exanthematous", "contact", "varicella", "mpox", "scabies"]):
            transmission = "direct_contact"
        else:
            transmission = "non_communicable_environmental"

        # Typical Duration
        if any(w in name_lower for w in ["tuberculosis", "chronic", "hiv", "filariasis", "arthritis"]):
            duration = "14-90+"
        elif any(w in name_lower for w in ["norovirus", "food poisoning", "bacillus cereus", "cholera"]):
            duration = "1-3"
        elif any(w in name_lower for w in ["cold", "rhinitis", "croup"]):
            duration = "3-7"
        elif any(w in name_lower for w in ["dengue", "chikungunya", "typhoid", "pneumonia", "measles"]):
            duration = "7-14"
        else:
            duration = "5-10"

        # Outbreak Relevance
        if any(w in name_lower for w in ["cholera", "covid", "influenza", "dengue", "measles", "ebola", "yellow fever", "nipah", "plague", "meningitis", "sars"]):
            outbreak_relevance = "critical"
        elif any(w in cat_lower for w in ["respiratory", "enteric", "vector-borne", "exanthematous", "zoonotic"]):
            outbreak_relevance = "high"
        else:
            outbreak_relevance = "moderate"

        # Associated Signal Sources
        sources = ["community", "doctor", "clinic"]
        if any(w in transmission for w in ["respiratory", "airborne", "droplet"]):
            sources.extend(["pharmacy", "testing", "absenteeism", "emergency", "wastewater"])
        elif any(w in transmission for w in ["fecal", "waterborne"]):
            sources.extend(["pharmacy", "testing", "wastewater", "absenteeism"])
        elif "vector" in transmission:
            sources.extend(["pharmacy", "testing", "emergency"])
        else:
            sources.extend(["pharmacy", "testing"])
        sources = sorted(list(set(sources)))

        enriched_record = {
            "condition_id": cond_id,
            "disease_id": cond_id, # Alias for backward compatibility
            "condition_name": name,
            "name": name,          # Alias for backward compatibility
            "category": category,
            "symptom_ids": validated_sym_ids,
            "key_symptoms": validated_sym_ids, # Alias
            "syndrome_ids": syn_ids,
            "primary_syndrome": prim_syn,
            "secondary_syndromes": sec_syns,
            "typical_severity": severity,
            "seasonality": seasonality,
            "transmission_pattern": transmission,
            "typical_duration_days": duration,
            "outbreak_relevance": outbreak_relevance,
            "associated_signal_sources": sources
        }

        enriched_conditions.append(enriched_record)

    # Save back to disease_reference.json
    out_data = {
        "version": "2.1.0",
        "total_conditions": len(enriched_conditions),
        "description": "HealthSignal Standardized 100+ Reference Disease/Condition Dataset for Synthetic Scenario & Multi-Symptom Pattern Modeling (Non-Diagnostic Reference Only)",
        "conditions": enriched_conditions
    }

    with open(DIS_PATH, "w", encoding="utf-8") as f:
        json.dump(out_data, f, indent=2)

    print(f"Successfully enriched all {len(enriched_conditions)} conditions in {DIS_PATH}!")

if __name__ == "__main__":
    main()
