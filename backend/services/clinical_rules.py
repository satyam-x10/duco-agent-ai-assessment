"""Clinical medical necessity and CPT/ICD-10 rule lookup service."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional, Tuple, Dict, Any

BASE_DIR = Path(__file__).resolve().parent.parent


class ClinicalRulesService:
    def __init__(self, mock_rules_path: Optional[Path] = None):
        self.mock_rules_path = mock_rules_path or (BASE_DIR / "mock_data" / "clinical_rules.json")
        self._rules: Dict[str, Any] = {}
        self.load_rules()

    def load_rules(self) -> None:
        if self.mock_rules_path.exists():
            with open(self.mock_rules_path, "r", encoding="utf-8") as f:
                self._rules = json.load(f)

    @property
    def version(self) -> str:
        return self._rules.get("version", "2026.1-demo")

    def get_cpt(self, code: str) -> Optional[dict]:
        return self._rules.get("cpt", {}).get(code.strip())

    def get_all_cpt_catalog(self) -> Dict[str, dict]:
        """Returns the entire dictionary of CPT rules and descriptions."""
        return self._rules.get("cpt", {})

    def get_icd10(self, code: str) -> Optional[dict]:
        return self._rules.get("icd10", {}).get(code.strip().upper())

    def supports(self, cpt_code: str, diagnosis_codes: list[str]) -> Tuple[Optional[bool], str]:
        rule = self.get_cpt(cpt_code)
        if not rule:
            return None, f"CPT {cpt_code} is absent from clinical rule catalog {self.version}; manual review required."
        prefixes = rule.get("supporting_diagnosis_prefixes", [])
        if not prefixes:
            return True, "No diagnosis-prefix restriction configured."
        if not diagnosis_codes:
            return None, f"No diagnosis supplied for CPT {cpt_code}; medical necessity is indeterminate."
        normalized = [code.upper() for code in diagnosis_codes]
        if any(code.startswith(prefix.upper()) for code in normalized for prefix in prefixes):
            return True, "At least one diagnosis matches the configured support rule."
        return False, (
            f"CPT {cpt_code} is not medically necessary under the mock rule because it lacks a supporting diagnosis. "
            f"Expected one of: {', '.join(prefixes)} (catalog {self.version})."
        )
