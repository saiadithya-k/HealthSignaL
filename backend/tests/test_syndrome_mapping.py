import pytest
from app.core.syndrome_mapping import syndrome_service

def test_symptom_master_list_257():
    symptoms = syndrome_service.symptoms
    assert len(symptoms) == 257, f"Expected exactly 257 symptoms, got {len(symptoms)}"
    
    # 1. Unique IDs S001–S257
    ids = [s["symptom_id"] for s in symptoms]
    assert len(ids) == 257, "IDs count mismatch"
    assert len(set(ids)) == 257, "Duplicate symptom IDs detected!"
    expected_ids = [f"S{i:03d}" for i in range(1, 258)]
    assert ids == expected_ids, "Symptom IDs must be exactly sequential S001–S257"

    # 2. No duplicate symptom names
    names = [s["name"].strip().lower() for s in symptoms]
    assert len(set(names)) == 257, "Duplicate symptom names detected!"

    # 3. Every symptom has a clinical category
    for s in symptoms:
        assert s.get("category"), f"Symptom {s['symptom_id']} is missing clinical category"
        assert len(s["category"].strip()) > 0

    # 4. Every symptom has syndrome mapping
    for s in symptoms:
        assert s.get("associated_syndromes"), f"Symptom {s['symptom_id']} is missing associated_syndromes"
        assert len(s["associated_syndromes"]) >= 1, f"Symptom {s['symptom_id']} has empty syndrome mapping"

    # 5. Every symptom has severity information
    for s in symptoms:
        assert s.get("severities"), f"Symptom {s['symptom_id']} is missing severities"
        assert isinstance(s["severities"], list) and len(s["severities"]) >= 1

    # 6. Aliases are included
    for s in symptoms:
        assert "aliases" in s, f"Symptom {s['symptom_id']} is missing aliases key"
        assert isinstance(s["aliases"], list) and len(s["aliases"]) >= 1, f"Symptom {s['symptom_id']} has no aliases"

def test_alias_based_mapping():
    # Test symptom mapping using aliases
    mapped_pyrexia = syndrome_service.map_symptoms_to_syndromes(["pyrexia"])
    assert "acute_febrile_illness" in mapped_pyrexia

    mapped_sob = syndrome_service.map_symptoms_to_syndromes(["breathlessness", "hacking"])
    assert "severe_acute_respiratory_infection" in mapped_sob or "lower_respiratory_illness" in mapped_sob

    mapped_emesis = syndrome_service.map_symptoms_to_syndromes(["queasiness", "loose motions"])
    assert "gastroenteritis_emetic" in mapped_emesis or "acute_watery_diarrhea" in mapped_emesis

def test_syndrome_master_45_categories():
    syndromes = syndrome_service.syndromes
    assert len(syndromes) == 45, f"Expected exactly 45 syndromes, got {len(syndromes)}"
    codes = [s["code"] for s in syndromes]
    assert "acute_febrile_illness" in codes
    assert "influenza_like_illness" in codes
    assert "acute_watery_diarrhea" in codes
    assert "acute_encephalitic" in codes
    assert "febrile_arthritic" in codes
    assert "viral_hemorrhagic_fever" in codes

def test_disease_reference_catalog_100_plus():
    diseases = syndrome_service.diseases
    assert len(diseases) >= 100, f"Expected 100+ disease reference profiles, got {len(diseases)}"
    
    valid_sym_ids = set(s["symptom_id"] for s in syndrome_service.symptoms)
    valid_syn_codes = set(s["code"] for s in syndrome_service.syndromes)

    c_ids = [d.get("condition_id") or d.get("disease_id") for d in diseases]
    assert len(c_ids) == len(set(c_ids)), "Duplicate condition IDs detected!"

    c_names = [d.get("condition_name") or d.get("name") for d in diseases]
    assert len(c_names) == len(set(c_names)), "Duplicate condition names detected!"

    for d in diseases:
        # Schema checks
        assert d.get("condition_id"), f"Condition missing condition_id: {d}"
        assert d.get("condition_name"), f"Condition missing condition_name: {d}"
        assert d.get("typical_severity"), f"Condition missing typical_severity: {d}"
        assert d.get("seasonality"), f"Condition missing seasonality: {d}"
        assert d.get("transmission_pattern"), f"Condition missing transmission_pattern: {d}"
        assert d.get("typical_duration_days"), f"Condition missing typical_duration_days: {d}"
        assert d.get("outbreak_relevance"), f"Condition missing outbreak_relevance: {d}"
        assert isinstance(d.get("associated_signal_sources"), list) and len(d["associated_signal_sources"]) > 0

        # Linkage checks: Symptoms
        sym_ids = d.get("symptom_ids") or d.get("key_symptoms") or []
        assert len(sym_ids) >= 1, f"Condition {d['condition_id']} has no symptom_ids"
        for sid in sym_ids:
            assert sid in valid_sym_ids, f"Condition {d['condition_id']} references invalid symptom ID: {sid}"

        # Linkage checks: Syndromes
        syn_ids = d.get("syndrome_ids") or [d.get("primary_syndrome")]
        assert len(syn_ids) >= 1, f"Condition {d['condition_id']} has no syndrome_ids"
        for scode in syn_ids:
            assert scode in valid_syn_codes, f"Condition {d['condition_id']} references invalid syndrome code: {scode}"

def test_hierarchical_many_to_many_mapping():
    # Fever (S001) + Cough (S021) should map to acute_febrile_illness, influenza_like_illness, upper_respiratory_infection, etc.
    mapped = syndrome_service.map_symptoms_to_syndromes(["S001", "S021"])
    assert "acute_febrile_illness" in mapped
    assert "upper_respiratory_infection" in mapped
    assert "influenza_like_illness" in mapped

    # Test multi-symptom mapping with names
    mapped_names = syndrome_service.map_symptoms_to_syndromes(["Fever", "Severe splitting headache", "Neck stiffness (Nuchal rigidity)"])
    assert "acute_febrile_illness" in mapped_names
    assert "meningeal_irritation" in mapped_names

def test_pharmacy_mapping():
    assert syndrome_service.map_drug_to_syndrome("antipyretic") == "acute_febrile_illness"
    assert syndrome_service.map_drug_to_syndrome("antidiarrheal") == "acute_watery_diarrhea"
    assert syndrome_service.map_drug_to_syndrome("antihistamine") == "upper_respiratory_infection"
    assert syndrome_service.map_drug_to_syndrome("bronchodilator") == "bronchospastic_obstructive"

def test_testing_mapping():
    assert syndrome_service.map_test_to_syndrome("rapid_antigen_influenza") == "influenza_like_illness"
    assert syndrome_service.map_test_to_syndrome("stool_culture_vibrio") == "acute_watery_diarrhea"
    assert syndrome_service.map_test_to_syndrome("rapid_dengue_ns1") == "febrile_arthritic"
    assert syndrome_service.map_test_to_syndrome("csf_viral_encephalitis") == "acute_encephalitic"

def test_source_reliability():
    assert syndrome_service.get_source_reliability("testing") == 0.95
    assert syndrome_service.get_source_reliability("doctor") == 0.90
    assert syndrome_service.get_source_reliability("clinic") == 0.88
    assert syndrome_service.get_source_reliability("wastewater") == 0.85
    assert syndrome_service.get_source_reliability("community") == 0.70

