import pandas as pd
from typing import List
from app.data_generation.schemas import (
    PROHIBITED_IDENTIFYING_FIELDS,
    REQUIRED_DATA_COLUMNS,
    ValidationResult
)

class DatasetValidator:
    """Validates aggregate time-series datasets against schema requirements and privacy boundaries."""

    @staticmethod
    def validate_dataframe(df: pd.DataFrame, institution_id: str) -> ValidationResult:
        errors = []
        warnings = []
        prohibited_found = []

        if df is None or df.empty:
            return ValidationResult(
                is_valid=False,
                institution_id=institution_id,
                total_records=0,
                missing_values_count=0,
                missing_rate_pct=100.0,
                errors=["Dataset is empty or None"]
            )

        # 1. Privacy Boundary Check (CRITICAL)
        col_names_lower = [str(col).lower() for col in df.columns]
        for col in col_names_lower:
            if col in PROHIBITED_IDENTIFYING_FIELDS or any(p_field in col for p_field in ["patient", "mrn", "ssn", "dob", "address"]):
                prohibited_found.append(col)
                errors.append(f"PRIVACY VIOLATION: Prohibited identifying column detected: '{col}'")

        # 2. Required Columns Check
        for req_col in REQUIRED_DATA_COLUMNS:
            if req_col not in df.columns:
                errors.append(f"Schema error: Missing required column '{req_col}'")

        # 3. Institution Isolation Check
        if "institution_id" in df.columns:
            unique_insts = df["institution_id"].unique()
            if len(unique_insts) > 1 or (len(unique_insts) == 1 and unique_insts[0] != institution_id):
                errors.append(f"Institution Isolation Error: Expected only '{institution_id}', found {list(unique_insts)}")

        # 4. Range and Data Type Checks
        if "service_count" in df.columns:
            if (df["service_count"] < 0).any():
                errors.append("Range Error: Negative service_count values detected")

        if "data_completeness" in df.columns:
            if ((df["data_completeness"] < 0.0) | (df["data_completeness"] > 1.0)).any():
                errors.append("Range Error: data_completeness must be between 0.0 and 1.0")

        # 5. Missing Values Check
        total_cells = df.size
        missing_count = int(df.isnull().sum().sum())
        missing_pct = (missing_count / total_cells * 100.0) if total_cells > 0 else 0.0

        if missing_pct > 15.0:
            warnings.append(f"High missingness warning: {missing_pct:.2f}% of cells are missing")

        # 6. Duplicate Observations Check
        if {"date", "institution_id", "syndrome_category"}.issubset(df.columns):
            duplicates = df.duplicated(subset=["date", "institution_id", "syndrome_category"]).sum()
            if duplicates > 0:
                errors.append(f"Duplicate Error: Found {duplicates} duplicate (date, institution_id, syndrome_category) rows")

        is_valid = (len(errors) == 0)

        return ValidationResult(
            is_valid=is_valid,
            institution_id=institution_id,
            total_records=len(df),
            missing_values_count=missing_count,
            missing_rate_pct=round(missing_pct, 2),
            prohibited_fields_found=prohibited_found,
            errors=errors,
            warnings=warnings
        )
