import os
import json
from typing import Dict, List, Any

_CORE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "core"))
_SYNDROME_MASTER_PATH = os.path.join(_CORE_DIR, "syndrome_master.json")

def load_canonical_45_syndromes() -> List[Dict[str, Any]]:
    if os.path.exists(_SYNDROME_MASTER_PATH):
        with open(_SYNDROME_MASTER_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("syndromes", [])
    return []

# Canonical baseline relative frequencies (Domain-calibrated realistic epidemiological ratios)
BASE_SYNDROME_WEIGHTS = {
    # High-Frequency Respiratory & Febrile
    "upper_respiratory_infection": 0.160,
    "influenza_like_illness": 0.120,
    "acute_febrile_illness": 0.110,
    "lower_respiratory_illness": 0.085,
    "bronchospastic_obstructive": 0.055,
    "acute_otolaryngologic_suppurative": 0.040,
    "pediatric_croup_stridor": 0.030,
    "severe_acute_respiratory_infection": 0.025,
    
    # Enteric / Gastrointestinal
    "acute_watery_diarrhea": 0.080,
    "gastroenteritis_emetic": 0.050,
    "bloody_diarrhea_dysentery": 0.020,
    "febrile_enteric": 0.020,
    "acute_jaundice_hepatitic": 0.015,
    "severe_dehydration_shock": 0.012,

    # Vector-borne & Febrile
    "febrile_arthritic": 0.035,
    "acute_fever_rash": 0.025,
    "vector_malaria_paroxysmal": 0.020,
    "viral_hemorrhagic_fever": 0.005,
    "vector_lymphatic_filarial": 0.003,

    # Dermatological / Mucocutaneous
    "vesiculopustular_eruptive": 0.015,
    "oral_ulcerative_stomatitis": 0.012,
    "cutaneous_ulcerative_eschar": 0.004,
    "mucocutaneous_lymph_node": 0.004,

    # Cardiovascular / Systemic
    "acute_allergic_anaphylactic": 0.018,
    "acute_coronary_ischemic": 0.015,
    "acute_heart_failure_congestive": 0.012,
    "cardiac_arrhythmic_syncope": 0.010,
    "systemic_inflammatory_sepsis": 0.010,

    # Urologic / ENT / Renal
    "urinary_tract_infection_febrile": 0.025,
    "acute_ophthalmic_conjunctivitis": 0.020,
    "acute_kidney_injury_oliguria": 0.005,
    "acute_hemolytic_cytopenic": 0.003,

    # Neurological
    "meningeal_irritation": 0.006,
    "acute_encephalitic": 0.004,
    "acute_flaccid_paralysis": 0.002,
    "cranial_neuropathy_dysautonomia": 0.002,
    "foodborne_neurotoxic": 0.002,
    "zoonotic_rabies_encephalopathy": 0.001,

    # Pediatric / Zoonotic / Environmental
    "post_infectious_asthenia": 0.010,
    "unspecified_community_cluster": 0.008,
    "pediatric_malnutrition_wasting": 0.005,
    "zoonotic_leptospiral": 0.004,
    "environmental_heat_stroke": 0.004,
    "environmental_hypothermia_cold": 0.003,
    "chemical_toxic_inhalation": 0.002
}

def get_institution_syndrome_weights(institution_id: str) -> Dict[str, float]:
    """
    Computes non-IID normalized 45-syndrome baseline ratio distribution per institution profile.
    """
    base = BASE_SYNDROME_WEIGHTS.copy()

    if institution_id == "inst-a":
        # Urban: High volume, higher URI, ILI, asthma, allergic, cardiac
        base["upper_respiratory_infection"] *= 1.3
        base["influenza_like_illness"] *= 1.2
        base["bronchospastic_obstructive"] *= 1.4
        base["acute_allergic_anaphylactic"] *= 1.3
        base["acute_coronary_ischemic"] *= 1.3
        base["respiratory"] = 0.40
        base["gastrointestinal"] = 0.25
        base["fever_flu"] = 0.20
        base["other"] = 0.15

    elif institution_id == "inst-b":
        # Semi-Urban: Higher enteric / GI / diarrheal
        base["acute_watery_diarrhea"] *= 1.8
        base["gastroenteritis_emetic"] *= 1.7
        base["bloody_diarrhea_dysentery"] *= 1.6
        base["febrile_enteric"] *= 1.5
        base["acute_jaundice_hepatitic"] *= 1.5
        base["respiratory"] = 0.20
        base["gastrointestinal"] = 0.45
        base["fever_flu"] = 0.25
        base["other"] = 0.10

    elif institution_id == "inst-c":
        # Rural: Higher fever, vector-borne, malaria, febrile arthritic, zoonotic
        base["acute_febrile_illness"] *= 2.0
        base["vector_malaria_paroxysmal"] *= 2.2
        base["febrile_arthritic"] *= 1.8
        base["zoonotic_leptospiral"] *= 2.0
        base["pediatric_malnutrition_wasting"] *= 2.0
        base["respiratory"] = 0.15
        base["gastrointestinal"] = 0.15
        base["fever_flu"] = 0.55
        base["other"] = 0.15

    elif institution_id == "inst-d":
        # Mixed: Balanced seasonal transition
        base["acute_febrile_illness"] *= 1.1
        base["influenza_like_illness"] *= 1.1
        base["acute_watery_diarrhea"] *= 1.1
        base["respiratory"] = 0.30
        base["gastrointestinal"] = 0.30
        base["fever_flu"] = 0.25
        base["other"] = 0.15
    else:
        base["respiratory"] = 0.30
        base["gastrointestinal"] = 0.25
        base["fever_flu"] = 0.25
        base["other"] = 0.15

    # Normalize
    tot = sum(base.values())
    return {k: v / tot for k, v in base.items()}
