import pytest
from app.core.syndrome_mapping import syndrome_service

def test_symptom_master_list_257():
    symptoms = syndrome_service.symptoms
    assert len(symptoms) == 257, f"Expected exactly 257 symptoms, got {len(symptoms)}"
    first_sym = symptoms[0]
    assert first_sym["symptom_id"] == "S001"
    assert first_sym["name"] == "Fever"
    assert "acute_febrile_illness" in first_sym["associated_syndromes"]

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
    d_map = {d["disease_id"]: d for d in diseases}
    assert "D001" in d_map
    assert d_map["D001"]["name"] == "Common Cold (Rhinovirus/Coronavirus)"
    assert d_map["D001"]["primary_syndrome"] == "upper_respiratory_infection"

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
