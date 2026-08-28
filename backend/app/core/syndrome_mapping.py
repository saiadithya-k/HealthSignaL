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
        Maps a list of symptom IDs (e.g. S001) or symptom names to one or more of the 45 standardized syndromes.
        """
        syndrome_set = set()
        symptom_list = self.symptoms

        # Create quick lookup dicts
        by_id = {s["symptom_id"]: s for s in symptom_list}
        by_name = {s["name"].lower(): s for s in symptom_list}

        for item in symptom_ids_or_names:
            item_clean = str(item).strip()
            
            # Match by symptom ID
            if item_clean in by_id:
                for syn in by_id[item_clean].get("associated_syndromes", []):
                    syndrome_set.add(syn)
                continue

            # Match by symptom name
            item_lower = item_clean.lower()
            matched = False
            for name, sinfo in by_name.items():
                if name == item_lower or item_lower in name:
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

    def get_syndrome_master_list(self) -> List[Dict[str, Any]]:
        """Returns the 45 standardized syndrome master list."""
        return self.syndromes

    def get_symptom_master_list(self) -> List[Dict[str, Any]]:
        """Returns the 257 standardized symptom master list."""
        return self.symptoms

    def get_disease_reference_catalog(self) -> List[Dict[str, Any]]:
        """Returns the 100+ disease/condition reference profiles."""
        return self.diseases

# Singleton service instance
syndrome_service = SyndromeMappingService()
