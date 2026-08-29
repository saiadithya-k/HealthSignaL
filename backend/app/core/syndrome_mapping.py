import os
import json
import yaml
from typing import Dict, List, Any, Optional

_CORE_DIR = os.path.dirname(__file__)
_SYNDROME_MASTER_PATH = os.path.join(_CORE_DIR, "syndrome_master.json")
_SYMPTOMS_MASTER_PATH = os.path.join(_CORE_DIR, "symptoms_master.json")
_DISEASE_REF_PATH = os.path.join(_CORE_DIR, "disease_reference.json")
_YAML_MAP_PATH = os.path.join(_CORE_DIR, "syndrome_map.yaml")

class SyndromeMappingService:
    """
    Core ontology service for HealthSignal.
    Manages:
    - 45 Standardized Syndrome Categories
    - 257 Standardized Symptoms (many-to-many associations)
    - 100+ Disease/Condition Reference Profiles (non-diagnostic simulation knowledge)
    - Source Reliability & Early Warning Weights
    """

    def __init__(self):
        self._syndromes_data: Dict[str, Any] = {}
        self._symptoms_data: Dict[str, Any] = {}
        self._disease_data: Dict[str, Any] = {}
        self._yaml_config: Dict[str, Any] = {}
        self._load_all()

    def _load_all(self):
        # 1. Load 45 Syndromes Master
        if os.path.exists(_SYNDROME_MASTER_PATH):
            with open(_SYNDROME_MASTER_PATH, "r", encoding="utf-8") as f:
                self._syndromes_data = json.load(f) or {}

        # 2. Load 257 Symptoms Master
        if os.path.exists(_SYMPTOMS_MASTER_PATH):
            with open(_SYMPTOMS_MASTER_PATH, "r", encoding="utf-8") as f:
                self._symptoms_data = json.load(f) or {}

        # 3. Load 100+ Disease Reference
        if os.path.exists(_DISEASE_REF_PATH):
            with open(_DISEASE_REF_PATH, "r", encoding="utf-8") as f:
                self._disease_data = json.load(f) or {}

        # 4. Load YAML mappings & reliability
        if os.path.exists(_YAML_MAP_PATH):
            with open(_YAML_MAP_PATH, "r", encoding="utf-8") as f:
                self._yaml_config = yaml.safe_load(f) or {}

    @property
    def syndromes(self) -> List[Dict[str, Any]]:
        """Returns the list of 45 standardized syndromes."""
        return self._syndromes_data.get("syndromes", [])

    @property
    def symptoms(self) -> List[Dict[str, Any]]:
        """Returns the list of 257 standardized symptoms."""
        return self._symptoms_data.get("symptoms", [])

    @property
    def diseases(self) -> List[Dict[str, Any]]:
        """Returns the 100+ condition reference catalog."""
        return self._disease_data.get("conditions", [])

    @property
    def source_reliability(self) -> Dict[str, Any]:
        return self._yaml_config.get("source_reliability", {})

    @property
    def pharmacy_mapping(self) -> Dict[str, str]:
        return self._yaml_config.get("pharmacy_mapping", {})

    @property
    def testing_mapping(self) -> Dict[str, str]:
        return self._yaml_config.get("testing_mapping", {})

    def map_symptoms_to_syndromes(self, symptom_ids_or_names: List[str]) -> List[str]:
        """
        Hierarchical and many-to-many mapping:
        Maps a list of symptom IDs (e.g. S001), symptom names, or symptom aliases
        to one or more of the 45 standardized syndromes.
        """
        syndrome_set = set()
        symptom_list = self.symptoms

        # Create quick lookup dicts
        by_id = {s["symptom_id"]: s for s in symptom_list}
        by_name = {s["name"].lower(): s for s in symptom_list}
        
        # Also build alias lookup
        by_alias = {}
        for s in symptom_list:
            for alias in s.get("aliases", []):
                alias_clean = alias.strip().lower()
                if alias_clean not in by_alias:
                    by_alias[alias_clean] = s

        for item in symptom_ids_or_names:
            item_clean = str(item).strip()
            
            # 1. Match by symptom ID
            if item_clean in by_id:
                for syn in by_id[item_clean].get("associated_syndromes", []):
                    syndrome_set.add(syn)
                continue

            # 2. Match by symptom name
            item_lower = item_clean.lower()
            matched = False
            for name, sinfo in by_name.items():
                if name == item_lower or item_lower in name or name in item_lower:
                    for syn in sinfo.get("associated_syndromes", []):
                        syndrome_set.add(syn)
                    matched = True
                    break

            # 3. Match by symptom alias
            if not matched:
                for alias_key, sinfo in by_alias.items():
                    if alias_key == item_lower or item_lower in alias_key or alias_key in item_lower:
                        for syn in sinfo.get("associated_syndromes", []):
                            syndrome_set.add(syn)
                        matched = True
                        break

            if not matched:
                syndrome_set.add("unspecified_community_cluster")

        return sorted(list(syndrome_set)) if syndrome_set else ["unspecified_community_cluster"]

    def map_drug_to_syndrome(self, drug_category: str) -> str:
        """Maps pharmacy dispensing drug categories to an aggregate syndrome."""
        clean_cat = str(drug_category).strip().lower()
        return self.pharmacy_mapping.get(clean_cat, "unspecified_community_cluster")

    def map_test_to_syndrome(self, test_type: str) -> str:
        """Maps lab diagnostic test types to a proxy syndrome."""
        clean_test = str(test_type).strip().lower()
        return self.testing_mapping.get(clean_test, "unspecified_community_cluster")

    def get_source_reliability(self, source_name: str) -> float:
        """Returns the reliability weight score (0.0 - 1.0) for a given data source stream."""
        source_key = str(source_name).strip().lower()
        info = self.source_reliability.get(source_key, {})
        return float(info.get("score", 0.70))

    def get_source_lead_lag_days(self, source_name: str) -> int:
        """Returns the typical temporal lead/lag offset in days for a data stream."""
        source_key = str(source_name).strip().lower()
        offsets = {
            "community": 0,
            "pharmacy": 0,
            "doctor": 1,
            "clinic": 2,
            "testing": 2,
            "emergency": 1,
            "absenteeism": 1,
            "wastewater": -4
        }
        return offsets.get(source_key, 0)

    def get_drugs_for_syndromes(self, syndrome_codes: List[str]) -> List[str]:
        """Configuration-driven reverse lookup: Finds all pharmacy drug categories that map to given syndromes."""
        syn_set = set(str(s).strip().lower() for s in syndrome_codes)
        matched_drugs = []
        for drug, mapped_syn in self.pharmacy_mapping.items():
            if str(mapped_syn).strip().lower() in syn_set:
                matched_drugs.append(drug)
        return matched_drugs if matched_drugs else ["antipyretic"]

    def get_tests_for_syndromes(self, syndrome_codes: List[str]) -> List[str]:
        """Configuration-driven reverse lookup: Finds all diagnostic test types that map to given syndromes."""
        syn_set = set(str(s).strip().lower() for s in syndrome_codes)
        matched_tests = []
        for test, mapped_syn in self.testing_mapping.items():
            if str(mapped_syn).strip().lower() in syn_set:
                matched_tests.append(test)
        return matched_tests if matched_tests else ["rapid_antigen_influenza"]


    def get_syndrome_master_list(self) -> List[Dict[str, Any]]:
        """Returns the 45 standardized syndrome master list."""
        return self.syndromes

    def get_symptom_master_list(self) -> List[Dict[str, Any]]:
        """Returns the 257 standardized symptom master list."""
        return self.symptoms

    def get_disease_reference_catalog(self) -> List[Dict[str, Any]]:
        """Returns the 100+ disease/condition reference profiles."""
        return self.diseases

    def get_condition_by_id(self, condition_id: str) -> Optional[Dict[str, Any]]:
        """Lookup disease/condition by condition_id (e.g. C002, D002)."""
        clean_id = str(condition_id).strip().upper()
        for d in self.diseases:
            if (d.get("condition_id") or "").upper() == clean_id or (d.get("disease_id") or "").upper() == clean_id:
                return d
        return None

    def get_condition_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Lookup disease/condition by name or keyword."""
        clean_name = str(name).strip().lower()
        for d in self.diseases:
            d_name = (d.get("condition_name") or d.get("name") or "").lower()
            if clean_name in d_name or d_name in clean_name:
                return d
        return None

    def map_syndrome_to_coarse_category(self, syndrome_code: str) -> str:
        """Maps any of the 45 granular syndrome codes to the 4 coarse demand forecasting categories."""
        code = str(syndrome_code).strip().lower()
        if code in [
            "upper_respiratory_infection", "lower_respiratory_illness", "influenza_like_illness",
            "severe_acute_respiratory_infection", "bronchospastic_obstructive", "pediatric_croup_stridor",
            "chemical_toxic_inhalation"
        ]:
            return "respiratory"
        elif code in [
            "acute_watery_diarrhea", "bloody_diarrhea_dysentery", "gastroenteritis_emetic",
            "febrile_enteric", "acute_jaundice_hepatitic", "esophageal_food_impaction"
        ]:
            return "gastrointestinal"
        elif code in [
            "acute_febrile_illness", "febrile_arthritic", "acute_fever_rash",
            "vector_malaria_paroxysmal", "systemic_inflammatory_sepsis", "viral_hemorrhagic_fever",
            "cutaneous_ulcerative_eschar", "zoonotic_leptospiral", "vector_lymphatic_filarial"
        ]:
            return "fever_flu"
        else:
            return "other"

    def generate_symptom_combination_for_condition(
        self,
        condition_id: str,
        rng: Optional[Any] = None,
        primary_prob: float = 0.85,
        secondary_prob: float = 0.55,
        rare_prob: float = 0.25
    ) -> Dict[str, Any]:
        """
        Probabilistically generates a realistic combination of symptoms from a condition's profile.
        Primary symptoms have high probability, secondary medium, and rare lower probability.
        Returns a dict with selected symptom IDs, severity, and mapped syndromes.
        """
        import random
        cond = self.get_condition_by_id(condition_id)
        if not cond:
            raise ValueError(f"Unknown condition ID '{condition_id}' not found in disease reference catalog.")

        sym_list = list(cond.get("symptom_ids") or cond.get("key_symptoms") or [])
        if not sym_list:
            sym_list = ["S001", "S006"]

        n = len(sym_list)
        # Tier partitioning
        n_prim = max(1, n // 3)
        n_sec = max(1, (n - n_prim) // 2) if n > n_prim else 0
        
        primary_syms = sym_list[:n_prim]
        secondary_syms = sym_list[n_prim:n_prim + n_sec]
        rare_syms = sym_list[n_prim + n_sec:]

        chosen = []

        def coin_flip(p: float) -> bool:
            if rng is not None and hasattr(rng, "uniform"):
                return bool(rng.uniform(0.0, 1.0) < p)
            return bool(random.random() < p)

        for s in primary_syms:
            if coin_flip(primary_prob):
                chosen.append(s)

        for s in secondary_syms:
            if coin_flip(secondary_prob):
                chosen.append(s)

        for s in rare_syms:
            if coin_flip(rare_prob):
                chosen.append(s)

        # Ensure at least 1 symptom is chosen
        if not chosen:
            chosen.append(primary_syms[0])

        mapped_syndromes = self.map_symptoms_to_syndromes(chosen)
        # Also include condition's primary syndrome for alignment
        if cond.get("primary_syndrome") and cond["primary_syndrome"] not in mapped_syndromes:
            mapped_syndromes.append(cond["primary_syndrome"])

        severity_raw = cond.get("typical_severity", "mild_to_moderate")
        severity_val = "severe" if "severe" in severity_raw else "moderate" if "moderate" in severity_raw else "mild"

        return {
            "condition_id": cond["condition_id"],
            "condition_name": cond["condition_name"],
            "symptoms": chosen,
            "syndromes": sorted(list(set(mapped_syndromes))),
            "severity": severity_val,
            "category": cond.get("category", "General Clinical"),
            "transmission_pattern": cond.get("transmission_pattern", "respiratory_droplet"),
            "associated_signal_sources": cond.get("associated_signal_sources", ["community", "clinic"])
        }

# Singleton service instance
syndrome_service = SyndromeMappingService()
